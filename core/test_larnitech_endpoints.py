import requests

BASE = "https://1876d100.in.larnitech.com:8443"
HEADERS = {
    "e-passw": "11111111",
    "srv-serial": "1876d100",
}
ENDPOINTS = [
    "/api2/device/list",
    "/api/device/list",
    "/api2/devices/list",
    "/api2/device/all",
    "/api/device/listAll",
    "/api2/system/devices",
    "/api2/devices/all",
    "/api2/gateway/devices",
    "/api2/device/getAll",
]

print(f"🔍 Testing endpoints at {BASE}")
for ep in ENDPOINTS:
    url = BASE + ep
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        print(f"{ep} → {res.status_code}")
        if res.status_code == 200:
            print("✅ Possible match:", url)
            print(res.text[:300], "...\n")
    except Exception as e:
        print(f"{ep} → ❌ {e}")
