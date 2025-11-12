# core/test_larnitech_endpoints_extended.py
import requests, itertools, os, time

BASE = "https://1876d100.in.larnitech.com:8443"
ENDPOINTS = [
    "/api/device/list","/api2/device/list","/api2/devices/list","/api2/device/all",
    "/api/device/listAll","/api2/system/devices","/api2/devices/all","/api2/gateway/devices",
    "/api2/device/getAll","/api/devices","/api2/devices","/api/v1/device/list","/api/v1/devices"
]
HEADER_VARIANTS = [
    {"e-passw":"11111111","srv-serial":"1876d100"},
    {"Authorization":"Bearer 3673129911629553"},
    {"Authorization":"3673129911629553"},
    {"mode-is-remote":"4","srv-serial":"1876d100","e-passw":"11111111"},
    {"e-passw":"11111111","srv-serial":"1876d100","User-Agent":"LarnitechApp/1.0"},
]

print("Testing", BASE)
for ep in ENDPOINTS:
    for hdrs in HEADER_VARIANTS:
        url = BASE + ep
        try:
            r = requests.get(url, headers=hdrs, timeout=8, allow_redirects=True)
            print(f"{ep} | headers {list(hdrs.keys())} -> {r.status_code}")
            if r.status_code == 200:
                print("  ✅ POSSIBLE:", url, "headers:", hdrs)
                print("  Body preview:", r.text[:400])
                raise SystemExit(0)
        except Exception as e:
            print(f"{ep} | headers {list(hdrs.keys())} -> ERROR: {e}")
        time.sleep(0.25)
print("Done. No 200 found.")
