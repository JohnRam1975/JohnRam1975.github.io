"""Export portfolio HTML to full-bleed PDF (no white margins) via Chrome CDP."""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

try:
    import websocket
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client", "-q"])
    import websocket

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "index.html"
OUT = Path(r"C:\Users\Djohn\Temp\John-Ram-Portfolio.pdf")
PORT = 9334
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def wait_devtools(timeout: float = 20.0) -> str:
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1) as r:
                data = json.loads(r.read().decode())
                return data["webSocketDebuggerUrl"]
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.2)
    raise RuntimeError(f"DevTools not ready: {last_err}")


def recv_until(ws: websocket.WebSocket, wanted_id: int) -> dict:
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == wanted_id:
            return msg


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    uri = HTML.resolve().as_uri()

    proc = subprocess.Popen(
        [
            CHROME,
            f"--remote-debugging-port={PORT}",
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        browser_ws = wait_devtools()
        ws = websocket.create_connection(browser_ws, suppress_origin=True)

        req_id = 1
        ws.send(
            json.dumps(
                {
                    "id": req_id,
                    "method": "Target.createTarget",
                    "params": {"url": uri},
                }
            )
        )
        created = recv_until(ws, req_id)
        target_id = created["result"]["targetId"]
        ws.close()

        # Attach to page target
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=3) as r:
            pages = json.loads(r.read().decode())
        page = next(p for p in pages if p.get("id") == target_id)
        page_ws_url = page["webSocketDebuggerUrl"]
        ws = websocket.create_connection(page_ws_url, suppress_origin=True)

        req_id = 1

        def call(method: str, params: dict | None = None) -> dict:
            nonlocal req_id
            req_id += 1
            payload = {"id": req_id, "method": method}
            if params is not None:
                payload["params"] = params
            ws.send(json.dumps(payload))
            return recv_until(ws, req_id)

        call("Page.enable")
        # Wait for load
        time.sleep(1.2)
        call("Emulation.setDefaultBackgroundColorOverride", {"color": {"r": 0, "g": 11, "b": 30, "a": 1}})

        result = call(
            "Page.printToPDF",
            {
                "landscape": False,
                "displayHeaderFooter": False,
                "printBackground": True,
                "preferCSSPageSize": True,
                "paperWidth": 8.27,  # A4 inches
                "paperHeight": 11.69,
                "marginTop": 0,
                "marginBottom": 0,
                "marginLeft": 0,
                "marginRight": 0,
            },
        )
        data = base64.b64decode(result["result"]["data"])
        OUT.write_bytes(data)
        print(f"OK {OUT} ({len(data)} bytes)")
        ws.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
