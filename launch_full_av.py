import json
import subprocess
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8899"
SC = r"C:\Program Files\SuperCollider-3.14.1\sclang.exe"
PATCH = r"C:\Users\learn\Downloads\hermes-industrial-supercollider-PORTSAFE.scd"
NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)


def relay_alive():
    try:
        with urllib.request.urlopen(URL + "/health", timeout=1) as response:
            return json.load(response).get("ok") is True
    except Exception:
        return False


if not relay_alive():
    subprocess.Popen(["node", "server.js"], cwd=ROOT, creationflags=NEW_CONSOLE)
    for _ in range(20):
        if relay_alive():
            break
        time.sleep(0.15)
    else:
        raise SystemExit("AV relay failed to start.")

# Replace only the SuperCollider runtime; reuse the relay and browser endpoint.
subprocess.run(["taskkill", "/F", "/IM", "sclang.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(["taskkill", "/F", "/IM", "scsynth.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.4)
subprocess.Popen([SC, "-u", "57200", PATCH], creationflags=NEW_CONSOLE)
time.sleep(1.2)
webbrowser.open(URL)
print("Foundry AV launched: audio 57210, OSC 57220, visuals 8899")
