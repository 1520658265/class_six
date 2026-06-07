"""
Upload a local image to LiblibAI's temp OSS bucket and return its public URL.

Usage:
    python upload_to_liblib.py <image_path>
    # prints the public URL on success

Doc: https://resonate.feishu.cn/wiki/A9M2whHxsiKtu8kpIn3cZp0PnVw
"""

import json
import os
import sys
from pathlib import Path

import requests

from ai_config import get_service_dict
from gen_with_liblib import make_signed_url


VALID_EXTS = {".jpg", ".jpeg", ".png"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def upload(image_path: str) -> str:
    """Upload a local file and return its public OSS URL."""
    p = Path(image_path)
    if not p.is_file():
        raise FileNotFoundError(image_path)

    ext = p.suffix.lower()
    if ext not in VALID_EXTS:
        raise ValueError(f"unsupported extension {ext}; need one of {VALID_EXTS}")

    size = p.stat().st_size
    if size > MAX_BYTES:
        raise ValueError(f"file too large: {size} bytes (max {MAX_BYTES})")

    cfg = get_service_dict("liblib")
    api_host = cfg.get("api_host") or "openapi.liblibai.cloud"
    access_key = os.environ.get("LIBLIB_ACCESS_KEY") or cfg.get("access_key", "")
    secret_key = os.environ.get("LIBLIB_SECRET_KEY") or cfg.get("secret_key", "")

    sig_url = make_signed_url(api_host, "/api/generate/upload/signature", access_key, secret_key)
    sig_payload = {
        "name": p.stem,
        "extension": ext.lstrip("."),
    }
    sig_resp = requests.post(sig_url, json=sig_payload, timeout=30)
    sig_resp.raise_for_status()
    body = sig_resp.json()
    if body.get("code") != 0:
        raise RuntimeError(f"signature request failed: {body}")
    data = body["data"]

    post_url = data["postUrl"]
    key = data["key"]

    form = {
        "key": key,
        "policy": data["policy"],
        "x-oss-date": data["xOssDate"],
        "x-oss-expires": str(data["xOssExpires"]),
        "x-oss-signature": data["xOssSignature"],
        "x-oss-credential": data["xOssCredential"],
        "x-oss-signature-version": data["xOssSignatureVersion"],
    }

    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}[ext.lstrip(".")]
    with open(p, "rb") as fh:
        files = {"file": (p.name, fh, mime)}
        resp = requests.post(post_url, data=form, files=files, timeout=120)

    if resp.status_code not in (200, 204):
        raise RuntimeError(f"OSS upload failed: HTTP {resp.status_code} {resp.text[:500]}")

    public_url = f"{post_url}/{key}"
    return public_url


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python upload_to_liblib.py <image_path>", file=sys.stderr)
        sys.exit(2)
    url = upload(sys.argv[1])
    print(url)
