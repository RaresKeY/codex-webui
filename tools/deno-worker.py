#!/usr/local/bin/python
"""Replace Deno's implicit all-permission Node fork with scoped tool permissions."""
import os
import sys

arguments = sys.argv[1:]
if not arguments or arguments[0] != "run":
    raise SystemExit("Expected a translated Deno run worker")
arguments = [argument for argument in arguments[1:] if argument not in {"-A", "--allow-all"}]
permissions = [
    "--no-config", "--cached-only", "--node-modules-dir=manual",
    "--allow-read=/app,/tmp,/usr,/pnpm-workspace.yaml,/lerna.json,/package.json,/deno.json,/deno.jsonc",
    "--allow-write=/app/frontend,/tmp", "--allow-env", "--allow-sys=osRelease,cpus,homedir,uid,gid",
    "--allow-net=localhost,127.0.0.1", "--allow-ffi=/app/frontend/node_modules",
]
os.execv("/usr/local/bin/deno", ["deno", "run", *permissions, *arguments])
