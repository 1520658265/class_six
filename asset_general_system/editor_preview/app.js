"use strict";

const TILE_DEFS = {
  0: { name: "empty", color: [0, 0, 0] },
  1: { name: "grass", color: [88, 166, 83] },
  2: { name: "autumn_grass", color: [155, 147, 74] },
  3: { name: "dirt", color: [148, 104, 58] },
  4: { name: "forest_floor", color: [87, 122, 62] },
  5: { name: "water", color: [55, 129, 184] },
  6: { name: "snow", color: [218, 233, 238] },
  7: { name: "sand", color: [214, 185, 111] },
  8: { name: "stone_floor", color: [119, 119, 122] },
  9: { name: "wall", color: [70, 67, 73] },
  10: { name: "dirt_road", color: [185, 139, 80] },
  11: { name: "bridge", color: [139, 91, 53] },
  12: { name: "house", color: [136, 84, 62] },
  13: { name: "temple", color: [169, 160, 129] },
  14: { name: "market_stall", color: [192, 76, 73] },
  15: { name: "tree", color: [39, 102, 54] },
  16: { name: "pine", color: [38, 94, 84] },
  17: { name: "rock", color: [103, 104, 101] },
  18: { name: "campfire", color: [232, 111, 42] },
  19: { name: "chest", color: [178, 120, 39] },
  20: { name: "door", color: [101, 58, 37] },
  21: { name: "ruin_wall", color: [143, 126, 91] },
  22: { name: "dock", color: [121, 83, 52] },
  23: { name: "lighthouse", color: [205, 208, 198] },
  24: { name: "mountain", color: [85, 94, 88] },
  25: { name: "school", color: [188, 176, 137] },
  26: { name: "playground", color: [181, 91, 63] },
  27: { name: "toilet", color: [178, 184, 174] },
};

const STANDARD_LAYER_ORDER = ["terrain", "path", "building", "decoration", "collision"];
const state = {
  mapData: null,
  fileName: "",
  layerOrder: [],
  layerVisibility: {},
  overlays: {
    objects: true,
    events: true,
    regions: true,
  },
  selection: null,
  lockedRegions: [],
  zoom: 0.5,
  history: [],
  redo: [],
  drag: null,
};

const els = {
  fileInput: document.getElementById("fileInput"),
  stateInput: document.getElementById("stateInput"),
  exportStateButton: document.getElementById("exportStateButton"),
  mapSummary: document.getElementById("mapSummary"),
  layerControls: document.getElementById("layerControls"),
  objectsToggle: document.getElementById("objectsToggle"),
  eventsToggle: document.getElementById("eventsToggle"),
  regionsToggle: document.getElementById("regionsToggle"),
  selectionInfo: document.getElementById("selectionInfo"),
  lockButton: document.getElementById("lockButton"),
  clearButton: document.getElementById("clearButton"),
  undoButton: document.getElementById("undoButton"),
  redoButton: document.getElementById("redoButton"),
  lockedList: document.getElementById("lockedList"),
  zoomSelect: document.getElementById("zoomSelect"),
  statusText: document.getElementById("statusText"),
  canvas: document.getElementById("mapCanvas"),
  mapInfo: document.getElementById("mapInfo"),
  regionList: document.getElementById("regionList"),
};

const ctx = els.canvas.getContext("2d");

els.fileInput.addEventListener("change", handleFileChange);
els.stateInput.addEventListener("change", handleStateFileChange);
els.exportStateButton.addEventListener("click", exportEditorState);
els.objectsToggle.addEventListener("change", () => setOverlay("objects", els.objectsToggle.checked));
els.eventsToggle.addEventListener("change", () => setOverlay("events", els.eventsToggle.checked));
els.regionsToggle.addEventListener("change", () => setOverlay("regions", els.regionsToggle.checked));
els.lockButton.addEventListener("click", lockSelection);
els.clearButton.addEventListener("click", clearSelection);
els.undoButton.addEventListener("click", undo);
els.redoButton.addEventListener("click", redo);
els.zoomSelect.addEventListener("change", () => {
  state.zoom = Number(els.zoomSelect.value);
  render();
});
els.canvas.addEventListener("pointerdown", handlePointerDown);
els.canvas.addEventListener("pointermove", handlePointerMove);
els.canvas.addEventListener("pointerup", handlePointerUp);
els.canvas.addEventListener("pointercancel", cancelDrag);

