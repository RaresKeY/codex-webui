#!/usr/bin/env python3
"""Production UI checks with synthetic API fixtures in offscreen Firefox."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
DECISION = {'model': 'gpt-6.1-sol', 'effort': 'low', 'modelConfidence': .8, 'effortConfidence': .7,
            'contextMissing': None, 'reviewNeeded': False, 'policy': '2026-10-05-v5'}
THREAD = {'id': 'c1', 'name': 'A calmer place to build', 'cwd': '/workspace/codex-webui-2', 'model': 'gpt-6.1-sol', 'status': 'idle', 'turns': [{'id': 't0', 'status': 'completed', 'items': [
    {'id': 'u0', 'type': 'userMessage', 'content': [{'type': 'text', 'text': 'Make this workspace simpler, with room to focus on the conversation.'}]},
    {'id': 'r0', 'type': 'reasoning', 'summary': ['Keep useful workspace tools within reach.']},
    {'id': 'x0', 'type': 'commandExecution', 'command': 'python -m pytest', 'aggregatedOutput': 'All checks passed.', 'status': 'completed'},
    {'id': 'x1', 'type': 'commandExecution', 'command': 'git diff --check', 'aggregatedOutput': '', 'status': 'completed'},
    {'id': 'a0', 'type': 'agentMessage', 'text': 'A little more space, a lot less noise.\n\nThe conversation is now at the center of the workspace, with the tools you need just a click away.\n\n### Your workspace, simplified\n\n- **One sidebar** for chats, projects, tasks, and images.\n- **Automatic routing** chooses a model and reasoning effort for each message.\n- **Workspace tools** open when you need them.\n\nCommands and thought summaries stay tucked away until you expand them. Keep building; the details are still here.'},
]}]}


class Fixtures(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    calls = []
    fail_route = False
    sockets = []
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'frontend/dist'), **kwargs)
    def log_message(self, *_):
        pass
    def reply(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    @classmethod
    def emit(cls, value):
        data = json.dumps(value).encode()
        frame = bytes([0x81, len(data)]) if len(data) < 126 else b'\x81\x7e' + struct.pack('!H', len(data))
        for connection in cls.sockets[:]:
            try: connection.sendall(frame + data)
            except OSError: cls.sockets.remove(connection)
    def do_GET(self):
        path = self.path.split('?')[0]
        if path.startswith('/ws/'):
            key = self.headers.get('Sec-WebSocket-Key', '')
            accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
            self.send_response(101); self.send_header('Upgrade', 'websocket'); self.send_header('Connection', 'Upgrade'); self.send_header('Sec-WebSocket-Accept', accept); self.end_headers()
            self.sockets.append(self.connection)
            self.connection.settimeout(1)
            while not getattr(self.server, 'stopping', False):
                try:
                    if not self.connection.recv(4096): break
                except socket.timeout: continue
                except OSError: break
            return
        if path == '/api/bootstrap':
            self.reply({'projects': [{'id': 1, 'name': 'WebUI 2', 'workspace': '/workspace/codex-webui-2'}], 'threads': {'data': [THREAD]}, 'models': {'data': [{'id': DECISION['model']}]}, 'system': {'runtime': 'container'}, 'tasks': [], 'workspace': [], 'features': {}})
        elif path == '/api/approvals': self.reply({'data': []})
        elif path.endswith('/realtime/capability'): self.reply({'available': False, 'reason': 'Synthetic browser fixture'})
        elif path == '/api/threads/c1': self.reply({'thread': THREAD})
        elif path.startswith('/api/threads/'): self.reply({'thread': {'id': path.rsplit('/', 1)[-1], 'turns': []}})
        elif path.startswith('/api/'): self.reply({'data': []})
        else: super().do_GET()
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
        self.calls.append((self.path, body))
        if self.path.endswith('/route'):
            time.sleep(.15)
            self.reply({'detail': 'Jev routing failed. Your message was not sent to Codex.'}, 409) if self.fail_route else self.reply(DECISION)
        elif self.path.endswith('/turns'):
            self.reply({'turn': {'id': 'fixture-turn'}}, 201)
            def finish():
                self.emit({'method': 'item/agentMessage/delta', 'params': {'threadId': 'c1', 'turnId': 'fixture-turn', 'itemId': 'a1', 'delta': 'The selected model received your original message.'}})
                self.emit({'method': 'turn/completed', 'params': {'threadId': 'c1', 'turn': {'id': 'fixture-turn', 'status': 'completed'}}})
            threading.Timer(.2, finish).start()
        elif self.path == '/api/threads': self.reply({'thread': {'id': 'new-fixture', 'name': 'Untitled conversation', 'cwd': '/workspace/codex-webui-2', 'model': DECISION['model']}})
        else: self.reply({})
    def do_PATCH(self): self.reply({})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bidi-helper', type=Path, default=Path.home() / 'workspace/godot-performance-lab/tools/firefox_bidi_profile.py')
    args = parser.parse_args()
    sys.path.insert(0, str(args.bidi_helper.parent))
    spec = importlib.util.spec_from_file_location('webui_bidi', args.bidi_helper)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Fixtures)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    output = ROOT / 'evidence/ui'; output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='webui2-firefox-') as profile, socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
        probe.close()
        with (ROOT / 'tmp/browser.log').open('w') as log:
            process = subprocess.Popen(['gamescope', '--backend', 'headless', '-W', '1440', '-H', '1000', '--', 'firefox', '--headless', '--no-remote', '--profile', profile, '--remote-allow-system-access', '--remote-debugging-port', str(port)], stdout=log, stderr=log, start_new_session=True)
            bidi = None
            try:
                for _ in range(100):
                    try: bidi = module.Bidi(port=port); break
                    except (OSError, RuntimeError): time.sleep(.1)
                if bidi is None: raise RuntimeError('Firefox BiDi did not start; see tmp/browser.log')
                bidi.command('session.new', {'capabilities': {}})
                bidi.command('session.subscribe', {'events': ['log.entryAdded']})
                context = str(bidi.command('browsingContext.create', {'type': 'tab'})['result']['context'])
                def evaluate(expression): return module.evaluate_json(bidi, context, expression)
                def wait(expression):
                    for _ in range(100):
                        if evaluate(expression): return
                        time.sleep(.05)
                    screenshot("failure.png")
                    print("Fixture requests:", Fixtures.calls)
                    print(evaluate("document.body.innerText.slice(-1800)"))
                    raise AssertionError(expression)
                def click(selector): evaluate(f"(() => {{ document.querySelector({json.dumps(selector)}).click(); return true; }})()")
                def fill(value): evaluate(f"(() => {{ const t=document.querySelector('textarea'); Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(t,{json.dumps(value)}); t.dispatchEvent(new Event('input',{{bubbles:true}})); return true; }})()")
                def screenshot(name):
                    result = bidi.command('browsingContext.captureScreenshot', {'context': context, 'origin': 'viewport'})
                    (output / name).write_bytes(base64.b64decode(result['result']['data']))
                def viewport(width, height): bidi.command('browsingContext.setViewport', {'context': context, 'viewport': {'width': width, 'height': height}, 'devicePixelRatio': 1})
                bidi.command('browsingContext.navigate', {'context': context, 'url': f'http://127.0.0.1:{server.server_port}', 'wait': 'complete'})
                viewport(1440, 1000)
                wait("document.querySelector('.message.assistant') !== null")
                measurements = evaluate("(() => { const c=document.querySelector('.composer').getBoundingClientRect(); const m=document.querySelector('.content-area').getBoundingClientRect(); return {sidebar:document.querySelector('.chat-sidebar').getBoundingClientRect().width,mainX:m.x,composerWidth:c.width,composerBottom:c.bottom,overflow:document.documentElement.scrollWidth>innerWidth,font:getComputedStyle(document.querySelector('.message.assistant .markdown-content')).fontSize,commandsOpen:document.querySelector('.command-group').open,thoughtOpen:document.querySelector('.reasoning-disclosure').open}; })()")
                screenshot('desktop.png')
                print(json.dumps(measurements))
                assert measurements['sidebar'] == 260 and measurements['mainX'] == 260
                assert measurements['font'] == '16px' and not measurements['overflow']
                assert not measurements['commandsOpen'] and not measurements['thoughtOpen']
                screenshot('desktop.png')
                click('[aria-label="Open context panel"]'); wait("document.querySelector('.context-panel') !== null")
                screenshot('desktop-context.png')
                click('[aria-label="Close context panel"]')
                fill('Synthetic ordering check')
                click('[aria-label="Send message"]')
                wait("document.querySelector('textarea').value === '' && !document.querySelector('.send-button .spin')")
                calls = [call for call in Fixtures.calls if call[0].endswith(('/route', '/resume', '/turns'))]
                assert [call[0].rsplit('/', 1)[-1] for call in calls] == ['route', 'resume', 'turns']
                assert calls[0][1]['input'] == calls[2][1]['input'] == 'Synthetic ordering check'
                assert calls[1][1] == {'model': DECISION['model']}
                assert calls[2][1]['effort'] == 'low'
                Fixtures.fail_route = True
                before = len(Fixtures.calls)
                fill('Preserve this failed draft')
                click('[aria-label="Send message"]')
                wait("document.querySelector('[role=alert]') !== null || document.querySelector('.event-card.failed') !== null")
                wait("!document.querySelector('[aria-label=\"Send message\"]').disabled")
                assert evaluate("document.querySelector('textarea').value") == 'Preserve this failed draft'
                assert len(Fixtures.calls) == before + 1
                viewport(390, 844)
                wait("document.querySelector('.chat-sidebar') === null")
                assert not evaluate('document.documentElement.scrollWidth > innerWidth')
                screenshot('phone.png')
                click('[aria-label="Expand conversations"]'); wait("document.querySelector('.chat-sidebar') !== null")
                screenshot('phone-navigation.png')
                click('.new-chat'); wait("document.querySelector('.chat-welcome') !== null && document.querySelector('textarea') !== null")
                assert evaluate("document.querySelector('.chat-sidebar') === null")
                screenshot('phone-new-chat.png')
                click('[aria-label="Expand conversations"]'); wait("document.querySelector('.chat-sidebar') !== null")
                click('.sidebar-nav button'); wait("document.querySelector('.page-header h2')?.textContent === 'Projects'")
                assert evaluate("document.querySelector('[aria-label=\"Expand conversations\"]') !== null")
                errors = [event for event in bidi.events if event.get('method') == 'log.entryAdded' and event.get('params', {}).get('level') == 'error' and event.get('params', {}).get('type') == 'javascript']
                assert not errors, errors
                (output / 'checks.json').write_text(json.dumps({'syntheticFixtures': True, 'desktop': measurements, 'phone': {'width': 390, 'height': 844}, 'checks': ['geometry', 'collapsed activity', 'context panel', 'ordered send', 'failed draft retained', 'phone no overflow', 'exclusive navigation', 'new chat', 'secondary page access'], 'uncaughtErrors': len(errors)}, indent=2) + '\n')
                print('Browser checks passed: desktop 1440×1000, phone 390×844, ordered send and fail-closed draft retention.')
            finally:
                server.stopping = True; server.shutdown()
                if bidi:
                    try: bidi.command('session.end', {})
                    except Exception: pass
                    bidi.close()
                try: os.killpg(process.pid, signal.SIGTERM); process.wait(timeout=5)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    if process.poll() is None: os.killpg(process.pid, signal.SIGKILL)


if __name__ == '__main__': main()
