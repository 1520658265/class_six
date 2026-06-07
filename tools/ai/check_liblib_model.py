"""Quick check: query a Liblib model version's metadata."""
import json
import sys
import requests
from gen_with_liblib import make_signed_url
from ai_config import get_service_dict

uuid_to_check = sys.argv[1]
cfg = get_service_dict("liblib")
url = make_signed_url(
    cfg.get("api_host") or "openapi.liblibai.cloud",
    "/api/model/version/get",
    cfg["access_key"],
    cfg["secret_key"],
)
resp = requests.post(url, json={"versionUuid": uuid_to_check}, timeout=30)
print(f"HTTP {resp.status_code}")
try:
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
except Exception:
    print(resp.text[:1000])
