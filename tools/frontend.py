#!/usr/bin/env python3
"""Install exact lockfile tarballs and run frontend tools in an offline Deno container."""
import argparse
import fcntl
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
LOCK = FRONTEND / "package-lock.json"
IMAGE = "localhost/codex-webui-2-tools:local"


def install(fetch=False):
    lock_hash = hashlib.sha256(LOCK.read_bytes()).hexdigest()
    marker = FRONTEND / "node_modules/.codex-lock.sha256"
    if marker.exists() and marker.read_text() == lock_hash:
        return
    cache = Path(os.environ.get("PACKAGE_CACHE", str(Path.home() / ".npm/_cacache/content-v2")))
    packages = json.loads(LOCK.read_text())["packages"]
    for name, package in packages.items():
        if not name:
            continue
        machine = {"x86_64": "x64", "aarch64": "arm64"}.get(platform.machine(), platform.machine())
        if package.get("os") and "linux" not in package["os"]:
            continue
        if package.get("cpu") and machine not in package["cpu"]:
            continue
        algorithm, encoded = package["integrity"].split("-", 1)
        digest = base64.b64decode(encoded).hex()
        cached = cache / algorithm / digest[:2] / digest[2:4] / digest[4:]
        if cached.exists():
            data = cached.read_bytes()
        elif fetch:
            url = package["resolved"]
            if not url.startswith("https://registry.npmjs.org/"):
                raise RuntimeError("Only the locked npm registry is allowed")
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
        else:
            raise RuntimeError(f"Missing locked package {name}; --fetch requires explicit download authorization")
        if hashlib.new(algorithm, data).hexdigest() != digest:
            raise RuntimeError(f"Integrity check failed for {name}")
        destination = FRONTEND / name
        if not destination.resolve().is_relative_to(FRONTEND.resolve()):
            raise RuntimeError("Invalid lockfile path")
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive.getmembers():
                parts = Path(member.name).parts
                if not parts or member.name.startswith("/") or parts[0] in {".", ".."}:
                    continue
                member.name = str(Path(*parts[1:]))
                if member.name == ".":
                    continue
                archive.extract(member, destination, filter="data")
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(lock_hash)


def container(arguments, network="none", cache=False):
    mounts = ["--volume", f"{FRONTEND}:/app/frontend:rw", "--volume", f"{ROOT / 'tools'}:/app/tools:ro"]
    if cache:
        path = Path.home() / ".npm/_cacache/content-v2"
        if path.exists():
            mounts += ["--volume", f"{path}:/package-cache:ro", "--env", "PACKAGE_CACHE=/package-cache"]
    subprocess.run([
        "podman", "run", "--rm", "--pull=never", f"--network={network}", "--userns=keep-id",
        "--user", f"{os.getuid()}:{os.getgid()}", "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--read-only", "--tmpfs", "/tmp:rw,size=512m", "--env", "DENO_DIR=/tmp/deno-cache",
        *mounts, "--workdir", "/app/frontend", IMAGE, *arguments,
    ], check=True)


def run(script, arguments):
    container(["deno", "run", "--no-config", "--cached-only", "--node-modules-dir=manual",
               "--allow-read=/app,/tmp,/usr,/pnpm-workspace.yaml,/lerna.json,/package.json,/deno.json,/deno.jsonc", "--allow-write=/app/frontend,/tmp", "--allow-env",
               "--allow-sys=osRelease,cpus,homedir,uid,gid",
               "--allow-net=localhost,127.0.0.1",
               "--allow-ffi=/app/frontend/node_modules", "--allow-run=/app/tools/deno-worker.py,/app/frontend/node_modules/@esbuild",
               script, *arguments])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "build", "lint", "test", "check"])
    parser.add_argument("--fetch", action="store_true", help="Explicitly authorized locked dependency download; no lifecycle scripts")
    parser.add_argument("--inside-install", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.inside_install:
        install(args.fetch)
        return
    container(["python", "/app/tools/frontend.py", "install", "--inside-install", *(["--fetch"] if args.fetch else [])], network="pasta" if args.fetch else "none", cache=True)
    if args.action in {"build", "check"}:
        run("node_modules/typescript/lib/tsc.js", ["-b"])
        run("node_modules/vite/bin/vite.js", ["build"])
    if args.action in {"lint", "check"}:
        run("node_modules/eslint/bin/eslint.js", [".", "--max-warnings=0"])
    if args.action in {"test", "check"}:
        run("/app/tools/run-vitest.mjs", [])


if __name__ == "__main__":
    lock_root = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    # Inside the locked host wrapper, the installer has no host runtime-dir mount.
    if "--inside-install" in __import__("sys").argv:
        main()
    else:
        with (lock_root / "podman-build-retention.lock").open("a") as build_lock:
            fcntl.flock(build_lock, fcntl.LOCK_SH)
            main()
