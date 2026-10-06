#!/usr/bin/env python3
"""Check turn presentation and response branching with synthetic APIs in offscreen Firefox."""
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


class TurnFixtures(SidebarFixtures):
    forks = []
    fail_fork = True
    thread = {"id":"c1", "name":"Research and outputs", "cwd":"/workspace/codex-webui-2", "status":"idle", "turns":[
        {"id":"early", "status":"completed", "durationMs":27000, "startedAt":1791300000, "completedAt":1791300027, "items":[
            {"id":"u", "type":"userMessage", "content":[{"type":"text","text":"Find recent research and write a short report."}]},
            {"id":"comment", "type":"agentMessage", "phase":"commentary", "text":"I’ll check the sources and prepare the report."},
            {"id":"search", "type":"webSearch", "query":"research", "results":[{"title":"Publisher’s report","url":"https://example.org/report"}]},
            {"id":"file", "type":"fileChange", "status":"completed", "changes":[{"path":"/workspace/codex-webui-2/report.md", "diff":"+Short research report", "kind":{"type":"add"}}]},
            {"id":"answer", "type":"agentMessage", "phase":"final_answer", "text":"The report is ready. [Publisher’s report](https://example.org/report)."}]},
        {"id":"later", "status":"completed", "durationMs":8000, "completedAt":1791300035, "items":[
            {"id":"u2", "type":"userMessage", "content":[{"type":"text","text":"What next?"}]},
            {"id":"a2", "type":"agentMessage", "phase":"final_answer", "text":"Review the report and choose a follow-up."}]}]}
    threads = [thread]
    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ('/api/threads/c1', '/api/threads/branch'):
            thread = self.thread if path.endswith('/c1') else {**self.thread, 'id':'branch', 'name':'Branched research', 'turns':self.thread['turns'][:1]}
            return self.reply({'thread':thread})
        if path.endswith('/jev/activity'):
            return self.reply({'data':[], 'nextCursor':None})
        return super().do_GET()
    def do_POST(self):
        if self.path == '/api/threads/c1/fork':
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            type(self).forks.append(body)
            time.sleep(.2)
            if self.fail_fork: return self.reply({'detail':'Synthetic branch unavailable'}, 503)
            return self.reply({'thread':{**self.thread, 'id':'branch', 'name':'Branched research', 'turns':self.thread['turns'][:1]}},201)
        return super().do_POST()



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-bundle', type=Path)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'evidence/ui/turn-presentation')
    args = parser.parse_args()
    if args.baseline_bundle:
        TurnFixtures.bundle = args.baseline_bundle.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    helper = Path.home() / 'workspace/godot-performance-lab/tools/firefox_bidi_profile.py'
    sys.path.insert(0, str(helper.parent))
    spec = importlib.util.spec_from_file_location('permissions_bidi', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = ThreadingHTTPServer(('127.0.0.1', 0), TurnFixtures)
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
                wait("document.querySelectorAll('[aria-label=\"Branch chat from here\"]').length === 2")
                assert evaluate("document.querySelector('.turn-work > summary').textContent.includes('Worked for 27s') && !document.querySelector('.turn-work').open")
                assert evaluate("document.querySelector('.event-feed > .message.assistant').textContent.includes('The report is ready') && getComputedStyle(document.querySelector('.response-time')).opacity === '0'")
                assert not evaluate("Boolean(document.querySelector('[aria-label*=\"Rate\"], [aria-label*=\"Thumb\"]'))")
                screenshot('desktop-collapsed.png')
                click('.turn-work > summary')
                assert evaluate("document.querySelector('.turn-work').open && document.querySelector('.turn-work').textContent.includes('I’ll check the sources') && document.querySelector('.turn-work').textContent.includes('Searched the web')")
                screenshot('desktop-expanded.png')
                click('.turn-work > summary')
                point = evaluate("(() => {const r=document.querySelector('.event-feed > .message.assistant').getBoundingClientRect();return {x:Math.round(r.x+40),y:Math.round(r.y+20)}})()")
                bidi.command('input.performActions', {'context':context,'actions':[{'type':'pointer','id':'mouse','parameters':{'pointerType':'mouse'},'actions':[{'type':'pointerMove','origin':'viewport',**point}]}]})
                wait("getComputedStyle(document.querySelector('.response-time')).opacity === '1'")
                screenshot('desktop-hover-time.png')
                click('[aria-label="Sources and outputs"]')
                wait("document.querySelector('.chat-summary') !== null")
                assert evaluate("document.querySelectorAll('.chat-summary a').length === 1 && document.querySelector('.chat-summary').textContent.includes('report.md') && document.querySelector('.chat-summary a small').textContent === 'example.org'")
                geometry = evaluate("(() => {const s=document.querySelector('.chat-summary').getBoundingClientRect(),m=document.querySelector('.event-feed > .message.assistant').getBoundingClientRect();return {summaryLeft:s.left,messageRight:m.right,overflow:document.documentElement.scrollWidth>innerWidth}})()")
                assert not geometry['overflow'] and geometry['messageRight'] <= geometry['summaryLeft'], geometry
                screenshot('desktop-summary.png')
                for width,height in [(390,844),(320,640)]:
                    viewport(width,height)
                    wait("document.querySelector('.chat-summary') !== null")
                    assert evaluate("(() => {const r=document.querySelector('.chat-summary').getBoundingClientRect();return r.left>=0 && r.right<=innerWidth && r.top>=0 && r.bottom<=innerHeight && document.documentElement.scrollWidth<=innerWidth})()")
                    screenshot(f'phone-{width}-summary.png')
                click('[aria-label="Close sources and outputs"]')
                assert evaluate("document.activeElement.getAttribute('aria-label') === 'Sources and outputs'")
                viewport(1440,1000)
                click('[aria-label="Branch chat from here"]')
                click('[aria-label="Branch chat from here"]')
                wait("Boolean(document.querySelector('.branch-error'))")
                assert TurnFixtures.forks == [{'turn_id':'early'}], TurnFixtures.forks
                TurnFixtures.fail_fork = False
                click('[aria-label="Branch chat from here"]')
                wait("document.querySelector('.conversation-title')?.textContent === 'Branched research' && document.querySelectorAll('[aria-label=\"Branch chat from here\"]').length === 1")
                assert not evaluate("document.querySelector('.event-feed').textContent.includes('What next?')")
                assert TurnFixtures.forks == [{'turn_id':'early'},{'turn_id':'early'}]
                assert not TurnFixtures.calls, 'Branching must not submit prompts'
                screenshot('desktop-branch.png')
                errors = [event for event in bidi.events if event.get('method') == 'log.entryAdded' and event.get('params', {}).get('type') == 'javascript' and event.get('params', {}).get('level') == 'error']
                assert not errors, errors
                (output/'checks.json').write_text(json.dumps({'syntheticFixtures':True,'viewports':['1440x1000','390x844','320x640'],'forks':TurnFixtures.forks,'modelCalls':0,'uncaughtErrors':len(errors)},indent=2)+'\n')
                print('Turn browser checks passed: collapsed/expanded work, website/output summary, hover time, exact branch point and visible failure, desktop/phone; no ratings or inference.')

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
