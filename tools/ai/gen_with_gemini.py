"""
Generate an image with gemini-3.1-flash-image-preview via the bobdong.cn proxy.

Usage:
    python gen_with_gemini.py <prompt_file> [-o OUT_BASENAME] [--aspect RATIO] [--size SIZE]
        [--ref IMAGE_PATH ...]

    --aspect: aspect ratio, e.g. "1:1", "3:2", "7:2", "16:9". Default: model picks.
    --size:   output resolution, "1K" or "2K". Default: "1K".
    --ref:    reference image(s) to attach as multimodal input (repeatable).
              Used to preserve face/identity, control style, or guide pose.
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import time

import requests

from ai_config import get_service_config

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT_DIR = os.path.join(HERE, "out")
MAX_ATTEMPTS = 4
RETRY_DELAY_SEC = 2.0


def encode_image_part(path: str) -> dict:
    """Read a local image and return a Gemini inlineData part."""
    mime, _ = mimetypes.guess_type(path)
    if not mime or not mime.startswith("image/"):
        mime = "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return {"inlineData": {"mimeType": mime, "data": b64}}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("prompt_file")
    p.add_argument("-o", "--out", help="Output basename (no extension). Default: out/<prompt_stem>")
    p.add_argument("--aspect", help="Aspect ratio, e.g. 1:1, 3:2, 7:2. If omitted, model decides.")
    p.add_argument("--size", default="1K", choices=["1K", "2K"], help="Output resolution (default: 1K)")
    p.add_argument("--ref", action="append", default=[], metavar="PATH",
                   help="Path to a reference image. Repeatable; max ~5 in practice.")
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
        "gemini_image",
        env_prefix="GEMINI_IMAGE",
        default_host="bobdong.cn",
        default_model="gemini-3.1-flash-image-preview",
    )
    endpoint = (
        f"https://{config['api_host']}/v1beta/models/"
        f"{config['model']}:generateContent?key={config['api_key']}"
    )

    image_config = {"imageSize": args.size}
    if args.aspect:
        image_config["aspectRatio"] = args.aspect

    parts = []
    for ref_path in args.ref:
        if not os.path.isfile(ref_path):
            print(f"[ERROR] reference image not found: {ref_path}")
            return 1
        parts.append(encode_image_part(ref_path))
    parts.append({"text": prompt})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": image_config,
        },
    }

    print(f"[INFO] prompt: {args.prompt_file} ({len(prompt)} chars)")
    print(f"[INFO] model: {config['model']}, host: {config['api_host']}")
    print(f"[INFO] imageConfig: {image_config}")
    if args.ref:
        print(f"[INFO] reference images: {args.ref}")

    resp = None
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                timeout=300,
            )
            print(f"[INFO] attempt {attempt}/{MAX_ATTEMPTS} HTTP {resp.status_code}, body {len(resp.content)} bytes")
            break
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
        print(f"[ERROR] {resp.text[:1000]}")
        return 1

    data = resp.json()
    parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts") or []

    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline:
            mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
            ext = ".jpg" if "jpeg" in mime or "jpg" in mime else ".png"
            out_path = out_basename + ext
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(inline.get("data", "")))
            print(f"[OK] -> {out_path}")
            return 0

    print(f"[ERROR] no image in response: {json.dumps(data, ensure_ascii=False)[:500]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