render();

function handleFileChange(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) {
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    try {
      const data = JSON.parse(String(reader.result));
      validateMapData(data);
      loadMapData(data, file.name);
    } catch (error) {
      setStatus(error.message, true);
    }
  };
  reader.onerror = () => setStatus("Could not read file.", true);
  reader.readAsText(file, "utf-8");
}

function handleStateFileChange(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) {
    return;
  }
  if (!state.mapData) {
    setStatus("Open a map_data.json before loading editor state.", true);
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    try {
      const data = JSON.parse(String(reader.result));
      applyEditorStateDocument(data);
      setStatus(`Loaded ${file.name}.`, false);
      render();
    } catch (error) {
      setStatus(error.message, true);
    }
  };
  reader.onerror = () => setStatus("Could not read editor state file.", true);
  reader.readAsText(file, "utf-8");
}

function validateMapData(data) {
  if (!data || typeof data !== "object") {
    throw new Error("Invalid map data.");
  }
  if (!data.map || !Number.isInteger(data.map.width) || !Number.isInteger(data.map.height)) {
    throw new Error("Missing map dimensions.");
  }
  if (!data.layers || typeof data.layers !== "object") {
    throw new Error("Missing layers.");
  }

  const expectedLength = data.map.width * data.map.height;
  for (const [name, layer] of Object.entries(data.layers)) {
    if (!Array.isArray(layer)) {
      throw new Error(`Layer ${name} is not an array.`);
    }
    if (layer.length !== expectedLength) {
      throw new Error(`Layer ${name} length is ${layer.length}; expected ${expectedLength}.`);
    }
  }
}

function loadMapData(data, fileName) {
  state.mapData = data;
  state.fileName = fileName;
  state.layerOrder = getLayerOrder(data.layers);
  state.layerVisibility = Object.fromEntries(
    state.layerOrder.map((name) => [name, name !== "collision"]),
  );
  state.selection = null;
  state.lockedRegions = [];
  state.history = [];
  state.redo = [];
  state.drag = null;
  setStatus(`Loaded ${fileName}.`, false);
  render();
}

function applyEditorStateDocument(data) {
  if (!data || typeof data !== "object") {
    throw new Error("Invalid editor state.");
  }
  if (!data.map || data.map.width !== state.mapData.map.width || data.map.height !== state.mapData.map.height) {
    throw new Error("Editor state map size does not match the loaded map.");
  }

  const visibility = data.layer_visibility || {};
  for (const layerName of Object.keys(visibility)) {
    if (!state.layerOrder.includes(layerName)) {
      throw new Error(`Editor state references unknown layer: ${layerName}`);
    }
  }
  state.layerVisibility = {
    ...state.layerVisibility,
    ...Object.fromEntries(Object.entries(visibility).map(([key, value]) => [key, Boolean(value)])),
  };
  state.selection = data.selection ? clampRect(data.selection) : null;
  state.lockedRegions = (data.locked_regions || []).map((region) => {
    const rect = clampRect(region);
    return {
      id: String(region.id || nextLockId()),
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
      layers: Array.isArray(region.layers) ? region.layers : null,
      reason: String(region.reason || "user_locked"),
    };
  });
  state.history = [];
  state.redo = [];
}

function getLayerOrder(layers) {
  const names = Object.keys(layers);
  const ordered = STANDARD_LAYER_ORDER.filter((name) => names.includes(name));
  const extra = names.filter((name) => !ordered.includes(name)).sort();
  return [...ordered, ...extra];
}

function render() {
  updateControls();
  renderSidebars();
  renderCanvas();
}

