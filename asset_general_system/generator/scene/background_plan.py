from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .contracts import scene_paths
from .progress import mark_completed, mark_in_progress


EXTRACT_METHODS = {"extract_from_concept", "extract_and_cleanup"}


def build_background_plan(scene_dir: str | Path, force: bool = False, concept_image: str | Path | None = None) -> dict[str, Any]:
    paths = scene_paths(scene_dir)
    if paths.background_plan.exists() and not force:
        return _read_json(paths.background_plan)
    mark_in_progress(paths.root, "4_background_plan")
    art_request = _read_json(paths.art_request)
    concept_path = Path(concept_image) if concept_image else paths.concept_image
    if concept_image and not concept_path.is_absolute():
        concept_path = paths.root / concept_path
    concept_image = _relative_to_scene(paths.root, concept_path)
    plan = {
        "version": "1.0",
        "kind": "background_plan",
        "scene_id": paths.root.name,
        "concept_image": concept_image,
        "tile_size": art_request.get("tile_size") or [64, 64],
        "map_size": art_request.get("map_size") or [64, 64],
        "image_size": _image_size(concept_path),
        "review_items": [],
        "background_entities": [],
        "foreground_objects": [],
    }
    for obj in art_request.get("objects", []) or []:
        if not isinstance(obj, dict):
            continue
        if obj.get("asset_role") == "base_terrain" or obj.get("category") == "terrain_tile":
            plan["review_items"].append(_base_terrain_review_item(obj))
        else:
            plan["foreground_objects"].append(
                {
                    "id": obj.get("id"),
                    "category": obj.get("category"),
                    "display_name": obj.get("display_name"),
                    "placement_zone": obj.get("placement_zone"),
                }
            )
    for target in art_request.get("generation_targets", []) or []:
        if isinstance(target, dict) and target.get("asset_role") == "composite_source":
            entity = _background_entity(target)
            plan["background_entities"].append(entity)
            plan["review_items"].extend(entity["parts"])
    _write_json(paths.background_plan, plan)
    mark_completed(paths.root, "4_background_plan")
    return plan


def write_background_review_html(scene_dir: str | Path, force: bool = False) -> Path:
    paths = scene_paths(scene_dir)
    if paths.background_review.exists() and not force:
        return paths.background_review
    plan = _read_json(paths.background_plan)
    html = _review_html(plan)
    paths.background_review.write_text(html, encoding="utf-8")
    return paths.background_review


def extract_background_tiles(scene_dir: str | Path, force: bool = False) -> list[str]:
    paths = scene_paths(scene_dir)
    plan = _read_json(paths.background_plan)
    concept_path = paths.root / str(plan.get("concept_image") or "")
    if not concept_path.exists():
        raise FileNotFoundError(f"concept image not found: {concept_path}")
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("PIL not available for background tile extraction") from exc

    paths.background_tiles_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    with Image.open(concept_path).convert("RGBA") as source:
        for item in plan.get("review_items", []) or []:
            if not isinstance(item, dict) or item.get("method") not in EXTRACT_METHODS:
                continue
            rect = item.get("crop_rect")
            if not _valid_rect(rect):
                continue
            asset_id = _safe_id(item.get("asset_id") or item.get("id") or "background_tile")
            png_path = paths.background_tiles_dir / f"{asset_id}.png"
            json_path = paths.background_tiles_dir / f"{asset_id}.json"
            if png_path.exists() and json_path.exists() and not force:
                written.append(asset_id)
                continue
            x, y, w, h = [int(v) for v in rect]
            tile = source.crop((x, y, x + w, y + h))
            target_size = item.get("target_size") or plan.get("tile_size") or [64, 64]
            if isinstance(target_size, list) and len(target_size) == 2:
                target = (int(target_size[0]), int(target_size[1]))
                if tile.size != target:
                    tile = tile.resize(target, Image.Resampling.NEAREST)
            tile.save(png_path, "PNG")
            tile.close()
            _write_json(
                json_path,
                {
                    "asset_id": asset_id,
                    "source": "background_plan",
                    "method": item.get("method"),
                    "concept_image": plan.get("concept_image"),
                    "crop_rect": rect,
                    "target_size": list(target_size),
                    "review_item_id": item.get("id"),
                },
            )
            written.append(asset_id)
    return written


def _base_terrain_review_item(obj: dict[str, Any]) -> dict[str, Any]:
    source_canvas = obj.get("source_canvas") or [64, 64]
    return {
        "id": str(obj.get("id")),
        "asset_id": str(obj.get("asset_id") or obj.get("id")),
        "kind": "base_terrain",
        "display_name": obj.get("display_name") or obj.get("id"),
        "method": "extract_or_regenerate",
        "status": "pending_review",
        "crop_rect": None,
        "target_size": source_canvas,
        "notes": "Large uniform terrain is often a good extraction candidate if the concept image has a clean patch.",
    }


