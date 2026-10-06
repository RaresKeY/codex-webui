"""Restricted Flatpak, CDP over inherited pipes; no TCP debugging endpoint."""
import fcntl
import base64
import configparser
import json
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from .core import APP, DATA, origin

PROFILE = '/var/data/codex-webui-browser/profile'

def launch_command(headed=False, debug=True, initial='about:blank'):
    flags = ['--user-data-dir=' + PROFILE, '--password-store=basic', '--mute-audio',
             '--no-first-run', '--disable-sync', '--disable-background-networking',
             '--disable-component-update', '--disable-breakpad']
    if not headed: flags += ['--headless=new']
    else: flags += ['--ozone-platform=wayland']
    if debug: flags += ['--remote-debugging-pipe']
    flags += [initial]
    chrome = 'umask 077; mkdir -p /var/data/codex-webui-browser/home /var/data/codex-webui-browser/config /var/data/codex-webui-browser/cache /var/data/codex-webui-browser/data; exec /app/bin/chromium ' + ' '.join(__import__('shlex').quote(f) for f in flags)
    if debug: chrome += ' 3<&0 4>&1'
    command = ['flatpak', 'run', '--user', '--share=network', '--unshare=ipc',
               '--nodevice=all', '--device=dri', '--nosocket=x11', '--nosocket=fallback-x11',
               '--nosocket=pulseaudio', '--nosocket=cups', '--nosocket=pcsc',
               '--nosocket=ssh-auth', '--nosocket=gpg-agent', '--nosocket=session-bus', '--nosocket=system-bus',
               '--session-bus', '--talk-name=org.freedesktop.portal.Flatpak',
               '--no-talk-name=org.kde.plasma.browser.integration',
               '--no-talk-name=org.freedesktop.Flatpak', '--no-talk-name=org.freedesktop.portal.Desktop',
               '--no-a11y-bus', '--no-documents-portal',
               '--nofilesystem=host:reset', '--nofilesystem=home', '--nofilesystem=xdg-download',
               '--nofilesystem=xdg-run/pipewire-0', '--disallow=bluetooth', '--clear-env',
               '--env=HOME=/var/data/codex-webui-browser/home',
               '--env=XDG_CONFIG_HOME=/var/data/codex-webui-browser/config',
               '--env=XDG_CACHE_HOME=/var/data/codex-webui-browser/cache',
               '--env=XDG_DATA_HOME=/var/data/codex-webui-browser/data',
               '--command=sh']
    # The Flatpak --sandbox override makes Cobalt's renderer subprocesses fail
    # on this build. Deny inherited service grants explicitly instead.
    services = ('org.xfce.ScreenSaver','org.gnome.SessionManager','org.kde.kwalletd6',
                'org.freedesktop.secrets','org.cinnamon.ScreenSaver','org.freedesktop.Notifications',
                'org.freedesktop.FileManager1','com.canonical.AppMenu.Registrar','org.gnome.ScreenSaver',
                'org.kde.kwalletd5','org.gnome.Mutter.IdleMonitor.*','org.freedesktop.ScreenSaver',
                'ca.desrt.dconf','org.mate.ScreenSaver')
    command += ['--no-talk-name=' + name for name in services]
    command += ['--system-no-talk-name=org.freedesktop.UPower', '--disallow=devel', '--disallow=multiarch']
    command += ['--no-talk-name=org.mpris.MediaPlayer2.chromium.*']
    if headed:
        display = os.environ.get('WAYLAND_DISPLAY')
        if not display: raise ValueError('Visible login requires a Wayland session')
        command += ['--socket=wayland', '--env=WAYLAND_DISPLAY=' + display]
    else: command += ['--nosocket=wayland']
    return command + [APP, '-c', chrome]

def environment():
    # Flatpak needs the host session bus to start, but it is not exposed to Chromium.
    return {k: v for k, v in os.environ.items() if k in (
        'PATH', 'HOME', 'LANG', 'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS', 'WAYLAND_DISPLAY')}

