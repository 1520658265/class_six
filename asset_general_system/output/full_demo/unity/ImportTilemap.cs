using System;
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
