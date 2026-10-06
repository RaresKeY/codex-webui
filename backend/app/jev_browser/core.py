from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
APP = "io.github.ungoogled_software.ungoogled_chromium"
DATA = Path.home() / ".local/share/codex-webui-browser"

def origin(url):
    parsed = urlsplit(url)
    if parsed.username or parsed.password or not parsed.hostname:
        raise ValueError('URL must have a host and no embedded credentials')
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost', '[::1]', '::1')):
        raise ValueError('HTTPS required except loopback fixtures')
    return urlunsplit((parsed.scheme, parsed.netloc, '', '', ''))
