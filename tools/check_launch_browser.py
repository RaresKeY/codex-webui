#!/usr/bin/env python3
"""Check sidebar layout and navigation in production Firefox using synthetic API data."""
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

from check_browser import ROOT, THREAD
from urllib.parse import parse_qs, urlsplit
from check_permissions_browser import PermissionFixtures


class SidebarFixtures(PermissionFixtures):
    projects = [{'id': 1, 'name': 'WebUI 2', 'workspace': '/workspace/codex-webui-2'}]
    threads = [{**THREAD, 'id': f'recent-{i}', 'name': f'Recent chat {i}', 'updatedAt': time.time()-86400-i, 'turns': []} for i in range(12)]
    created = 0
    fast = False
    sockets = []
    calls = []
    fail_project = False
    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/api/bootstrap':
            return self.reply({'health': {'codex_available': True}, 'projects': self.projects, 'threads': {'data': []}, 'models': {'data': []}, 'system': {'runtime': 'container'}, 'tasks': [], 'workspace': [], 'features': {}})
        if path == '/api/threads': return self.reply({'data': self.threads})
        if path.startswith('/api/threads/') and path.count('/') == 3:
            return self.reply({'thread': next((chat for chat in self.threads if chat['id'] == path.split('/')[3]), {})})
        return super().do_GET()
    def do_PATCH(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
        thread_id = self.path.split('/')[3]
        for chat in self.threads:
            if chat['id'] == thread_id and 'name' in body: chat['name'] = body['name']
            if chat['id'] == thread_id and 'project_id' in body: chat['projectId'] = str(body['project_id']) if body['project_id'] else ''
        return self.reply(body)
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
        self.calls.append((self.path, body))
        if self.path == '/api/projects':
            time.sleep(.25)
            if self.fail_project: return self.reply({'detail': 'Synthetic invalid workspace'}, 422)
            project = {**body, 'id': len(self.projects)+1, 'updated_at': time.time()}
            self.projects.append(project)
            return self.reply(project, 201)
        if self.path == '/api/threads':
            time.sleep(.5)
            type(self).created += 1
            chat = {**THREAD, 'id': f'launch-{self.created}', 'name': 'Untitled conversation', 'projectId': '', 'status': 'idle', 'updatedAt': time.time(), 'turns': []}
            self.threads.insert(0, chat)
            return self.reply({'thread': chat}, 201)
        if self.path.endswith('/messages'):
            thread_id = self.path.split('/')[3]
            if 'fail' in body['input']:
                return self.stream_reply([{'error': {'status': 409, 'message': 'Synthetic routing failure. Prompt was not sent.'}}])
            from check_browser import DECISION
            decision = {**DECISION, 'model': 'gpt-6-luna', 'effort': 'low'}
            turn_id = 'turn-' + thread_id
            chat = next(chat for chat in self.threads if chat['id'] == thread_id)
            chat['status'] = 'active'
            self.emit({'method': 'turn/started', 'params': {'threadId': thread_id, 'turn': {'id': turn_id}}})
            def finish():
                chat['status'] = 'idle'
                self.emit({'method': 'turn/completed', 'params': {'threadId': thread_id, 'turn': {'id': turn_id, 'status': 'completed'}}})
            if self.fast:
                finish()
                time.sleep(.5)
            else: threading.Timer(4, finish).start()
            return self.stream_reply([{'stage': 'routing'}, {'result': {'turn': {'id': turn_id}, 'decision': decision, 'modelChangeAcknowledged': True}}])
        return self.reply({})



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-bundle', type=Path)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'evidence/ui/launch-pad')
    args = parser.parse_args()
    if args.baseline_bundle:
        SidebarFixtures.bundle = args.baseline_bundle.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    helper = Path.home() / 'workspace/godot-performance-lab/tools/firefox_bidi_profile.py'
    sys.path.insert(0, str(helper.parent))
    spec = importlib.util.spec_from_file_location('permissions_bidi', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = ThreadingHTTPServer(('127.0.0.1', 0), SidebarFixtures)
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
                wait("document.querySelector('.launch-pad:not([hidden])') !== null && document.querySelectorAll('.launch-recents .launch-row').length === 10")
                assert not SidebarFixtures.calls, 'Landing must not create or send a chat'
                screenshot('desktop-launch.png')
                def fill_prompt(value):
                    evaluate(f"(() => {{const t=document.querySelector('[aria-label=\"New chat prompt\"]'); Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(t,{json.dumps(value)}); t.dispatchEvent(new Event('input',{{bubbles:true}})); return true;}})()")
                asks = ['  First independent ask\n\n ', '  Second ask Ω\n ']
                for ask in asks:
                    fill_prompt(ask)
                    click('[aria-label="Launch new chat"]')
                    wait("document.querySelector('[aria-label=\"New chat prompt\"]').value === ''")
                wait("document.querySelectorAll('.launch-recents .chat-activity-spinner').length >= 2")
                assert evaluate("Boolean(document.querySelector('.launch-pad:not([hidden])'))")
                screenshot('desktop-running.png')
                wait("document.querySelectorAll('.launch-recents .chat-unread-dot').length >= 2")
                messages = [body['input'] for path,body in SidebarFixtures.calls if path.endswith('/messages')]
                assert messages == asks, messages
                assert len([path for path,_ in SidebarFixtures.calls if path == '/api/threads']) == 2
                screenshot('desktop-finished.png')
                bidi.command('browsingContext.navigate', {'context':context,'url':url,'wait':'complete'})
                wait("document.querySelectorAll('.launch-recents .chat-unread-dot').length >= 2")
                click('.launch-recents .launch-row')
                wait("document.querySelector('.chat-surface:not([hidden])') !== null")
                assert evaluate("document.querySelectorAll('.launch-recents .chat-unread-dot').length") == 1
                opened = SidebarFixtures.threads[0]['id']
                SidebarFixtures.emit({'method': 'turn/completed', 'params': {'threadId': opened, 'turn': {'id': 'turn-' + opened, 'status': 'completed'}}})
                time.sleep(.15)
                assert evaluate("document.querySelectorAll('.launch-recents .chat-unread-dot').length") == 1
                before = len(SidebarFixtures.calls)
                click('.new-chat')
                wait("document.querySelector('.launch-pad:not([hidden])') !== null")
                assert len(SidebarFixtures.calls) == before
                SidebarFixtures.emit({'method': 'turn/completed', 'params': {'threadId': opened, 'turn': {'id': 'turn-' + opened, 'status': 'completed'}}})
                time.sleep(.15)
                assert evaluate("document.querySelectorAll('.launch-recents .chat-unread-dot').length") == 1
                failed_ask = '  fail and preserve this draft\n '
                fill_prompt(failed_ask); click('[aria-label="Launch new chat"]')
                wait("document.querySelector('.launch-job [role=alert]') !== null")
                click('.launch-job [role=alert] button')
                assert evaluate("document.querySelector('[aria-label=\"New chat prompt\"]').value") == failed_ask
                assert len([path for path,_ in SidebarFixtures.calls if path.endswith('/messages')]) == 3
                # Newer external chats can push the failed chat out of the recent ten.
                for i in range(11):
                    SidebarFixtures.threads.insert(0, {**THREAD, 'id': f'external-{i}', 'name': f'External {i}', 'updatedAt': time.time()+i, 'turns': []})
                for _ in range(300):
                    if evaluate("document.querySelector('.launch-recents')?.textContent.includes('External 10')"): break
                    time.sleep(.05)
                else: raise AssertionError('History refresh did not discover external chats')
                wait("document.querySelector('.launch-job [role=alert]') !== null")
                click('.launch-job [role=alert] button')
                assert evaluate("document.querySelector('[aria-label=\"New chat prompt\"]').value") == failed_ask
                click('.launch-job [role=alert] button:last-child')
                SidebarFixtures.fast = True
                fill_prompt('Complete before acknowledgement'); click('[aria-label="Launch new chat"]')
                wait("Array.from(document.querySelectorAll('.launch-recents .launch-row')).some(row => row.textContent.includes('Complete before acknowledgement') && row.querySelector('.chat-unread-dot'))")
                wait("!Array.from(document.querySelectorAll('.launch-row small')).some(x => x.textContent === 'Choosing model')")
                assert not evaluate("Boolean(document.querySelector('.launch-recents .chat-activity-spinner'))")
                for width,height,name in [(390,844,'phone'),(320,640,'narrow'),(854,480,'landscape')]:
                    viewport(width,height)
                    assert not evaluate("document.documentElement.scrollWidth > innerWidth")
                    screenshot(name+'-launch.png')
                assert len([path for path,_ in SidebarFixtures.calls if path.endswith('/messages')]) == 4
                viewport(1440,1000)
                if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"): click('[aria-label="Expand conversations"]')
                assert evaluate("document.querySelector('[aria-label=\"New chat workspace\"]').value") == ''
                click('[aria-label="Manage projects"]')
                wait("document.querySelector('.launch-prompt h1')?.textContent === 'WebUI 2'")
                assert evaluate("document.querySelector('[aria-label=\"New chat workspace\"]').value") == '1'
                assert not evaluate("document.querySelector('.launch-recents')?.textContent.includes('Complete before acknowledgement')")
                screenshot('desktop-project.png')
                fill_prompt('  hello  '); click('[aria-label="Launch new chat"]')
                wait("document.querySelector('.launch-auto small')?.textContent.includes('6-luna')")
                assert SidebarFixtures.threads[0]['projectId'] == '1'
                assert [body['input'] for path,body in SidebarFixtures.calls if path.endswith('/messages')][-1] == '  hello  '
                screenshot('desktop-project-hello.png')
                click('.project-launch-header button')
                wait("document.querySelector('.modal h3')?.textContent === 'Create a project'")
                def fill_name(value):
                    evaluate("(() => { const input=document.querySelector('.project-create-form input'); const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; setter.call(input,"+json.dumps(value)+"); input.dispatchEvent(new Event('input',{bubbles:true})); return true })()")
                fill_name('Learn Python')
                click('[aria-label="Folder color #78a7ff"]')
                screenshot('desktop-project-create.png')
                SidebarFixtures.fail_project = True
                click('.project-create-form [type=submit]')
                wait("document.querySelector('.project-create-form [role=alert]') !== null")
                assert evaluate("document.querySelector('.project-create-form input').value") == 'Learn Python'
                SidebarFixtures.fail_project = False
                evaluate("(() => { const form=document.querySelector('.project-create-form'); form.requestSubmit(); form.requestSubmit(); return true })()")
                wait("document.querySelector('.modal') === null && document.querySelector('.launch-prompt h1')?.textContent === 'Learn Python'")
                assert len([path for path,_ in SidebarFixtures.calls if path == '/api/projects']) == 2
                assert SidebarFixtures.projects[-1]['color'] == '#78a7ff'
                fill_prompt('  New project ask  '); click('[aria-label="Launch new chat"]')
                wait("document.querySelector('.launch-auto small')?.textContent.includes('6-luna')")
                assert SidebarFixtures.threads[0]['projectId'] == '2'
                click('.new-chat'); wait("document.querySelector('.launch-prompt h1')?.textContent === 'Start something new'")
                assert evaluate("document.querySelector('[aria-label=\"New chat workspace\"]').value") == ''
                for width,height,name in [(390,844,'phone'),(320,640,'narrow')]:
                    viewport(width,height)
                    if evaluate("Boolean(document.querySelector('.chat-sidebar'))"): click('[aria-label="Close conversations"]')
                    assert not evaluate("document.documentElement.scrollWidth > innerWidth")
                    screenshot(name+'-project-model.png')
                click('.launch-recents .launch-row')
                wait("document.querySelector('.chat-surface:not([hidden])') !== null && document.querySelector('.composer-last-model') !== null")
                assert evaluate("document.querySelector('.composer-last-model').textContent.includes('6-luna')")
                for width,height,name in [(390,844,'phone'),(320,640,'narrow')]:
                    viewport(width,height)
                    assert evaluate("getComputedStyle(document.querySelector('.composer-last-model')).display !== 'none'")
                    assert not evaluate("document.documentElement.scrollWidth > innerWidth")
                    screenshot(name+'-composer-last-model.png')
                viewport(1440,1000)
                if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"): click('[aria-label="Expand conversations"]')
                click('[aria-label="Manage projects"]'); click('.project-launch-header button')
                wait("document.querySelector('.modal') !== null")
                click('.project-options summary')
                for width,height,name in [(390,844,'phone'),(320,640,'narrow')]:
                    viewport(width,height)
                    assert not evaluate("document.documentElement.scrollWidth > innerWidth")
                    assert evaluate("(() => { const r=document.querySelector('.modal').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight })()")
                    screenshot(name+'-project-create.png')
                viewport(1440,1000)
                fill_name('Focus check')
                evaluate("(() => { document.querySelector('.project-create-form [type=submit]').focus(); return true })()")
                bidi.command('input.performActions', {'context': context, 'actions': [{'type':'key','id':'keyboard','actions':[{'type':'keyDown','value':'\ue004'},{'type':'keyUp','value':'\ue004'}]}]})
                assert evaluate("document.activeElement.getAttribute('aria-label')") == 'Close dialog'
                bidi.command('input.performActions', {'context': context, 'actions': [{'type':'key','id':'keyboard','actions':[{'type':'keyDown','value':'\ue00c'},{'type':'keyUp','value':'\ue00c'}]}]})
                wait("document.querySelector('.modal') === null")


                errors = [event for event in bidi.events if event.get('method')=='log.entryAdded' and event.get('params',{}).get('type')=='javascript' and event.get('params',{}).get('level')=='error']
                assert not errors, f'{len(errors)} uncaught JavaScript errors'
                result = {'syntheticFixtures': True, 'checks': ['default prompt landing with last 10', 'no eager chat creation', 'two independent submissions without navigation', 'exact Unicode and padded prompts', 'running spinners', 'unread completion dots', 'reload preserves unread IDs', 'opening chat clears dot', 'new chat does not create a thread', 'failed prompt restoration without retry', 'failed recovery outside recent ten', 'external history discovery', 'duplicate completion remains read', 'completion before HTTP acknowledgement stays complete', 'phone/narrow/landscape no overflow', 'normal chat no project', 'project scoped quick composer', 'project greeting exact ask and recorded model', 'project creation colors/failure/double-submit/selection', 'project dialog focus and Escape'], 'uncaughtJavaScriptErrors': len(errors)}
                (output/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
                print('Launch-pad checks passed: concurrent exact prompts, spinners, unread dots, reload, failures, races and mobile layouts; no paid calls.')

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
