#!/usr/bin/env python3
"""Check the installed App Server's real new-thread API offline, without inference."""
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, "/app")  # Check the packaged backend in the runtime image.
from fastapi.testclient import TestClient
from backend.app.config import Settings
from backend.app.main import create_app


def main():
    with tempfile.TemporaryDirectory(prefix="webui-thread-check-") as directory:
        root = Path(directory)
        os.environ["CODEX_HOME"] = str(root / "codex")
        (root / "codex").mkdir()
        (root / "workspace").mkdir()
        settings = Settings(
            data_dir=root / "data", workspace_root=root / "workspace",
            codex_command="/usr/local/bin/codex app-server", codex_enabled=True,
            allowed_hosts=["testserver"], allowed_origins=["http://testserver"],
        )
        with TestClient(create_app(settings)) as client:
            assert client.get("/api/health").json()["codex_available"]
            response = client.post("/api/threads", json={"cwd": ".", "sandbox": "read-only"})
            assert response.status_code == 201, response.status_code
            thread = response.json()["thread"]
            assert thread["historyMode"] == "legacy"
            thread_id = thread["id"]
            response = client.get(f"/api/threads/{thread_id}")
            assert response.status_code == 200, response.status_code
            assert response.json()["thread"]["turns"] == []
            for model in ("gpt-6-luna", "gpt-6.1-sol"):
                response = client.post(f"/api/threads/{thread_id}/resume", json={"model": model})
                assert response.status_code == 200, response.status_code
        print("Native offline lifecycle passed: legacy creation, empty history, both model-change requests.")


if __name__ == "__main__":
    main()
