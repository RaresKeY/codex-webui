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
from app.browser_service import BrowserService, BrowserAction, Session

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers()
        self.wfile.write(b'''<!doctype html><title>Browser fixture</title><h1>Waiting</h1><button onclick="document.querySelector('h1').textContent='Ready'">Open result</button><input aria-label="Search"><input type=password aria-label="Password" value="fixture-secret">''')
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
        print('PASS audited Flatpak browser, screenshot, observed click/type, password omission, cursor signal, stable polling observation; no external sites or inference')
try: asyncio.run(run())
finally:
    server.shutdown();server.server_close()
    shutil.rmtree(profile_path, ignore_errors=True)
    smoke_directory.cleanup()
