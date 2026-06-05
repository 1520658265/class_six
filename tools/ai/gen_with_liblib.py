"""
Generate an image with LiblibAI custom model API.

Doc: https://resonate.feishu.cn/wiki/UAMVw67NcifQHukf8fpccgS5n6d

Endpoint base: https://openapi.liblibai.cloud
- Submit text2img: POST /api/generate/webui/text2img
- Submit img2img:  POST /api/generate/webui/img2img
- Query status:    POST /api/generate/webui/status

Auth: each request appends AccessKey/Signature/Timestamp/SignatureNonce as
query params. Signature = HMAC-SHA1(uri + "&" + ts + "&" + nonce, SecretKey),
url-safe-base64 without padding.

Config (tools/ai/config.local.json):
    {
      "services": {
        "liblib": {
          "api_host": "openapi.liblibai.cloud",
          "access_key": "...",
          "secret_key": "...",
          "checkpoint_id": "<base model versionUuid>",
          "loras": [
            {"modelId": "<lora versionUuid>", "weight": 0.9}
          ],
          "template_uuid_text2img": "e10adc3949ba59abbe56e057f20f883e"
        }
      }
    }

Usage:
    python gen_with_liblib.py <prompt_file> [-o OUT_BASENAME]
        [--negative <path>] [--width 832] [--height 1216]
        [--steps 30] [--cfg 7] [--seed -1]
        [--source <url>]                  # img2img mode
        [--controlnet-image <url>] [--controlnet-type pose]
        [--lora versionUuid:weight] ...   # extra LoRAs (repeatable)
        [--count 1]
"""

import argparse
import base64
import hmac
import json
import os
import sys
import time
import uuid
from hashlib import sha1
from pathlib import Path

import requests

from ai_config import get_service_dict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT_DIR = os.path.join(HERE, "out")
SUBMIT_MAX_ATTEMPTS = 4
SUBMIT_RETRY_DELAY = 2.0
POLL_INTERVAL = 3.0
POLL_TIMEOUT = 600  # 10 minutes; Liblib auto-times-out at 30 min
DEFAULT_TEMPLATE_TEXT2IMG = "e10adc3949ba59abbe56e057f20f883e"
DEFAULT_TEMPLATE_IMG2IMG = "9c7d531dc75f476aa833b3d452b8f7ad"

# Status codes from Liblib doc 5.5
STATUS_PENDING = 1
STATUS_RUNNING = 2
STATUS_GENERATED = 3
STATUS_AUDITING = 4
STATUS_SUCCESS = 5
STATUS_FAILED = 6
STATUS_TIMEOUT = 7
TERMINAL_STATUSES = {STATUS_SUCCESS, STATUS_FAILED, STATUS_TIMEOUT}

# ControlNet preprocessor enum (subset; doc section 4.2.5)
CONTROLNET_PREPROCESSOR = {
    "canny": 0,
    "depth": 3,
    "pose": 7,
    "openpose": 7,
    "lineart": 13,
    "softedge": 11,
}


def make_signed_url(api_host: str, uri: str, access_key: str, secret_key: str) -> str:
    """Build the signed request URL per Liblib auth scheme."""
    timestamp = str(int(time.time() * 1000))
    nonce = uuid.uuid4().hex
    content = f"{uri}&{timestamp}&{nonce}"
    digest = hmac.new(secret_key.encode(), content.encode(), sha1).digest()
    signature = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return (
        f"https://{api_host}{uri}"
        f"?AccessKey={access_key}"
        f"&Signature={signature}"
        f"&Timestamp={timestamp}"
        f"&SignatureNonce={nonce}"
    )