def _background_entity(target: dict[str, Any]) -> dict[str, Any]:
    composite_id = str(target.get("composite_id") or target.get("id"))
    parts = []
    for part in target.get("parts", []) or []:
        if not isinstance(part, dict):
            continue
        key = str(part.get("key"))
        parts.append(
            {
                "id": f"{composite_id}:{key}",
                "asset_id": f"{composite_id}_{key}",
                "kind": "composite_part",
                "composite_id": composite_id,
                "part_key": key,
                "display_name": part.get("display_name") or key,
                "method": "extract_or_regenerate",
                "status": "pending_review",
                "crop_rect": None,
                "target_size": [64, 64],
                "notes": "Use extraction only when this part is clean, grid-aligned, and reusable.",
            }
        )
    return {
        "id": composite_id,
        "source_target_id": target.get("id"),
        "type": target.get("composite_type"),
        "display_name": target.get("display_name"),
        "footprint": target.get("footprint"),
        "layout": target.get("layout") or [],
        "parts": parts,
    }


def _review_html(plan: dict[str, Any]) -> str:
    plan_json = json.dumps(plan, ensure_ascii=False)
    return _HTML_TEMPLATE.replace("__PLAN_JSON__", plan_json)


def _image_size(path: Path) -> list[int] | None:
    if not path.exists():
        return None
    try:
        from PIL import Image

        with Image.open(path) as image:
            return [image.width, image.height]
    except Exception:
        return None


def _relative_to_scene(scene_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(scene_dir)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _valid_rect(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(item, int | float) and int(item) >= 0 for item in value)
        and int(value[2]) > 0
        and int(value[3]) > 0
    )


def _safe_id(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_") or "background_tile"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


_HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Background Tile Review</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f1e7;
      --panel: #fffdf8;
      --ink: #241f1a;
      --muted: #6f665c;
      --line: #d6c8b5;
      --accent: #256f5d;
      --warn: #9a5c10;
      --bad: #9b2f2f;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Segoe UI, system-ui, sans-serif; background: var(--bg); color: var(--ink); }
    header { height: 48px; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; border-bottom: 1px solid var(--line); background: var(--panel); }
    h1 { font-size: 16px; margin: 0; font-weight: 650; }
    button, select { font: inherit; }
    button { min-height: 32px; border: 1px solid var(--line); background: #fff; color: var(--ink); padding: 6px 10px; cursor: pointer; }
    button:hover { border-color: var(--accent); }
    button.active { background: var(--accent); border-color: var(--accent); color: white; }
    main { display: grid; grid-template-columns: minmax(420px, 1fr) 360px; height: calc(100vh - 48px); }
    .stage { min-width: 0; overflow: auto; padding: 16px; }
    .canvas-wrap { width: min(100%, 1024px); position: relative; border: 1px solid var(--line); background: #d8c28a; }
    canvas { display: block; width: 100%; height: auto; image-rendering: pixelated; }
    aside { border-left: 1px solid var(--line); background: var(--panel); overflow: auto; padding: 12px; }
    .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }
    .hint { color: var(--muted); font-size: 12px; line-height: 1.45; }
    .items { display: grid; gap: 8px; margin-top: 10px; }
    .item { border: 1px solid var(--line); background: white; padding: 8px; cursor: pointer; }
    .item.selected { border-color: var(--accent); box-shadow: inset 3px 0 0 var(--accent); }
    .item-title { display: flex; justify-content: space-between; gap: 8px; font-size: 13px; font-weight: 650; }
    .item-meta { margin-top: 4px; color: var(--muted); font-size: 12px; }
    .method { color: var(--warn); }
    .method.extract_from_concept, .method.extract_and_cleanup { color: var(--accent); }
    .method.ignore { color: var(--bad); }
    textarea { width: 100%; min-height: 180px; resize: vertical; font-family: Consolas, monospace; font-size: 12px; }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; height: auto; }
      aside { border-left: 0; border-top: 1px solid var(--line); }
    }
  </style>
