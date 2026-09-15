from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin

AGENT_VERSION = "12.3.0"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def require_runtime_packages():
    try:
        import requests
    except ImportError as exc:
        raise SystemExit("Missing 'requests'. Run install_agent.ps1 first.") from exc
    return requests


def list_printers() -> int:
    if platform.system() != "Windows":
        print("Printer discovery is supported on Windows only.")
        return 1
    try:
        import win32print
    except ImportError:
        print("pywin32 is not installed. Run install_agent.ps1 first.")
        return 1
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    printers = win32print.EnumPrinters(flags)
    default = win32print.GetDefaultPrinter()
    print(f"Default printer: {default}")
    for item in printers:
        name = item[2]
        marker = "*" if name == default else " "
        print(f"{marker} {name}")
    return 0


def _fit_box(image_size, page_size, mode, image_dpi, printer_dpi):
    iw, ih = image_size
    pw, ph = page_size
    if iw <= 0 or ih <= 0:
        raise ValueError("Invalid image dimensions.")

    if mode == "ORIGINAL":
        dpi_x = float(image_dpi[0] or 300)
        dpi_y = float(image_dpi[1] or 300)
        target_w = max(1, int(iw * float(printer_dpi[0]) / dpi_x))
        target_h = max(1, int(ih * float(printer_dpi[1]) / dpi_y))
        scale = min(1.0, pw / target_w, ph / target_h)
        width = int(target_w * scale)
        height = int(target_h * scale)
    else:
        scale = min(pw / iw, ph / ih) if mode == "FIT" else max(pw / iw, ph / ih)
        width = max(1, int(iw * scale))
        height = max(1, int(ih * scale))

    left = int((pw - width) / 2)
    top = int((ph - height) / 2)
    return left, top, left + width, top + height


def print_image_windows(path: Path, printer_name: str, copies: int, fit_mode: str) -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Physical printing is supported by this agent on Windows only.")
    try:
        import win32con
        import win32print
        import win32ui
        from PIL import Image, ImageOps, ImageWin
    except ImportError as exc:
        raise RuntimeError("Pillow/pywin32 are missing. Run install_agent.ps1.") from exc

    printer = printer_name.strip() or win32print.GetDefaultPrinter()
    image = Image.open(path)
    image = ImageOps.exif_transpose(image).convert("RGB")
    image_dpi = image.info.get("dpi") or (300, 300)

    dc = win32ui.CreateDC()
    dc.CreatePrinterDC(printer)
    try:
        printable_w = dc.GetDeviceCaps(win32con.HORZRES)
        printable_h = dc.GetDeviceCaps(win32con.VERTRES)
        dpi_x = dc.GetDeviceCaps(win32con.LOGPIXELSX)
        dpi_y = dc.GetDeviceCaps(win32con.LOGPIXELSY)

        # Rotate to the orientation that uses more of the current printer page.
        page_landscape = printable_w > printable_h
        image_landscape = image.width > image.height
        if page_landscape != image_landscape:
            image = image.rotate(90, expand=True)

        mode = fit_mode if fit_mode in {"FIT", "FILL", "ORIGINAL"} else "FIT"
        if mode == "FILL":
            page_ratio = printable_w / max(printable_h, 1)
            image_ratio = image.width / max(image.height, 1)
            if image_ratio > page_ratio:
                new_w = max(1, int(image.height * page_ratio))
                left = max(0, int((image.width - new_w) / 2))
                image = image.crop((left, 0, left + new_w, image.height))
            elif image_ratio < page_ratio:
                new_h = max(1, int(image.width / page_ratio))
                top = max(0, int((image.height - new_h) / 2))
                image = image.crop((0, top, image.width, top + new_h))

        box = _fit_box(
            image.size,
            (printable_w, printable_h),
            mode,
            image_dpi,
            (dpi_x, dpi_y),
        )
        left, top, right, bottom = box
        draw_box = (left, top, right, bottom)
        dib = ImageWin.Dib(image)

        dc.StartDoc(path.name)
        try:
            for _ in range(max(1, min(int(copies), 99))):
                dc.StartPage()
                dib.draw(dc.GetHandleOutput(), draw_box)
                dc.EndPage()
        finally:
            dc.EndDoc()
    finally:
        dc.DeleteDC()


