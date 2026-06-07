// DemoScene.js - Phaser 3 场景示例

class DemoScene extends Phaser.Scene {
    constructor() {
        super({ key: 'DemoScene' });
    }

    preload() {
        this.load.image('default_rpg_32', 'tilesets/default_rpg_32.png');
        this.load.tilemapTiledJSON('map', 'tilemap.json');
    }

    create() {
        const map = this.make.tilemap({ key: 'map' });
        const tileset = map.addTilesetImage('default_rpg_32', 'default_rpg_32');

        // 创建所有 tile layer
        const terrainLayer = map.createLayer('terrain', tileset, 0, 0);
        const pathLayer = map.createLayer('path', tileset, 0, 0);
        const buildingLayer = map.createLayer('building', tileset, 0, 0);
        const decorationLayer = map.createLayer('decoration', tileset, 0, 0);
        const collisionLayer = map.createLayer('collision', tileset, 0, 0);
        if (collisionLayer) collisionLayer.setVisible(false);

        // 加载对象层
        const objectLayer = map.getObjectLayer('objects');
        if (objectLayer) {
            objectLayer.objects.forEach(obj => {
                const props = {};
                (obj.properties || []).forEach(p => { props[p.name] = p.value; });

                if (props.sprite_path) {
                    // 异步加载对象 sprite
                    const key = `obj_${obj.name}`;
                    this.load.image(key, props.sprite_path);
                    this.load.once('complete', () => {
                        this.add.image(obj.x + obj.width / 2, obj.y + obj.height / 2, key);
                    });
                    this.load.start();
                }
            });
        }

        // 加载事件层
        const eventLayer = map.getObjectLayer('events');
        if (eventLayer) {
            eventLayer.objects.forEach(event => {
                console.log('Event:', event.type, 'at', event.x, event.y);
            });
        }
    }

    update() {
        // 游戏逻辑
    }
}

// 导出全局
if (typeof window !== 'undefined') {
    window.DemoScene = DemoScene;
}
