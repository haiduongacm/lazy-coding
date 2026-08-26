"""HTML artifact viewer."""

import http.server
import threading
from pathlib import Path
from typing import Optional


class Viewer:
    """Local HTML artifact viewer."""

    def __init__(self, port: int = 4387):
        self.port = port
        self.server = None
        self.thread = None

    def open(self, html_file: str):
        """Open HTML file in viewer."""
        file_path = Path(html_file).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Serve the file
        self._serve(file_path.parent)
        return {"opened": str(file_path), "url": f"http://localhost:{self.port}/{file_path.name}"}

    def _serve(self, directory: Path):
        """Start HTTP server."""
        if self.server:
            return

        handler = lambda *args: http.server.SimpleHTTPRequestHandler(
            *args, directory=str(directory)
        )

        self.server = http.server.HTTPServer(("", self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the viewer server."""
        if self.server:
            self.server.shutdown()
            self.server = None
            self.thread = None