</head>
<body>
  <header>
    <h1>Background Tile Review</h1>
    <div class="row" style="margin:0">
      <button id="exportBtn">导出 JSON</button>
      <button id="copyBtn">复制 JSON</button>
    </div>
  </header>
  <main>
    <section class="stage">
      <div class="canvas-wrap">
        <canvas id="canvas"></canvas>
      </div>
      <p class="hint">拖拽框选当前条目的 crop rect。开启网格吸附时，选择会吸附到概念图对应的地图格。</p>
    </section>
    <aside>
      <div class="row">
        <button data-method="extract_from_concept">可直接裁</button>
        <button data-method="extract_and_cleanup">裁后修整</button>
        <button data-method="regenerate">重生成</button>
        <button data-method="ignore">忽略</button>
      </div>
      <label class="row"><input type="checkbox" id="snap" checked> 网格吸附</label>
      <div class="hint" id="selectionInfo"></div>
      <div class="items" id="items"></div>
      <h2 style="font-size:14px;margin:16px 0 8px">导出内容</h2>
      <textarea id="jsonOut" spellcheck="false"></textarea>
    </aside>
  </main>
  <script>
    const plan = __PLAN_JSON__;
    const items = plan.review_items || [];
    let selected = items[0] || null;
    let image = new Image();
    let dragging = false;
    let dragStart = null;
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const itemList = document.getElementById('items');
    const jsonOut = document.getElementById('jsonOut');
    const snap = document.getElementById('snap');
    const selectionInfo = document.getElementById('selectionInfo');

    image.onload = () => {
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      plan.image_size = [canvas.width, canvas.height];
      render();
    };
    image.src = plan.concept_image;

    function gridStep() {
      const map = plan.map_size || [64, 64];
      return [canvas.width / map[0], canvas.height / map[1]];
    }
    function snapPoint(p) {
      if (!snap.checked) return p;
      const [gx, gy] = gridStep();
      return [Math.round(p[0] / gx) * gx, Math.round(p[1] / gy) * gy];
    }
    function canvasPoint(evt) {
      const rect = canvas.getBoundingClientRect();
      return [
        (evt.clientX - rect.left) * canvas.width / rect.width,
        (evt.clientY - rect.top) * canvas.height / rect.height,
      ];
    }
    function rectFromPoints(a, b) {
      const x1 = Math.max(0, Math.min(a[0], b[0]));
      const y1 = Math.max(0, Math.min(a[1], b[1]));
      const x2 = Math.min(canvas.width, Math.max(a[0], b[0]));
      const y2 = Math.min(canvas.height, Math.max(a[1], b[1]));
      return [Math.round(x1), Math.round(y1), Math.round(x2 - x1), Math.round(y2 - y1)];
    }
    function render() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0);
      drawGrid();
      for (const item of items) {
        if (!item.crop_rect) continue;
        const r = item.crop_rect;
        ctx.strokeStyle = item === selected ? '#256f5d' : 'rgba(40,40,40,.6)';
        ctx.lineWidth = item === selected ? 4 : 2;
        ctx.strokeRect(r[0], r[1], r[2], r[3]);
      }
      renderItems();
      updateJson();
    }
    function drawGrid() {
      const [gx, gy] = gridStep();
      ctx.strokeStyle = 'rgba(255,255,255,.22)';
      ctx.lineWidth = 1;
      for (let x = 0; x <= canvas.width; x += gx) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
      }
      for (let y = 0; y <= canvas.height; y += gy) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
      }
    }
    function renderItems() {
      itemList.innerHTML = '';
      items.forEach((item) => {
        const el = document.createElement('button');
        el.className = 'item' + (item === selected ? ' selected' : '');
        el.innerHTML = `<div class="item-title"><span>${item.display_name || item.id}</span><span class="method ${item.method}">${item.method}</span></div><div class="item-meta">${item.kind} | ${item.id}<br>${item.crop_rect ? item.crop_rect.join(', ') : 'no crop rect'}</div>`;
        el.onclick = () => { selected = item; render(); };
        itemList.appendChild(el);
      });
      selectionInfo.textContent = selected ? `当前: ${selected.id}` : '没有 review item';
    }
    function updateJson() {
      jsonOut.value = JSON.stringify(plan, null, 2);
    }
    canvas.addEventListener('pointerdown', (evt) => {
      if (!selected) return;
      dragging = true;
      dragStart = snapPoint(canvasPoint(evt));
    });
    canvas.addEventListener('pointermove', (evt) => {
      if (!dragging || !selected) return;
      const current = snapPoint(canvasPoint(evt));
      selected.crop_rect = rectFromPoints(dragStart, current);
      render();
    });
    window.addEventListener('pointerup', () => { dragging = false; });
    document.querySelectorAll('[data-method]').forEach((button) => {
      button.addEventListener('click', () => {
        if (!selected) return;
        selected.method = button.dataset.method;
        selected.status = 'reviewed';
        render();
      });
    });
    document.getElementById('exportBtn').onclick = () => {
      const blob = new Blob([jsonOut.value + '\\n'], {type: 'application/json'});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'background_plan.reviewed.json';
      a.click();
      URL.revokeObjectURL(a.href);
    };
    document.getElementById('copyBtn').onclick = async () => {
      await navigator.clipboard.writeText(jsonOut.value);
    };
  </script>
</body>
</html>
"""
