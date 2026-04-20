import requests, sys

url = "http://127.0.0.1:8000/analyze_url"
payload = {"url": "https://www.youtube.com/shorts/En6lhg53DTA"}

try:
    r = requests.post(url, json=payload, timeout=300)
    print("STATUS:", r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)
except Exception as e:
    print("ERROR:", e)
    sys.exit(1)