def audit(headed=False):
    command=launch_command(headed)
    command[-1]='cat /.flatpak-info'
    result=subprocess.run(command,env=environment(),capture_output=True,text=True,timeout=15,check=True)
    config=configparser.ConfigParser(interpolation=None)
    config.optionxform=str
    config.read_string(result.stdout)
    context=dict(config['Context']) if config.has_section('Context') else {}
    values=lambda name:set(filter(None,context.get(name,'').split(';')))
    if values('filesystems') or values('shared')!={'network'} or values('devices')!={'dri'}:
        raise ValueError('Effective Flatpak permissions differ from the restricted contract')
    if values('sockets')!=({'wayland'} if headed else set()): raise ValueError('Unexpected Flatpak sockets')
    if values('features') or values('persistent')-set(['.pki']): raise ValueError('Unexpected Flatpak features or persistence grants')
    bus=dict(config['Session Bus Policy']) if config.has_section('Session Bus Policy') else {}
    system=dict(config['System Bus Policy']) if config.has_section('System Bus Policy') else {}
    if bus!={'org.freedesktop.portal.Flatpak':'talk'} or system:
        raise ValueError('Unexpected Flatpak service permissions')
    return {'context':context,'session_bus':bus,'system_bus':system}

class Browser:
    def __init__(self, allowed, headed=False):
        self.allowed = set(allowed)
        self.headed = headed
        self.pending = queue.Queue()
        self.identifier = 0
        self.session = None
        self.target = None
        self.process = None
        self.lock = None
        self.observer_script = Path(__file__).with_name('observer.js').read_text()

    def navigation_permitted(self, url, method='GET'):
        try: return origin(url) in self.allowed
        except ValueError: return False

    def __enter__(self):
        if not shutil.which('flatpak'): raise ValueError('Flatpak is missing')
        audit(self.headed)
        DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = (DATA / 'profile.lock').open('a')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.process = subprocess.Popen(launch_command(self.headed), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=environment(), start_new_session=True)
            threading.Thread(target=self._read, daemon=True).start()
            target = self.call('Target.createTarget', {'url': 'about:blank'})['targetId']
            self.target = target
            self.session = self.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
            self.call('Target.setDiscoverTargets', {'discover': True}, root=True)
            self.call('Page.enable')
            self.call('Runtime.enable')
            self.call('Fetch.enable', {'patterns': [{'urlPattern': '*', 'resourceType': 'Document', 'requestStage': 'Request'}]})
            self.call('Browser.setDownloadBehavior', {'behavior': 'deny'}, root=True)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def _read(self):
        buffer = b''
        while True:
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                self.pending.put(None)
                return
            buffer += chunk
            if len(buffer) > 4_000_000:
                self.pending.put(None)
                return
            while b'\0' in buffer:
                raw, buffer = buffer.split(b'\0', 1)
                if raw:
                    try: self.pending.put(json.loads(raw))
                    except ValueError: self.pending.put(None)

    def _send(self, method, params, session=None):
        self.identifier += 1
        message = {'id': self.identifier, 'method': method, 'params': params}
        if session: message['sessionId'] = session
        self.process.stdin.write(json.dumps(message).encode() + b'\0')
        self.process.stdin.flush()
        return self.identifier

    def _event(self, message):
        if message.get('method') == 'Target.targetCreated':
            target = message['params']['targetInfo']
            if target['type'] == 'page' and self.target and target['targetId'] != self.target:
                self._send('Target.closeTarget', {'targetId': target['targetId']})
        elif message.get('method') == 'Fetch.requestPaused':
            info = message['params']
            permitted = self.navigation_permitted(info['request']['url'],info['request'].get('method','GET'))
            method = 'Fetch.continueRequest' if permitted else 'Fetch.failRequest'
            params = {'requestId': info['requestId']}
            if not permitted: params['errorReason'] = 'BlockedByClient'
            self._send(method, params, message.get('sessionId'))
        elif message.get('method') == 'Page.javascriptDialogOpening':
            self._send('Page.handleJavaScriptDialog', {'accept': False}, message.get('sessionId'))

    def call(self, method, params=None, root=False):
        identifier = self._send(method, params or {}, None if root else self.session)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try: message = self.pending.get(timeout=max(.01, deadline-time.monotonic()))
            except queue.Empty: raise TimeoutError('Browser operation timed out')
            if message is None: raise RuntimeError('Browser pipe closed')
            self._event(message)
            if message.get('id') == identifier:
                if 'error' in message: raise RuntimeError('Browser protocol rejected operation')
                return message.get('result', {})
        raise TimeoutError('Browser operation timed out')

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate', {'expression': expression, 'returnByValue': True, 'awaitPromise': True})
        if result.get('exceptionDetails'): raise RuntimeError('DOM operation failed')
        return result.get('result', {}).get('value')

    def navigate(self, url):
        if not self.navigation_permitted(url): raise ValueError('Navigation not allowed')
        self.call('Page.navigate', {'url': url})
        self.wait(1)

    def wait(self, seconds):
        # Pump protocol events while requests are paused at the origin gate.
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try: message = self.pending.get(timeout=min(.1, max(.001, deadline-time.monotonic())))
            except queue.Empty: continue
            if message is None: raise RuntimeError('Browser pipe closed')
            self._event(message)

    def snapshot(self, config):
        return self.evaluate('(' + self.observer_script + ')(' + json.dumps(config) + ')')

    def settled_snapshot(self, config, timeout=8):
        deadline=time.monotonic()+timeout
        polls=0
        while True:
            try:
                snapshot=self.snapshot(config)
            except RuntimeError:
                # Navigation can destroy the JS context between CDP commands.
                # Retry only this local read, bounded by the readiness deadline.
                if time.monotonic()>=deadline: raise
                self.wait(.25);polls+=1;continue
            if snapshot['ready']!='loading' and not snapshot.get('pending_images',0):
                return snapshot, polls
            if time.monotonic()>=deadline: return snapshot, polls
            self.wait(.25)
            polls+=1

    def screenshot(self, path):
        result=self.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
        data=base64.b64decode(result['data'],validate=True)
        if len(data)>16_000_000: raise ValueError('Screenshot too large')
        with Path(path).open('wb') as out:
            os.chmod(path,0o600)
            out.write(data)

    def image_bytes(self,snapshot,target,max_bytes):
        url=self.evaluate('window.__jev.image('+json.dumps({'version':snapshot['version'],'target':target})+')')
        if not url or origin(url) not in self.allowed: raise ValueError('Image target stale or outside allowed origins')
        frame=self.call('Page.getFrameTree')['frameTree']['frame']['id']
        resource=self.call('Page.getResourceContent',{'frameId':frame,'url':url})
        if not resource.get('base64Encoded'): raise ValueError('Image resource is not binary')
        data=base64.b64decode(resource['content'],validate=True)
        if len(data)>max_bytes: raise ValueError('Image exceeds task byte limit')
        return url,data

    def execute(self, snapshot, action):
        if action['op'] == 'WAIT': return self.wait(.5)
        if action['op'] in ('DONE', 'BLOCKED'): return
        if action['op'] not in ('CLICK', 'SCROLL', 'TYPE'): raise ValueError('Unsupported operation')
        result = self.evaluate('window.__jev.execute(' + json.dumps({'version': snapshot['version'], **action}) + ')')
        if result != 'ok': raise ValueError('Observed target changed or is blocked')
        self.wait(.3)

    def previous_entry(self):
        history=self.call('Page.getNavigationHistory')
        index=history['currentIndex']-1
        if index<0: return None
        entry=history['entries'][index]
        allowed=self.navigation_permitted(entry['url'])
        return entry if allowed else None

    def back(self):
        # Only existing history entries at approved origins; no generated URL.
        entry=self.previous_entry()
        if not entry: raise ValueError('No approved previous page')
        self.call('Page.navigateToHistoryEntry',{'entryId':entry['id']})
        self.wait(.3)

    def __exit__(self, *unused):
        if self.process:
            try:
                if self.process.poll() is None: self._send('Browser.close', {})
                self.process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                self.process.terminate()
                try: self.process.wait(timeout=3)
                except subprocess.TimeoutExpired: self.process.kill(); self.process.wait()
            for stream in (self.process.stdin, self.process.stdout):
                if stream: stream.close()
        if self.lock: self.lock.close()
