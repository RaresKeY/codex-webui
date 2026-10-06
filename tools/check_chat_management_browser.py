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
    threads = [{**THREAD, 'id': f'recent-{i}', 'name': f'Recent chat {i}', 'projectId':'1', 'status':'idle', 'updatedAt': time.time()-i, 'turns': []} for i in range(12)]
    archived = []
    calls = []
    sockets = []
    fail_delete = False
    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/api/bootstrap':
            return self.reply({'health': {'codex_available': True}, 'projects': self.projects, 'threads': {'data': []}, 'models': {'data': []}, 'system': {'runtime': 'container'}, 'tasks': [], 'workspace': [], 'features': {}})
        if path == '/api/threads':
            return self.reply({'data': self.archived if parse_qs(urlsplit(self.path).query).get('archived') == ['true'] else self.threads})
        if path.startswith('/api/threads/') and path.count('/') == 3:
            return self.reply({'thread': next((chat for chat in self.threads+self.archived if chat['id'] == path.split('/')[3]), {})})
        return super().do_GET()
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
        self.calls.append((self.path, body))
        thread_id = self.path.split('/')[3]
        if self.path.endswith('/archive'):
            chat = next(chat for chat in self.threads if chat['id'] == thread_id)
            self.threads.remove(chat); self.archived.append(chat)
            self.emit({'method':'thread/archived','params':{'threadId':thread_id}})
            return self.reply({})
        if self.path.endswith('/unarchive'):
            chat = next(chat for chat in self.archived if chat['id'] == thread_id)
            self.archived.remove(chat); self.threads.insert(0, chat)
            self.emit({'method':'thread/unarchived','params':{'threadId':thread_id}})
            return self.reply({'thread':chat})
        raise AssertionError('Unexpected POST '+self.path)
    def do_DELETE(self):
        self.calls.append((self.path, {})); time.sleep(.3)
        if self.fail_delete: return self.reply({'detail':'Synthetic failure'},409)
        if self.path.startswith('/api/projects/'):
            project_id = self.path.split('/')[3]
            self.projects[:] = [p for p in self.projects if str(p['id']) != project_id]
            for chat in self.threads+self.archived:
                if chat.get('projectId') == project_id: chat['projectId'] = ''
        else:
            thread_id = self.path.split('/')[3]
            self.threads[:] = [chat for chat in self.threads if chat['id'] != thread_id]
            self.archived[:] = [chat for chat in self.archived if chat['id'] != thread_id]
            self.emit({'method':'thread/deleted','params':{'threadId':thread_id}})
        return self.reply({},204)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-bundle', type=Path)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'evidence/ui/chat-management')
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
                wait("document.querySelectorAll('.launch-recents .launch-row').length === 10")
                if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"): click('[aria-label="Expand conversations"]')
                def menu():
                    click('.chat-list .conversation-details summary')
                    wait("document.querySelector('.chat-list .conversation-details[open] .conversation-details-body')?.matches(':popover-open')")
                history_geometry = evaluate("document.querySelector('.chat-list').getBoundingClientRect().height")
                menu()
                assert evaluate("document.querySelector('.chat-list').getBoundingClientRect().height") == history_geometry, 'Action menu moved history rows'
                screenshot('desktop-chat-actions.png')
                key('\ue00c')
                wait("!document.querySelector('.conversation-details[open]') && document.activeElement.matches('.conversation-details > summary')")
                for width,height in [(390,844),(320,640)]:
                    viewport(width,height)
                    if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"): click('[aria-label="Expand conversations"]')
                    menu()
                    assert evaluate("(() => {const r=document.querySelector('.conversation-details[open] .conversation-details-body').getBoundingClientRect();return r.left>=0 && r.top>=0 && r.right<=innerWidth && r.bottom<=innerHeight})()")
                    screenshot(f'phone-{width}-chat-actions.png')
                    key('\ue00c'); wait("!document.querySelector('.conversation-details[open]')")
                viewport(1440,1000)
                if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"): click('[aria-label="Expand conversations"]')
                menu(); click('.chat-list .conversation-details[open] .chat-menu-action:not(.danger)')
                wait("!document.querySelector('.chat-list')?.textContent.includes('Recent chat 0')")
                assert len(SidebarFixtures.archived) == 1
                click('.sidebar-archive-link')
                wait("document.querySelector('.archived-list')?.textContent.includes('Recent chat 0')")
                screenshot('desktop-archived.png')
                click('.archived-list .conversation-details summary')
                click('.archived-list .chat-menu-action:not(.danger)')
                wait("document.querySelector('.archive-empty') !== null")
                assert len(SidebarFixtures.archived) == 0
                click('.new-chat'); menu(); click('.chat-list .conversation-details[open] .danger')
                wait("document.querySelector('.modal h3')?.textContent === 'Delete chat?'")
                assert evaluate("document.querySelector('.modal').textContent.includes('cannot be undone')")
                screenshot('desktop-delete.png')
                before=len(SidebarFixtures.calls)
                click('.delete-confirmation .button:not(.destructive-button)')
                assert len(SidebarFixtures.calls)==before
                menu(); click('.chat-list .conversation-details[open] .danger')
                SidebarFixtures.fail_delete=True
                click('.destructive-button'); wait("document.querySelector('.delete-confirmation [role=alert]') !== null")
                assert len(SidebarFixtures.threads)==12
                SidebarFixtures.fail_delete=False
                evaluate("(() => { const b=document.querySelector('.destructive-button'); b.click(); b.click(); return true })()")
                wait("document.querySelector('.modal') === null")
                assert len(SidebarFixtures.calls)==before+2
                assert len(SidebarFixtures.threads)==11
                wait("!document.querySelector('.chat-list')?.textContent.includes('Recent chat 0')")
                SidebarFixtures.emit({'method':'turn/started','params':{'threadId':'recent-1','turn':{'id':'active-fixture'}}})
                wait("document.querySelector('.chat-list .chat-running-label') !== null")
                menu()
                assert evaluate("Array.from(document.querySelectorAll('.chat-list .conversation-details[open] .chat-menu-action')).every(button => button.disabled)")
                SidebarFixtures.emit({'method':'turn/completed','params':{'threadId':'recent-1','turn':{'id':'active-fixture','status':'completed'}}})
                wait("document.querySelector('.chat-list .chat-running-label') === null")
                click('[aria-label="Manage projects"]')
                wait("document.querySelector('[aria-label=\"Project actions\"]') !== null")
                click('[aria-label="Project actions"]'); click('.project-overflow .danger')
                wait("document.querySelector('.modal h3')?.textContent === 'Delete project?'")
                assert evaluate("document.querySelector('.modal').textContent.includes('files will stay on disk')")
                for width,height,name in [(390,844,'phone'),(320,640,'narrow')]:
                    viewport(width,height)
                    assert not evaluate("document.documentElement.scrollWidth > innerWidth")
                    assert evaluate("(() => {const r=document.querySelector('.modal').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth})()")
                    screenshot(name+'-delete-project.png')
                key('\ue00c'); wait("document.querySelector('.modal') === null")
                assert len(SidebarFixtures.projects)==1
                viewport(1440,1000)
                click('[aria-label="Project actions"]'); click('.project-overflow .danger'); click('.destructive-button')
                wait("document.querySelector('.modal') === null && document.querySelector('.project-empty') !== null")
                assert len(SidebarFixtures.threads)==11
                assert all(chat['projectId']=='' for chat in SidebarFixtures.threads)
                if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"): click('[aria-label="Expand conversations"]')
                click('.new-chat')
                bidi.command('browsingContext.navigate', {'context':context,'url':url,'wait':'complete'})
                wait("document.querySelectorAll('.launch-recents .launch-row').length === 10")
                assert not evaluate("document.querySelector('.launch-recents').textContent.includes('Recent chat 0')")
                if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"): click('[aria-label="Expand conversations"]')
                menu()
                assert evaluate("document.querySelector('.chat-list .conversation-details[open]').parentElement.querySelector('.chat-row').title.includes('No project')")
                errors = [event for event in bidi.events if event.get('method')=='log.entryAdded' and event.get('params',{}).get('type')=='javascript' and event.get('params',{}).get('level')=='error']
                assert not errors, f'{len(errors)} uncaught JavaScript errors'
                result={'syntheticFixtures':True,'checks':['archive removes from recents','archived list and restore','cancel makes no delete request','failure retains chat and dialog','double confirmation sends once','active turn disables archive/delete','permanent deletion survives reload','project deletion preserves chats and unassigns','Escape cancellation','390/320 dialogs fit'],'uncaughtJavaScriptErrors':0}
                (output/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
                print('Chat management browser checks passed; no paid calls or real chat changes.')

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
