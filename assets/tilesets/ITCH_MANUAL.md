# itch.io 手动下载清单

itch.io 的下载链接是登录后动态生成的，脚本无法直下。下面是值得手动下载的资源。

## 下载方式（任选其一）

**方式 A：浏览器逐个下载**
打开链接 → 点 **Download Now** → 如果作者要"Name your own price"，输入 0 → 点 **No thanks, just take me to the downloads** → 选 zip 下载到 `D:\Claude\godot\assets\tilesets\itch\`

**方式 B：装 itch.io 官方 CLI butler（推荐重度用户）**
```powershell
# 下载 butler
iwr https://broth.itch.zone/butler/windows-amd64/LATEST/butler.zip -OutFile butler.zip
Expand-Archive butler.zip -DestinationPath C:\tools\butler
$env:Path += ";C:\tools\butler"

# 登录（浏览器扫码）
butler login

# 下载（先 fetch 资产 ID，命令格式：butler fetch <user>/<game>:<channel>）
# 示例（需要先在 itch.io 上 Add to library）
butler fetch pipoya/pipoya-rpg-tileset-32x32
```

## 推荐资源清单

### 一线必拿

- [PIPOYA FREE RPG Tileset 32x32](https://pipoya.itch.io/pipoya-rpg-tileset-32x32) — 经典日式 RPG
- [PIPOYA Free RPG Character Sprites 32x32](https://pipoya.itch.io/pipoya-free-rpg-character-sprites-32x32) — 配套角色
- [Open RPG Fantasy Tilesets by finalbossblues](https://finalbossblues.itch.io/openrtp-tiles) — CC0，幻想 RPG 全套
- [Free 24x24 Pixel RPG Tileset by Pixel_Poem](https://pixel-poem.itch.io/free-rpg-tileset) — 24x24 综合
- [Free Top-Down RPG 32x32 by Mixel](https://mixelslime.itch.io/free-top-down-rpg-32x32-tile-set) — 户外/废墟

### 等距 (Isometric)

- [Isometric RPG Tileset 64×32 by Woulette](https://woulette.itch.io/isometric-rpg-tileset-64x32-v1-1)
- [Natural RPG Isometric by raptor-reece](https://raptor-reece.itch.io/isometric-tiles-free)

### 主题/扩展

- [Epic RPG World - Ancient Ruins (Free Demo)](https://rafaelmatos.itch.io/epic-rpg-world-pack-free-demo-ancient-ruins-asset-tileset)
- [FREE Retro World Tilesets (RPG Maker MV)](https://srobinson111.itch.io/rpg-maker-mv-world-tilesets)

### 角色精灵

- [40 RPG Character Asset Pack](https://aklingon.itch.io/40-rpg-character-asset-pack) — 40 个全动画
- [RPG character base by Franuka](https://franuka.itch.io/rpg-character-base)
- [Memao Fantasy Character Pack](https://sleeping-robot-games.itch.io/fantasy-character-sprite-pack)
- [Top-Down Character Base by Super](https://ertylerex.itch.io/top-down-character-base)
- [16x16 RPG character by @javikolog (旧版)](https://route1rodent.itch.io/16x16-rpg-character-sprite-sheet)
- [16x16 RPG character by @javikolog (新版)](https://route1rodent.itch.io/new-16x16-rpg-character-sprite-sheet)
- [12x16 Top Down NPCs](https://syvalia.itch.io/rpg-type-retro-top-down-npc-sprites)

### UI / 头像

- [Free Basic Pixel UI for RPG](https://free-game-assets.itch.io/free-basic-pixel-art-ui-for-rpg)
- [Fantasy RPG UI](https://free-game-assets.itch.io/fantasy-rpg-user-interface)
- [Free RPG Fantasy Avatars](https://free-game-assets.itch.io/free-rpg-fantasy-avatar-icons) — 50 头像

### 大包合集

- [Kenney Game Assets All-in-1](https://kenney.itch.io/kenney-game-assets) — 60000+，全 CC0（≈ 数 GB）

## 聚合搜索页

逛累了再淘：

- [itch.io 免费 RPG tilemap](https://itch.io/game-assets/free/genre-rpg/tag-tilemap)
- [itch.io 免费 RPG Maker tileset](https://itch.io/game-assets/free/tag-rpgmaker/tag-tileset)
- [itch.io 2D + Tileset](https://itch.io/game-assets/free/tag-2d/tag-tileset)
- [itch.io JRPG](https://itch.io/game-assets/free/tag-jrpg)
- [CraftPix 免费区](https://craftpix.net/freebies/) — 注册免费账号即可下载
