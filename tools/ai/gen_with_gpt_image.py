"""
Generate an image with gpt-image-2-pro via the bobdong.cn proxy.
Uses /v1/images/generations endpoint (OpenAI-compatible).
Supports transparent PNG output.

Usage:
    python gen_with_gpt_image.py <prompt_file> [-o OUT_BASENAME] [--size SIZE] [--transparent]
"""

import argparse
import base64
import json
import os
import sys
import time

import requests

from ai_config import get_service_config

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT_DIR = os.path.join(HERE, "out")
MAX_ATTEMPTS = 4
RETRY_DELAY_SEC = 2.0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("prompt_file")
    p.add_argument("-o", "--out", help="Output basename (no extension). Default: out/<prompt_stem>")
    p.add_argument("--size", default="1024x1024", help="Image size (default: 1024x1024)")
    p.add_argument("--transparent", action="store_true", help="Request transparent background")
    args = p.parse_args()

    with open(args.prompt_file, "r", encoding="utf-8") as f:
        prompt = f.read().strip()

    if args.out:
        out_basename = args.out
    else:
        stem = os.path.splitext(os.path.basename(args.prompt_file))[0]
        os.makedirs(DEFAULT_OUT_DIR, exist_ok=True)
        out_basename = os.path.join(DEFAULT_OUT_DIR, stem)

    config = get_service_config(
        "gpt_image",
        env_prefix="GPT_IMAGE",
        default_host="bobdong.cn",
        default_model="gpt-image-2-pro",
    )
    endpoint = f"https://{config['api_host']}/v1/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    }

    payload = {
        "model": config["model"],
        "prompt": prompt,
        "n": 1,
        "size": args.size,
    }

    if args.transparent:
        payload["background"] = "transparent"

    print(f"[INFO] prompt: {args.prompt_file} ({len(prompt)} chars)")
    print(
        f"[INFO] model: {config['model']}, host: {config['api_host']}, "
        f"size: {args.size}, transparent: {args.transparent}"
    )

    resp = None
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                timeout=300,
            )
            print(f"[INFO] attempt {attempt}/{MAX_ATTEMPTS} HTTP {resp.status_code}, body {len(resp.content)} bytes")
            if resp.status_code == 200:
                break
            if attempt < MAX_ATTEMPTS:
                print(f"[WARN] retry: {resp.text[:200]}")
                time.sleep(RETRY_DELAY_SEC * attempt)
        except requests.exceptions.RequestException as e:
            last_error = e
            print(f"[WARN] attempt {attempt}/{MAX_ATTEMPTS} failed: {type(e).__name__}: {e}")
            if attempt == MAX_ATTEMPTS:
                print(f"[ERROR] request failed after {MAX_ATTEMPTS} attempts")
                return 1
            time.sleep(RETRY_DELAY_SEC * attempt)

    if resp is None:
        print(f"[ERROR] no response object; last error: {last_error}")
        return 1

    if resp.status_code != 200:
        print(f"[ERROR] HTTP {resp.status_code}: {resp.text[:1000]}")
        return 1

    data = resp.json()
    images = data.get("data") or []

    if not images:
        print(f"[ERROR] no image in response: {json.dumps(data, ensure_ascii=False)[:500]}")
        return 1

    item = images[0]
    b64_data = item.get("b64_json", "")
    url = item.get("url", "")

    if b64_data:
        out_path = out_basename + ".png"
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(b64_data))
        print(f"[OK] -> {out_path}")
        return 0
    elif url:
        print(f"[INFO] downloading from URL: {url}")
        img_resp = requests.get(url, timeout=120)
        if img_resp.status_code == 200:
            out_path = out_basename + ".png"
            with open(out_path, "wb") as f:
                f.write(img_resp.content)
            print(f"[OK] -> {out_path}")
            return 0
        else:
            print(f"[ERROR] failed to download image: HTTP {img_resp.status_code}")
            return 1
    else:
        print(f"[ERROR] no image data or URL in response: {json.dumps(data, ensure_ascii=False)[:500]}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
