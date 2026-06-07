# Unity Tilemap 导入说明

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
