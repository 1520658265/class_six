# 战斗特效动效实现规划

> **基于现有 8 张单帧特效图，在 Godot 中通过 Tween/Particles/Shader 实现完整动效**
> **素材位置**：`assets/art/characters/yuansheng/battle/effects/`
> **像素规格**：96×96 透明 PNG

---

## 一、整体架构

```
BattleVFX (Node2D) — 挂在角色或场景上
├── spawn_effect(effect_name, position, direction)
└── 每次调用实例化一个临时节点，播完自动 queue_free
```

---

## 二、逐个特效动效方案

### 1. 推搡灰尘 (push_dust)

**文件**：`char_yuansheng_fx_push_dust_v1.png`
**触发时机**：推人命中瞬间，生成在被推者脚下

| 属性 | 动画 | 时长 |
|------|------|------|
| scale | (0.3, 0.3) → (1.2, 1.0) | 0.15s |
| position.x | 0 → +8px（随推方向） | 0.3s |
| position.y | 0 → -4px | 0.2s |
| modulate.a | 0.9 → 0.0 | 0.35s |

**加分做法**：用 GPUParticles2D，把这张图当粒子贴图，发射 3-5 个粒子，随机大小 0.5-1.0，散射角 ±30°，模拟灰尘飘散。

---

### 2. 挥击弧线 (punch_arc)

**文件**：`char_yuansheng_fx_punch_arc_v1.png`
**触发时机**：出拳动作帧（attack frame）瞬间，跟随拳头位置

| 属性 | 动画 | 时长 |
|------|------|------|
| scale | (0.0, 0.0) → (1.0, 1.0) | 0.08s（快速弹出） |
| rotation | -15° → +5° | 0.12s（随挥拳弧度） |
| modulate.a | 1.0 → 0.0 | 0.15s |

**关键**：出现极快、消失也快，要有"唰"的感觉。可以叠加 Shader 让弧线尾端更透明。

```gdscript
var tween = create_tween()
tween.tween_property(sprite, "scale", Vector2(1.0, 1.0), 0.08).from(Vector2.ZERO).set_ease(Tween.EASE_OUT)
tween.parallel().tween_property(sprite, "rotation", deg_to_rad(5), 0.12).from(deg_to_rad(-15))
tween.parallel().tween_property(sprite, "modulate:a", 0.0, 0.15).set_delay(0.05)
```

---

### 3. 受击星星 (hurt_stars)

**文件**：`char_yuansheng_fx_hurt_stars_v1.png`
**触发时机**：被击中瞬间，生成在受击点

| 属性 | 动画 | 时长 |
|------|------|------|
| scale | (0.0, 0.0) → (1.3, 1.3) → (1.0, 1.0) | 0.1s 弹出 + 0.05s 回弹 |
| rotation | 随机初始角 + 旋转 30° | 0.3s |
| modulate.a | 1.0 → 0.0 | 0.25s（延迟 0.1s 开始淡出） |

**加分做法**：把星星图作为 GPUParticles2D 贴图，发射 5-8 颗粒子，向四周爆散（速度 50-100px/s），带重力下坠，比单张图动态感强很多。

---

### 4. 闪避残影 (dodge_afterimage)

**文件**：`char_yuansheng_fx_dodge_afterimage_v1.png`
**触发时机**：闪避动作触发时，在原位置留残影

**推荐方案**：不用这张静态图，改用实时复制角色 sprite 的方式：

```gdscript
func spawn_afterimage():
    var ghost = Sprite2D.new()
    ghost.texture = body_sprite.texture
    ghost.global_position = body_sprite.global_position
    ghost.modulate = Color(0.6, 0.5, 0.8, 0.6)  # 紫灰色半透明
    get_tree().current_scene.add_child(ghost)

    var tween = create_tween()
    tween.tween_property(ghost, "modulate:a", 0.0, 0.25)
    tween.tween_callback(ghost.queue_free)
```

闪避过程中每隔 0.05s 生成一个残影，连续 3-4 个，形成拖影效果。

---

### 5. 勇气爆发亮闪 (courage_flash)

**文件**：`char_yuansheng_fx_courage_flash_v1.png`
**触发时机**：勇气槽满/爆发技能激活，生成在角色中心

| 属性 | 动画 | 时长 |
|------|------|------|
| scale | (0.0, 0.0) → (1.5, 1.5) → (1.0, 1.0) | 0.2s 爆开 + 0.1s 收 |
| modulate | 白色 → 金黄 Color(1, 0.9, 0.4) | 0.15s |
| modulate.a | 1.0 → 0.0 | 0.4s |

