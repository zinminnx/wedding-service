import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from django.conf import settings


GRAPH_BASE = "https://graph.microsoft.com/v1.0"
TOKEN_BASE = "https://login.microsoftonline.com"
MAX_SIMPLE_UPLOAD = 250 * 1024 * 1024


class GraphConfigurationError(RuntimeError):
    pass


class GraphAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class GraphConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    drive_id: str
    root_folder: str
    timeout: int

    @property
    def complete(self):
        return bool(self.tenant_id and self.client_id and self.client_secret and self.drive_id)

    @property
    def missing(self):
        values = {
            "GRAPH_TENANT_ID": self.tenant_id,
            "GRAPH_CLIENT_ID": self.client_id,
            "GRAPH_CLIENT_SECRET": self.client_secret,
            "GRAPH_DRIVE_ID": self.drive_id,
        }
        return [name for name, value in values.items() if not value]


def get_graph_config(*, drive_id_override=""):
    return GraphConfig(
        tenant_id=getattr(settings, "GRAPH_TENANT_ID", "") or "",
        client_id=getattr(settings, "GRAPH_CLIENT_ID", "") or "",
        client_secret=getattr(settings, "GRAPH_CLIENT_SECRET", "") or "",
        drive_id=(drive_id_override or getattr(settings, "GRAPH_DRIVE_ID", "") or "").strip(),
        root_folder=(getattr(settings, "GRAPH_ROOT_FOLDER", "EverVow") or "EverVow").strip(" /"),
        timeout=int(getattr(settings, "GRAPH_TIMEOUT_SECONDS", 20)),
    )