def post_json(url: str, payload: dict) -> dict:
    """POST JSON with retry. Returns parsed body or raises."""
    last_error = None
    for attempt in range(1, SUBMIT_MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json()
            print(f"[WARN] attempt {attempt}/{SUBMIT_MAX_ATTEMPTS} HTTP {resp.status_code}: {resp.text[:300]}")
        except requests.exceptions.RequestException as e:
            last_error = e
            print(f"[WARN] attempt {attempt}/{SUBMIT_MAX_ATTEMPTS} {type(e).__name__}: {e}")
        if attempt < SUBMIT_MAX_ATTEMPTS:
            time.sleep(SUBMIT_RETRY_DELAY * attempt)
    raise RuntimeError(f"request failed after {SUBMIT_MAX_ATTEMPTS} attempts: {last_error}")


def parse_lora_arg(spec: str) -> dict:
    """Parse '<versionUuid>:<weight>' into Liblib additionalNetwork entry."""
    if ":" not in spec:
        raise argparse.ArgumentTypeError(f"--lora must be 'uuid:weight', got: {spec}")
    model_id, weight = spec.split(":", 1)
    try:
        return {"modelId": model_id.strip(), "weight": float(weight)}
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid lora weight: {weight}")


def build_text2img_payload(args, prompt: str, negative: str, cfg: dict) -> dict:
    """Assemble the /text2img request body."""
    params = {
        "checkPointId": args.checkpoint or cfg.get("checkpoint_id"),
        "prompt": prompt,
        "sampler": args.sampler,
        "steps": args.steps,
        "cfgScale": args.cfg,
        "width": args.width,
        "height": args.height,
        "imgCount": args.count,
        "randnSource": 0,
        "seed": args.seed,
        "restoreFaces": 0,
    }
    if negative:
        params["negativePrompt"] = negative

    loras = list(cfg.get("loras") or [])
    loras.extend(args.lora or [])
    if loras:
        params["additionalNetwork"] = loras[:5]

    if args.controlnet_image:
        cn_type = args.controlnet_type or "openpose"
        preprocessor = CONTROLNET_PREPROCESSOR.get(cn_type)
        if preprocessor is None:
            raise SystemExit(f"unknown --controlnet-type: {cn_type}")
        params["controlNet"] = [{
            "unitOrder": 1,
            "sourceImage": args.controlnet_image,
            "preprocessor": preprocessor,
            "controlWeight": args.controlnet_weight,
            "startingControlStep": 0,
            "endingControlStep": 1,
            "pixelPerfect": 1,
            "controlMode": 0,
            "resizeMode": 1,
        }]

    if not params["checkPointId"]:
        raise SystemExit(
            "missing checkpoint id; pass --checkpoint or set "
            "services.liblib.checkpoint_id in config.local.json"
        )

    template = cfg.get("template_uuid_text2img") or DEFAULT_TEMPLATE_TEXT2IMG
    return {"templateUuid": template, "generateParams": params}


def build_img2img_payload(args, prompt: str, negative: str, cfg: dict) -> dict:
    """Assemble the /img2img request body. Requires --source URL."""
    params = {
        "checkPointId": args.checkpoint or cfg.get("checkpoint_id"),
        "prompt": prompt,
        "sampler": args.sampler,
        "steps": args.steps,
        "cfgScale": args.cfg,
        "imgCount": args.count,
        "randnSource": 0,
        "seed": args.seed,
        "restoreFaces": 0,
        "sourceImage": args.source,
        "resizeMode": 0,
        "resizedWidth": args.width,
        "resizedHeight": args.height,
        "mode": 0,
        "denoisingStrength": args.denoise,
    }
    if negative:
        params["negativePrompt"] = negative

    loras = list(cfg.get("loras") or [])
    loras.extend(args.lora or [])
    if loras:
        params["additionalNetwork"] = loras[:5]

    if args.controlnet_image:
        cn_type = args.controlnet_type or "openpose"
        preprocessor = CONTROLNET_PREPROCESSOR.get(cn_type)
        if preprocessor is None:
            raise SystemExit(f"unknown --controlnet-type: {cn_type}")
        params["controlNet"] = [{
            "unitOrder": 1,
            "sourceImage": args.controlnet_image,
            "preprocessor": preprocessor,
            "controlWeight": args.controlnet_weight,
            "startingControlStep": 0,
            "endingControlStep": 1,
            "pixelPerfect": 1,
            "controlMode": 0,
            "resizeMode": 1,
        }]

    if not params["checkPointId"]:
        raise SystemExit(
            "missing checkpoint id; pass --checkpoint or set "
            "services.liblib.checkpoint_id in config.local.json"
        )

    template = cfg.get("template_uuid_img2img") or DEFAULT_TEMPLATE_IMG2IMG
    return {"templateUuid": template, "generateParams": params}


def poll_until_done(api_host: str, access_key: str, secret_key: str, generate_uuid: str) -> dict:
    """Poll /status until terminal. Returns the final data block."""
    deadline = time.time() + POLL_TIMEOUT
    last_status = None
    while time.time() < deadline:
        url = make_signed_url(api_host, "/api/generate/webui/status", access_key, secret_key)
        body = post_json(url, {"generateUuid": generate_uuid})
        data = body.get("data") or {}
        status = data.get("generateStatus")
        if status != last_status:
            print(f"[INFO] status={status} ({_status_name(status)}) "
                  f"progress={data.get('percentCompleted', 0):.0%}")
            last_status = status
        if status in TERMINAL_STATUSES:
            return data
        time.sleep(POLL_INTERVAL)
    raise RuntimeError(f"polling timeout after {POLL_TIMEOUT}s")


def _status_name(status):
    return {
        STATUS_PENDING: "pending",
        STATUS_RUNNING: "running",
        STATUS_GENERATED: "generated",
        STATUS_AUDITING: "auditing",
        STATUS_SUCCESS: "success",
        STATUS_FAILED: "failed",
        STATUS_TIMEOUT: "timeout",
    }.get(status, f"unknown({status})")


def download_image(url: str, out_path: str) -> None:
    """Stream-download a URL to disk."""
    with requests.get(url, timeout=120, stream=True) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("prompt_file", help="Path to prompt text file (UTF-8). Used as the positive prompt.")
    p.add_argument("-o", "--out", help="Output basename (no extension). Default: out/<prompt_stem>")
    p.add_argument("--negative", help="Path to a negative prompt text file")
    p.add_argument("--width", type=int, default=832)
    p.add_argument("--height", type=int, default=1216)
    p.add_argument("--steps", type=int, default=30)
    p.add_argument("--cfg", type=float, default=7.0)
    p.add_argument("--sampler", type=int, default=15, help="Sampler enum (15 = DPM++ 2M Karras)")
    p.add_argument("--seed", type=int, default=-1)
    p.add_argument("--count", type=int, default=1, help="imgCount, 1-4")
    p.add_argument("--checkpoint", help="Override checkpoint versionUuid")
    p.add_argument("--lora", action="append", type=parse_lora_arg, default=[],
                   metavar="UUID:WEIGHT", help="Add a LoRA (repeatable, max 5 total)")
    p.add_argument("--source", help="img2img source image URL (switches to img2img mode)")
    p.add_argument("--denoise", type=float, default=0.6, help="img2img denoising strength")
    p.add_argument("--controlnet-image", help="ControlNet reference image URL")
    p.add_argument("--controlnet-type", default="openpose",
                   choices=sorted(CONTROLNET_PREPROCESSOR.keys()))
    p.add_argument("--controlnet-weight", type=float, default=0.9)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    prompt_path = Path(args.prompt_file)
    prompt = prompt_path.read_text(encoding="utf-8").strip()

    negative = ""
    if args.negative:
        negative = Path(args.negative).read_text(encoding="utf-8").strip()

    if args.out:
        out_basename = args.out
    else:
        os.makedirs(DEFAULT_OUT_DIR, exist_ok=True)
        out_basename = os.path.join(DEFAULT_OUT_DIR, prompt_path.stem)

    cfg = get_service_dict("liblib")
    api_host = cfg.get("api_host") or "openapi.liblibai.cloud"
    access_key = os.environ.get("LIBLIB_ACCESS_KEY") or cfg.get("access_key", "")
    secret_key = os.environ.get("LIBLIB_SECRET_KEY") or cfg.get("secret_key", "")
    if not access_key or not secret_key:
        raise SystemExit(
            "missing liblib access_key/secret_key. Add them to "
            "tools/ai/config.local.json under services.liblib, or set "
            "LIBLIB_ACCESS_KEY / LIBLIB_SECRET_KEY env vars."
        )

    if args.source:
        uri = "/api/generate/webui/img2img"
        payload = build_img2img_payload(args, prompt, negative, cfg)
        mode = "img2img"
    else:
        uri = "/api/generate/webui/text2img"
        payload = build_text2img_payload(args, prompt, negative, cfg)
        mode = "text2img"

    print(f"[INFO] mode: {mode}, host: {api_host}, prompt: {prompt_path} ({len(prompt)} chars)")
    print(f"[INFO] size: {args.width}x{args.height}, steps={args.steps}, "
          f"cfg={args.cfg}, seed={args.seed}, count={args.count}")
    if payload["generateParams"].get("additionalNetwork"):
        print(f"[INFO] LoRAs: {payload['generateParams']['additionalNetwork']}")
    if payload["generateParams"].get("controlNet"):
        print(f"[INFO] ControlNet: {args.controlnet_type} weight={args.controlnet_weight}")

    submit_url = make_signed_url(api_host, uri, access_key, secret_key)
    submit_resp = post_json(submit_url, payload)
    if submit_resp.get("code") != 0:
        print(f"[ERROR] submit failed: {json.dumps(submit_resp, ensure_ascii=False)[:500]}")
        return 1
    generate_uuid = (submit_resp.get("data") or {}).get("generateUuid")
    if not generate_uuid:
        print(f"[ERROR] no generateUuid in response: {submit_resp}")
        return 1
    print(f"[INFO] task submitted: generateUuid={generate_uuid}")

    final = poll_until_done(api_host, access_key, secret_key, generate_uuid)
    status = final.get("generateStatus")
    if status != STATUS_SUCCESS:
        print(f"[ERROR] task ended with status {status} ({_status_name(status)}): "
              f"{final.get('generateMsg', '')}")
        return 1

    images = final.get("images") or []
    if not images:
        print(f"[ERROR] success status but no images: {final}")
        return 1

    print(f"[INFO] cost {final.get('pointsCost', '?')} points, "
          f"balance {final.get('accountBalance', '?')}")

    rc = 0
    for i, img in enumerate(images):
        url = img.get("imageUrl")
        if not url:
            print(f"[WARN] image {i} has no url; auditStatus={img.get('auditStatus')}")
            rc = 1
            continue
        suffix = "" if len(images) == 1 else f"_{i + 1}"
        out_path = f"{out_basename}{suffix}.png"
        try:
            download_image(url, out_path)
            print(f"[OK] -> {out_path} (seed={img.get('seed')})")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] download failed for {url}: {e}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())




