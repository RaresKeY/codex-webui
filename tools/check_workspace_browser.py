#!/usr/bin/env python3
"""Check editable file links with synthetic APIs in offscreen Firefox."""
import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer

from check_browser import ROOT
from urllib.parse import parse_qs, urlsplit
from check_sidebar_browser import SidebarFixtures


class FileFixtures(SidebarFixtures):
    fail_save = True
    file_content = 'This is a test file.\n\nYou can edit this text in the side panel.\n'
    saves = []
    thread = {"id":"c1", "name":"Open a file in the sidebar", "cwd":"/workspace/codex-webui-2", "status":"idle", "turns":[{"id":"t1", "status":"completed", "items":[{"id":"a", "type":"agentMessage", "phase":"final_answer", "text":"Saved [test.txt](test.txt). [Missing file](missing.txt). [Website](https://example.org/report)."}]}]}
    threads = [thread]
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/threads/c1': return self.reply({'thread':self.thread})
        if path == '/api/workspace/tree': return self.reply([{'name':'test.txt','path':'test.txt','type':'file'}, {'name':'notes.txt','path':'notes.txt','type':'file'}])
        if path == '/api/workspace/file':
            selected = parse_qs(urlsplit(self.path).query).get('path',[''])[0]
            if selected.endswith('missing.txt'): return self.reply({'detail':'File not found'},404)
            return self.reply({'path': selected.removeprefix('/workspace/codex-webui-2/'), 'content':self.file_content if selected.endswith('test.txt') else 'Notes\n'})
        if path.endswith('/jev/activity'): return self.reply({'data':[], 'nextCursor':None})
        return super().do_GET()
    def do_PUT(self):
        if urlsplit(self.path).path == '/api/workspace/file':
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
            type(self).saves.append(body)
            time.sleep(.2)
            if self.fail_save: return self.reply({'detail':'Synthetic save failure'},503)
            type(self).file_content = body['content']
            return self.reply({'ok':True})
        return super().do_PUT()



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-bundle', type=Path)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'evidence/ui/file-view')
    args = parser.parse_args()
    if args.baseline_bundle:
        FileFixtures.bundle = args.baseline_bundle.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    helper = Path.home() / 'workspace/godot-performance-lab/tools/firefox_bidi_profile.py'
    sys.path.insert(0, str(helper.parent))
    spec = importlib.util.spec_from_file_location('permissions_bidi', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = ThreadingHTTPServer(('127.0.0.1', 0), FileFixtures)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory(prefix='webui-permission-browser-') as temporary:
        directory = Path(temporary)
        profile = directory / 'profile'
        profile.mkdir()
        (profile / 'user.js').write_text('user_pref("ui.primaryPointerCapabilities", 6);\nuser_pref("ui.allPointerCapabilities", 6);\n')
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        with (directory / 'browser.log').open('w') as log:
            process = subprocess.Popen(['gamescope', '--backend', 'headless', '-W', '1440', '-H', '1000', '--', 'firefox', '--headless', '--no-remote', '--profile', str(profile), '--remote-allow-system-access', '--remote-debugging-port', str(port)], stdout=log, stderr=log, start_new_session=True)
            bidi = None
            try:
                for _ in range(100):
                    try:
                        bidi = module.Bidi(port=port)
                        break
                    except (OSError, RuntimeError):
                        time.sleep(.1)
                assert bidi is not None, 'Firefox BiDi startup failed'
                bidi.command('session.new', {'capabilities': {}})
                bidi.command('session.subscribe', {'events': ['log.entryAdded']})
                context = str(bidi.command('browsingContext.create', {'type': 'tab'})['result']['context'])
                url = f'http://127.0.0.1:{server.server_port}/'
                def evaluate(expression):
                    return module.evaluate_json(bidi, context, f'({expression}) ?? null')
                def wait(expression):
                    for _ in range(120):
                        if evaluate(expression):
                            return
                        time.sleep(.05)
                    screenshot('failure.png')
                    raise AssertionError(expression)
                def screenshot(name):
                    result = bidi.command('browsingContext.captureScreenshot', {'context':context, 'origin':'viewport'})
                    (output / name).write_bytes(base64.b64decode(result['result']['data']))
                def click(selector):
                    evaluate(f"(() => {{document.querySelector({json.dumps(selector)}).click(); return true;}})()")
                def key(value):
                    bidi.command('input.performActions', {'context':context, 'actions':[{'type':'key','id':'keyboard','actions':[{'type':'keyDown','value':value},{'type':'keyUp','value':value}]}]})
                def viewport(width, height):
                    bidi.command('browsingContext.setViewport', {'context':context,'viewport':{'width':width,'height':height}})
                    time.sleep(.25)
                def bounds():
                    return evaluate("(() => {const menu=document.querySelector('.permissions-menu')?.getBoundingClientRect(); return {overflow:document.documentElement.scrollWidth > innerWidth, menuFits:!menu || (menu.left >= 0 && menu.right <= innerWidth && menu.top >= 0 && menu.bottom <= innerHeight)};})()")
                def touch(selector):
                    point = evaluate(f"(() => {{const r=document.querySelector({json.dumps(selector)}).getBoundingClientRect(); return {{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}};}})()")
                    bidi.command('input.performActions', {'context':context,'actions':[{'type':'pointer','id':'finger','parameters':{'pointerType':'touch'},'actions':[{'type':'pointerMove','origin':'viewport',**point},{'type':'pointerDown','button':0},{'type':'pointerUp','button':0}]}]})
                viewport(1440, 1000)
                bidi.command('browsingContext.navigate', {'context':context,'url':url,'wait':'complete'})
                wait("document.querySelector('.chat-title') !== null")
                click('.chat-title')
                wait("document.querySelector('a[href=\"test.txt\"]') !== null")
                assert evaluate("document.querySelector('[aria-label=\"Sources and outputs\"]').title === 'Sources and outputs' && document.querySelector('[aria-label=\"Open context panel\"]').title === 'Open context panel'")
                assert evaluate("document.querySelector('a[href^=\"https://example.org\"]').target === '_blank'")
                click('a[href="test.txt"]')
                wait("document.querySelector('.workspace-numbered-editor textarea')?.value.includes('This is a test file')")
                assert evaluate("document.querySelector('.workspace-file-tab').textContent.includes('test.txt') && document.querySelector('.workspace-breadcrumbs').textContent.includes('codex-webui-2') && document.querySelectorAll('.workspace-line-number').length === 4")
                wait("document.querySelectorAll('.workspace-file-tree .tree-row').length === 2")
                assert evaluate("document.querySelector('.workspace-file-tree .tree-row.active')?.textContent.includes('test.txt')")
                screenshot('desktop-file.png')
                evaluate("(() => {const t=document.querySelector('.workspace-numbered-editor textarea');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(t,'Edited test file\\nSecond line\\n');t.dispatchEvent(new Event('input',{bubbles:true}));return true})()")
                wait("document.querySelector('[aria-label=\"Unsaved changes\"]') !== null")
                evaluate("(() => {const b=document.querySelector('.workspace-file-actions .button');b.click();b.click();return true})()")
                wait("document.querySelector('.workspace-file-error')?.textContent.includes('Synthetic save failure')")
                assert evaluate("document.querySelector('.workspace-numbered-editor textarea').value.startsWith('Edited test file')")
                assert len(FileFixtures.saves) == 1
                FileFixtures.fail_save = False
                click('.workspace-file-actions .button')
                wait("!document.querySelector('[aria-label=\"Unsaved changes\"]') && document.querySelector('.workspace-file-actions .button').disabled")
                assert FileFixtures.file_content == 'Edited test file\nSecond line\n'
                click('[aria-label="Close context panel"]')
                click('a[href="missing.txt"]')
                wait("document.querySelector('.workspace-file-main [role=\"alert\"]')?.textContent.includes('File not found')")
                assert not evaluate("Boolean(document.querySelector('.workspace-numbered-editor textarea'))")
                click('[aria-label="Close context panel"]')
                click('a[href="test.txt"]')
                wait("document.querySelector('.workspace-numbered-editor textarea')?.value.startsWith('Edited test file')")
                evaluate("(() => {const t=document.querySelector('.workspace-numbered-editor textarea');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(t,'Unsaved draft');t.dispatchEvent(new Event('input',{bubbles:true}));return true})()")
                wait("document.querySelector('[aria-label=\"Unsaved changes\"]') !== null")
                click('[aria-label="Close context panel"]')
                click('a[href="test.txt"]')
                wait("document.querySelector('.workspace-numbered-editor textarea')?.value === 'Unsaved draft'")
                click('.workspace-file-tree .tree-row')
                wait("document.querySelector('.workspace-numbered-editor textarea')?.value === 'Unsaved draft'")
                evaluate("(() => {const t=document.querySelector('.workspace-numbered-editor textarea');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(t,'Line\\n'.repeat(2000));t.dispatchEvent(new Event('input',{bubbles:true}));return true})()")
                wait("document.querySelector('.workspace-numbered-editor textarea').value.length > 9000")
                evaluate("(() => {const t=document.querySelector('.workspace-numbered-editor textarea');t.scrollTop=11000;t.dispatchEvent(new Event('scroll'));return true})()")
                wait("Number(document.querySelector('.workspace-line-number')?.textContent)>400")
                assert evaluate("document.querySelectorAll('.workspace-line-number').length<=120")
                evaluate("(() => {const t=document.querySelector('.workspace-numbered-editor textarea');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(t,'Unsaved draft');t.dispatchEvent(new Event('input',{bubbles:true}));t.scrollTop=0;t.dispatchEvent(new Event('scroll'));return true})()")
                for width,height in [(390,844),(320,640)]:
                    viewport(width,height)
                    if not evaluate("Boolean(document.querySelector('.workspace-file-view'))"): click('a[href="test.txt"]')
                    wait("document.querySelector('.workspace-numbered-editor textarea')?.value === 'Unsaved draft'")
                    assert evaluate("(() => {const r=document.querySelector('.workspace-file-view').getBoundingClientRect(),e=document.querySelector('.workspace-numbered-editor textarea').getBoundingClientRect();return document.documentElement.scrollWidth<=innerWidth && r.right<=innerWidth && e.width>150 && document.querySelector('.workspace-file-tree').getBoundingClientRect().bottom<=innerHeight})()")
                    wait("(() => {const t=document.querySelector('.context-tool-tabs [aria-selected=\"true\"]').getBoundingClientRect();return t.left>=0 && t.right<=innerWidth})()")
                    screenshot(f'phone-{width}-file.png')
                errors = [event for event in bidi.events if event.get('method') == 'log.entryAdded' and event.get('params', {}).get('type') == 'javascript' and event.get('params', {}).get('level') == 'error']
                assert not errors, errors
                (output/'checks.json').write_text(json.dumps({'syntheticFixtures':True,'viewports':['1440x1000','390x844','320x640'],'saves':len(FileFixtures.saves),'draftRetained':True,'uncaughtErrors':len(errors)},indent=2)+'\n')
                print('File browser checks passed: file links, editable numbered view, breadcrumbs/tree, visible read/save errors, successful save, retained draft and desktop/phone fit.')

            finally:
                server.stopping = True
                server.shutdown()
                if bidi:
                    try:
                        bidi.command('session.end', {})
                    except Exception:
                        pass
                    bidi.close()
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=5)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)


if __name__ == '__main__':
    main()