class OneDriveGraphClient:
    """Minimal app-only Microsoft Graph client.

    Client secrets and bearer tokens are never persisted in the database.
    The access token is cached only in this Python process until shortly before expiry.
    """

    def __init__(self, config=None):
        self.config = config or get_graph_config()
        if not self.config.complete:
            raise GraphConfigurationError(
                "OneDrive is not configured. Missing: " + ", ".join(self.config.missing)
            )
        self._access_token = None
        self._token_expires_at = 0

    def _token(self):
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token
        token_url = f"{TOKEN_BASE}/{urllib.parse.quote(self.config.tenant_id, safe='')}/oauth2/v2.0/token"
        body = urllib.parse.urlencode(
            {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            token_url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise GraphAPIError(f"Microsoft token request failed with HTTP {exc.code}.") from exc
        except OSError as exc:
            raise GraphAPIError("Microsoft token request could not be reached.") from exc
        token = payload.get("access_token")
        if not token:
            raise GraphAPIError("Microsoft token response did not contain an access token.")
        self._access_token = token
        self._token_expires_at = time.time() + int(payload.get("expires_in", 3600))
        return token

    def _json_request(self, method, path, payload=None):
        url = path if path.startswith("http") else GRAPH_BASE + path
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._token()}",
            "Accept": "application/json",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except urllib.error.HTTPError as exc:
            raise GraphAPIError(f"Microsoft Graph request failed with HTTP {exc.code}.") from exc
        except OSError as exc:
            raise GraphAPIError("Microsoft Graph could not be reached.") from exc

    def health_check(self):
        return self._json_request("GET", f"/drives/{urllib.parse.quote(self.config.drive_id, safe='')}")

    def _root_item(self):
        return self._json_request("GET", f"/drives/{urllib.parse.quote(self.config.drive_id, safe='')}/root")

    def get_item_by_path(self, remote_path):
        clean_path = str(remote_path or "").replace("\\", "/").strip("/")
        if not clean_path:
            return self._root_item()
        encoded_path = urllib.parse.quote(clean_path, safe="/")
        return self._json_request(
            "GET",
            f"/drives/{urllib.parse.quote(self.config.drive_id, safe='')}/root:/{encoded_path}",
        )

    def rename_item(self, item_id, new_name):
        if not item_id:
            raise GraphAPIError("OneDrive item ID is required.")
        clean_name = str(new_name or "").strip(" /\\")
        if not clean_name or "/" in clean_name or "\\" in clean_name:
            raise GraphAPIError("OneDrive rename requires one folder/file name, not a path.")
        return self._json_request(
            "PATCH",
            f"/drives/{urllib.parse.quote(self.config.drive_id, safe='')}/items/{urllib.parse.quote(item_id, safe='')}",
            {"name": clean_name},
        )

    def ensure_folder(self, folder_path):
        segments = [part for part in folder_path.replace("\\", "/").split("/") if part]
        parent = self._root_item()
        for segment in segments:
            parent_id = parent.get("id")
            if not parent_id:
                raise GraphAPIError("OneDrive folder lookup returned no item ID.")
            encoded = urllib.parse.quote(segment, safe="")
            lookup_path = (
                f"/drives/{urllib.parse.quote(self.config.drive_id, safe='')}/items/"
                f"{urllib.parse.quote(parent_id, safe='')}:/{encoded}"
            )
            try:
                parent = self._json_request("GET", lookup_path)
                continue
            except GraphAPIError:
                pass
            parent = self._json_request(
                "POST",
                f"/drives/{urllib.parse.quote(self.config.drive_id, safe='')}/items/"
                f"{urllib.parse.quote(parent_id, safe='')}/children",
                {
                    "name": segment,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "fail",
                },
            )
        return parent

    def upload_bytes(self, remote_path, content, content_type="application/octet-stream"):
        if len(content) > MAX_SIMPLE_UPLOAD:
            raise GraphAPIError("This foundation supports files up to 250 MB per simple upload.")
        clean_path = remote_path.replace("\\", "/").strip("/")
        if not clean_path:
            raise GraphAPIError("Remote path is required.")
        folder_path = clean_path.rsplit("/", 1)[0] if "/" in clean_path else ""
        if folder_path:
            self.ensure_folder(folder_path)
        encoded_path = urllib.parse.quote(clean_path, safe="/")
        url = (
            f"{GRAPH_BASE}/drives/{urllib.parse.quote(self.config.drive_id, safe='')}/"
            f"root:/{encoded_path}:/content"
        )
        request = urllib.request.Request(
            url,
            data=content,
            method="PUT",
            headers={
                "Authorization": f"Bearer {self._token()}",
                "Content-Type": content_type or "application/octet-stream",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise GraphAPIError(f"OneDrive upload failed with HTTP {exc.code}.") from exc
        except OSError as exc:
            raise GraphAPIError("OneDrive upload could not reach Microsoft Graph.") from exc

    def download_bytes(self, item_id):
        url = (
            f"{GRAPH_BASE}/drives/{urllib.parse.quote(self.config.drive_id, safe='')}/items/"
            f"{urllib.parse.quote(item_id, safe='')}/content"
        )
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise GraphAPIError(f"OneDrive download failed with HTTP {exc.code}.") from exc
        except OSError as exc:
            raise GraphAPIError("OneDrive download could not reach Microsoft Graph.") from exc

    def download_thumbnail_bytes(self, item_id, size="small"):
        safe_size = size if size in {"small", "medium", "large"} else "small"
        url = (
            f"{GRAPH_BASE}/drives/{urllib.parse.quote(self.config.drive_id, safe='')}/items/"
            f"{urllib.parse.quote(item_id, safe='')}/thumbnails/0/{safe_size}/content"
        )
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise GraphAPIError(f"OneDrive thumbnail download failed with HTTP {exc.code}.") from exc
        except OSError as exc:
            raise GraphAPIError("OneDrive thumbnail download could not reach Microsoft Graph.") from exc

    def delete_item(self, item_id):
        url = (
            f"{GRAPH_BASE}/drives/{urllib.parse.quote(self.config.drive_id, safe='')}/items/"
            f"{urllib.parse.quote(item_id, safe='')}"
        )
        request = urllib.request.Request(
            url,
            method="DELETE",
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout):
                return True
        except urllib.error.HTTPError as exc:
            raise GraphAPIError(f"OneDrive delete failed with HTTP {exc.code}.") from exc
        except OSError as exc:
            raise GraphAPIError("OneDrive delete could not reach Microsoft Graph.") from exc
