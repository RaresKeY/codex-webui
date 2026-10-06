"""Opt-in synthetic Flatpak browser smoke; no external sites or inference."""
import sys, asyncio, json, threading, argparse, tempfile, uuid, shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', action='store_true', help='Launch the audited headless Chromium Flatpak on a synthetic loopback fixture')
if not parser.parse_args().run:
    parser.error('Explicit --run is required')
import app.jev_browser.browser as driver
from app.jev_browser.browser import Browser
# Smoke owns a separate profile/lock and never touches an active user session.
smoke_directory = tempfile.TemporaryDirectory(prefix='codex-webui-browser-smoke-')
profile_name = 'smoke-' + uuid.uuid4().hex
driver.DATA = Path(smoke_directory.name)
driver.PROFILE = '/var/data/codex-webui-browser/' + profile_name
profile_path = Path.home() / '.var/app' / driver.APP / 'data/codex-webui-browser' / profile_name
from app.browser_service import BrowserService, BrowserAction, BrowserInput, Session

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers()
        self.wfile.write((b'<script></script>' if self.path == '/read' else b"<script>document.cookie='smoke_cookie=saved; Max-Age=3600; SameSite=Lax'</script>") + b'''<!doctype html><title>Browser fixture</title><h1>Waiting</h1><button onclick="document.querySelector('h1').textContent='Ready'">Open result</button><iframe srcdoc="&lt;input type=checkbox&gt;"></iframe><input aria-label="Search"><input type=password aria-label="Password" value="fixture-secret">''')
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}'
async def run():
    signals=[]
    async def publish(message): signals.append(message)
    service=BrowserService(True,publish)
    with Browser([url]) as browser:
        browser.call('Emulation.setDeviceMetricsOverride',{'width':1280,'height':900,'deviceScaleFactor':1,'mobile':False})
        browser.navigate(url)
        service.sessions['fixture']=Session(browser)
        observation=await service.action('fixture',BrowserAction(action='observe'))
        assert 'fixture-secret' not in json.dumps(observation)
        assert all(e['label']!='Password' for e in observation['elements'])
        target=next(e for e in observation['elements'] if e['label']=='Open result')
        assert target['bounds']['width']>0
        refreshed=await service.refresh('fixture')
        assert refreshed['frame'] and service.sessions['fixture'].snapshot['version']==observation['version']
        observation=await service.action('fixture',BrowserAction(action='click',target=target['id'],version=observation['version']))
        assert 'Ready' in observation['text']
        assert any(s['params']['action']=='pointer' for s in signals)
        target=next(e for e in observation['elements'] if e['label']=='Search')
        await service.action('fixture',BrowserAction(action='type',target=target['id'],version=observation['version'],text='hello'))
        assert browser.evaluate("document.querySelector('[aria-label=Search]').value")=='hello'
        bounds=browser.evaluate("(()=>{const r=document.querySelector('[aria-label=Search]').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
        await service.user_input('fixture',BrowserInput(action='click',**bounds))
        await service.user_input('fixture',BrowserInput(action='text',text=' human'))
        assert browser.evaluate("document.querySelector('[aria-label=Search]').value")=='hello human'
        await service.user_input('fixture',BrowserInput(action='key',key='Backspace'))
        assert browser.evaluate("document.querySelector('[aria-label=Search]').value")=='hello huma'
        bounds=browser.evaluate("(()=>{const f=document.querySelector('iframe'),r=f.getBoundingClientRect(),b=f.contentDocument.querySelector('input').getBoundingClientRect();return {x:r.x+f.clientLeft+b.x+b.width/2,y:r.y+f.clientTop+b.y+b.height/2}})()")
        await service.user_input('fixture',BrowserInput(action='click',**bounds))
        assert browser.evaluate("document.querySelector('iframe').contentDocument.querySelector('input').checked") is True
        print('PASS audited Flatpak browser, screenshot, observed click/type, password omission, cursor signal, stable polling observation; no external sites or inference')
async def cookie_restart():
    with Browser([url]) as browser:
        browser.navigate(url + '/read')
        assert 'smoke_cookie=saved' in browser.evaluate('document.cookie')
    print('PASS persistent cookie survives clean browser shutdown/reopen in isolated profile')
try:
    asyncio.run(run())
    asyncio.run(cookie_restart())
finally:
    server.shutdown();server.server_close()
    shutil.rmtree(profile_path, ignore_errors=True)
    smoke_directory.cleanup()
