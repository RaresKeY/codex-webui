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
import zlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
def fixture_png():
    def chunk(kind, body): return struct.pack('!I', len(body)) + kind + body + struct.pack('!I', zlib.crc32(kind + body))
    width, height = 400, 240
    pixels = b''.join(b'\0' + b''.join(bytes((75 + x * 100 // width, 90 + y * 80 // height, 120)) for x in range(width)) for y in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')
PNG = fixture_png()
PNG_DATA = base64.b64encode(PNG).decode()
PLUGIN = {'id': 'notes@local', 'name': 'notes', 'displayName': 'Local Notes', 'description': 'Find workspace notes'}
MENTIONS = [
    {'id': 'skill:review', 'kind': 'skill', 'name': 'review', 'displayName': 'Code review', 'description': 'Review changes', 'insertText': '$review'},
    {**PLUGIN, 'id': 'plugin:notes@local', 'kind': 'plugin', 'insertText': '@notes'},
    {'id': 'app:drive', 'kind': 'app', 'name': 'drive', 'displayName': 'Drive', 'description': 'Find documents', 'insertText': '$drive'},
]
MENTIONS.extend({'id': f'skill:task-{index}', 'kind': 'skill', 'name': f'task-{index}', 'displayName': f'Task {index}', 'description': 'A separate useful skill', 'insertText': f'$task-{index}'} for index in range(15))
FILE_MENTION = {'id': 'file:src%2Fmain.py', 'kind': 'file', 'name': 'src/main.py', 'displayName': 'main.py', 'description': 'src/main.py', 'insertText': '@src/main.py'}
DECISION = {'model': 'gpt-6.1-sol', 'effort': 'low', 'modelConfidence': .8, 'effortConfidence': .7,
            'contextMissing': None, 'reviewNeeded': False, 'policy': '2026-10-05-v5'}
THREAD = {'id': 'c1', 'name': 'A calmer place to build', 'cwd': '/workspace/codex-webui-2', 'model': 'gpt-6.1-sol', 'status': 'idle', 'turns': [{'id': 't0', 'webui': {'model': 'gpt-6-luna', 'effort': 'medium'}, 'status': 'completed', 'items': [
    {'id': 'u0', 'type': 'userMessage', 'content': [{'type': 'text', 'text': 'Make this workspace simpler, with room to focus on the conversation.'}, {'type': 'localImage', 'path': '/workspace/codex-webui-2/preview.png'}]},
    {'id': 'r0', 'type': 'reasoning', 'summary': ['Keep useful workspace tools within reach.']},
    {'id': 'x0', 'type': 'commandExecution', 'command': 'python -m pytest', 'aggregatedOutput': 'All checks passed.', 'status': 'completed'},
    {'id': 'x1', 'type': 'commandExecution', 'command': 'git diff --check', 'aggregatedOutput': '', 'status': 'completed'},
    {'id': 'a0', 'type': 'agentMessage', 'text': 'A little more space, a lot less noise.\n\nThe conversation is now at the center of the workspace, with the tools you need just a click away.\n\n### Your workspace, simplified\n\n- **One sidebar** for chats, projects, tasks, and images.\n- **Automatic routing** chooses a model and reasoning effort for each message.\n- **Workspace tools** open when you need them.\n\nCommands and thought summaries stay tucked away until you expand them. Keep building; the details are still here.'},
    {'id': 'img0', 'type': 'imageGeneration', 'status': 'completed', 'result': PNG_DATA},
]}]}

THEME_MARKDOWN = '''### A simple comparison

The numbers below are illustrative examples.

| Example outcome | Change after three years | After five years |
| :--- | ---: | ---: |
| The starting assumption stays unchanged long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_ | **+33%** | **+61%** |
| The starting assumption finishes lower | **+6%** | **+29%** |

> Keep assumptions visible when comparing outcomes.

Use `total` for the result. [Read the guide](https://example.com/guide).

```python
total = sum(values)
print(total)
    # long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_long_token_
```
'''


def check_theme(evaluate, wait, click, viewport, screenshot, bidi, output, baseline):
    """Measure real Markdown surfaces and responsive scrolling without submitting a prompt."""
    measurements = []
    for width, height, name in [(1440, 1000, 'desktop'), (390, 844, 'phone'), (320, 640, 'narrow-phone')]:
        viewport(width, height)
        if name == 'desktop':
            wait("document.querySelector('.launch-recents button') !== null")
            click('.launch-recents button')
        wait("document.querySelector('.message.assistant table') !== null")
        evaluate("(() => {document.querySelector('.event-feed').scrollTop=0;document.activeElement?.blur();return true})()")
        time.sleep(.15)
        colors = evaluate("""(() => {
            const color = (selector, property) => getComputedStyle(document.querySelector(selector))[property];
            const wrap = document.querySelector('.markdown-table-wrap');
            wrap.scrollLeft = wrap.scrollWidth;
            const scrolls = wrap.scrollLeft > 0;
            wrap.scrollLeft = 0;
            return {header:color('.markdown-content th','backgroundColor'),headerText:color('.markdown-content th','color'),
                sidebarToken:getComputedStyle(document.documentElement).getPropertyValue('--sidebar').trim(),
                sidebar:document.querySelector('.chat-sidebar') ? color('.chat-sidebar','backgroundColor') : null,
                border:color('.markdown-table-wrap','borderTopColor'),body:color('.markdown-content td','color'),
                codeHeader:color('.markdown-code-header','backgroundColor'),inlineCodeBorder:color('.markdown-content p code','borderTopColor'),
                quoteBorder:color('.markdown-content blockquote','borderLeftColor'),overflow:document.documentElement.scrollWidth>innerWidth,
                tableWidth:wrap.clientWidth,tableScrollWidth:wrap.scrollWidth,tableScrolls:scrolls,
                codeWhiteSpace:color('.markdown-code-block code','whiteSpace'),
                codeWidth:document.querySelector('.markdown-code-block pre').clientWidth,
                codeScrollWidth:document.querySelector('.markdown-code-block pre').scrollWidth,
                disabledSend:document.querySelector('[aria-label="Send message"]').disabled};
        })()""")
        assert not colors['overflow'] and colors['disabledSend'], colors
        if not baseline:
            assert not colors['tableScrolls'], 'Text tables must soft-wrap without horizontal scrolling'
            assert colors['codeWhiteSpace'] == 'pre-wrap' and colors['codeScrollWidth'] <= colors['codeWidth'], colors
        def channels(value):
            return [int(channel.strip()) for channel in value.removeprefix('rgb(').removesuffix(')').split(',')]
        def luminance(value):
            channels_linear = [component / 12.92 if component <= .04045 else ((component + .055) / 1.055) ** 2.4 for component in [c / 255 for c in channels(value)]]
            return sum(component * weight for component, weight in zip(channels_linear, [.2126, .7152, .0722]))
        colors['headerContrast'] = round((luminance(colors['headerText']) + .05) / (luminance(colors['header']) + .05), 2)
        assert colors['headerContrast'] >= 4.5, colors
        if not baseline:
            assert colors['header'] == 'rgb(28, 28, 28)', colors
            if colors['sidebar']:
                assert colors['header'] == colors['sidebar'], colors
            for field in ('header', 'headerText', 'border', 'codeHeader', 'inlineCodeBorder', 'quoteBorder'):
                assert len(set(channels(colors[field]))) == 1, (field, colors[field])
        prefix = 'before-' if baseline else 'after-'
        screenshot(prefix + name + '-table.png')
        evaluate("(() => {document.querySelector('.markdown-code-header button').scrollIntoView({block:'center'});document.querySelector('.markdown-code-header button').focus();return true})()")
        wait("getComputedStyle(document.activeElement).outlineStyle !== 'none'")
        screenshot(prefix + name + '-code-focus.png')
        measurements.append({'viewport':f'{width}x{height}',**colors})
    errors = [event for event in bidi.events if event.get('method') == 'log.entryAdded' and event.get('params', {}).get('type') == 'javascript' and event.get('params', {}).get('level') == 'error']
    assert not errors and not Fixtures.calls, (len(errors), Fixtures.calls)
    report = {'syntheticFixtures':True,'baseline':baseline,'measurements':measurements,'uncaughtErrors':len(errors),'modelCalls':0}
    (output / ('before-checks.json' if baseline else 'checks.json')).write_text(json.dumps(report,indent=2)+'\n')
    print('Theme checks passed at desktop, phone and narrow phone widths: Markdown contrast, code/table soft wrapping and copy focus; no model calls.')


class Fixtures(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    calls = []
    fail_route = False
    fail_bootstrap = False
    fail_history = False
    history_delay = 1.2
    response_delay = 1.0
    send_delay = .15
    turn_number = 0
    baseline = False
    bundle = ROOT / 'frontend/dist'
    sockets = []
    search_queries = []
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.bundle), **kwargs)
    def log_message(self, *_):
        pass
    def reply(self, data, status=200):
        body = json.dumps(data).encode()
        try:
            self.send_response(status); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Aborting obsolete fixture reads is expected.
    def stream_reply(self, frames):
        body = (''.join(json.dumps(frame) + '\n' for frame in frames)).encode()
        self.send_response(201); self.send_header('Content-Type', 'application/x-ndjson'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    @classmethod
    def emit(cls, value):
        data = json.dumps(value).encode()
        frame = bytes([0x81, len(data)]) if len(data) < 126 else b'\x81\x7e' + struct.pack('!H', len(data))
        for connection in cls.sockets[:]:
            try: connection.sendall(frame + data)
            except OSError: cls.sockets.remove(connection)
    def do_GET(self):
        path = self.path.split('?')[0]
        if path.startswith('/ws/') or path == '/api/activity':
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
            if self.fail_bootstrap: self.reply({'detail': 'Synthetic offline service'}, 503); return
            if self.baseline: time.sleep(self.history_delay)
            self.reply({'health': {'codex_available': True}, 'projects': [{'id': 1, 'name': 'WebUI 2', 'workspace': '/workspace/codex-webui-2'}], 'threads': {'data': [THREAD] if self.baseline else []}, 'models': {'data': []}, 'system': {'runtime': 'container'}, 'tasks': [], 'workspace': [], 'features': {}})
        elif path == '/api/threads':
            query = parse_qs(urlsplit(self.path).query).get('q', [''])[0]
            if query:
                self.search_queries.append(query)
                if query == 'alpha': time.sleep(1)
                return self.reply({'data': [{**THREAD, 'id': f'search-{query}', 'name': f'{query} remote result'}]})
            time.sleep(self.history_delay)
            self.reply({'detail': 'Synthetic history failure'}, 504) if self.fail_history else self.reply({'data': [THREAD]})
        elif path == '/api/plugins': self.reply({'data': [PLUGIN]})
        elif path == '/api/mentions': self.reply({'data': MENTIONS, 'errors': []})
        elif path == '/api/mention-files': self.reply({'data': [FILE_MENTION] if 'main' in parse_qs(urlsplit(self.path).query).get('q', [''])[0] else []})
        elif path == '/api/models': self.reply({'data': [{'id': DECISION['model']}, {'id': 'gpt-6-luna'}]})
        elif path == '/api/usage': self.reply({})
        elif path == '/api/workspace/image':
            image_path = parse_qs(urlsplit(self.path).query).get('path', [''])[0]
            if 'relative-review.png' in image_path and image_path != '/workspace/codex-webui-2/./relative-review.png':
                return self.reply({'detail': 'Image resolved outside the fixture project'}, 404)
            self.send_response(200); self.send_header('Content-Type', 'image/png'); self.send_header('Content-Length', str(len(PNG))); self.end_headers(); self.wfile.write(PNG)
        elif path == '/api/approvals': self.reply({'data': []})
        elif path.endswith('/realtime/capability'): self.reply({'available': False, 'reason': 'Synthetic browser fixture'})
        elif path == '/api/threads/c1': self.reply({'thread': THREAD})
        elif path.endswith('/permissions'): self.reply({'mode': 'default'})
        elif path.endswith('/execution'): self.reply({'model': 'auto', 'effort': 'medium'})
        elif path.startswith('/api/threads/'): self.reply({'thread': {'id': path.rsplit('/', 1)[-1], 'turns': []}})
        elif path.startswith('/api/'): self.reply({'data': []})
        else: super().do_GET()
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
        self.calls.append((self.path, body))
        if self.path.endswith('/messages'):
            type(self).turn_number += 1
            turn_id = f'fixture-turn-{self.turn_number}'
            item_id = f'fixture-answer-{self.turn_number}'
            time.sleep(self.send_delay)
            if self.fail_route:
                self.stream_reply([{'stage': 'routing'}, {'error': {'status': 409, 'message': 'Jev routing failed. Your message was not sent to Codex.'}}])
            else:
                self.stream_reply([{'stage': 'routing'}, {'stage': 'switching', 'decision': DECISION}, {'stage': 'sending', 'decision': DECISION}, {'result': {'turn': {'id': turn_id}, 'decision': DECISION, 'modelChangeAcknowledged': True}}])
                def finish():
                    self.emit({'method': 'webui/modelSelected', 'params': {'threadId': 'c1', 'model': DECISION['model'], 'effort': DECISION['effort']}})
                    answer = 'The selected model received your original message.'
                    if body.get('input') == 'Navigation draft': answer += '\n\n![Project preview](./relative-review.png)'
                    self.emit({'method': 'item/agentMessage/delta', 'params': {'threadId': 'c1', 'turnId': turn_id, 'itemId': item_id, 'delta': answer}})
                    if not self.baseline: self.emit({'method': 'item/completed', 'params': {'threadId': 'c1', 'turnId': turn_id, 'item': {'id': f'image-{turn_id}', 'type': 'imageGeneration', 'status': 'completed', 'result': PNG_DATA}}})
                    self.emit({'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'c1', 'tokenUsage': {'total': {'totalTokens': 999999}, 'last': {'totalTokens': 12500}, 'modelContextWindow': 100000}}})
                    threading.Timer(.4, lambda: self.emit({'method': 'turn/completed', 'params': {'threadId': 'c1', 'turn': {'id': turn_id, 'status': 'completed'}}})).start()
                threading.Timer(self.response_delay, finish).start()
        elif self.path.endswith(('/route', '/turns')): self.reply({'detail': 'Use the unified messages operation'}, 409)
        elif self.path == '/api/threads': self.reply({'thread': {'id': 'new-fixture', 'name': 'Untitled conversation', 'cwd': '/workspace/codex-webui-2', 'model': DECISION['model']}})
        else: self.reply({})
    def do_PATCH(self): self.reply({})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bidi-helper', type=Path, default=Path.home() / 'workspace/godot-performance-lab/tools/firefox_bidi_profile.py')
    parser.add_argument('--baseline-bundle', type=Path, help='Capture the previous runtime bundle against matched synthetic states')
    parser.add_argument('--bundle', type=Path, help='Production bundle to verify without rebuilding it')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'evidence/ui')
    parser.add_argument('--theme-only', action='store_true', help='Check Markdown colors and responsive tables without model calls')
    args = parser.parse_args()
    if args.bundle:
        Fixtures.bundle = args.bundle.resolve()
    if args.baseline_bundle:
        Fixtures.baseline = not args.theme_only
        Fixtures.bundle = args.baseline_bundle.resolve()
    if args.theme_only:
        Fixtures.history_delay = .1
        THREAD['turns'][0]['items'] = [
            {'id':'theme-user','type':'userMessage','content':[{'type':'text','text':'Show a simple comparison.'}]},
            {'id':'theme-answer','type':'agentMessage','text':THEME_MARKDOWN},
        ]
    sys.path.insert(0, str(args.bidi_helper.parent))
    spec = importlib.util.spec_from_file_location('webui_bidi', args.bidi_helper)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Fixtures)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    output = args.output_dir.resolve(); output.mkdir(parents=True, exist_ok=True)
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
                def fill(value): evaluate(f"(() => {{ const t=document.querySelector('textarea'); Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(t,{json.dumps(value)}); t.focus(); t.setSelectionRange(t.value.length,t.value.length); t.dispatchEvent(new Event('input',{{bubbles:true}})); t.dispatchEvent(new Event('select',{{bubbles:true}})); return true; }})()")
                def key(value, code=None):
                    bidi.command('input.performActions', {'context': context, 'actions': [{'type': 'key', 'id': 'keyboard', 'actions': [{'type': 'keyDown', 'value': value}, {'type': 'keyUp', 'value': value}]}]})
                def screenshot(name):
                    result = bidi.command('browsingContext.captureScreenshot', {'context': context, 'origin': 'viewport'})
                    (output / name).write_bytes(base64.b64decode(result['result']['data']))
                def viewport(width, height): bidi.command('browsingContext.setViewport', {'context': context, 'viewport': {'width': width, 'height': height}, 'devicePixelRatio': 1})
                bidi.command('browsingContext.navigate', {'context': context, 'url': f'http://127.0.0.1:{server.server_port}', 'wait': 'complete'})
                viewport(1440, 1000)
                if args.theme_only:
                    check_theme(evaluate, wait, click, viewport, screenshot, bidi, output, bool(args.baseline_bundle))
                    return
                if Fixtures.baseline:
                    wait("document.querySelector('.loading-screen') !== null")
                    screenshot('before-desktop-shell.png')
                    wait("document.querySelector('.launch-recents button') !== null"); click('.launch-recents button')
                    wait("document.querySelector('.message.assistant') !== null")
                    screenshot('before-desktop.png')
                    assert evaluate("document.querySelectorAll('.inline-image').length") == 0
                    fill('  Synthetic ordering check\n\n '); click('[aria-label="Send message"]')
                    wait("document.querySelector('textarea').value === '' && document.querySelector('.turn-activity') !== null")
                    spinner_count = evaluate("document.querySelectorAll('.event-feed .spin, .send-button .spin').length")
                    screenshot('before-desktop-working.png')
                    wait("document.querySelector('.turn-activity') === null")
                    viewport(390, 844)
                    wait("document.querySelector('.chat-sidebar') === null")
                    fill('@no'); screenshot('before-phone-plugins.png')
                    (output / 'before-checks.json').write_text(json.dumps({'matchedSyntheticStates': True, 'previousBundle': True, 'messageSpinners': spinner_count, 'inlineImages': 0, 'pluginMenu': False, 'resolutions': ['1440x1000', '390x844']}, indent=2) + '\n')
                    print(f'Baseline captured: {spinner_count} message spinners, no inline image/plugin menu.')
                    return
                wait("document.querySelector('.app-shell') !== null")
                assert evaluate("document.querySelector('.loading-screen') === null && document.querySelector('.history-notice')?.textContent.includes('Loading')")
                screenshot('desktop-shell.png')
                wait("document.querySelector('.chat-row') !== null")
                click('.chat-row')
                wait("document.querySelector('.message.assistant') !== null && document.querySelector('.chat-progress') === null")
                wait("Array.from(document.querySelectorAll('.inline-image img')).every(image => image.complete && image.naturalWidth > 0)")
                screenshot('desktop-restored-effort.png')
                assert evaluate("document.querySelector('.chat-model-select')?.textContent.includes('6-luna') && document.querySelector('.chat-model-effort')?.textContent.includes('medium')"), 'Reopened Auto chat must show its recorded model and effort'
                assert evaluate("document.querySelectorAll('.inline-image').length === 2")
                click('.inline-image'); wait("document.querySelector('.image-viewer')?.open === true")
                screenshot('desktop-image.png')
                key('\ue00c'); wait("document.querySelector('.image-viewer') === null")
                assert evaluate("document.activeElement.classList.contains('inline-image')")
                fill('@no'); wait("document.querySelector('.plugin-suggestions [role=option]') !== null")
                screenshot('desktop-plugins.png')
                key('\ue007')
                wait("document.querySelector('textarea').value === '@notes '")
                assert not Fixtures.calls
                fill('')

                measurements = evaluate("(() => { const c=document.querySelector('.composer').getBoundingClientRect(); const m=document.querySelector('.content-area').getBoundingClientRect(); return {sidebar:document.querySelector('.chat-sidebar').getBoundingClientRect().width,mainX:m.x,composerWidth:c.width,composerBottom:c.bottom,overflow:document.documentElement.scrollWidth>innerWidth,font:getComputedStyle(document.querySelector('.message.assistant .markdown-content')).fontSize,commandsOpen:document.querySelector('.command-group').open,thoughtOpen:document.querySelector('.reasoning-disclosure').open}; })()")
                screenshot('desktop.png')
                print(json.dumps(measurements))
                assert measurements['sidebar'] == 280 and measurements['mainX'] == 280
                assert measurements['font'] == '16px' and not measurements['overflow']
                assert not measurements['commandsOpen'] and not measurements['thoughtOpen']
                screenshot('desktop.png')
                click('[aria-label="Open context panel"]'); wait("document.querySelector('.context-panel') !== null")
                screenshot('desktop-context.png')
                click('[aria-label="Close context panel"]')
                exact_ask = '  Synthetic ordering check\n\n '
                fill(exact_ask)
                click('[aria-label="Send message"]')
                wait("document.querySelector('textarea').value === '' && document.querySelector('.chat-progress') !== null")
                assert evaluate("document.querySelectorAll('.event-feed .spin').length === 1 && !document.querySelector('.turn-activity') && !document.querySelector('.response-placeholder') && !document.querySelector('.send-button .spin')")
                assert evaluate("document.querySelector('.composer-last-model').textContent.replaceAll(' ','').includes(document.querySelector('.chat-model-select strong').textContent) && document.querySelector('.composer-last-model small').textContent === document.querySelector('.chat-model-effort').textContent"), 'Composer lagged behind the selected model/effort'
                screenshot('desktop-working.png')
                wait("document.querySelector('.chat-progress')?.textContent.includes('Responding')")
                assert evaluate("document.querySelectorAll('.event-feed .spin').length === 1")
                wait("document.querySelectorAll('.inline-image').length === 3 && Array.from(document.querySelectorAll('.inline-image img')).every(image => image.complete && image.naturalWidth > 0)")
                screenshot('desktop-streaming.png')
                wait("document.querySelector('.chat-progress') === null")
                assert '12,500 / 100,000 tokens' in evaluate("document.querySelector('.composer .context-button').getAttribute('aria-label')")
                assert not evaluate("Boolean(document.querySelector('.chat-header .context-button'))")
                evaluate("(() => { document.querySelector('.composer .context-button').focus(); return true })()")
                wait("document.querySelector('.context-tooltip')?.textContent.includes('13% used (87% left)')")
                screenshot('desktop-context-tooltip.png')
                key('\ue00c')
                wait("!document.querySelector('.context-tooltip')")

                calls = [call for call in Fixtures.calls if call[0].endswith(('/messages', '/route', '/resume', '/turns'))]
                assert len(calls) == 1 and calls[0][0].endswith('/messages')
                assert calls[0][1] == {'input': exact_ask}
                fill('@notes'); wait("document.querySelector('.plugin-suggestions [role=option]')?.textContent.includes('Local Notes') === true")
                # Simulate a busy frame without delaying real keyboard input.
                # A deferred insertion-caret callback must not rewind typing.
                evaluate("(() => { window.mentionFrames=[]; window.originalMentionFrame=window.requestAnimationFrame; window.requestAnimationFrame=callback => { window.mentionFrames.push(callback); return 0; }; return true; })()")
                key('\ue007'); wait("document.querySelector('textarea').value === '@notes '")
                key('h'); wait("document.querySelector('textarea').value === '@notes h'")
                evaluate("(() => { window.requestAnimationFrame=window.originalMentionFrame; window.mentionFrames.forEach(callback => callback(performance.now())); delete window.mentionFrames; delete window.originalMentionFrame; return true; })()")
                key('i'); wait("document.querySelector('textarea').value === '@notes hi'")
                click('[aria-label="Send message"]')
                wait("document.querySelector('textarea').value === '' && document.querySelector('.chat-progress') !== null")
                assert Fixtures.calls[-1][1] == {'input': '@notes hi', 'mentions': ['plugin:notes@local']}, Fixtures.calls[-1]
                wait("document.querySelector('.chat-progress') === null")
                fill('@notes'); wait("document.querySelector('.plugin-suggestions [role=option]')?.textContent.includes('Local Notes') === true")
                key('\ue007'); wait("document.querySelector('textarea').value === '@notes '")
                fill('Mention removed'); fill('@notes manually restored')
                click('[aria-label="Send message"]')
                wait("document.querySelector('textarea').value === '' && document.querySelector('.chat-progress') !== null")
                assert Fixtures.calls[-1][1] == {'input': '@notes manually restored'}
                wait("document.querySelector('.chat-progress') === null")
                # @ lists all invocable categories and selects native skill/app syntax.
                fill('@'); wait("document.querySelectorAll('.plugin-suggestions [role=option]').length === 12")
                assert evaluate("Array.from(document.querySelectorAll('.plugin-suggestions small')).map(item => item.textContent).join(' ')").find('skill') >= 0
                screenshot('desktop-all-mentions.png')
                for _ in range(11): key('\ue015')
                wait("document.querySelector('.plugin-options [aria-selected=true]')?.id === 'plugin-option-11'")
                assert evaluate("(() => { const menu=document.querySelector('.plugin-suggestions').getBoundingClientRect(); const active=document.querySelector('.plugin-options [aria-selected=true]').getBoundingClientRect(); return active.top >= menu.top && active.bottom <= menu.bottom; })()")
                screenshot('desktop-mentions-keyboard.png')
                fill('@review'); wait("document.querySelector('.plugin-suggestions [role=option]')?.textContent.includes('Code review') === true")
                key('\ue007'); wait("document.querySelector('textarea').value === '$review '")
                fill('$review @drive'); wait("document.querySelector('.plugin-suggestions [role=option]')?.textContent.includes('Drive') === true")
                key('\ue007'); wait("document.querySelector('textarea').value === '$review $drive '")
                fill('$review $drive @src/main'); wait("document.querySelector('.plugin-suggestions [role=option]')?.textContent.includes('main.py') === true")
                key('\ue007'); wait("document.querySelector('textarea').value === '$review $drive @src/main.py '")
                click('[aria-label="Send message"]')
                wait("document.querySelector('textarea').value === '' && document.querySelector('.chat-progress') !== null")
                assert Fixtures.calls[-1][1] == {'input': '$review $drive @src/main.py ', 'mentions': ['skill:review', 'app:drive', FILE_MENTION['id']]}
                wait("document.querySelector('.chat-progress') === null")
                assert evaluate("Array.from(document.querySelectorAll('.message.assistant .message-model')).some(item => item.textContent.includes('gpt-6-luna') && item.textContent.includes('medium'))")
                assert evaluate("Array.from(document.querySelectorAll('.message.assistant .message-model')).some(item => item.textContent.includes('gpt-6.1-sol') && item.textContent.includes('low'))")
                assert evaluate("document.querySelector('.chat-model-select')?.textContent.includes('6.1-sol') && document.querySelector('.chat-model-effort')?.textContent.includes('low')")
                # Typing the next draft while awaiting acknowledgement must survive.
                Fixtures.send_delay = .6
                fill('first draft'); click('[aria-label="Send message"]')
                fill('next draft')
                wait("document.querySelector('.chat-progress') === null")
                assert evaluate("document.querySelector('textarea').value") == 'next draft'
                Fixtures.send_delay = .15
                # Secondary pages retain the active chat and its pending request.
                Fixtures.send_delay = .6
                fill('Navigation draft'); click('[aria-label="Send message"]')
                fill('Next draft while navigating')
                click('[aria-label="Manage projects"]')
                wait("document.querySelector('.page-header h2')?.textContent === 'Projects'")
                assert evaluate("document.querySelector('.chat-surface').hidden && getComputedStyle(document.querySelector('.chat-surface')).display === 'none'")
                click('.sidebar-brand'); wait("document.querySelector('.launch-pad:not([hidden])') !== null"); click('.launch-recents button')
                wait("!document.querySelector('.chat-surface').hidden && document.querySelector('.chat-progress') === null")
                assert evaluate("document.querySelector('textarea').value") == 'Next draft while navigating'
                wait("Boolean(document.querySelector('img[alt=\"Project preview\"]')?.naturalWidth)")
                assert evaluate("document.querySelector('img[alt=\"Project preview\"]').getAttribute('src')") == '/api/workspace/image?path=%2Fworkspace%2Fcodex-webui-2%2F.%2Frelative-review.png'
                screenshot('desktop-navigation-retained.png')
                Fixtures.send_delay = .15

                # A slow previous query cannot replace a newer remote result.
                def search(value):
                    evaluate(f"(() => {{ const input=document.querySelector('[aria-label=\"Search all resumable chats\"]'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,{json.dumps(value)}); input.dispatchEvent(new Event('input',{{bubbles:true}})); return true; }})()")
                if not evaluate("Boolean(document.querySelector('.sidebar-search'))"):
                    click('[aria-label="Search chats"]')
                search('alpha')
                for _ in range(100):
                    if 'alpha' in Fixtures.search_queries: break
                    time.sleep(.05)
                assert 'alpha' in Fixtures.search_queries
                search('  beta  ')
                wait("Boolean(document.querySelector('.chat-row')?.textContent.includes('beta remote result'))")
                time.sleep(1.1)
                assert evaluate("document.querySelector('.chat-row')?.textContent.includes('beta remote result')")
                click('[aria-label="Close chat search"]')
                wait("Boolean(document.querySelector('.chat-row')?.textContent.includes('A calmer place to build'))")
                Fixtures.fail_route = True
                before = len(Fixtures.calls)
                exact_failed_draft = '  Preserve this failed draft\n '
                fill(exact_failed_draft)
                click('[aria-label="Send message"]')
                wait("document.querySelector('[role=alert]') !== null || document.querySelector('.event-card.failed') !== null")
                wait("!document.querySelector('[aria-label=\"Send message\"]').disabled")
                assert evaluate("document.querySelector('textarea').value") == exact_failed_draft
                assert len(Fixtures.calls) == before + 1
                viewport(390, 844)
                wait("document.querySelector('.chat-sidebar') === null")
                assert not evaluate('document.documentElement.scrollWidth > innerWidth')
                screenshot('phone.png')
                click('.composer .context-button')
                wait("document.querySelector('.context-tooltip') !== null")
                assert evaluate("(() => { const r=document.querySelector('.context-tooltip').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight })()")
                screenshot('phone-context-tooltip.png')
                key('\ue00c')
                viewport(320, 640)
                click('.composer .context-button')
                wait("document.querySelector('.context-tooltip') !== null")
                assert not evaluate('document.documentElement.scrollWidth > innerWidth')
                assert evaluate("(() => { const r=document.querySelector('.context-tooltip').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth })()")
                screenshot('narrow-context-tooltip.png')
                key('\ue00c')
                viewport(390, 844)
                fill('@'); wait("document.querySelector('.plugin-suggestions') !== null")
                assert not evaluate('document.documentElement.scrollWidth > innerWidth')
                screenshot('phone-plugins.png')
                key('\ue00c'); fill(exact_failed_draft)
                click('[aria-label="Expand conversations"]'); wait("document.querySelector('.chat-sidebar') !== null")
                screenshot('phone-navigation.png')
                click('.new-chat'); wait("document.querySelector('.launch-pad:not([hidden])') !== null")
                assert evaluate("document.querySelector('.launch-auto')?.textContent.includes('Jev')")
                assert evaluate("document.querySelector('.chat-sidebar') === null")
                screenshot('phone-new-chat.png')
                click('[aria-label="Expand conversations"]'); wait("document.querySelector('.chat-sidebar') !== null")
                click('[aria-label="Manage projects"]'); wait("document.querySelector('.page-header h2')?.textContent === 'Projects'")
                assert evaluate("document.querySelector('[aria-label=\"Expand conversations\"]') !== null")
                Fixtures.fail_bootstrap = True
                bidi.command('browsingContext.navigate', {'context': context, 'url': f'http://127.0.0.1:{server.server_port}', 'wait': 'complete'})
                wait("document.querySelector('.loading-screen [role=alert]') !== null")
                assert not evaluate("document.body.innerText.includes('Demo data')")
                screenshot('phone-startup-error.png')
                Fixtures.fail_bootstrap = False; Fixtures.fail_history = True; Fixtures.history_delay = .1
                click('.loading-screen button'); wait("document.querySelector('.app-shell') !== null")
                click('[aria-label="Expand conversations"]'); wait("document.querySelector('.history-notice [type=button]') !== null")
                Fixtures.fail_history = False
                click('.history-notice button'); wait("document.querySelector('.launch-recents button') !== null"); click('.launch-recents button'); wait("document.querySelector('.message.assistant') !== null && document.querySelector('.chat-progress') === null")
                if evaluate("document.querySelector('.chat-sidebar') !== null"): click('[aria-label="Collapse conversations"]')
                wait("document.querySelector('.chat-sidebar') === null")
                assert evaluate("document.querySelector('.chat-model-select')?.textContent.includes('6-luna') && document.querySelector('.chat-model-effort')?.textContent.includes('medium')")
                screenshot('phone-restored-effort.png')
                assert not evaluate('document.documentElement.scrollWidth > innerWidth')
                recorded = THREAD['turns'][0].pop('webui')
                try:
                    bidi.command('browsingContext.navigate', {'context': context, 'url': f'http://127.0.0.1:{server.server_port}', 'wait': 'complete'})
                    wait("document.querySelector('.launch-recents button') !== null"); click('.launch-recents button')
                    wait("document.querySelector('.message.assistant') !== null && document.querySelector('.chat-progress') === null")
                    assert evaluate("document.querySelector('.message.assistant .message-effort')?.textContent.includes('effort unknown') && document.querySelector('.chat-model-select')?.textContent.includes('Jev') && !document.querySelector('.chat-model-effort')")
                    screenshot('phone-unknown-effort.png')
                finally:
                    THREAD['turns'][0]['webui'] = recorded
                errors = [event for event in bidi.events if event.get('method') == 'log.entryAdded' and event.get('params', {}).get('level') == 'error' and event.get('params', {}).get('type') == 'javascript']
                assert not errors, errors
                (output / 'checks.json').write_text(json.dumps({'syntheticFixtures': True, 'desktop': measurements, 'phone': {'width': 390, 'height': 844}, 'checks': ['geometry', 'collapsed activity', 'context panel', 'single backend send', 'exact padded input', 'failed draft retained', 'phone no overflow', 'exclusive navigation', 'new chat', 'secondary page access'], 'featureChecks': ['shell before slow history', '@ skill/plugin/app/file selection and native metadata', 'per-message effort survives later model selections', 'Auto header restores recorded effort and leaves unknown effort explicit', 'fast typing after mentions survives delayed frames', 'deleted plugin mention does not reactivate implicitly', 'draft edited during send', 'pending send and draft survive secondary pages', 'stale searches cannot replace current results', 'relative Markdown images resolve in the project', 'inline images decoded and modal Escape/focus', 'one turn spinner, no bottom plate', 'last context total and hover limit', 'explicit startup error and history retry', 'phone plugin menu without overflow'], 'uncaughtErrors': len(errors)}, indent=2) + '\n')
                print('Browser checks passed: desktop 1440×1000, phone 390×844, one backend send and exact whitespace preservation.')
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
