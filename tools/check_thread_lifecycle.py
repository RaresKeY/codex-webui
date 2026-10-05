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
            plugins = client.get("/api/plugins")
            assert plugins.status_code == 200, plugins.status_code
            assert isinstance(plugins.json()["data"], list)
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
                assert response.json()["modelChangeAcknowledged"] is True

            # Keep native metadata/loading/settings RPCs real; replace only paid
            # routing and inference transport with bounded synthetic fixtures.
            codex = client.app.state.codex
            original_request = codex.request
            observed = []
            async def request(method, params):
                observed.append((method, params))
                if method == "turn/start":
                    return {"turn": {"id": "synthetic-turn"}}
                return await original_request(method, params)
            async def choose(task):
                return {"model": "gpt-6-luna", "effort": "low", "reviewNeeded": False, "policy": "2026-10-05-v5"}
            codex.request = request
            client.app.state.router.choose = choose
            ask = "  Synthetic request\n\n "
            response = client.post(f"/api/threads/{thread_id}/messages", json={"input": ask})
            assert response.status_code == 201, response.status_code
            assert response.json()["modelChangeAcknowledged"] is True
            assert observed[-2] == ("thread/settings/update", {"threadId": thread_id, "model": "gpt-6-luna", "effort": "low"})
            assert observed[-1][0] == "turn/start"
            assert observed[-1][1]["input"][0]["text"] == ask
        print("Native offline lifecycle passed: installed plugin discovery, legacy history, real model acknowledgements, synthetic routed submission with exact text.")


if __name__ == "__main__":
    main()