**叠加效果**：
- 角色本体同步闪白 0.1s（Shader `mix(texture_color, white, flash_amount)`）
- 屏幕微震（Camera shake，幅度 2px，时长 0.15s）
- 可叠一层 CanvasItem shader 做径向光晕

```gdscript
# 屏幕微震
var cam = get_viewport().get_camera_2d()
var original_offset = cam.offset
var tween = create_tween()
for i in 4:
    tween.tween_property(cam, "offset", original_offset + Vector2(randf_range(-2, 2), randf_range(-2, 2)), 0.03)
tween.tween_property(cam, "offset", original_offset, 0.05)
```

---

### 6. 摔倒落地尘 (fall_dust)

**文件**：`char_yuansheng_fx_fall_dust_v1.png`
**触发时机**：被击倒落地那一帧

| 属性 | 动画 | 时长 |
|------|------|------|
| scale.x | 0.5 → 1.3 | 0.12s（横向扩散） |
| scale.y | 1.0 → 0.6 | 0.12s（纵向压扁） |
| position.y | 0 → -3px | 0.15s |
| modulate.a | 0.8 → 0.0 | 0.3s |

**叠加**：落地瞬间屏幕震动（幅度 3px，持续 0.1s），给重量感。

---

### 7. 命中抖动线 (hit_lines)

**文件**：`char_yuansheng_fx_hit_lines_v1.png`
**触发时机**：任何攻击命中瞬间，叠加在受击点

注意：此图为白色速度线，需要**加法混合**才能在深色背景上显现。

| 属性 | 动画 | 时长 |
|------|------|------|
| material.blend_mode | Add（加法混合） | — |
| scale | (0.5, 0.5) → (1.2, 1.2) | 0.06s |
| modulate.a | 1.0 → 0.0 | 0.1s |
| rotation | 随机角度 | 固定 |

**关键**：存活极短（0.1s），配合顿帧（hit stop）使用效果最好：

```gdscript
# 命中顿帧
Engine.time_scale = 0.1
await get_tree().create_timer(0.05 * 0.1).timeout
Engine.time_scale = 1.0
```

---

### 8. 后退滑步灰尘 (slide_dust)

**文件**：`char_yuansheng_fx_slide_dust_v1.png`
**触发时机**：角色后退/被推开滑行时，持续生成

| 属性 | 动画 | 时长 |
|------|------|------|
| scale | (0.6, 0.6) → (1.0, 1.0) | 0.15s |
| position.y | 0 → -6px | 0.2s |
| modulate.a | 0.7 → 0.0 | 0.25s |

**持续生成**：滑行期间每 0.08s 在脚底生成一个，形成连续烟尘轨迹。每个实例随机 ±2px 偏移 + ±10° 旋转，避免重复感。

---

## 三、通用增强手段（全局适用）

| 技巧 | 效果 | 适用场景 |
|------|------|---------|
| **Hit Stop（顿帧）** | 命中瞬间时间暂停 0.03-0.05s | 所有攻击命中 |
| **Camera Shake** | 屏幕震动 2-4px | 重击、落地、勇气爆发 |
| **Flash White** | 被击者全身闪白一帧 | 所有受击 |
| **Knockback Tween** | 被击者位移 10-20px | 推搡、重击 |
| **Slow Motion** | 关键一击 time_scale=0.3 持续 0.2s | Boss 战最后一击 |

---

## 四、打击感组合公式

一次完整的"命中"应同时触发多个效果叠加：

```
攻击命中 =
  Hit Stop (0.04s)
  + Hit Lines (加法混合闪现)
  + Hurt Stars (爆散)
  + Flash White (受击者闪白)
  + Knockback (受击者后退)
  + Camera Shake (轻微)
  + Push Dust (脚下扬尘)
```

一次"重击/BOSS 击倒"：

```
重击命中 =
  Hit Stop (0.08s，更长)
  + Slow Motion (0.2s)
  + Hit Lines × 2 (双层叠加)
  + Fall Dust (落地扬尘)
  + Camera Shake (幅度 4px)
  + Flash White (持续 0.15s)
```

---

## 五、后续扩展预留

本文档后续可追加：
- 武器专属特效（书包砸击震波、扫帚横扫风压、饭盒砸地弹跳等）
- 情绪状态特效（自卑暗角、护短爆发光环、"姐姐在底"暖光）
- 环境互动特效（课桌碎裂、黑板粉笔灰、煤炉火星）
- Shader 代码实现细节
