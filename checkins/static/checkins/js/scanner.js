(function () {
    "use strict";

    const root = document.querySelector(".scanner-page");
    if (!root) return;

    const video = document.getElementById("qrVideo");
    const startButton = document.getElementById("startCamera");
    const stopButton = document.getElementById("stopCamera");
    const switchButton = document.getElementById("switchCamera");
    const status = document.getElementById("cameraStatus");
    const placeholder = document.getElementById("cameraPlaceholder");
    const hint = document.getElementById("scannerHint");
    const passPrefix = root.dataset.passPrefix || "/reception/pass/";

    let stream = null;
    let detector = null;
    let animationId = null;
    let currentFacingMode = "environment";
    let detecting = false;
    let locked = false;

    function setStatus(text, state) {
        status.textContent = text;
        status.dataset.state = state || "";
    }

    function stopCamera() {
        if (animationId) cancelAnimationFrame(animationId);
        animationId = null;
        if (stream) stream.getTracks().forEach((track) => track.stop());
        stream = null;
        video.srcObject = null;
        placeholder.hidden = false;
        stopButton.disabled = true;
        switchButton.disabled = true;
        startButton.disabled = false;
        setStatus("Camera off", "idle");
    }

    function extractToken(rawValue) {
        const value = String(rawValue || "").trim();
        if (!value) return "";

        let candidate = value;
        const marker = "/reception/pass/";
        if (candidate.includes(marker)) {
            try {
                const parsed = new URL(candidate, window.location.origin);
                candidate = parsed.pathname.split(marker)[1].split("/")[0];
            } catch (error) {
                candidate = candidate.split(marker)[1].split("/")[0];
            }
        }

        return /^[A-Za-z0-9_-]+$/.test(candidate) ? candidate : "";
    }

    function openPass(rawValue) {
        if (locked) return;
        const token = extractToken(rawValue);
        if (!token) {
            setStatus("Wrong QR", "error");
            hint.textContent = "This QR is not an EverAfter entrance pass. Keep scanning.";
            return;
        }

        locked = true;
        setStatus("Pass found", "success");
        hint.textContent = "Opening reception pass...";
        stopCamera();
        window.location.assign(passPrefix + encodeURIComponent(token) + "/");
    }

    async function detectLoop() {
        if (!stream || !detector || locked) return;
        if (!detecting && video.readyState >= 2) {
            detecting = true;
            try {
                const codes = await detector.detect(video);
                if (codes && codes.length) {
                    openPass(codes[0].rawValue);
                }
            } catch (error) {
                // Some browsers throw while a frame is changing. Continue scanning.
            } finally {
                detecting = false;
            }
        }
        animationId = requestAnimationFrame(detectLoop);
    }

    async function startCamera() {
        locked = false;

        if (!window.isSecureContext) {
            setStatus("HTTPS required", "error");
            hint.textContent = "Camera access is blocked on an insecure HTTP address. Use the HTTPS live domain, or use the manual fallback below.";
            return;
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setStatus("Unsupported", "error");
            hint.textContent = "This browser cannot access the camera. Use Chrome/Edge/Safari on a modern phone or use the manual fallback.";
            return;
        }

        if (!("BarcodeDetector" in window)) {
            setStatus("Scanner unsupported", "error");
            hint.textContent = "This browser has camera access but no built-in QR detector. Use a recent Chrome/Edge browser or the manual fallback.";
            return;
        }

        try {
            const formats = await window.BarcodeDetector.getSupportedFormats();
            if (!formats.includes("qr_code")) throw new Error("QR format unsupported");
            detector = new window.BarcodeDetector({ formats: ["qr_code"] });

            if (stream) stopCamera();
            setStatus("Starting...", "working");

            stream = await navigator.mediaDevices.getUserMedia({
                audio: false,
                video: {
                    facingMode: { ideal: currentFacingMode },
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });
            video.srcObject = stream;
            await video.play();
            placeholder.hidden = true;
            startButton.disabled = true;
            stopButton.disabled = false;
            switchButton.disabled = false;
            setStatus("Scanning", "success");
            hint.textContent = "Hold the QR inside the frame. A valid pass opens automatically.";
            detectLoop();
        } catch (error) {
            stopCamera();
            setStatus("Camera blocked", "error");
            hint.textContent = "Camera permission was denied or unavailable. Allow camera permission in the browser, or use the manual fallback.";
        }
    }

    startButton.addEventListener("click", startCamera);
    stopButton.addEventListener("click", stopCamera);
    switchButton.addEventListener("click", async function () {
        currentFacingMode = currentFacingMode === "environment" ? "user" : "environment";
        stopCamera();
        await startCamera();
    });

    document.addEventListener("visibilitychange", function () {
        if (document.hidden && stream) stopCamera();
    });
    window.addEventListener("beforeunload", stopCamera);
})();
