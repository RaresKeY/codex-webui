#!/usr/bin/env python3
"""Check Jev activity in offscreen production Firefox using synthetic API data."""
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


class JevFixtures(SidebarFixtures):
    fail_activity = False
    activity_reads = 0
    records = [{"id": index, "thread_id": "c1", "turn_id": "t0" if index in (5, 3) else None,
                "source": {5: "auto", 4: "auto", 3: "manual", 2: "auto", 1: "preview"}[index],
                "status": {5: "submitted", 4: "stopped", 3: "submitted", 2: "pending", 1: "classified"}[index],
                "stage": "switching" if index == 4 else "routing" if index <= 2 else "sending",
                "started_at": "2026-10-06T12:00:00Z", "updated_at": "2026-10-06T12:00:01Z", "duration_ms": 1250,
                "decision": {"model": "gpt-6.1-sol", "effort": "low", "policy": "fixture-policy",
                             **({} if index == 3 else {"modelConfidence": .8, "effortConfidence": .7,
                             "modelProbabilities": {"gpt-6.1-sol": .8, "gpt-6-luna": .2},
                             "effortProbabilities": {"low": .7, "medium": .2, "high": .08, "xhigh": .015, "max": .005},
                             "usage": {"input_tokens": 1200, "output_tokens": 90},
                             "preparation": {key: {"choice": choice, "confidence": .8, "probabilities": {"yes": .8, "no": .1, "unclear": .1}} for key, choice in [("online_search", "yes"), ("fresh_information", "yes"), ("project_context", "unclear")]}})}} for index in range(5, 0, -1)]

    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith("/api/threads/") and path.endswith("/jev/activity"):
            type(self).activity_reads += 1
            if self.fail_activity:
                return self.reply({"detail": "Synthetic unavailable activity"}, 503)
            before = int(parse_qs(urlsplit(self.path).query).get("before", ["999"])[0])
            thread_id = path.split("/")[3]
            items = [item for item in self.records if item["id"] < before and item["thread_id"] == thread_id and item["source"] != "preview"]
            return self.reply({"data": items[:3], "nextCursor": items[2]["id"] if len(items) > 3 else None})
        if path.startswith("/api/jev/activity/") and path.endswith("/turn"):
            return self.reply({"threadId": "c1", "turnId": "t0", "status": "completed"})
        return super().do_GET()



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-bundle', type=Path)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'evidence/ui/jev-activity')
    args = parser.parse_args()
    if args.baseline_bundle:
        JevFixtures.bundle = args.baseline_bundle.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    helper = Path.home() / 'workspace/godot-performance-lab/tools/firefox_bidi_profile.py'
    sys.path.insert(0, str(helper.parent))
    spec = importlib.util.spec_from_file_location('permissions_bidi', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = ThreadingHTTPServer(('127.0.0.1', 0), JevFixtures)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory(prefix='webui-permission-browser-') as temporary:
        directory = Path(temporary)
        profile = directory / 'profile'
        profile.mkdir()
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
                wait("document.querySelector('.chat-surface:not([hidden]) .message.assistant') !== null && document.querySelector('.jev-turn-step') !== null")
                assert not evaluate("Boolean(document.querySelector('.context-panel'))")
                click('.jev-turn-step')
                wait("document.querySelector('.jev-context') !== null && document.querySelectorAll('.jev-record').length === 3 && document.querySelector('.jev-record[open]') !== null")
                assert evaluate("document.querySelectorAll('.jev-record[open] progress').length === 7")
                assert evaluate("document.querySelector('.jev-preparation').textContent.includes('Up-to-date information') && document.querySelector('.jev-preparation').textContent.includes('Useful')")
                assert evaluate("document.querySelector('.jev-record[open]').textContent.includes('1,200')")
                assert evaluate("document.querySelectorAll('.jev-record[open] .jev-process-flow li[data-state=complete]').length === 3")
                click('.jev-record[open] footer button')
                wait("document.querySelector('.jev-turn-status')?.textContent.includes('Completed')")
                screenshot('desktop.png')
                click('.jev-more')
                wait("document.querySelectorAll('.jev-record').length === 4 && !document.querySelector('.jev-more')")
                reads = JevFixtures.activity_reads
                time.sleep(6)
                assert JevFixtures.activity_reads == reads, 'Jev history must not poll'
                changed = {**JevFixtures.records[3], 'status':'stopped', 'updated_at':'2026-10-06T12:00:02Z'}
                JevFixtures.records[3] = changed
                JevFixtures.emit({'method':'webui/jevActivity','params':{'threadId':'c1','activity':changed}})
                wait("document.querySelectorAll('.jev-status.stopped').length === 2")
                assert evaluate("document.querySelectorAll('.jev-record').length === 4")
                assert JevFixtures.activity_reads == reads, 'Stage events must not refetch history'
                other = {**changed, 'id':99, 'thread_id':'chat-1', 'decision':{'model':'gpt-6-luna','effort':'low'}}
                JevFixtures.emit({'method':'webui/jevActivity','params':{'threadId':'chat-1','activity':other}})
                time.sleep(.2)
                assert evaluate("document.querySelectorAll('.jev-record').length === 4"), 'Another chat leaked into this sidebar'
                for width,height in [(390,844),(320,640)]:
                    viewport(width,height)
                    wait("!document.querySelector('.context-panel')")
                    click('[aria-label="Open context panel"]')
                    wait("document.querySelector('.jev-context') !== null")
                    assert not evaluate("Boolean(document.querySelector('.chat-sidebar'))")
                    assert not evaluate("document.documentElement.scrollWidth > innerWidth")
                    assert evaluate("(() => {const r=document.querySelector('.context-panel').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth})()")
                    screenshot(f'phone-{width}.png')
                    click('[aria-label="Close context panel"]')
                viewport(1440,1000)
                if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"):
                    click('[aria-label="Expand conversations"]')
                evaluate("(() => {Array.from(document.querySelectorAll('.chat-title')).find(button=>button.textContent.includes('Conversation 1 —')).click();return true;})()")
                wait("document.querySelector('.chat-heading').textContent.includes('Conversation 1 —')")
                evaluate("(() => {Array.from(document.querySelectorAll('.sidebar-nav button')).find(b=>b.textContent==='Jev').click();return true;})()")
                wait("document.querySelector('.jev-context') !== null && document.querySelectorAll('.jev-record').length === 1")
                assert not evaluate("document.querySelector('.jev-context').textContent.includes('1,200')"), 'Other chat details leaked'
                JevFixtures.fail_activity = True
                click('[aria-label="Reload Jev history"]')
                wait("document.querySelector('.jev-context [role=alert]') !== null")
                screenshot('error.png')
                JevFixtures.fail_activity = False
                click('[aria-label="Reload Jev history"]')
                wait("!document.querySelector('.jev-context [role=alert]')")
                errors = [event for event in bidi.events if event.get('method')=='log.entryAdded' and event.get('params',{}).get('type')=='javascript' and event.get('params',{}).get('level')=='error']
                assert not errors, f'{len(errors)} uncaught JavaScript errors'
                assert JevFixtures.calls == [], JevFixtures.calls
                result = {'syntheticFixtures':True,'viewports':['1440x1000','390x844','320x640'],'checks':['turn-linked sidebar','process stages','probabilities and usage','native status','pagination','no five-second polling','event updates preserve older runs','chat isolation','phone fit','read failure and reload'],'uncaughtJavaScriptErrors':len(errors),'modelCalls':0}
                (output/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
                print('Jev checks passed: turn-linked sidebar, event updates without polling, chat isolation, desktop/phone; no model calls.')

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
