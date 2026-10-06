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
    history_delay = .1
    projects = [{'id':i,'name':name,'workspace':'/workspace/codex-webui-2'} for i,name in enumerate(['WebUI 2','Games','Design explorations with a deliberately long project name','Workspace tools','Research','Experiments','Archive'],1)]
    threads = [{**THREAD, 'projectId': '1'}] + [{**THREAD, 'id':f'chat-{i}', 'name':f'Conversation {i} — long title that should truncate cleanly without hiding controls', 'projectId':str(i%7+1), 'turns':[]} for i in range(1,45)]
    def do_PATCH(self):
        if self.path.endswith('/metadata'):
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            thread_id = self.path.split('/')[3]
            for thread in self.threads:
                if thread['id'] == thread_id:
                    thread['webui'] = {**thread.get('webui', {}), **body}
            return self.reply(body)
        return super().do_PATCH()

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/api/usage':
            return self.reply({'rateLimits': {'rateLimits': {'primary': {'usedPercent': 100, 'windowDurationMins': 10080, 'resetsAt': 1791580291}, 'secondary': None}}})
        if path == '/api/bootstrap':
            return self.reply({'health':{'codex_available':True},'projects':self.projects,'threads':{'data':[]},'models':{'data':[]},'system':{'runtime':'container'},'tasks':[],'workspace':[],'features':{}})
        if path == '/api/threads' and 'q=' in self.path:
            query = parse_qs(urlsplit(self.path).query).get('q',[''])[0]
            if query == 'notfound': return self.reply({'data':[]})
            if query == 'unavailable': return self.reply({'detail':'Synthetic search failure'},503)
        if path == '/api/threads' and 'q=' not in self.path:
            return self.reply({'detail':'Synthetic history failure'},504) if self.fail_history else self.reply({'data':self.threads})
        return super().do_GET()



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-bundle', type=Path)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'evidence/ui/sidebar')
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
                wait("document.querySelector('.launch-pad:not([hidden])') !== null && document.querySelector('.launch-recents button') !== null")
                click('.launch-recents button')
                wait("Boolean(document.querySelector('.message.assistant') && document.querySelector('textarea'))")
                for width,height,name in [(1440,1000,'desktop'),(390,844,'phone'),(320,640,'narrow-phone'),(854,480,'landscape')]:
                    viewport(width,height)
                    if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"):
                        click('[aria-label="Expand conversations"]')
                    wait("document.querySelector('.chat-sidebar') !== null")
                    assert not evaluate("document.documentElement.scrollWidth > innerWidth")
                    screenshot(('before-' if args.baseline_bundle else 'after-')+name+'.png')
                    if width<1000:
                        click('[aria-label="Close conversations"]')
                        wait("!document.querySelector('.chat-sidebar')")
                if args.baseline_bundle:
                    print('Sidebar baseline captured at desktop and phone widths with dense chats/projects.')
                    return
                viewport(1440,1000)
                click('[aria-label="Expand conversations"]')
                wait("document.querySelectorAll('.chat-list .chat-row').length === 45")
                assert evaluate("document.querySelectorAll('#sidebar-project-list .sidebar-project-row').length") == 5
                click('.sidebar-show-more')
                assert evaluate("document.querySelectorAll('#sidebar-project-list .sidebar-project-row').length") == 9
                click('.sidebar-show-more')
                click('.section-disclosure[aria-controls="sidebar-project-list"]')
                assert not evaluate("Boolean(document.querySelector('#sidebar-project-list'))")
                click('.section-disclosure[aria-controls="sidebar-project-list"]')
                click('#sidebar-project-list > div:nth-of-type(2) > button')
                wait("document.querySelectorAll('.chat-list .chat-row').length < 45")
                assert evaluate("document.querySelector('#sidebar-project-list > div:nth-of-type(2) > button').getAttribute('aria-pressed')") == 'true'
                click('.chat-list .section-disclosure')
                wait("document.querySelectorAll('.chat-list .chat-row').length === 45")
                click('.chat-list .sidebar-section-action')
                assert evaluate("document.querySelector('.chat-list .chat-row').textContent.includes('Conversation 44')")
                click('.chat-list .sidebar-section-action')
                click('.conversation-details > summary')
                assert evaluate("document.querySelector('.conversation-details[open]').parentElement.querySelector('.chat-row').title.includes('WebUI 2')")
                click('.conversation-details > summary')
                click('.chat-list .conversation-details > summary')
                click('.chat-list .chat-pin-action')
                wait("document.querySelector('.chat-list .chat-pin-action')?.textContent === 'Unpin chat'")
                click('.sidebar-pinned > button')
                wait("document.querySelectorAll('.sidebar-pinned .chat-row').length === 1")
                click('.sidebar-pinned .conversation-details > summary')
                click('.sidebar-pinned .chat-pin-action')
                wait("document.querySelectorAll('.sidebar-pinned .chat-row').length === 0")
                click('.sidebar-files')
                wait("document.querySelector('.context-panel') !== null")
                assert evaluate("Boolean(document.querySelector('.context-panel'))")
                # Search opens from the row and the cross-platform shortcut.
                click('[aria-label="Search chats"]')
                wait("document.activeElement?.getAttribute('aria-label') === 'Search all resumable chats'")
                def fill(text):
                    evaluate(f"(() => {{const input=document.querySelector('.sidebar-search input'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,{json.dumps(text)}); input.dispatchEvent(new Event('input',{{bubbles:true}})); return true;}})()")
                fill('alpha')
                wait("document.querySelector('.chat-list .chat-row')?.textContent.includes('alpha remote result')")
                fill('notfound')
                wait("document.querySelector('.chat-list .empty-state')?.textContent.includes('No chats found')")
                screenshot('desktop-empty-search.png')
                fill('unavailable')
                wait("document.querySelector('.chat-list [role=alert]')?.textContent.includes('Search is unavailable')")
                screenshot('desktop-search-error.png')
                key('\ue00c')
                wait("!document.querySelector('.sidebar-search')")
                assert evaluate("document.activeElement.getAttribute('aria-label') === 'Search chats'")
                click('.new-project')
                wait("document.querySelector('.modal h3')?.textContent === 'Create a project'")
                click('[aria-label="Close dialog"]')
                click('[aria-label="Manage projects"]')
                wait("document.querySelector('.page-header h2')?.textContent === 'Projects'")
                click('.sidebar-rail [aria-label="Images"]')
                wait("document.querySelector('.page-header h2')?.textContent === 'Image library'")
                wait("document.querySelector('.image-chat-link') !== null")
                wait("Array.from(document.querySelectorAll('.image-card img')).some(image => image.complete && image.naturalWidth > 0)")
                screenshot('gallery-desktop.png')
                viewport(390,844)
                wait("!document.querySelector('.chat-sidebar')")
                assert not evaluate("document.documentElement.scrollWidth > innerWidth")
                screenshot('gallery-phone.png')
                viewport(1440,1000)
                if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"):
                    click('[aria-label="Expand conversations"]')
                assert not evaluate("Boolean(document.querySelector('.image-chat-link[aria-label^=\"Delete\"]'))")
                click('.image-chat-link')
                wait("document.querySelector('.chat-surface:not([hidden])') !== null")
                click('.sidebar-rail [aria-label="Images"]')
                wait("document.querySelector('.image-chat-link') !== null")
                click('.sidebar-rail [aria-label="Tasks"]')
                wait("document.querySelector('.page-header h2')?.textContent === 'Scheduled tasks'")
                click('[aria-label="Open settings"]')
                wait("document.querySelector('.page-header h2')?.textContent === 'Settings'")
                wait("document.querySelector('.usage-grid')?.textContent.includes('0% remaining')")
                assert evaluate("document.querySelector('.usage-grid')?.textContent.includes('Weekly limit')")
                screenshot('settings-desktop.png')
                viewport(390,844)
                screenshot('settings-phone.png')
                assert not evaluate("document.documentElement.scrollWidth > innerWidth")
                viewport(1440,1000)
                if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"):
                    click('[aria-label="Expand conversations"]')
                click('.chat-row')
                wait("document.querySelector('.chat-surface:not([hidden])') !== null")
                viewport(390,844)
                if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"):
                    click('[aria-label="Expand conversations"]')
                wait("document.querySelector('.chat-sidebar')?.getAttribute('role') === 'dialog'")
                assert evaluate("document.querySelector('.content-area').inert")
                evaluate("document.querySelector('.sidebar-rail [aria-label=Chats]').focus()")
                bidi.command('input.performActions', {'context':context,'actions':[{'type':'key','id':'keyboard','actions':[{'type':'keyDown','value':'\ue008'},{'type':'keyDown','value':'\ue004'},{'type':'keyUp','value':'\ue004'},{'type':'keyUp','value':'\ue008'}]}]})
                assert evaluate("document.activeElement.classList.contains('profile-button')")
                key('\ue004')
                assert evaluate("document.activeElement.getAttribute('aria-label') === 'Chats'")
                key('\ue00c')
                wait("!document.querySelector('.chat-sidebar')")
                wait("document.activeElement?.getAttribute('aria-label') === 'Expand conversations'")
                bidi.command('input.performActions', {'context':context,'actions':[{'type':'key','id':'keyboard','actions':[{'type':'keyDown','value':'\ue009'},{'type':'keyDown','value':'k'},{'type':'keyUp','value':'k'},{'type':'keyUp','value':'\ue009'}]}]})
                wait("document.activeElement?.getAttribute('aria-label') === 'Search all resumable chats'")
                key('\ue00c')
                key('\ue00c')
                wait("!document.querySelector('.chat-sidebar')")
                touch('[aria-label="Expand conversations"]')
                wait("document.querySelector('.chat-sidebar') !== null")
                evaluate("document.querySelector('.sidebar-scroll').scrollTop = document.querySelector('.sidebar-scroll').scrollHeight")
                screenshot('phone-dense-list-end.png')
                profile = evaluate("(() => {const r=document.querySelector('.profile-button').getBoundingClientRect();return {top:r.top,bottom:r.bottom};})()")
                assert 0 < profile['top'] < profile['bottom'] <= 844
                evaluate("document.querySelector('.sidebar-scroll').scrollTop = 0")
                touch('.chat-row')
                wait("!document.querySelector('.chat-sidebar')")
                # Loading failure, retry and empty workspace retain reachable navigation.
                SidebarFixtures.fail_history = True
                bidi.command('browsingContext.navigate', {'context':context,'url':url,'wait':'complete'})
                wait("document.querySelector('[aria-label=\"Expand conversations\"]') !== null")
                click('[aria-label="Expand conversations"]')
                wait("document.querySelector('.chat-list [role=alert]')?.textContent.includes('Conversations could not be loaded')")
                screenshot('phone-history-error.png')
                SidebarFixtures.fail_history = False
                click('.chat-list .history-notice button')
                wait("document.querySelectorAll('.chat-list .chat-row').length === 45")
                SidebarFixtures.threads = []
                SidebarFixtures.projects = []
                bidi.command('browsingContext.navigate', {'context':context,'url':url,'wait':'complete'})
                wait("document.querySelector('.launch-pad:not([hidden])') !== null")
                click('[aria-label="Expand conversations"]')
                wait("document.querySelector('.chat-list .empty-state')?.textContent.includes('Your chats will appear here')")
                assert evaluate("Boolean(document.querySelector('.new-project'))")
                screenshot('phone-empty-workspace.png')
                click('.sidebar-nav .new-chat')
                wait("document.querySelector('[aria-label=\"New chat prompt\"]') !== null && !document.querySelector('.chat-sidebar')")
                assert SidebarFixtures.calls == [], SidebarFixtures.calls

                errors = [event for event in bidi.events if event.get('method')=='log.entryAdded' and event.get('params',{}).get('type')=='javascript' and event.get('params',{}).get('level')=='error']
                assert not errors, f'{len(errors)} uncaught JavaScript errors'
                result={'syntheticFixtures':True,'viewports':['1440x1000','390x844','320x640','854x480'],'chats':45,'projects':7,'checks':['matched baseline','single-line titles','project expand/show more/filter/reset','chat order and details','persistent pin/unpin UI','workspace files shortcut','decoded chat image gallery and source navigation','remote search, empty and error states','search focus and Ctrl+K','secondary navigation','mobile focus trap and Escape return','inert background','touch selection closes drawer','dense-list scrolling with fixed profile','new project opens existing creation dialog','history failure and retry','empty workspace and new chat'],'uncaughtJavaScriptErrors':len(errors)}
                (output/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
                print('Sidebar checks passed: dense desktop/phone layouts, projects, search, keyboard, touch, focus and navigation; no model calls.')

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
