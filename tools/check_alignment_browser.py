#!/usr/bin/env python3
"""Check sidebar and launch alignment with synthetic data or read-only live geometry."""
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
from urllib.parse import urlsplit
from check_sidebar_browser import SidebarFixtures


class AlignmentFixtures(SidebarFixtures):
    threads = [{**thread, 'status': 'idle', 'webui': {'last_turn_model': 'gpt-6-luna', 'last_turn_effort': 'low'}} for thread in SidebarFixtures.threads]
    def do_GET(self):
        if urlsplit(self.path).path == '/api/jev/activity':
            return self.reply({'data': [], 'nextCursor': None})
        return super().do_GET()



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--url')
    parser.add_argument('--bundle', type=Path, help='Use a prepared frontend bundle for synthetic checks')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'evidence/ui/alignment')
    args = parser.parse_args()
    if args.bundle:
        AlignmentFixtures.bundle = args.bundle.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    helper = Path.home() / 'workspace/godot-performance-lab/tools/firefox_bidi_profile.py'
    sys.path.insert(0, str(helper.parent))
    spec = importlib.util.spec_from_file_location('permissions_bidi', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = ThreadingHTTPServer(('127.0.0.1', 0), AlignmentFixtures)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory(prefix='webui-alignment-browser-') as temporary:
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
                bidi.command('session.subscribe', {'events': ['log.entryAdded', 'network.beforeRequestSent']})
                bidi.command('script.addPreloadScript', {'functionDeclaration': "() => { const Native = window.WebSocket; window.__alignmentSockets = []; window.WebSocket = class extends Native { constructor(...args) { super(...args); window.__alignmentSockets.push(this); } }; }"})
                context = str(bidi.command('browsingContext.create', {'type': 'tab'})['result']['context'])
                url = args.url or f'http://127.0.0.1:{server.server_port}/'
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
                    if args.url:
                        return  # Never capture real chats, even when a live check fails.
                    result = bidi.command('browsingContext.captureScreenshot', {'context':context, 'origin':'viewport'})
                    (output / name).write_bytes(base64.b64decode(result['result']['data']))
                def click(selector):
                    evaluate(f"(() => {{document.querySelector({json.dumps(selector)}).click(); return true;}})()")
                def viewport(width, height):
                    bidi.command('browsingContext.setViewport', {'context':context,'viewport':{'width':width,'height':height}})
                    time.sleep(.25)
                measurements = []
                geometry = r"""(() => {
                    const root=document.querySelector('.launch-pad:not([hidden])');
                    const bounds=e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width}};
                    const title=root.querySelector('.launch-prompt h1'), heading=root.querySelector('.launch-recents h2'), rows=Array.from(root.querySelectorAll('.launch-row'));
                    const sidebar=document.querySelector('.chat-sidebar');
                    const actions=sidebar ? [...sidebar.querySelectorAll('.sidebar-nav > button:not([aria-controls]),.sidebar-archive-link')].filter(e=>e.getClientRects().length) : [];
                    return {overflow:document.documentElement.scrollWidth>innerWidth, heading:bounds(heading), title:bounds(title), header:bounds(root.querySelector('.launch-recents > header')),
                        rows:rows.slice(0,4).map(row=>{const meta=row.querySelector('small'),node=Array.from(meta.childNodes).find(n=>n.nodeType===Node.TEXT_NODE&&n.textContent.trim()),range=document.createRange();if(node)range.selectNodeContents(node);return {row:bounds(row),title:bounds(row.querySelector('strong')),meta:bounds(meta),time:node?bounds(range):null,model:row.querySelector('.recent-model') ? bounds(row.querySelector('.recent-model')) : null}}),
                        sidebar:actions.map(row=>{const icon=row.querySelector('svg'),node=Array.from(row.childNodes).find(n=>n.nodeType===Node.TEXT_NODE&&n.textContent.trim());const range=document.createRange();range.selectNodeContents(node);return {icon:bounds(icon),text:bounds(range),row:bounds(row)}})};
                })()"""
                for width,height,name in [(1440,1000,'desktop'),(390,844,'phone'),(320,640,'narrow-phone')]:
                    viewport(width,height)
                    bidi.command('browsingContext.navigate', {'context':context,'url':url,'wait':'complete'})
                    wait("document.querySelector('.launch-pad:not([hidden]) .launch-recents .launch-row') !== null")
                    if args.url:
                        wait("window.isSecureContext && window.__alignmentSockets.some(socket => socket.readyState === WebSocket.OPEN && socket.url.startsWith('wss:'))")
                    if not evaluate("Boolean(document.querySelector('.chat-sidebar'))"):
                        click('[aria-label="Expand conversations"]')
                    wait("document.querySelector('.chat-sidebar') !== null")
                    result=evaluate(geometry)
                    assert not result['overflow'], result
                    if not args.baseline:
                        icons=[item['icon']['left'] for item in result['sidebar']]
                        labels=[item['text']['left'] for item in result['sidebar']]
                        assert max(icons)-min(icons)<=1, ('sidebar icons',icons)
                        assert max(labels)-min(labels)<=1, ('sidebar labels',labels)
                        if width<1000: assert all(item['row']['bottom']-item['row']['top']>=44 for item in result['sidebar'])
                        for row in result['rows']:
                            assert abs(row['title']['left']-result['heading']['left'])<=1, ('recent title',row,result['heading'])
                            assert abs(row['meta']['right']-result['header']['right'])<=1, ('metadata edge',row,result['header'])
                            if row['time']:
                                assert abs(row['time']['right']-row['meta']['right'])<=1, ('time alignment',row)
                            assert row['title']['left']-row['row']['left']>=7.5, ('hover title inset',row)
                            assert row['row']['right']-row['meta']['right']>=7.5, ('hover metadata inset',row)
                        rights=[row['meta']['right'] for row in result['rows']]
                        assert max(rights)-min(rights)<=1, ('metadata column',rights)
                    measurements.append({'viewport':f'{width}x{height}','geometry':result})
                    if not args.url: screenshot(('before-' if args.baseline else 'after-')+name+'-sidebar.png')
                    if width<1000:
                        click('[aria-label="Close conversations"]')
                        wait("!document.querySelector('.chat-sidebar')")
                    if not args.url: screenshot(('before-' if args.baseline else 'after-')+name+'-launch.png')
                    point=evaluate("(() => {const rows=document.querySelectorAll('.launch-recents button.launch-row'),row=rows[Math.min(1,rows.length-1)];row.scrollIntoView({block:'nearest'});const r=row.getBoundingClientRect();window.__alignmentHoverRow=row;return {x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}})()")
                    bidi.command('input.performActions', {'context':context,'actions':[{'type':'pointer','id':'mouse','parameters':{'pointerType':'mouse'},'actions':[{'type':'pointerMove','origin':'viewport',**point}]}]})
                    wait("window.__alignmentHoverRow.matches(':hover')")
                    result['hover']=evaluate("(() => {const row=window.__alignmentHoverRow,r=row.getBoundingClientRect(),style=getComputedStyle(row);return {background:style.backgroundColor,leftInset:parseFloat(style.paddingLeft),rightInset:parseFloat(style.paddingRight),fits:r.left>=0&&r.right<=innerWidth}})()")
                    assert result['hover']['fits'], result['hover']
                    assert result['hover']['background'] not in ('transparent', 'rgba(0, 0, 0, 0)'), result['hover']
                    if not args.baseline:
                        assert result['hover']['leftInset']>=8 and result['hover']['rightInset']>=8, result['hover']
                    if not args.url: screenshot(('before-' if args.baseline else 'after-')+name+'-hover.png')
                    evaluate("(() => {window.__alignmentHoverRow.focus();return true})()")
                    bidi.command('input.performActions', {'context':context,'actions':[{'type':'key','id':'keyboard','actions':[{'type':'keyDown','value':'\ue004'},{'type':'keyUp','value':'\ue004'}]}]})
                    wait("document.activeElement.matches('.launch-row:focus-visible')")
                    result['focus']=evaluate("(() => {const row=document.activeElement,r=row.getBoundingClientRect(),style=getComputedStyle(row);return {background:style.backgroundColor,outline:style.outlineStyle,fits:r.left>=4&&r.right<=innerWidth-4}})()")
                    assert result['focus']['outline']!='none' and result['focus']['fits'], result['focus']
                    if not args.baseline:
                        assert result['focus']['background']==result['hover']['background'], result['focus']
                    if not args.url: screenshot(('before-' if args.baseline else 'after-')+name+'-focus.png')
                    if args.url:
                        if width<1000:
                            click('[aria-label="Expand conversations"]')
                        evaluate("(() => {Array.from(document.querySelectorAll('.sidebar-nav > button')).find(button=>button.textContent.trim()==='Jev').click();return true})()")
                        wait("Boolean(document.querySelector('.jev-page .page-header > button')) && !document.querySelector('.jev-page .page-header > button').disabled")
                        assert evaluate("!document.querySelector('.jev-page [role=\"alert\"]') && document.documentElement.scrollWidth <= innerWidth"), 'Live Jev page failed'
                errors=[event for event in bidi.events if event.get('method')=='log.entryAdded' and event.get('params',{}).get('type')=='javascript' and event.get('params',{}).get('level')=='error']
                assert not errors, f'{len(errors)} uncaught JavaScript errors'
                assert AlignmentFixtures.calls == [], AlignmentFixtures.calls
                mutations=sum(event.get('params',{}).get('request',{}).get('method') not in ('GET','HEAD','OPTIONS') for event in bidi.events if event.get('method')=='network.beforeRequestSent')
                assert mutations == 0, f'{mutations} HTTP mutations'
                report={'syntheticFixtures': not bool(args.url),'liveHttps': bool(args.url),'secureWss': bool(args.url),'jevPage': bool(args.url),'baseline':args.baseline,'measurements':measurements,'uncaughtJavaScriptErrors':len(errors),'httpMutations':mutations,'modelCalls':0}
                target='live-checks.json' if args.url else 'before-checks.json' if args.baseline else 'checks.json'
                (output/target).write_text(json.dumps(report,indent=2)+'\n')
                print('Alignment browser checks passed at desktop, phone and narrow phone widths; no model calls.')

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
