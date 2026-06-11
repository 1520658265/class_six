"""
PixelLab v2 API 直连客户端
直接 HTTP 调 v2，绕过 SDK 1.0.5 (走 v1) 的功能限制

支持:
- balance: 查 USD + 免费 generations 余额
- enhance_pixen_prompt: 优化 prompt
- create_pixen: 主力生成 (32-512px, 支持 view/direction/detail)
- create_pixflux: 备用生成 (32-400px)
- create_tileset: Wang 瓦片集 (异步 + 轮询)
- generate_8_rotations_v3: 8 方向角色 (异步)
- create_character_v3: 创建可命名角色 (异步)

依赖: pip install requests pillow
"""

from __future__ import annotations

import base64
import io
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Literal

import requests
from PIL import Image


BASE_URL = "https://api.pixellab.ai/v2"

# v2 枚举 - 实测合法值（文档说的 low/medium/high 是错的，实际同 v1 SDK）
DetailV2 = Literal["low detail", "medium detail", "highly detailed"]
OutlineV2 = Literal[
    "single color black outline", "single color outline",
    "selective outline", "lineless",
]
ViewV2 = Literal["side", "low top-down", "high top-down"]
DirectionV2 = Literal[
    "south", "south-east", "east", "north-east",
    "north", "north-west", "west", "south-west",
]