function renderCanvas() {
  if (!state.mapData) {
    els.canvas.width = 960;
    els.canvas.height = 640;
    ctx.fillStyle = "#182018";
    ctx.fillRect(0, 0, els.canvas.width, els.canvas.height);
    ctx.fillStyle = "#dbe3d7";
    ctx.font = "16px system-ui, sans-serif";
    ctx.fillText("Open a map_data.json file", 32, 42);
    return;
  }

  const map = state.mapData.map;
  const tileSize = scaledTileSize();
  els.canvas.width = map.width * tileSize;
  els.canvas.height = map.height * tileSize;
  ctx.clearRect(0, 0, els.canvas.width, els.canvas.height);

  for (const layerName of state.layerOrder) {
    if (!state.layerVisibility[layerName]) {
      continue;
    }
    drawLayer(layerName, state.mapData.layers[layerName], tileSize);
  }

  if (state.overlays.regions) {
    drawRegions(tileSize);
  }
  if (state.overlays.objects) {
    drawObjects(tileSize);
  }
  if (state.overlays.events) {
    drawEvents(tileSize);
  }

  drawLockedRegions(tileSize);
  drawSelection(tileSize);
  drawGrid(tileSize);
}

function drawLayer(layerName, layer, tileSize) {
  const map = state.mapData.map;
  if (layerName === "collision") {
    drawCollisionLayer(layer, tileSize);
    return;
  }

  for (let y = 0; y < map.height; y += 1) {
    for (let x = 0; x < map.width; x += 1) {
      const tileId = layer[y * map.width + x];
      if (!tileId) {
        continue;
      }
      const tile = TILE_DEFS[tileId] || { color: [220, 40, 180] };
      ctx.fillStyle = rgb(tile.color);
      ctx.fillRect(x * tileSize, y * tileSize, tileSize, tileSize);
      if (layerName === "building" || layerName === "decoration") {
        ctx.strokeStyle = "rgba(22, 25, 22, 0.42)";
        ctx.lineWidth = 1;
        ctx.strokeRect(x * tileSize + 0.5, y * tileSize + 0.5, tileSize - 1, tileSize - 1);
      }
    }
  }
}

function drawCollisionLayer(layer, tileSize) {
  const map = state.mapData.map;
  for (let y = 0; y < map.height; y += 1) {
    for (let x = 0; x < map.width; x += 1) {
      if (!layer[y * map.width + x]) {
        continue;
      }
      ctx.fillStyle = "rgba(182, 60, 52, 0.34)";
      ctx.fillRect(x * tileSize, y * tileSize, tileSize, tileSize);
    }
  }
}

function drawRegions(tileSize) {
  ctx.save();
  ctx.lineWidth = Math.max(1, Math.floor(tileSize / 10));
  ctx.strokeStyle = "rgba(255, 255, 255, 0.86)";
  ctx.fillStyle = "rgba(255, 255, 255, 0.1)";
  for (const region of state.mapData.regions || []) {
    const [x, y, width, height] = region.bounds;
    ctx.fillRect(x * tileSize, y * tileSize, width * tileSize, height * tileSize);
    ctx.strokeRect(x * tileSize, y * tileSize, width * tileSize, height * tileSize);
    if (tileSize >= 12) {
      ctx.fillStyle = "rgba(12, 18, 14, 0.82)";
      ctx.font = `${Math.max(10, Math.floor(tileSize * 0.42))}px system-ui, sans-serif`;
      ctx.fillText(region.type || region.id, x * tileSize + 4, y * tileSize + Math.max(12, tileSize - 4));
      ctx.fillStyle = "rgba(255, 255, 255, 0.1)";
    }
  }
  ctx.restore();
}

