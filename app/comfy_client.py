"""Minimal ComfyUI API client: upload an image, queue a graph, follow progress, fetch outputs."""

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import websocket


class ComfyError(RuntimeError):
    pass


class ComfyClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client_id = uuid.uuid4().hex

    def _post_json(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(self.base_url + path, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise ComfyError(f"{path}: HTTP {e.code}\n{e.read().decode(errors='replace')}") from e

    def _get_json(self, path: str) -> dict:
        with urllib.request.urlopen(self.base_url + path, timeout=30) as r:
            return json.load(r)

    def upload_image(self, path: Path, name: str) -> str:
        boundary = uuid.uuid4().hex
        body = b"".join([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="image"; filename="{name}"\r\n'.encode(),
            b"Content-Type: image/png\r\n\r\n",
            path.read_bytes(),
            f"\r\n--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
            f"--{boundary}--\r\n".encode(),
        ])
        req = urllib.request.Request(self.base_url + "/upload/image", data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            info = json.load(r)
        return f"{info['subfolder']}/{info['name']}" if info.get("subfolder") else info["name"]

    def run(self, graph: dict, on_progress=None, on_status=None, should_cancel=None) -> dict:
        """Queue `graph` and block until it finishes. Returns its /history entry."""
        on_progress = on_progress or (lambda value, maximum: None)
        on_status = on_status or (lambda text: None)
        ws_url = self.base_url.replace("http", "ws", 1) + f"/ws?clientId={self.client_id}"
        ws = websocket.create_connection(ws_url, timeout=5)
        try:
            prompt_id = self._post_json("/prompt", {"prompt": graph, "client_id": self.client_id})["prompt_id"]
            while True:
                if should_cancel and should_cancel():
                    self._post_json("/interrupt", {})
                    raise ComfyError("cancelled")
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                if not isinstance(raw, str):
                    continue  # binary preview frames
                msg = json.loads(raw)
                data = msg.get("data", {})
                if data.get("prompt_id") not in (None, prompt_id):
                    continue
                kind = msg.get("type")
                if kind == "progress":
                    on_progress(data["value"], data["max"])
                elif kind == "executing" and data.get("node"):
                    title = graph.get(data["node"], {}).get("_meta", {}).get("title", data["node"])
                    on_status(title)
                elif kind == "execution_error":
                    raise ComfyError(f"{data.get('node_type')}: {data.get('exception_message')}")
                elif kind == "execution_interrupted":
                    raise ComfyError("interrupted")
                elif kind == "execution_success" or (kind == "executing" and data.get("node") is None):
                    break
        finally:
            ws.close()
        return self._get_json(f"/history/{prompt_id}")[prompt_id]

    def download_images(self, history: dict, dest_dir: Path) -> list[Path]:
        """Save every image output of a finished run into dest_dir, in order."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for output in history.get("outputs", {}).values():
            for img in output.get("images", []):
                query = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img["subfolder"],
                                                "type": img["type"]})
                target = dest_dir / img["filename"]
                with urllib.request.urlopen(f"{self.base_url}/view?{query}", timeout=60) as r:
                    target.write_bytes(r.read())
                files.append(target)
        return sorted(files)
