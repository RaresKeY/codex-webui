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
        if path == "/api/jev/activity":
            type(self).activity_reads += 1
            if self.fail_activity:
                return self.reply({"detail": "Synthetic unavailable activity"}, 503)
            before = int(parse_qs(urlsplit(self.path).query).get("before", ["999"])[0])
            items = [item for item in self.records if item["id"] < before]
            return self.reply({"data": items[:4], "nextCursor": items[3]["id"] if len(items) > 4 else None})
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
                wait("document.querySelector('.sidebar-nav button') !== null")
                def open_jev():
                    evaluate("(() => {Array.from(document.querySelectorAll('.sidebar-nav button')).find(b => b.textContent === 'Jev').click(); return true;})()")
                    wait("document.querySelector('.jev-page') !== null && document.querySelectorAll('.jev-record').length === 4")
                open_jev()
                evaluate("(() => {document.querySelector('.jev-record summary').focus(); return true;})()")
                key('\ue006')
                wait("document.querySelector('.jev-record[open]') !== null")
                assert evaluate("document.querySelectorAll('.jev-record[open] progress').length === 7")
                assert evaluate("document.querySelector('.jev-preparation').textContent.includes('Up-to-date information') && document.querySelector('.jev-preparation').textContent.includes('Useful')")
                assert evaluate("document.querySelector('.jev-record[open]').textContent.includes('1,200')")
                click('.jev-record[open] footer button')
                wait("document.querySelector('.jev-turn-status')?.textContent.includes('Completed')")
                click('.jev-more')
                wait("document.querySelectorAll('.jev-record').length === 5 && !document.querySelector('.jev-more')")
                JevFixtures.records[3]['status'] = 'stopped'
                wait("document.querySelectorAll('.jev-status.stopped').length === 2")
                assert evaluate("document.querySelectorAll('.jev-record').length === 5")
                screenshot('desktop-details.png')
                for width,height,name in [(390,844,'phone'),(320,640,'narrow-phone')]:
                    viewport(width,height)
                    if evaluate("Boolean(document.querySelector('.chat-sidebar'))"):
                        click('[aria-label="Close conversations"]')
                        wait("!document.querySelector('.chat-sidebar')")
                    assert not evaluate("document.documentElement.scrollWidth > innerWidth")
                    screenshot(name+'-details.png')
                    click('[aria-label="Expand conversations"]')
                    wait("document.querySelector('.chat-sidebar') !== null")
                    assert evaluate("document.querySelector('.content-area').inert")
                    point = evaluate("(() => {const b=Array.from(document.querySelectorAll('.sidebar-nav button')).find(b=>b.textContent==='Jev'); const r=b.getBoundingClientRect(); return {x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)};})()")
                    bidi.command('input.performActions', {'context':context,'actions':[{'type':'pointer','id':'finger','parameters':{'pointerType':'touch'},'actions':[{'type':'pointerMove','origin':'viewport',**point},{'type':'pointerDown','button':0},{'type':'pointerUp','button':0}]}]})
                    wait("!document.querySelector('.chat-sidebar')")
                click('.jev-record[open] footer button:last-child')
                wait("document.querySelector('.chat-surface:not([hidden])') !== null && document.querySelector('.message.assistant') !== null")
                viewport(1440,1000)
                if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"):
                    click('[aria-label="Expand conversations"]')
                JevFixtures.records = []
                open_jev_empty = "(() => {Array.from(document.querySelectorAll('.sidebar-nav button')).find(b=>b.textContent==='Jev').click(); return true;})()"
                evaluate(open_jev_empty)
                wait("document.querySelector('.jev-empty')?.textContent.includes('No routing activity yet')")
                screenshot('empty.png')
                JevFixtures.fail_activity = True
                click('.jev-page .page-header .button')
                wait("document.querySelector('.jev-page [role=alert]') !== null")
                screenshot('error.png')
                JevFixtures.fail_activity = False
                click('.jev-page .page-header .button')
                wait("!document.querySelector('.jev-page [role=alert]')")
                errors = [event for event in bidi.events if event.get('method')=='log.entryAdded' and event.get('params',{}).get('type')=='javascript' and event.get('params',{}).get('level')=='error']
                assert not errors, f'{len(errors)} uncaught JavaScript errors'
                assert JevFixtures.calls == [], JevFixtures.calls
                result = {'syntheticFixtures': True, 'viewports': ['1440x1000','390x844','320x640'], 'checks': ['sidebar navigation','keyboard details','probabilities and usage','native actual turn status','older pagination','live update preserves older pages','phone drawer and touch','no horizontal overflow','open source chat','empty state','read failure and refresh'], 'uncaughtJavaScriptErrors': len(errors), 'modelCalls': 0}
                (output/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
                print('Jev browser checks passed at desktop and phone widths; no model calls.')

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
