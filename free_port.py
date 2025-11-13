#!/usr/bin/env python3
import os
import subprocess

def pids_on_port(port: int) -> list[int]:
    try:
        # Use netstat to find PIDs listening on the port (Windows)
        output = subprocess.check_output(['netstat', '-ano'], text=True, errors='ignore')
    except Exception:
        return []
    pids = set()
    target = f":{port}"
    for line in output.splitlines():
        line = line.strip()
        if target in line and 'LISTEN' in line.upper():
            parts = line.split()
            if parts:
                try:
                    pid = int(parts[-1])
                    pids.add(pid)
                except Exception:
                    pass
    return sorted(pids)

def kill_pids(pids: list[int]) -> None:
    for pid in pids:
        # Force kill via taskkill (works for python/uvicorn)
        try:
            subprocess.call(['taskkill', '/PID', str(pid), '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

if __name__ == '__main__':
    port = int(os.getenv('PORT', '7000'))
    p = pids_on_port(port)
    if p:
        kill_pids(p)
        print({'ok': True, 'killed': p})
    else:
        print({'ok': True, 'killed': []})