@dataclass
class GenerationResult:
    """统一的生成结果"""
    image: Image.Image
    usage: dict
    raw_response: dict

    def save(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.image.save(path)
        return path


class PixelLabV2Error(Exception):
    """v2 API 错误"""
    def __init__(self, status: int, detail: Any, message: str = ""):
        self.status = status
        self.detail = detail
        msg = f"[{status}] {message}\n  详情: {detail}" if message else f"[{status}] {detail}"
        super().__init__(msg)


class PixelLabV2Client:
    def __init__(self, token: Optional[str] = None, timeout: int = 120):
        self.token = token or os.environ.get("PIXELLAB_TOKEN", "")
        if not self.token:
            raise ValueError("缺少 token，传入参数或设环境变量 PIXELLAB_TOKEN")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })

    def _post(self, endpoint: str, json_body: dict, retries: int = 2) -> dict:
        url = f"{BASE_URL}{endpoint}"
        last_err = None
        for attempt in range(retries + 1):
            try:
                r = self.session.post(url, json=json_body, timeout=self.timeout)
                if r.status_code >= 400:
                    try:
                        detail = r.json().get("detail", r.text)
                    except Exception:
                        detail = r.text
                    # 4xx 是参数错, 不重试
                    if 400 <= r.status_code < 500:
                        raise PixelLabV2Error(r.status_code, detail, f"POST {endpoint} 失败")
                    # 5xx 重试
                    last_err = PixelLabV2Error(r.status_code, detail, f"POST {endpoint} 5xx")
                else:
                    return r.json()
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                last_err = e
                if attempt < retries:
                    wait = 2 ** attempt
                    print(f"  [网络重试] {attempt+1}/{retries} 后 {wait}s 重试: {e}")
                    time.sleep(wait)
                    continue
                raise PixelLabV2Error(0, str(e), f"POST {endpoint} 网络错误")
            if attempt < retries and last_err:
                time.sleep(2 ** attempt)
        raise last_err if last_err else RuntimeError("unreachable")

    def _get(self, endpoint: str) -> dict:
        url = f"{BASE_URL}{endpoint}"
        r = self.session.get(url, timeout=self.timeout)
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            raise PixelLabV2Error(r.status_code, detail, f"GET {endpoint} 失败")
        return r.json()

    @staticmethod
    def _decode_image(b64: str) -> Image.Image:
        raw = base64.b64decode(b64)
        return Image.open(io.BytesIO(raw)).convert("RGBA")

    @staticmethod
    def _extract_image_b64(image_field: Any) -> str:
        """v2 响应里 image 字段可能是 {'base64': '...'} 或 {'type':'base64','base64':'...'}"""
        if isinstance(image_field, dict):
            return image_field.get("base64", "")
        return image_field

    # ========== 账户 ==========

    def get_balance(self) -> dict:
        """
        v2 余额返回示例:
        {
            "credits": {"type": "usd", "usd": 10.5},
            "subscription": {
                "type": "generations",
                "plan": "Tier 2",
                "generations": 450,
                "total": 2000
            }
        }
        免费用户的 subscription 可能是 Free Trial，generations 显示剩余次数
        """
        return self._get("/balance")

    # ========== Prompt 增强 ==========

    def enhance_pixen_prompt(
        self,
        description: str,
        image_size: dict,
        outline: Optional[OutlineV2] = None,
        detail: Optional[DetailV2] = None,
        view: Optional[ViewV2] = None,
        direction: Optional[DirectionV2] = None,
        no_background: bool = True,
    ) -> str:
        """约 $0.002/次, 把简短描述扩展成像素艺术专用 prompt"""
        body = {
            "description": description,
            "image_size": image_size,
            "no_background": no_background,
        }
        if outline:   body["outline"] = outline
        if detail:    body["detail"] = detail
        if view:      body["view"] = view
        if direction: body["direction"] = direction

        resp = self._post("/enhance-pixen-prompt", body)
        return resp.get("enhanced_prompt", description)

    # ========== Pixen 主力生成 ==========

    def create_pixen(
        self,
        description: str,
        width: int,
        height: int,
        no_background: bool = True,
        outline: Optional[OutlineV2] = "single color black outline",
        detail: Optional[DetailV2] = "medium detail",
        view: Optional[ViewV2] = "high top-down",
        direction: Optional[DirectionV2] = "south",
    ) -> GenerationResult:
        """
        Pixen 主力模型 (32-512px, w/h 必须 4 的倍数)
        注意: pixen v2 不支持 negative_description!
              要排除内容必须直接写在 description 里 (例: "without X, no Y, not Z")
        """
        if width % 4 or height % 4:
            raise ValueError("width/height 必须是 4 的倍数")
        if not (32 <= width <= 512 and 32 <= height <= 512):
            raise ValueError("尺寸必须在 32-512 之间")

        body = {
            "description": description,
            "image_size": {"width": width, "height": height},
            "no_background": no_background,
        }
        if outline:   body["outline"] = outline
        if detail:    body["detail"] = detail
        if view:      body["view"] = view
        if direction: body["direction"] = direction

        resp = self._post("/create-image-pixen", body)
        b64 = self._extract_image_b64(resp.get("image", {}))
        return GenerationResult(
            image=self._decode_image(b64),
            usage=resp.get("usage", {}),
            raw_response=resp,
        )

    # ========== Pixflux 备用 ==========

    def create_pixflux(
        self,
        description: str,
        width: int,
        height: int,
        no_background: bool = True,
        init_image: Optional[Image.Image] = None,
        palette: Optional[list[str]] = None,
    ) -> GenerationResult:
        """Pixflux 备用模型 (32-400px), 支持 init_image"""
        body = {
            "description": description,
            "image_size": {"width": width, "height": height},
            "no_background": no_background,
        }
        if init_image is not None:
            buf = io.BytesIO()
            init_image.save(buf, format="PNG")
            body["init_image"] = {
                "type": "base64",
                "base64": base64.b64encode(buf.getvalue()).decode(),
            }
        if palette:
            body["palette"] = palette

        resp = self._post("/create-image-pixflux", body)
        b64 = self._extract_image_b64(resp.get("image", {}))
        return GenerationResult(
            image=self._decode_image(b64),
            usage=resp.get("usage", {}),
            raw_response=resp,
        )

    # ========== 异步任务轮询 ==========

    def poll_job(
        self,
        job_id: str,
        interval: float = 3.0,
        max_wait: float = 300.0,
    ) -> dict:
        """轮询 /background-jobs/{job_id} 直到 completed/failed"""
        elapsed = 0.0
        while elapsed < max_wait:
            resp = self._get(f"/background-jobs/{job_id}")
            status = resp.get("status", "")
            if status == "completed":
                return resp
            if status == "failed":
                raise PixelLabV2Error(500, resp.get("error", "job failed"),
                                      f"任务 {job_id} 失败")
            time.sleep(interval)
            elapsed += interval
        raise PixelLabV2Error(408, "timeout", f"等待 {max_wait}s 后任务仍未完成")

    # ========== Tileset (异步) ==========

    def create_tileset(
        self,
        lower_description: str,
        upper_description: str,
        transition_description: str,
        tile_size: int = 16,
        transition_size: float = 0.5,
        view: ViewV2 = "high top-down",
        outline: OutlineV2 = "single color black outline",
        detail: DetailV2 = "medium detail",
    ) -> dict:
        """
        Wang 瓦片集 (16 或 23 块), 用于地图编辑器
        例: 草地→泥地 过渡:
          lower="green grass", upper="brown dirt", transition="grass with patches of dirt"
        """
        if tile_size not in (16, 32):
            raise ValueError("tile_size 必须是 16 或 32")

        body = {
            "lower_description": lower_description,
            "upper_description": upper_description,
            "transition_description": transition_description,
            "tile_size": {"width": tile_size, "height": tile_size},
            "transition_size": transition_size,
            "view": view,
            "outline": outline,
            "detail": detail,
        }
        resp = self._post("/create-tileset", body)
        job_id = resp.get("background_job_id")
        tileset_id = resp.get("tileset_id")

        print(f"  [tileset] 任务 {job_id[:8]}... 提交，轮询中...")
        self.poll_job(job_id)

        return self.get_tileset(tileset_id)

    def get_tileset(self, tileset_id: str) -> dict:
        return self._get(f"/tilesets/{tileset_id}")

    # ========== 8 方向角色 (异步) ==========

    def create_8_rotations_v3(
        self,
        description: str,
        width: int = 64,
        height: int = 64,
    ) -> dict[str, Image.Image]:
        """
        从描述生成 8 方向角色，返回 {direction: PIL.Image}
        消耗约 ceil(s*s*8 / 65536) generations
        """
        body = {
            "description": description,
            "image_size": {"width": width, "height": height},
        }
        resp = self._post("/generate-8-rotations-v3", body)
        job_id = resp.get("background_job_id")
        print(f"  [8方向] 任务 {job_id[:8]}... 提交，轮询中...")

        result = self.poll_job(job_id)
        last = result.get("last_response", {})
        images_dict = last.get("images", {})

        return {
            direction: self._decode_image(self._extract_image_b64(img))
            for direction, img in images_dict.items()
        }


def format_balance(balance: dict) -> str:
    """格式化打印余额"""
    out = []
    credits = balance.get("credits", {})
    sub = balance.get("subscription", {})

    if credits:
        out.append(f"USD Credits: ${credits.get('usd', 0):.2f}")
    if sub:
        plan = sub.get("plan", "Free Trial")
        gen = sub.get("generations", 0)
        total = sub.get("total", 0)
        if total:
            out.append(f"订阅: {plan} | 生成额度: {gen}/{total}")
        else:
            out.append(f"订阅: {plan} | 生成额度: {gen}")
    return " | ".join(out) if out else str(balance)


if __name__ == "__main__":
    """简单自测"""
    client = PixelLabV2Client()

    print("[1/2] 查余额...")
    bal = client.get_balance()
    print(f"  {format_balance(bal)}")
    print(f"  原始: {bal}")

    print("\n[2/2] 测试 enhance (花 $0.002)...")
    enhanced = client.enhance_pixen_prompt(
        description="red brick rural school building",
        image_size={"width": 256, "height": 256},
        view="high top-down",
        direction="south",
        detail="highly detailed",
    )
    print(f"  增强结果: {enhanced}")