class EverVowAgent:
    def __init__(self, base_url: str, token: str, printer_name: str, poll_seconds: float, timeout: float, dry_run: bool):
        self.requests = require_runtime_packages()
        self.base_url = base_url.rstrip("/") + "/"
        self.token = token
        self.printer_name = printer_name
        self.poll_seconds = max(1.0, poll_seconds)
        self.timeout = max(5.0, timeout)
        self.dry_run = dry_run
        self.hostname = platform.node()[:120]
        self.session = self.requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "User-Agent": f"EverVow-Print-Agent/{AGENT_VERSION}",
        })

    def url(self, path: str) -> str:
        return urljoin(self.base_url, path.lstrip("/"))

    def api_post(self, path: str, payload: dict | None = None):
        response = self.session.post(self.url(path), json=payload or {}, timeout=self.timeout)
        try:
            data = response.json()
        except Exception:
            data = {"ok": False, "error": response.text[:500]}
        if response.status_code >= 400:
            raise RuntimeError(data.get("error") or f"HTTP {response.status_code}")
        return data

    def heartbeat_payload(self):
        return {
            "hostname": self.hostname,
            "printer_name": self.printer_name,
            "version": AGENT_VERSION,
        }

    def set_state(self, job_id: str, state: str, error: str = ""):
        return self.api_post(
            f"api/printing/agent/jobs/{job_id}/state/",
            {"state": state, "error": error[:500]},
        )

    def download_source(self, job: dict, target: Path):
        url = job.get("source_url") or self.url(f"api/printing/agent/jobs/{job['id']}/source/")
        response = self.session.get(url, stream=True, timeout=self.timeout)
        if response.status_code >= 400:
            try:
                message = response.json().get("error")
            except Exception:
                message = response.text[:300]
            raise RuntimeError(message or f"Source download failed: HTTP {response.status_code}")
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)

    def process(self, job: dict):
        job_id = job["id"]
        filename = Path(job.get("source_filename") or f"{job_id}.jpg").name
        suffix = Path(filename).suffix[:10] or ".img"
        with tempfile.TemporaryDirectory(prefix="everafter-print-") as temp_dir:
            source = Path(temp_dir) / f"{job_id}{suffix}"
            print(f"[{job_id}] downloading {filename} ...", flush=True)
            self.download_source(job, source)
            self.set_state(job_id, "printing")
            print(
                f"[{job_id}] printing {job.get('copies', 1)} copy/copies; "
                f"paper={job.get('paper_size')} fit={job.get('fit_mode')} "
                f"printer={self.printer_name or '<Windows default>'}",
                flush=True,
            )
            if self.dry_run:
                spool = Path(__file__).resolve().parent / "spool" / "dry-run"
                spool.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, spool / f"{job_id}{suffix}")
                print(f"[{job_id}] DRY RUN: saved source instead of printing.", flush=True)
            else:
                print_image_windows(
                    source,
                    self.printer_name,
                    int(job.get("copies") or 1),
                    str(job.get("fit_mode") or "FIT"),
                )
            self.set_state(job_id, "printed")
            print(f"[{job_id}] printed successfully.", flush=True)

    def run_once(self):
        payload = self.api_post("api/printing/agent/poll/", self.heartbeat_payload())
        job = payload.get("job")
        if not job:
            return False
        try:
            self.process(job)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            print(f"[{job.get('id')}] FAILED: {message}", file=sys.stderr, flush=True)
            try:
                self.set_state(job["id"], "failed", message)
            except Exception as state_exc:
                print(f"Could not report failure to server: {state_exc}", file=sys.stderr, flush=True)
        return True

    def run_forever(self):
        print(f"EverVow Local Print Agent {AGENT_VERSION}")
        print(f"Server:  {self.base_url}")
        print(f"Printer: {self.printer_name or '<Windows default printer>'}")
        print(f"Host:    {self.hostname}")
        print(f"Mode:    {'DRY RUN' if self.dry_run else 'PRINT'}")
        print("Press Ctrl+C to stop.\n")
        backoff = self.poll_seconds
        while True:
            try:
                had_job = self.run_once()
                backoff = self.poll_seconds
                if not had_job:
                    time.sleep(self.poll_seconds)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"Agent connection error: {exc}", file=sys.stderr, flush=True)
                time.sleep(min(backoff, 30.0))
                backoff = min(backoff * 1.8, 30.0)


def main() -> int:
    parser = argparse.ArgumentParser(description="EverVow Windows Local Print Agent")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent / "agent.env"))
    parser.add_argument("--once", action="store_true", help="Poll once, process at most one job, then exit.")
    parser.add_argument("--dry-run", action="store_true", help="Download/claim jobs but save them locally instead of printing.")
    parser.add_argument("--list-printers", action="store_true")
    args = parser.parse_args()

    if args.list_printers:
        return list_printers()

    load_env_file(Path(args.config))
    base_url = os.getenv("EVERAFTER_BASE_URL", "http://127.0.0.1:8000").strip()
    token = os.getenv("EVERAFTER_AGENT_TOKEN", "").strip()
    printer_name = os.getenv("EVERAFTER_PRINTER_NAME", "").strip()
    if not token:
        print("EVERAFTER_AGENT_TOKEN is missing. Create a Local Print Agent in EverVow and put the token in agent.env.", file=sys.stderr)
        return 2

    try:
        poll_seconds = float(os.getenv("EVERAFTER_POLL_SECONDS", "3"))
        timeout = float(os.getenv("EVERAFTER_REQUEST_TIMEOUT", "60"))
    except ValueError:
        print("Polling/timeout values in agent.env must be numbers.", file=sys.stderr)
        return 2

    agent = EverVowAgent(
        base_url=base_url,
        token=token,
        printer_name=printer_name,
        poll_seconds=poll_seconds,
        timeout=timeout,
        dry_run=args.dry_run or env_bool("EVERAFTER_DRY_RUN"),
    )
    try:
        if args.once:
            agent.run_once()
        else:
            agent.run_forever()
    except KeyboardInterrupt:
        print("\nAgent stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
