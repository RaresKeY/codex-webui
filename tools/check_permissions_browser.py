#!/usr/bin/env python3
"""Check permission selection in production Firefox using synthetic API data."""
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

from check_browser import Fixtures, ROOT


class PermissionFixtures(Fixtures):
    execution = {}
    reject_execution = False
    permissions = {}
    permission_calls = []
    reject_permissions = False
    history_delay = .1

    def permission_thread(self):
        parts = self.path.split('?')[0].split('/')
        return parts[3] if len(parts) == 5 and parts[1:3] == ['api', 'threads'] and parts[4] == 'permissions' else None

    def execution_thread(self):
        parts = self.path.split('?')[0].split('/')
        return parts[3] if len(parts) == 5 and parts[1:3] == ['api', 'threads'] and parts[4] == 'execution' else None

    def do_GET(self):
        if thread := self.execution_thread():
            return self.reply(self.execution.get(thread, {'model':'auto','effort':'medium'}))
        thread = self.permission_thread()
        if thread:
            return self.reply({'mode': self.permissions.get(thread, 'default')})
        return super().do_GET()

    def do_PATCH(self):
        if thread := self.execution_thread():
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
            time.sleep(.4)
            if self.reject_execution:
                return self.reply({'detail':'Synthetic model rejection'},409)
            self.execution[thread] = body
            return self.reply({**body,'acknowledged':True})
        thread = self.permission_thread()
        if not thread:
            return super().do_PATCH()
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
        self.permission_calls.append((thread, body))
        time.sleep(.4)
        if self.reject_permissions:
            return self.reply({'detail': 'Synthetic permission rejection. The choice was not applied.'}, 409)
        assert set(body) == {'mode'} and body['mode'] in ('default', 'full-auto', 'yolo')
        self.permissions[thread] = body['mode']
        return self.reply({'mode': body['mode'], 'acknowledged': True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-bundle', type=Path)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'evidence/ui/permissions')
    args = parser.parse_args()
    if args.baseline_bundle:
        PermissionFixtures.bundle = args.baseline_bundle.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    helper = Path.home() / 'workspace/godot-performance-lab/tools/firefox_bidi_profile.py'
    sys.path.insert(0, str(helper.parent))
    spec = importlib.util.spec_from_file_location('permissions_bidi', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = ThreadingHTTPServer(('127.0.0.1', 0), PermissionFixtures)
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
                wait("document.querySelector('.launch-pad:not([hidden])') !== null && document.querySelector('.launch-recents button') !== null")
                click('.launch-recents button')
                wait("Boolean(document.querySelector('.message.assistant') && document.querySelector('textarea'))")
                if args.baseline_bundle:
                    for width, height, name in [(1440,1000,'before-desktop.png'),(390,844,'before-phone.png')]:
                        viewport(width,height)
                        assert not bounds()['overflow']
                        screenshot(name)
                    print('Permission-control baseline captured at desktop and phone widths.')
                    return
                wait("document.querySelector('.permissions-trigger')?.textContent.includes('Default') && !document.querySelector('.permissions-trigger').disabled")
                screenshot('after-desktop.png')
                click('.permissions-trigger')
                wait("document.querySelectorAll('[role=menuitemradio]').length === 3")
                assert bounds() == {'overflow':False, 'menuFits':True}
                screenshot('desktop-menu.png')
                evaluate("(() => {const t=document.querySelector('textarea'); Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(t,'Keep this draft'); t.dispatchEvent(new Event('input',{bubbles:true})); return true;})()")
                click('[role=menuitemradio]:nth-of-type(2)')
                wait("document.querySelector('.permissions-menu')?.getAttribute('aria-busy') === 'true'")
                assert evaluate("document.querySelector('[aria-label=\"Send message\"]').disabled")
                wait("document.querySelector('.permissions-trigger')?.textContent.includes('Auto approve') && !document.querySelector('.permissions-menu')")
                assert evaluate("document.querySelector('textarea').value") == 'Keep this draft'
                click('.permissions-trigger')
                wait("document.activeElement?.getAttribute('aria-checked') === 'true'")
                assert evaluate("document.activeElement.textContent.includes('Auto approve')")
                key('\ue010')  # End: last choice.
                wait("document.activeElement.textContent.includes('YOLO')")
                key('\ue007')
                wait("document.querySelector('.permissions-trigger')?.textContent.includes('YOLO') && !document.querySelector('.permissions-menu')")
                assert len(PermissionFixtures.permission_calls) == 2
                assert not PermissionFixtures.calls, 'Permission buttons must not submit the composer'
                bidi.command('browsingContext.navigate', {'context':context,'url':url,'wait':'complete'})
                wait("document.querySelector('.launch-recents button') !== null")
                click('.launch-recents button')
                wait("document.querySelector('.permissions-trigger')?.textContent.includes('YOLO') && !document.querySelector('.permissions-trigger').disabled")
                PermissionFixtures.reject_permissions = True
                click('.permissions-trigger')
                click('[role=menuitemradio]:nth-of-type(1)')
                wait("document.querySelector('.permissions-error')?.textContent.includes('Synthetic permission rejection')")
                assert evaluate("document.querySelector('.permissions-trigger').textContent.includes('YOLO')")
                screenshot('desktop-rejection.png')
                PermissionFixtures.reject_permissions = False
                click('[role=menuitemradio]:nth-of-type(1)')
                wait("document.querySelector('.permissions-trigger')?.textContent.includes('Default') && !document.querySelector('.permissions-menu')")
                for width, height, name in [(390,844,'phone-menu.png'),(320,640,'narrow-phone-menu.png')]:
                    viewport(width,height)
                    touch('.permissions-trigger')
                    wait("document.querySelector('.permissions-menu') !== null")
                    assert bounds() == {'overflow':False, 'menuFits':True}, bounds()
                    screenshot(name)
                    key('\ue00c')
                    wait("!document.querySelector('.permissions-menu')")
                    assert evaluate("document.activeElement.classList.contains('permissions-trigger')")
                viewport(1440,1000)
                click('.execution-trigger')
                wait("document.querySelector('.execution-menu') !== null")
                assert evaluate("document.querySelectorAll('.execution-menu > [role=menuitemradio]').length") == 3
                click('.execution-menu > [role=menuitemradio]:nth-of-type(3)')
                wait("document.querySelector('.execution-menu')?.getAttribute('aria-busy') === 'true'")
                assert evaluate("document.querySelector('[aria-label=\"Send message\"]').disabled")
                wait("document.querySelector('.execution-menu')?.getAttribute('aria-busy') === 'false'")
                click('.effort-options button:nth-of-type(3)')
                wait("document.querySelector('.execution-trigger')?.getAttribute('aria-label').includes('high') && !document.querySelector('.execution-trigger').disabled")
                wait("!document.querySelector('.execution-trigger').disabled && document.querySelector('.effort-options button:nth-of-type(3)').getAttribute('aria-checked') === 'true'")
                assert PermissionFixtures.execution['c1'] == {'model':'gpt-6.1-sol','effort':'high'}, PermissionFixtures.execution
                assert evaluate("document.querySelector('.chat-model-select')?.textContent.includes('Manual') && document.querySelector('.chat-model-select')?.textContent.includes('6.1-sol') && document.querySelector('.chat-model-effort')?.textContent.includes('high')")
                screenshot('desktop-speed-menu.png')
                key('\ue00c')
                bidi.command('browsingContext.navigate', {'context':context,'url':url,'wait':'complete'})
                wait("document.querySelector('.launch-recents button') !== null")
                click('.launch-recents button')
                wait("document.querySelector('.execution-trigger')?.getAttribute('aria-label').includes('high') && !document.querySelector('.execution-trigger').disabled")
                assert evaluate("document.querySelector('.chat-model-effort')?.textContent.includes('high')"), 'Saved manual effort must take precedence over historical effort after reload'
                click('.execution-trigger')
                wait("document.querySelector('.execution-menu') !== null")
                PermissionFixtures.reject_execution = True
                click('.effort-options button:nth-of-type(5)')
                wait("document.querySelector('.execution-menu .permissions-error')?.textContent.includes('Synthetic model rejection')")
                assert evaluate("document.querySelector('.execution-trigger').getAttribute('aria-label').includes('high')")
                PermissionFixtures.reject_execution = False
                wait("!document.querySelector('.execution-trigger').disabled && document.activeElement?.getAttribute('aria-checked') === 'true'")
                key('\ue00c')
                wait("!document.querySelector('.execution-menu')")
                for width,height,name in [(390,844,'phone-speed-menu.png'),(320,640,'narrow-phone-speed-menu.png')]:
                    viewport(width,height)
                    touch('.execution-trigger')
                    wait("document.querySelector('.execution-menu') !== null")
                    assert bounds() == {'overflow':False,'menuFits':True}, bounds()
                    screenshot(name)
                    key('\ue00c')
                assert not PermissionFixtures.calls, 'Settings must never submit the composer'
                PermissionFixtures.emit({'method':'turn/started','params':{'threadId':'c1','turn':{'id':'active-fixture'}}})
                wait("document.querySelector('.permissions-trigger').disabled")
                PermissionFixtures.emit({'method':'turn/completed','params':{'threadId':'c1','turn':{'id':'active-fixture','status':'completed'}}})
                wait("!document.querySelector('.permissions-trigger').disabled")
                errors = [event for event in bidi.events if event.get('method') == 'log.entryAdded' and event.get('params',{}).get('level') == 'error' and event.get('params',{}).get('type') == 'javascript']
                assert not errors, f'{len(errors)} uncaught JavaScript errors'
                result = {'syntheticFixtures':True,'viewports':['1440x1000','390x844','320x640'],'checks':['menu choices','native acknowledgement gate','pending send disabled','draft retained','keyboard End/Enter/Escape and focus','saved selection after reload','rejected change retains choice','touch targets and no overflow','active turn disables changes','permission buttons never send a prompt','manual model and effort selection','model selection persistence and rejected-change retention','speed control at phone widths'],'uncaughtJavaScriptErrors':len(errors)}
                (output/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
                print('Permission browser checks passed: desktop, phone, keyboard, touch, acknowledgement, persistence, failure and active-turn states; no model calls.')
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
