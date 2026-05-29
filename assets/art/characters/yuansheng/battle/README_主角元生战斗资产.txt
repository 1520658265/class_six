主角元生战斗资产说明

目录结构

1. body/
- char_yuansheng_battle_body_sheet_v1.png
  横版战斗本体动作表透明版，8 个 pose。
- char_yuansheng_battle_body_sheet_v1_source.jpg
  原始生成图，保留作溯源。
- char_yuansheng_battle_pose_preview_v1.png
  8 个 pose 的透明预览。
- poses/*.png
  已切出的 96x96 单 pose 透明 PNG。

2. weapons/
- char_yuansheng_weapon_sheet_v2.png
  武器/校园物件分层表透明版。
- char_yuansheng_weapon_sheet_v2_source.jpg
  原始生成图，保留作溯源。
- char_yuansheng_weapon_preview_v1.png
  可替换武器预览。
- char_yuansheng_weapon_empty_v1.png
  空手/无武器透明占位。
- char_yuansheng_weapon_bag_v1.png
  书包，软挥击型。
- char_yuansheng_weapon_broom_v1.png
  扫帚，长柄型。
- char_yuansheng_weapon_lunchbox_v1.png
  铝饭盒，挥击/投掷型。
- char_yuansheng_weapon_yoyo_v1.png
  悠悠球，特殊远程型。
- char_yuansheng_weapon_eraser_v1.png
  黑板擦，小型投掷型。

3. effects/
- char_yuansheng_fx_sheet_v1.png
  基础战斗特效表透明版。
- char_yuansheng_fx_sheet_v1_source.jpg
  原始生成图，保留作溯源。
- char_yuansheng_fx_preview_v1.png
  特效预览。
- char_yuansheng_fx_*.png
  已切出的 96x96 单特效透明 PNG。

推荐 Godot 分层

CharacterBody2D
- BodySprite / AnimatedSprite2D：播放 body/poses 或后续正式动画帧。
- WeaponSlot / Node2D：跟随当前动作的手部挂点。
- WeaponSprite / Sprite2D：显示 weapons/ 下的可替换武器。
- AttackVfx / AnimatedSprite2D：播放 effects/ 下的命中、灰尘、闪避等特效。
- Hurtbox / Area2D
- Hitbox / Area2D

动态武器设计

- 不把书包、扫帚、饭盒、悠悠球直接画死在角色动作里。
- 角色本体只提供通用动作，例如 idle、run、push、punch、swing_body、hurt。
- 武器由 WeaponSprite 独立显示，按当前装备切换贴图。
- 每个动作帧配置 weapon_pos、weapon_rotation、weapon_z_index。
- 近战物件使用同一套 swing_body 动作，区别由武器贴图、攻击范围和特效决定。
- 投掷物如饭盒、黑板擦、悠悠球，攻击时可以从 WeaponSlot 复制出 Projectile 节点。

后续角色帧硬规则

- 所有后续主角战斗帧都必须能适配 weapons/ 里的这套武器：空手、书包、扫帚、铝饭盒、悠悠球、黑板擦。
- 角色本体帧必须保持手部可挂载武器，不能把某个武器直接烘焙进本体动作。
- 攻击、受击、跑动、待机等动作都要预留 WeaponSlot，对应帧应能记录手部挂点位置、旋转和前后层级。
- 如果后续生成新角色帧，prompt 里必须明确写“只画角色本体，不画武器；武器将作为独立层挂到手部”。

当前质量判断

- body v1 可作为战斗 pose 概念和原型占位，但还不是最终逐帧动画。
- weapon v2 的五个校园物件可作为第一版可替换武器，饭盒略偏工具箱造型，后续可以单独重绘优化。
- effects v1 可作为第一版基础特效，整体克制，没有魔法化。
