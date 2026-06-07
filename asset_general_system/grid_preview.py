#!/usr/bin/env python
"""
Grid VFX 预览生成器

把 Gemini 出的 2048×2048 raw 图按 N×M grid 切片，作为 sprite sheet
顺序播放。

用法：
    python grid_preview.py output/pencil_storm/pencil_storm_raw.png
    python grid_preview.py output/pencil_storm/pencil_storm_raw.png --grid 4x4 --fps 12

输出：
    pencil_storm_raw.grid.html  # 双击打开
"""

import argparse
from pathlib import Path


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>__TITLE__ - Grid Preview</title>
<style>
  :root {
    --bg: #1a1a1a;
    --panel: #262630;
    --border: #3a3a45;
    --text: #eee;
    --accent: #4af;
    --ok: #6f9;
  }
  * { box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    margin: 0;
    padding: 20px;
  }
  h1 { color: var(--accent); margin: 0 0 8px 0; }
  .subtitle { color: #888; margin-bottom: 20px; font-size: 14px; }
  .layout {
    display: grid;
    grid-template-columns: 1fr 320px;
    gap: 20px;
  }
  .stage {
    background:
      repeating-conic-gradient(#2a2a30 0% 25%, #333 0% 50%) 0 0 / 32px 32px;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 540px;
  }
  canvas {
    image-rendering: pixelated;
    border: 1px solid var(--border);
    background: #0a0a0e;
    max-width: 100%;
    max-height: 70vh;
  }
  .controls {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    height: fit-content;
  }
  h3 {
    margin: 16px 0 10px 0;
    color: var(--ok);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
  }
  h3:first-child { margin-top: 0; }
  button {
    background: var(--panel);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 10px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.15s;
  }
  button:hover { border-color: var(--accent); color: var(--accent); }
  .play-btn {
    width: 100%;
    background: var(--ok);
    color: #000;
    border: none;
    padding: 12px;
    font-weight: 600;
    margin-bottom: 12px;
  }
  .play-btn:hover { background: #8fc; }
  .row { display: flex; gap: 8px; margin-bottom: 8px; }
  .row button { flex: 1; }
  label {
    font-size: 12px;
    color: #aaa;
    display: block;
    margin: 12px 0 4px;
  }
  input[type=range] { width: 100%; }
  .value { float: right; color: var(--accent); }
  .frame-grid {
    display: grid;
    grid-template-columns: repeat(__COLS__, 1fr);
    gap: 4px;
    margin-top: 8px;
  }
  .frame-cell {
    aspect-ratio: 1;
    border: 1px solid var(--border);
    border-radius: 3px;
    overflow: hidden;
    position: relative;
    cursor: pointer;
    background: #000;
  }
  .frame-cell.active {
    border-color: var(--accent);
    box-shadow: 0 0 8px var(--accent);
  }
  .frame-cell::after {
    content: attr(data-idx);
    position: absolute;
    bottom: 1px; right: 3px;
    font-size: 9px;
    color: #fff;
    text-shadow: 0 0 3px #000;
    pointer-events: none;
  }
  .frame-cell canvas {
    width: 100%;
    height: 100%;
    border: none;
    display: block;
  }
  .info {
    font-size: 11px;
    color: #888;
    line-height: 1.6;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }
  kbd {
    background: #333;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 1px 5px;
    font-family: monospace;
    font-size: 10px;
  }
  .frame-info {
    text-align: center;
    color: var(--accent);
    font-size: 13px;
    margin-top: 8px;
    font-family: monospace;
  }
</style>
</head>
<body>
  <h1>__TITLE__ — __ROWS__×__COLS__ Grid Sprite Sheet</h1>
  <p class="subtitle">
    源图 __SIZE_W__×__SIZE_H__ · 单帧 __CELL_W__×__CELL_H__ ·
    共 __FRAME_COUNT__ 帧 · 顺序播放
  </p>

  <div class="layout">
    <div class="stage">
      <canvas id="main" width="__CELL_W__" height="__CELL_H__"></canvas>
    </div>

    <div class="controls">
      <button class="play-btn" id="play">▶ 播放 / 暂停 (空格)</button>

      <h3>播放控制</h3>
      <div class="row">
        <button id="prev">◀ 上一帧</button>
        <button id="next">下一帧 ▶</button>
      </div>
      <div class="row">
        <button id="loop-toggle" class="active">🔁 循环</button>
        <button id="reset">⟲ 重置</button>
      </div>

      <label>FPS <span class="value" id="fps-val">__FPS__</span></label>
      <input type="range" id="fps" min="1" max="30" value="__FPS__" step="1">

      <label>显示倍数 <span class="value" id="zoom-val">1.0x</span></label>
      <input type="range" id="zoom" min="50" max="200" value="100" step="10">

      <h3>当前帧</h3>
      <div class="frame-info" id="frame-info">0 / __MAX_IDX__</div>

      <h3>所有帧（点击跳转）</h3>
      <div class="frame-grid" id="frame-grid"></div>

      <div class="info">
        <kbd>Space</kbd> 播放/暂停 · <kbd>←→</kbd> 上下帧 · <kbd>R</kbd> 重置
      </div>
    </div>
  </div>

<script>
const SRC = '__RAW_URL__';
const ROWS = __ROWS__;
const COLS = __COLS__;
const CELL_W = __CELL_W__;
const CELL_H = __CELL_H__;
const FRAME_COUNT = ROWS * COLS;

const main = document.getElementById('main');
const ctx = main.getContext('2d');
const playBtn = document.getElementById('play');
const frameInfo = document.getElementById('frame-info');
const frameGrid = document.getElementById('frame-grid');

let img = new Image();
let frame = 0;
let playing = false;
let loop = true;
let fps = __FPS__;
let lastTime = 0;
let zoom = 1.0;

img.onload = () => {
  drawFrame(0);
  buildFrameGrid();
  start();
};
img.src = SRC;

function drawFrame(idx) {
  const r = Math.floor(idx / COLS);
  const c = idx % COLS;
  const sx = c * CELL_W;
  const sy = r * CELL_H;
  ctx.clearRect(0, 0, main.width, main.height);
  ctx.drawImage(img, sx, sy, CELL_W, CELL_H, 0, 0, main.width, main.height);
  frame = idx;
  frameInfo.textContent = idx + ' / ' + (FRAME_COUNT - 1) +
    '  (row ' + r + ', col ' + c + ')';
  document.querySelectorAll('.frame-cell').forEach((cell, i) => {
    cell.classList.toggle('active', i === idx);
  });
}

function buildFrameGrid() {
  for (let i = 0; i < FRAME_COUNT; i++) {
    const cell = document.createElement('div');
    cell.className = 'frame-cell';
    cell.dataset.idx = i;
    const cnv = document.createElement('canvas');
    cnv.width = CELL_W;
    cnv.height = CELL_H;
    const cctx = cnv.getContext('2d');
    const r = Math.floor(i / COLS);
    const c = i % COLS;
    cctx.drawImage(img, c * CELL_W, r * CELL_H, CELL_W, CELL_H, 0, 0, CELL_W, CELL_H);
    cell.appendChild(cnv);
    cell.addEventListener('click', () => {
      pause();
      drawFrame(i);
    });
    frameGrid.appendChild(cell);
  }
  document.querySelectorAll('.frame-cell')[0].classList.add('active');
}

function tick(now) {
  if (playing) {
    const elapsed = now - lastTime;
    const interval = 1000 / fps;
    if (elapsed >= interval) {
      let next = frame + 1;
      if (next >= FRAME_COUNT) {
        if (loop) next = 0;
        else { pause(); next = FRAME_COUNT - 1; }
      }
      drawFrame(next);
      lastTime = now;
    }
  }
  requestAnimationFrame(tick);
}

function start() {
  playing = true;
  playBtn.textContent = '⏸ 暂停 (空格)';
  lastTime = performance.now();
  requestAnimationFrame(tick);
}

function pause() {
  playing = false;
  playBtn.textContent = '▶ 播放 (空格)';
}

playBtn.addEventListener('click', () => {
  if (playing) pause(); else start();
});
document.getElementById('prev').addEventListener('click', () => {
  pause();
  drawFrame((frame - 1 + FRAME_COUNT) % FRAME_COUNT);
});
document.getElementById('next').addEventListener('click', () => {
  pause();
  drawFrame((frame + 1) % FRAME_COUNT);
});
document.getElementById('reset').addEventListener('click', () => {
  pause();
  drawFrame(0);
});

const loopBtn = document.getElementById('loop-toggle');
loopBtn.addEventListener('click', () => {
  loop = !loop;
  loopBtn.classList.toggle('active', loop);
  loopBtn.textContent = loop ? '🔁 循环' : '↪ 单次';
});

const fpsRange = document.getElementById('fps');
fpsRange.addEventListener('input', () => {
  fps = parseInt(fpsRange.value);
  document.getElementById('fps-val').textContent = fps;
});

const zoomRange = document.getElementById('zoom');
zoomRange.addEventListener('input', () => {
  zoom = parseInt(zoomRange.value) / 100;
  main.style.width = (CELL_W * zoom) + 'px';
  main.style.height = (CELL_H * zoom) + 'px';
  document.getElementById('zoom-val').textContent = zoom.toFixed(1) + 'x';
});

document.addEventListener('keydown', (e) => {
  if (e.code === 'Space') { e.preventDefault(); playing ? pause() : start(); }
  else if (e.key === 'ArrowLeft') { pause(); drawFrame((frame - 1 + FRAME_COUNT) % FRAME_COUNT); }
  else if (e.key === 'ArrowRight') { pause(); drawFrame((frame + 1) % FRAME_COUNT); }
  else if (e.key === 'r' || e.key === 'R') { pause(); drawFrame(0); }
});
</script>
</body>
</html>
"""


def get_image_size(path):
    try:
        from PIL import Image
        return Image.open(path).size
    except ImportError:
        return (2048, 2048)


def main():
    parser = argparse.ArgumentParser(description="Grid VFX 预览生成器")
    parser.add_argument("path", help="raw PNG 路径")
    parser.add_argument("--grid", default="4x4",
                        help="grid 布局，格式 ROWSxCOLS（默认 4x4）")
    parser.add_argument("--fps", type=int, default=12, help="播放帧率（默认 12）")
    parser.add_argument("--title", help="标题（默认从文件名推断）")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"[错误] 文件不存在: {path}")
        return 1

    try:
        rows, cols = (int(x) for x in args.grid.lower().split("x"))
    except ValueError:
        print(f"[错误] 无效的 grid 格式: {args.grid}（应为 ROWSxCOLS，如 4x4）")
        return 1

    title = args.title or path.stem.replace("_raw", "").replace("_", " ").title()
    size_w, size_h = get_image_size(path)
    cell_w = size_w // cols
    cell_h = size_h // rows
    frame_count = rows * cols

    html = (HTML_TEMPLATE
        .replace("__TITLE__", title)
        .replace("__RAW_URL__", path.name)
        .replace("__SIZE_W__", str(size_w))
        .replace("__SIZE_H__", str(size_h))
        .replace("__ROWS__", str(rows))
        .replace("__COLS__", str(cols))
        .replace("__CELL_W__", str(cell_w))
        .replace("__CELL_H__", str(cell_h))
        .replace("__FRAME_COUNT__", str(frame_count))
        .replace("__MAX_IDX__", str(frame_count - 1))
        .replace("__FPS__", str(args.fps)))

    out_path = path.with_suffix(".grid.html")
    out_path.write_text(html, encoding="utf-8")

    print("=" * 60)
    print("Grid VFX 预览生成完成")
    print("=" * 60)
    print(f"输入: {path}")
    print(f"输出: {out_path}")
    print(f"源图: {size_w}×{size_h}")
    print(f"切分: {rows} 行 × {cols} 列 = {frame_count} 帧")
    print(f"单帧: {cell_w}×{cell_h}")
    print(f"FPS:  {args.fps}（动画时长 {frame_count / args.fps:.2f}s）")
    print()
    print("双击 .grid.html 在浏览器查看")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
