#!/usr/bin/env python
"""
角色 4 方向行走图预览生成器

输入: 3x3 grid（3 方向 × 3 帧），第 4 方向（右）由代码水平翻转左方向得到。

行映射：
  Row 0: 朝下（DOWN）
  Row 1: 朝左（LEFT）
  Row 2: 朝上（UP）
  Right = LEFT 镜像

用法：
    python character_preview.py output/akatsuki_assassin_4dir/akatsuki_4dir_raw.png
"""

import argparse
from pathlib import Path


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>__TITLE__ - 4方向行走图</title>
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
  .directions {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
  }
  .dir-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    text-align: center;
  }
  .dir-name {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 8px;
    color: var(--accent);
  }
  .dir-name .icon { font-size: 18px; margin-right: 4px; }
  .canvas-wrap {
    aspect-ratio: 1;
    background:
      repeating-conic-gradient(#2a2a30 0% 25%, #333 0% 50%) 0 0 / 24px 24px;
    border-radius: 4px;
    overflow: hidden;
    position: relative;
  }
  canvas {
    width: 100%;
    height: 100%;
    image-rendering: pixelated;
  }
  .frame-info {
    margin-top: 6px;
    font-family: monospace;
    font-size: 11px;
    color: #888;
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
  button.active { background: var(--accent); border-color: var(--accent); color: #000; font-weight: 600; }
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
  .strip {
    margin-top: 24px;
    padding: 16px;
    background: var(--panel);
    border-radius: 8px;
    border: 1px solid var(--border);
  }
  .strip h3 { margin-top: 0; }
  .strip img {
    max-width: 100%;
    background:
      repeating-conic-gradient(#2a2a30 0% 25%, #333 0% 50%) 0 0 / 16px 16px;
    border-radius: 4px;
    image-rendering: pixelated;
  }
  .anim-mode {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    margin-bottom: 12px;
  }
</style>
</head>
<body>
  <h1>__TITLE__ — 4 方向行走图</h1>
  <p class="subtitle">
    源图 __SIZE_W__×__SIZE_H__ · 3 方向（DOWN/LEFT/UP）× 3 帧 + RIGHT 镜像 LEFT
  </p>

  <div class="layout">
    <div class="directions" id="dirs"></div>

    <div class="controls">
      <button class="play-btn" id="play">▶ 播放 / 暂停 (空格)</button>

      <h3>动画模式</h3>
      <div class="anim-mode">
        <button data-mode="loop" class="active">1→2→3 循环</button>
        <button data-mode="ping-pong">1→2→3→2 来回</button>
        <button data-mode="standard">1→2→1→3 RPG经典</button>
      </div>

      <h3>FPS</h3>
      <label>速度 <span class="value" id="fps-val">8</span></label>
      <input type="range" id="fps" min="2" max="20" value="8" step="1">

      <label>显示倍数 <span class="value" id="zoom-val">1.0x</span></label>
      <input type="range" id="zoom" min="50" max="300" value="100" step="10">

      <h3>同步</h3>
      <div class="row">
        <button id="sync-toggle" class="active">🔗 同步</button>
        <button id="reset">⟲ 重置</button>
      </div>

      <div class="info">
        <kbd>Space</kbd> 播放/暂停 ·
        <kbd>R</kbd> 重置 ·
        <kbd>1-3</kbd> 切换模式
        <br><br>
        <strong style="color:var(--ok)">RPG 经典模式</strong>：
        1→2→1→3 让 3 帧素材播出 4 帧动画的流畅感（标准 RPG Maker 走路逻辑）。
      </div>
    </div>
  </div>

  <div class="strip">
    <h3>原始 3×3 sprite sheet（绿幕已抠透明）</h3>
    <img src="__RAW_URL__" alt="sprite sheet">
  </div>

<script>
const SRC = '__RAW_URL__';
const ROWS = __ROWS__;
const COLS = __COLS__;
const CELL_W = __CELL_W__;
const CELL_H = __CELL_H__;

// 方向配置：name, icon, sprite-row, mirrorX
const DIRS = [
  { name: 'DOWN',  icon: '⬇', row: 0, mirror: false },
  { name: 'LEFT',  icon: '⬅', row: 1, mirror: false },
  { name: 'RIGHT', icon: '➡', row: 1, mirror: true  },
  { name: 'UP',    icon: '⬆', row: 2, mirror: false },
];

// 动画模式（帧序列）按 cols 数动态生成
const COLS_NUM = COLS;
function buildModes(n) {
  if (n === 3) {
    return {
      'loop':      [0, 1, 2],
      'ping-pong': [0, 1, 2, 1],
      'standard':  [0, 1, 0, 2],
    };
  }
  if (n === 4) {
    return {
      'loop':      [0, 1, 2, 3],
      'ping-pong': [0, 1, 2, 3, 2, 1],
      'standard':  [0, 1, 0, 2, 0, 3, 0, 2],
    };
  }
  // 通用：直接 0..n-1 顺播
  const seq = [];
  for (let i = 0; i < n; i++) seq.push(i);
  return {
    'loop':      seq.slice(),
    'ping-pong': seq.concat(seq.slice(1, -1).reverse()),
    'standard':  seq.slice(),
  };
}
const MODES = buildModes(COLS_NUM);

const dirsEl = document.getElementById('dirs');
const playBtn = document.getElementById('play');

let img = new Image();
let playing = true;
let fps = 8;
let zoom = 1.0;
let mode = 'loop';
let sync = true;
let frameStartTime = 0;

// 每个方向的状态
const dirStates = DIRS.map(() => ({
  seqIdx: 0,
  canvas: null,
  ctx: null,
  info: null,
}));

img.onload = () => {
  buildCards();
  start();
};
img.src = SRC;

function buildCards() {
  DIRS.forEach((d, i) => {
    const card = document.createElement('div');
    card.className = 'dir-card';
    card.innerHTML =
      '<div class="dir-name"><span class="icon">' + d.icon + '</span>' + d.name + '</div>' +
      '<div class="canvas-wrap"><canvas width="' + CELL_W + '" height="' + CELL_H + '"></canvas></div>' +
      '<div class="frame-info">frame 0</div>';
    dirsEl.appendChild(card);
    const cnv = card.querySelector('canvas');
    dirStates[i].canvas = cnv;
    dirStates[i].ctx = cnv.getContext('2d');
    dirStates[i].info = card.querySelector('.frame-info');
    drawFrameForDir(i, 0);
  });
}

function drawFrameForDir(dirIdx, seqIdx) {
  const d = DIRS[dirIdx];
  const seq = MODES[mode];
  const frameInRow = seq[seqIdx % seq.length];
  const sx = frameInRow * CELL_W;
  const sy = d.row * CELL_H;

  const ctx = dirStates[dirIdx].ctx;
  const cnv = dirStates[dirIdx].canvas;
  ctx.clearRect(0, 0, cnv.width, cnv.height);

  ctx.save();
  if (d.mirror) {
    ctx.translate(cnv.width, 0);
    ctx.scale(-1, 1);
  }
  ctx.drawImage(img, sx, sy, CELL_W, CELL_H, 0, 0, cnv.width, cnv.height);
  ctx.restore();

  dirStates[dirIdx].info.textContent =
    'frame ' + frameInRow + ' (seq ' + seqIdx + ')' +
    (d.mirror ? ' [mirror]' : '');
}

function tick(now) {
  if (!playing) return;
  const interval = 1000 / fps;
  if (now - frameStartTime >= interval) {
    DIRS.forEach((d, i) => {
      if (sync) {
        dirStates[i].seqIdx = (dirStates[0].seqIdx + 1) % MODES[mode].length;
      } else {
        dirStates[i].seqIdx = (dirStates[i].seqIdx + 1) % MODES[mode].length;
      }
    });
    if (sync) {
      const newIdx = (dirStates[0].seqIdx) % MODES[mode].length;
      DIRS.forEach((d, i) => {
        dirStates[i].seqIdx = newIdx;
        drawFrameForDir(i, newIdx);
      });
    } else {
      DIRS.forEach((d, i) => drawFrameForDir(i, dirStates[i].seqIdx));
    }
    frameStartTime = now;
  }
  requestAnimationFrame(tick);
}

function start() {
  playing = true;
  playBtn.textContent = '⏸ 暂停 (空格)';
  frameStartTime = performance.now();
  requestAnimationFrame(tick);
}

function pause() {
  playing = false;
  playBtn.textContent = '▶ 播放 (空格)';
}

function reset() {
  DIRS.forEach((d, i) => {
    dirStates[i].seqIdx = 0;
    drawFrameForDir(i, 0);
  });
}

playBtn.addEventListener('click', () => playing ? pause() : start());
document.getElementById('reset').addEventListener('click', () => { pause(); reset(); start(); });

document.querySelectorAll('[data-mode]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-mode]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    mode = btn.dataset.mode;
    reset();
  });
});

const syncBtn = document.getElementById('sync-toggle');
syncBtn.addEventListener('click', () => {
  sync = !sync;
  syncBtn.classList.toggle('active', sync);
  syncBtn.textContent = sync ? '🔗 同步' : '✂ 异步';
});

const fpsRange = document.getElementById('fps');
fpsRange.addEventListener('input', () => {
  fps = parseInt(fpsRange.value);
  document.getElementById('fps-val').textContent = fps;
});

const zoomRange = document.getElementById('zoom');
zoomRange.addEventListener('input', () => {
  zoom = parseInt(zoomRange.value) / 100;
  document.querySelectorAll('.dir-card .canvas-wrap').forEach(w => {
    w.style.maxWidth = (CELL_W * zoom) + 'px';
    w.style.margin = '0 auto';
  });
  document.getElementById('zoom-val').textContent = zoom.toFixed(1) + 'x';
});

document.addEventListener('keydown', (e) => {
  if (e.code === 'Space') { e.preventDefault(); playing ? pause() : start(); }
  else if (e.key === 'r' || e.key === 'R') { pause(); reset(); start(); }
  else if (e.key >= '1' && e.key <= '3') {
    const map = ['loop', 'ping-pong', 'standard'];
    const target = document.querySelector('[data-mode="' + map[parseInt(e.key) - 1] + '"]');
    if (target) target.click();
  }
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
    parser = argparse.ArgumentParser(description="角色 4 方向行走图预览")
    parser.add_argument("path", help="sprite sheet PNG")
    parser.add_argument("--grid", default="3x3",
                        help="grid 布局 ROWSxCOLS（默认 3x3，进阶 3x4）")
    parser.add_argument("--title", help="标题")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"[错误] 文件不存在: {path}")
        return 1

    try:
        rows, cols = (int(x) for x in args.grid.lower().split("x"))
    except ValueError:
        print(f"[错误] 无效 grid: {args.grid}")
        return 1

    if rows != 3:
        print(f"[警告] 当前预览只支持 3 行（DOWN/LEFT/UP）。rows={rows} 可能显示异常。")

    title = args.title or path.stem.replace("_raw", "").replace("_", " ").title()
    size_w, size_h = get_image_size(path)
    cell_w = size_w // cols
    cell_h = size_h // rows

    html = (HTML_TEMPLATE
        .replace("__TITLE__", title)
        .replace("__RAW_URL__", path.name)
        .replace("__SIZE_W__", str(size_w))
        .replace("__SIZE_H__", str(size_h))
        .replace("__ROWS__", str(rows))
        .replace("__COLS__", str(cols))
        .replace("__CELL_W__", str(cell_w))
        .replace("__CELL_H__", str(cell_h)))

    out_path = path.with_suffix(".character.html")
    out_path.write_text(html, encoding="utf-8")

    print("=" * 60)
    print(f"4 方向行走图预览生成完成（{rows}×{cols} = {rows * cols} cells）")
    print("=" * 60)
    print(f"输入: {path}")
    print(f"输出: {out_path}")
    print(f"单帧: {cell_w}×{cell_h}")
    print(f"每方向帧数: {cols}")
    print()
    print("方向映射:")
    print("  Row 0 → DOWN   (面朝下)")
    print("  Row 1 → LEFT   (面朝左)")
    print("  Row 1 → RIGHT  (镜像 LEFT)")
    print("  Row 2 → UP     (面朝上)")
    print()
    print("双击 .character.html 在浏览器查看")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