function drawObjects(tileSize) {
  for (const object of state.mapData.objects || []) {
    const cx = (object.x + object.width / 2) * tileSize;
    const cy = (object.y + object.height / 2) * tileSize;
    const radius = Math.max(3, tileSize * 0.22);
    ctx.fillStyle = object.type === "door" ? "rgba(70, 38, 24, 0.95)" : "rgba(242, 201, 76, 0.92)";
    ctx.strokeStyle = "rgba(20, 23, 20, 0.7)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
}

function drawEvents(tileSize) {
  for (const event of state.mapData.events || []) {
    const x = event.x * tileSize;
    const y = event.y * tileSize;
    const inset = Math.max(3, tileSize * 0.22);
    ctx.fillStyle = event.type === "player_spawn" ? "rgba(39, 105, 90, 0.95)" : "rgba(45, 108, 223, 0.86)";
    ctx.beginPath();
    ctx.moveTo(x + tileSize / 2, y + inset);
    ctx.lineTo(x + tileSize - inset, y + tileSize - inset);
    ctx.lineTo(x + inset, y + tileSize - inset);
    ctx.closePath();
    ctx.fill();
  }
}

function drawLockedRegions(tileSize) {
  ctx.save();
  ctx.lineWidth = Math.max(2, Math.floor(tileSize / 8));
  for (const region of state.lockedRegions) {
    ctx.fillStyle = "rgba(45, 108, 223, 0.18)";
    ctx.strokeStyle = "rgba(45, 108, 223, 0.92)";
    ctx.fillRect(region.x * tileSize, region.y * tileSize, region.width * tileSize, region.height * tileSize);
    ctx.strokeRect(region.x * tileSize, region.y * tileSize, region.width * tileSize, region.height * tileSize);
  }
  ctx.restore();
}

function drawSelection(tileSize) {
  if (!state.selection) {
    return;
  }
  const { x, y, width, height } = state.selection;
  ctx.save();
  ctx.lineWidth = Math.max(2, Math.floor(tileSize / 7));
  ctx.strokeStyle = "rgba(242, 201, 76, 0.98)";
  ctx.fillStyle = "rgba(242, 201, 76, 0.14)";
  ctx.fillRect(x * tileSize, y * tileSize, width * tileSize, height * tileSize);
  ctx.strokeRect(x * tileSize, y * tileSize, width * tileSize, height * tileSize);
  ctx.restore();
}

function drawGrid(tileSize) {
  if (tileSize < 12) {
    return;
  }
  const map = state.mapData.map;
  ctx.save();
  ctx.strokeStyle = "rgba(0, 0, 0, 0.1)";
  ctx.lineWidth = 1;
  for (let x = 0; x <= map.width; x += 1) {
    ctx.beginPath();
    ctx.moveTo(x * tileSize + 0.5, 0);
    ctx.lineTo(x * tileSize + 0.5, map.height * tileSize);
    ctx.stroke();
  }
  for (let y = 0; y <= map.height; y += 1) {
    ctx.beginPath();
    ctx.moveTo(0, y * tileSize + 0.5);
    ctx.lineTo(map.width * tileSize, y * tileSize + 0.5);
    ctx.stroke();
  }
  ctx.restore();
}

function updateControls() {
  const hasMap = Boolean(state.mapData);
  els.exportStateButton.disabled = !hasMap;
  els.lockButton.disabled = !state.selection;
  els.clearButton.disabled = !state.selection;
  els.undoButton.disabled = state.history.length === 0;
  els.redoButton.disabled = state.redo.length === 0;
}

function renderSidebars() {
  renderLayerControls();
  renderSelectionInfo();
  renderLockedList();
  renderMapInfo();
  renderRegionList();
}

function renderLayerControls() {
  if (!state.mapData) {
    els.layerControls.innerHTML = '<div class="emptyNote">No layers</div>';
    return;
  }

  els.layerControls.innerHTML = "";
  for (const layerName of state.layerOrder) {
    const label = document.createElement("label");
    label.className = "checkRow";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(state.layerVisibility[layerName]);
    checkbox.addEventListener("change", () => {
      record(`layer:${layerName}`, () => {
        state.layerVisibility[layerName] = checkbox.checked;
      });
      render();
    });

    const swatch = document.createElement("span");
    swatch.className = "layerSwatch";
    swatch.style.background = layerSwatch(layerName);

    const text = document.createElement("span");
    text.textContent = layerName;
    label.append(checkbox, swatch, text);
    els.layerControls.append(label);
  }
}

function renderSelectionInfo() {
  const bounds = state.selection
    ? `${state.selection.x}, ${state.selection.y}, ${state.selection.width}x${state.selection.height}`
    : "None";
  els.selectionInfo.innerHTML = `<dt>Bounds</dt><dd>${escapeHtml(bounds)}</dd>`;
}

function renderLockedList() {
  if (!state.lockedRegions.length) {
    els.lockedList.innerHTML = '<div class="emptyNote">No locked regions</div>';
    return;
  }
  els.lockedList.innerHTML = "";
  for (const region of state.lockedRegions) {
    const row = document.createElement("div");
    row.className = "lockRow";
    const meta = document.createElement("div");
    meta.className = "lockMeta";
    meta.innerHTML = `<strong>${escapeHtml(region.id)}</strong>${region.x}, ${region.y}, ${region.width}x${region.height}`;
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Remove";
    button.addEventListener("click", () => {
      record("unlock", () => {
        state.lockedRegions = state.lockedRegions.filter((item) => item.id !== region.id);
      });
      render();
    });
    row.append(meta, button);
    els.lockedList.append(row);
  }
}

function renderMapInfo() {
  if (!state.mapData) {
    els.mapSummary.textContent = "No map loaded";
    els.mapInfo.innerHTML = [
      ["Size", "-"],
      ["Tile", "-"],
      ["Layers", "-"],
      ["Regions", "-"],
      ["Objects", "-"],
      ["Events", "-"],
    ].map(([key, value]) => `<dt>${key}</dt><dd>${value}</dd>`).join("");
    return;
  }

  const map = state.mapData.map;
  const objects = state.mapData.objects || [];
  const events = state.mapData.events || [];
  const regions = state.mapData.regions || [];
  els.mapSummary.textContent = `${state.fileName} - ${map.width}x${map.height}`;
  els.mapInfo.innerHTML = [
    ["Size", `${map.width} x ${map.height}`],
    ["Tile", `${map.tile_width} x ${map.tile_height}`],
    ["Layers", String(state.layerOrder.length)],
    ["Regions", String(regions.length)],
    ["Objects", String(objects.length)],
    ["Events", String(events.length)],
  ].map(([key, value]) => `<dt>${key}</dt><dd>${escapeHtml(value)}</dd>`).join("");
}

function renderRegionList() {
  if (!state.mapData || !(state.mapData.regions || []).length) {
    els.regionList.innerHTML = '<div class="emptyNote">No regions</div>';
    return;
  }
  els.regionList.innerHTML = "";
  for (const region of state.mapData.regions) {
    const item = document.createElement("div");
    item.className = "listItem";
    item.innerHTML = `<strong>${escapeHtml(region.id)}</strong>${escapeHtml(region.type)} - ${region.bounds.join(", ")}`;
    els.regionList.append(item);
  }
}

function setOverlay(name, visible) {
  state.overlays[name] = visible;
  render();
}

function lockSelection() {
  if (!state.selection) {
    return;
  }
  record("lock", () => {
    state.lockedRegions.push({
      id: nextLockId(),
      x: state.selection.x,
      y: state.selection.y,
      width: state.selection.width,
      height: state.selection.height,
      layers: null,
      reason: "user_locked",
    });
  });
  render();
}

function clearSelection() {
  if (!state.selection) {
    return;
  }
  record("clear_selection", () => {
    state.selection = null;
  });
  render();
}

function handlePointerDown(event) {
  if (!state.mapData) {
    return;
  }
  const tile = eventToTile(event);
  if (!tile) {
    return;
  }
  state.drag = {
    anchor: tile,
    before: snapshot(),
  };
  state.selection = rectFromTiles(tile, tile);
  els.canvas.setPointerCapture(event.pointerId);
  render();
}

function handlePointerMove(event) {
  if (!state.drag) {
    return;
  }
  const tile = eventToTile(event);
  if (!tile) {
    return;
  }
  state.selection = rectFromTiles(state.drag.anchor, tile);
  render();
}

function handlePointerUp(event) {
  if (!state.drag) {
    return;
  }
  const before = state.drag.before;
  state.drag = null;
  if (els.canvas.hasPointerCapture(event.pointerId)) {
    els.canvas.releasePointerCapture(event.pointerId);
  }
  pushHistory("select", before, snapshot());
  render();
}

function cancelDrag(event) {
  if (!state.drag) {
    return;
  }
  state.selection = state.drag.before.selection;
  state.drag = null;
  if (els.canvas.hasPointerCapture(event.pointerId)) {
    els.canvas.releasePointerCapture(event.pointerId);
  }
  render();
}

function eventToTile(event) {
  const map = state.mapData.map;
  const rect = els.canvas.getBoundingClientRect();
  const px = (event.clientX - rect.left) * (els.canvas.width / rect.width);
  const py = (event.clientY - rect.top) * (els.canvas.height / rect.height);
  const tileSize = scaledTileSize();
  const x = clamp(Math.floor(px / tileSize), 0, map.width - 1);
  const y = clamp(Math.floor(py / tileSize), 0, map.height - 1);
  return { x, y };
}

function rectFromTiles(a, b) {
  const x = Math.min(a.x, b.x);
  const y = Math.min(a.y, b.y);
  const right = Math.max(a.x, b.x);
  const bottom = Math.max(a.y, b.y);
  return {
    x,
    y,
    width: right - x + 1,
    height: bottom - y + 1,
  };
}

function clampRect(rect) {
  const map = state.mapData.map;
  const x = clamp(Number(rect.x), 0, map.width - 1);
  const y = clamp(Number(rect.y), 0, map.height - 1);
  const width = clamp(Number(rect.width), 1, map.width - x);
  const height = clamp(Number(rect.height), 1, map.height - y);
  return { x, y, width, height };
}

function exportEditorState() {
  if (!state.mapData) {
    return;
  }
  const payload = {
    version: "0.1.0",
    source_file: state.fileName,
    map: {
      width: state.mapData.map.width,
      height: state.mapData.map.height,
      tile_width: state.mapData.map.tile_width,
      tile_height: state.mapData.map.tile_height,
    },
    layer_visibility: state.layerVisibility,
    selection: state.selection,
    locked_regions: state.lockedRegions,
    metadata: {
      exported_by: "editor_preview",
    },
  };
  const blob = new Blob([JSON.stringify(payload, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${baseName(state.fileName) || "tilemap"}_editor_state.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function record(action, mutator) {
  const before = snapshot();
  mutator();
  const after = snapshot();
  pushHistory(action, before, after);
}

function pushHistory(action, before, after) {
  if (JSON.stringify(before) === JSON.stringify(after)) {
    return;
  }
  state.history.push({ action, before, after });
  if (state.history.length > 50) {
    state.history.shift();
  }
  state.redo = [];
}

function undo() {
  const entry = state.history.pop();
  if (!entry) {
    return;
  }
  state.redo.push(entry);
  applySnapshot(entry.before);
  render();
}

function redo() {
  const entry = state.redo.pop();
  if (!entry) {
    return;
  }
  state.history.push(entry);
  applySnapshot(entry.after);
  render();
}

function snapshot() {
  return {
    layerVisibility: structuredClone(state.layerVisibility),
    selection: state.selection ? { ...state.selection } : null,
    lockedRegions: structuredClone(state.lockedRegions),
  };
}

function applySnapshot(snap) {
  state.layerVisibility = structuredClone(snap.layerVisibility);
  state.selection = snap.selection ? { ...snap.selection } : null;
  state.lockedRegions = structuredClone(snap.lockedRegions);
}

function scaledTileSize() {
  const tileWidth = state.mapData ? state.mapData.map.tile_width || 32 : 32;
  return Math.max(4, Math.round(tileWidth * state.zoom));
}

function nextLockId() {
  const used = new Set(state.lockedRegions.map((region) => region.id));
  let index = state.lockedRegions.length + 1;
  let id = `locked_${String(index).padStart(3, "0")}`;
  while (used.has(id)) {
    index += 1;
    id = `locked_${String(index).padStart(3, "0")}`;
  }
  return id;
}

function layerSwatch(layerName) {
  if (layerName === "terrain") {
    return "#58a653";
  }
  if (layerName === "path") {
    return "#b98b50";
  }
  if (layerName === "building") {
    return "#886054";
  }
  if (layerName === "decoration") {
    return "#27695a";
  }
  if (layerName === "collision") {
    return "#b63c34";
  }
  return "#8d97a0";
}

function setStatus(message, isError) {
  els.statusText.textContent = message;
  els.statusText.style.color = isError ? "var(--danger)" : "var(--muted)";
}

function rgb(color) {
  return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function baseName(name) {
  return String(name || "").replace(/\.[^.]+$/, "");
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
