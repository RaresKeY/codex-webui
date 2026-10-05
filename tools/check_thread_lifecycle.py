#!/usr/bin/env python3
"""Check the installed App Server's real new-thread API offline, without inference."""
import asyncio
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, "/app")  # Check the packaged backend in the runtime image.
from fastapi.testclient import TestClient
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.permissions import permission_overrides


def main():
    with tempfile.TemporaryDirectory(prefix="webui-thread-check-") as directory:
        root = Path(directory)
        os.environ["CODEX_HOME"] = str(root / "codex")
        (root / "codex").mkdir()
        (root / "workspace").mkdir()
        skill_dir = root / "workspace/.agents/skills/offline-review"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: offline-review\ndescription: Review synthetic offline fixtures\n---\nRead the supplied fixture.\n")
        (root / "workspace/main.py").write_text("print('fixture')\n")
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
            catalog = client.get("/api/mentions", params={"thread_id": thread_id})
            assert catalog.status_code == 200, catalog.status_code
            assert not catalog.json()["errors"], catalog.json()["errors"]
            assert any(entry["kind"] == "skill" and entry["insertText"] == "$offline-review" for entry in catalog.json()["data"])
            files = client.get("/api/mention-files", params={"q": "main"})
            assert files.status_code == 200, files.status_code
            assert any(entry["insertText"] == "@main.py" for entry in files.json()["data"])
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
            async def verify_permissions():
                for mode in ('full-auto', 'yolo', 'default'):
                    async with codex.subscribe() as queue:
                        await client.app.state.chat.set_permissions(thread_id, mode)
                        while True:
                            event = await asyncio.wait_for(queue.get(), 5)
                            if event.get('method') == 'thread/settings/updated' and event.get('params', {}).get('threadId') == thread_id:
                                effective = event['params']['threadSettings']
                                expected = permission_overrides(mode, settings)
                                assert effective['approvalPolicy'] == expected['approvalPolicy']
                                assert effective['approvalsReviewer'] == expected['approvalsReviewer']
                                assert effective['sandboxPolicy']['type'] == expected['sandboxPolicy']['type']
                                break
            client.portal.call(verify_permissions)
            # New chats snapshot the last explicitly acknowledged preset.
            for mode in ('full-auto', 'yolo', 'default'):
                response = client.patch(f"/api/threads/{thread_id}/permissions", json={'mode':mode})
                assert response.status_code == 200, response.status_code
                created = client.post('/api/threads', json={'cwd':'.'})
                assert created.status_code == 201, created.status_code
                result = created.json()
                expected = permission_overrides(mode, settings)
                assert result['approvalPolicy'] == expected['approvalPolicy']
                assert result['approvalsReviewer'] == expected['approvalsReviewer']
                assert result['sandbox']['type'] == expected['sandboxPolicy']['type']
                assert client.get(f"/api/threads/{result['thread']['id']}/permissions").json() == {'mode':mode}
            for model, effort in [('gpt-6.1-sol','high'), ('gpt-6-luna','max'), ('auto','medium')]:
                choice = {'model':model, 'effort':effort}
                response = client.patch(f"/api/threads/{thread_id}/execution", json=choice)
                assert response.status_code == 200, response.status_code
                assert client.get(f"/api/threads/{thread_id}/execution").json() == choice
            # Native lifecycle operations use only this disposable Codex home.
            archived = client.post(f"/api/threads/{thread_id}/archive")
            assert archived.status_code == 200, archived.text
            listing = client.get('/api/threads', params={'archived':True}).json()
            assert any(item['id'] == thread_id for item in listing['data'])
            restored = client.post(f"/api/threads/{thread_id}/unarchive")
            assert restored.status_code == 200, restored.text
            assert restored.json()['thread']['id'] == thread_id
            disposable = client.post('/api/threads', json={'cwd':'.'}).json()['thread']['id']
            assert client.post(f'/api/threads/{disposable}/archive').status_code == 200
            deleted = client.delete(f'/api/threads/{disposable}')
            assert deleted.status_code == 204, deleted.text
            assert all(item['id'] != disposable for item in client.get('/api/threads').json()['data'])
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
            assert observed[-2] == ("thread/settings/update", {"threadId": thread_id, "model": "gpt-6-luna", "effort": "low", **permission_overrides('default', settings)})
            assert observed[-1][0] == "turn/start"
            assert observed[-1][1]["input"][0]["text"] == ask
        print("Native offline lifecycle passed: skill/plugin/app discovery, rooted fuzzy files, legacy history, real model and permission acknowledgements, native archive/restore/archived deletion, synthetic routed submission with exact text.")


if __name__ == "__main__":
    main()
