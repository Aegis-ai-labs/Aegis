#!/usr/bin/env python3
"""
E2E connection check: bridge status + firmware contract tests.

Run with bridge already running:
  python scripts/check_e2e.py
"""
import json
import os
import subprocess
import sys
from urllib.request import urlopen
from urllib.error import URLError

BRIDGE_URL = "http://127.0.0.1:8000"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    print("=== AEGIS1 E2E check ===\n")

    # 1. Bridge health
    try:
        with urlopen(f"{BRIDGE_URL}/health", timeout=5) as r:
            health = json.loads(r.read().decode())
        print("[OK] Bridge health:", health.get("status", "?"))
    except URLError as e:
        print("[FAIL] Bridge not reachable:", e)
        print("       Start bridge: python -m bridge.main")
        sys.exit(1)

    # 2. API status (ESP32 connection)
    try:
        with urlopen(f"{BRIDGE_URL}/api/status", timeout=5) as r:
            status = json.loads(r.read().decode())
        esp32 = status.get("esp32_connected", status.get("connections", 0) > 0)
        n = status.get("connections", 0)
        clients = status.get("esp32_clients", [])
        if esp32 and n > 0:
            print("[OK] ESP32 connected:", n, "client(s)", clients)
        else:
            print("[--] ESP32 not connected (connections: 0)")
            print("     Check: BRIDGE_HOST in firmware/config.h = this machine IP")
            print("     Check: ESP32 on same WiFi, power/reset ESP32")
    except URLError as e:
        print("[FAIL] /api/status:", e)
        sys.exit(1)

    # 3. Firmware contract tests
    print("\n--- Firmware contract tests ---")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_firmware_main.py", "-v", "--tb=short", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if r.returncode == 0:
        print(r.stdout or "Firmware tests passed")
        print("[OK] Firmware contract tests passed")
    else:
        print(r.stdout or "")
        print(r.stderr or "")
        print("[FAIL] Firmware tests failed")
        sys.exit(1)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
