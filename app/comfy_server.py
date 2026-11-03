"""Start, watch and stop the ComfyUI server: the bundled portable copy, or the user's own install."""

import json
import subprocess
import threading
import urllib.request

from .settings import Engine

CREATE_NO_WINDOW = 0x08000000


class ComfyServer:
    def __init__(self, engine: Engine, extra_args: list[str] | None = None, on_log=None):
        self.engine = engine
        self.port = engine.port
        self.extra_args = extra_args or []
        self.on_log = on_log or (lambda line: None)
        self.proc: subprocess.Popen | None = None
        # True when a ComfyUI was already serving on the port (e.g. the user's own, opened for
        # another program). We use it as it is and never stop it.
        self.attached = False

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def installed(self) -> bool:
        return self.engine.python.exists() and (self.engine.comfy_dir / "main.py").exists()

    def running(self) -> bool:
        if self.attached:
            return self.system_stats() is not None
        return self.proc is not None and self.proc.poll() is None

    def start(self) -> None:
        if self.running():
            return
        if self.system_stats() is not None:
            self.attached = True
            self.on_log(f"Using the ComfyUI that is already running on port {self.port}.")
            return
        self.attached = False
        if not self.installed():
            raise RuntimeError("ComfyUI is not installed - run installer\\install.bat first.")
        cmd = [str(self.engine.python), "-s", str(self.engine.comfy_dir / "main.py"),
               "--disable-auto-launch", "--listen", "127.0.0.1", "--port", str(self.port), *self.extra_args]
        if self.engine.portable:
            cmd.insert(3, "--windows-standalone-build")
        cwd = self.engine.comfy_dir.parent if self.engine.portable else self.engine.comfy_dir
        self.on_log("$ " + " ".join(cmd))
        self.proc = subprocess.Popen(
            cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            creationflags=CREATE_NO_WINDOW,
        )
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        for line in self.proc.stdout:
            self.on_log(line.rstrip())
        self.on_log(f"[ComfyUI exited with code {self.proc.wait()}]")

    def stop(self) -> None:
        if self.attached:
            self.attached = False      # not ours to stop
            return
        if not self.running():
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.proc.kill()

    def system_stats(self) -> dict | None:
        """None while the server is not answering yet."""
        try:
            with urllib.request.urlopen(self.url + "/system_stats", timeout=2) as r:
                return json.load(r)
        except OSError:
            return None
