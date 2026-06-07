"""
Unity Tilemap 导出器。

把 TilemapData 导出为 Unity 可读的 JSON 格式 + 导入脚本指引。
Unity 没有像 Tiled 这样标准化的 JSON，但可以借助第三方工具
(SuperTiled2Unity) 或自定义导入脚本读取我们的 JSON 格式。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import TilemapData


class UnityExporter:
    """
    Unity Tilemap 导出器。

    输出文件：
    - map.unity.json: Unity 友好的扁平 JSON
    - import_tilemap.cs: C# 导入脚本（参考实现）
    - README.md: 导入说明
    """

    def export(
        self,
        tilemap: TilemapData,
        output_dir: Path,
    ) -> dict[str, Any]:
        """
        导出 Unity 项目结构。

        Args:
            tilemap: 地图数据
            output_dir: 输出目录

        Returns:
            导出报告
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        files = []

        # 1. 主数据 JSON
        data_path = output_dir / "map.unity.json"
        self._export_data(tilemap, data_path)
        files.append("map.unity.json")

        # 2. 导入脚本
        script_path = output_dir / "ImportTilemap.cs"
        self._write_import_script(script_path)
        files.append("ImportTilemap.cs")

        # 3. README
        readme_path = output_dir / "README.md"
        self._write_readme(readme_path)
        files.append("README.md")

        return {
            "engine": "unity",
            "output_dir": str(output_dir),
            "files": files,
            "layers": list(tilemap.layers.keys()),
            "object_count": len(tilemap.objects),
            "event_count": len(tilemap.events),
        }

    def _export_data(self, tilemap: TilemapData, path: Path) -> None:
        """导出 Unity 友好的扁平 JSON。"""
        data: dict[str, Any] = {
            "format_version": "1.0",
            "engine": "unity",
            "map": {
                "width": tilemap.map.width,
                "height": tilemap.map.height,
                "tileWidth": tilemap.map.tile_width,
                "tileHeight": tilemap.map.tile_height,
                "orientation": tilemap.map.orientation,
            },
            "tileset": {
                "id": tilemap.tileset.id,
                "image": tilemap.tileset.image,
                "tileWidth": tilemap.tileset.tile_width,
                "tileHeight": tilemap.tileset.tile_height,
                "columns": tilemap.tileset.columns,
                "tileCount": tilemap.tileset.tile_count,
            },
            "tileLayers": [
                {
                    "name": name,
                    "data": data_array,
                    "visible": name != "collision",
                }
                for name, data_array in tilemap.layers.items()
            ],
            "objects": [
                {
                    "id": obj.id,
                    "type": obj.type,
                    "x": obj.x,
                    "y": obj.y,
                    "width": obj.width,
                    "height": obj.height,
                    "properties": obj.properties,
                    "spriteRef": obj.sprite_ref,
                    "spritePath": obj.sprite_path,
                }
                for obj in tilemap.objects
            ],
            "events": [
                {
                    "id": ev.id,
                    "type": ev.type,
                    "x": ev.x,
                    "y": ev.y,
                    "properties": ev.properties,
                }
                for ev in tilemap.events
            ],
            "regions": [
                {
                    "id": r.id,
                    "type": r.type,
                    "bounds": r.bounds,
                    "center": r.center,
                    "access": r.access,
                    "priority": r.priority,
                }
                for r in tilemap.regions
            ],
        }

        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_import_script(self, path: Path) -> None:
        """写入 Unity 导入脚本（C#）。"""
        content = """using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Tilemaps;

[Serializable]
public class MapInfo {
    public int width;
    public int height;
    public int tileWidth;
    public int tileHeight;
}

[Serializable]
public class TileLayer {
    public string name;
    public int[] data;
    public bool visible;
}

[Serializable]
public class MapObject {
    public string id;
    public string type;
    public int x;
    public int y;
    public int width;
    public int height;
    public string spriteRef;
    public string spritePath;
}

[Serializable]
public class TilemapData {
    public string format_version;
    public MapInfo map;
    public TileLayer[] tileLayers;
    public MapObject[] objects;
}

public class ImportTilemap : MonoBehaviour {
    public TextAsset jsonFile;
    public Tile[] tilePalette; // index = tile_id - 1
    public Grid targetGrid;

    void Start() {
        if (jsonFile == null) return;
        var data = JsonUtility.FromJson<TilemapData>(jsonFile.text);
        BuildTilemap(data);
    }

    void BuildTilemap(TilemapData data) {
        foreach (var layer in data.tileLayers) {
            var go = new GameObject(layer.name);
            go.transform.SetParent(targetGrid.transform);
            var tilemap = go.AddComponent<Tilemap>();
            go.AddComponent<TilemapRenderer>();

            for (int y = 0; y < data.map.height; y++) {
                for (int x = 0; x < data.map.width; x++) {
                    int idx = y * data.map.width + x;
                    int tileId = layer.data[idx];
                    if (tileId <= 0 || tileId > tilePalette.Length) continue;
                    tilemap.SetTile(new Vector3Int(x, -y, 0), tilePalette[tileId - 1]);
                }
            }

            if (!layer.visible) {
                go.GetComponent<TilemapRenderer>().enabled = false;
            }
        }
    }
}
"""
        path.write_text(content, encoding="utf-8")

    def _write_readme(self, path: Path) -> None:
        """写入 Unity 导入说明。"""
        content = """# Unity Tilemap 导入说明

## 文件清单

- `map.unity.json`: 地图数据（扁平 JSON，Unity JsonUtility 可直接解析）
- `ImportTilemap.cs`: 导入脚本参考实现

## 导入步骤

1. 把 `map.unity.json` 放到 Unity 项目的 `Assets/Resources/` 目录
2. 把 `ImportTilemap.cs` 放到 `Assets/Scripts/`
3. 创建一个 Grid 节点，挂载 `ImportTilemap` 脚本
4. 配置：
   - `Json File`: 指向 `map.unity.json`
   - `Tile Palette`: 配置 Tile 数组（按 tile_id 顺序）
   - `Target Grid`: 拖入 Grid 节点
5. 运行场景即可看到地图

## 注意事项

- 第三方推荐：[SuperTiled2Unity](https://github.com/Seanba/SuperTiled2Unity) 可直接导入 Tiled JSON（即 `map.tiled.json`）
- 本导出器输出的是简化版 JSON，方便自定义 importer
- Unity Y 轴向上，所以脚本中 y 坐标取反
- objects 层数据在 `data.objects` 字段，可以根据 spritePath 加载 Sprite

## Object Sprite 加载示例

```csharp
foreach (var obj in data.objects) {
    if (string.IsNullOrEmpty(obj.spritePath)) continue;
    var sprite = Resources.Load<Sprite>(obj.spritePath.Replace(".png", ""));
    if (sprite != null) {
        var go = new GameObject(obj.id);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = sprite;
        go.transform.position = new Vector3(
            obj.x * data.map.tileWidth / 100f,
            -obj.y * data.map.tileHeight / 100f,
            0
        );
    }
}
```
"""
        path.write_text(content, encoding="utf-8")
