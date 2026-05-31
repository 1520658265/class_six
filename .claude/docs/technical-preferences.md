# Technical Preferences

<!-- Populated by /setup-engine. Updated as the user makes decisions throughout development. -->
<!-- All agents reference this file for project-specific standards and conventions. -->

## Engine & Language

- **Engine**: Godot 4.6
- **Language**: GDScript
- **Rendering**: GL Compatibility（mobile/desktop 一致）
- **Physics**: Godot Physics 2D（CharacterBody2D / Area2D 体系；横版格斗 RPG 默认带重力）

## Input & Platform

<!-- Written by /setup-engine. Read by /ux-design, /ux-review, /test-setup, /team-ui, and /dev-story -->
<!-- to scope interaction specs, test helpers, and implementation to the correct input methods. -->

- **Target Platforms**: PC (Steam / itch)，Demo 阶段本地运行
- **Input Methods**: 键盘/鼠标，手柄
- **Primary Input**: 键盘/鼠标（横版格斗 RPG / PC 主）
- **Gamepad Support**: Full（攻击 / 跳跃 / 闪避 / 互动 / 菜单全部 d-pad + 摇杆可达）
- **Touch Support**: None
- **Platform Notes**: UI 必须支持手柄/键盘双导航；不允许只有 hover 才能触发的交互；菜单焦点必须可视化。

## Naming Conventions

<!-- 反推自现有 scripts/ 与 scenes/，沿用项目既有惯例。 -->
<!-- 注意：本项目场景实际使用 snake_case，与模板默认 PascalCase 不同——保持现状一致。 -->

- **Classes**: PascalCase（如 `BaseCharacterController`）
- **Variables / Functions**: snake_case（如 `move_speed`、`apply_idle_pose()`）
- **Private members**: 前缀下划线（如 `_facing`、`_move_input`、`_load_sprite_frames()`）
- **Signals**: snake_case 过去时（如 `health_changed`、`stat_changed`、`dialogue_finished`）
- **Files**: snake_case 与 class_name 对齐（如 `base_character_controller.gd`）
- **Scenes**: snake_case（如 `dialogue_box.tscn`、`classroom_2b.tscn`）
- **Constants**: UPPER_SNAKE_CASE（如 `SPEED_WALK`、`SPEED_RUN`）
- **Resource IDs (asset / character)**: snake_case（如 `yuansheng`、`baoxianjin`、`lvfanhe`）

## Performance Budgets

- **Target Framerate**: 60 fps
- **Frame Budget**: 16.6 ms
- **Draw Calls**: ≤ 2000 per frame（GL Compatibility 的合理目标）
- **Memory Ceiling**: 512 MB（Demo 阶段；后续视实际机器调）

> 这些是默认值，等到了解目标机器后由 ADR 与 `/perf-profile` 重新校准。

## Testing

- **Framework**: gdunit4（待 `/test-setup` 真正集成后写入 `addons/`）
- **Minimum Coverage**: TBD（架构 + 首批 ADR 出来再定）
- **Required Tests**: 公式（属性变化、好感度、隐性变量增减）、状态机（战斗 / 移动 / 对白触发）、关键数据加载（dialogue JSON 解析、SaveManager 序列化）

## Forbidden Patterns

<!-- Add patterns that should never appear in this project's codebase -->
- [None configured yet — add as architectural decisions are made]

## Allowed Libraries / Addons

<!-- Add approved third-party dependencies here -->
- [None configured yet — gdunit4 will be added when `/test-setup` integrates it]

## Architecture Decisions Log

<!-- Quick reference linking to full ADRs in docs/architecture/ -->
- [No ADRs yet — use /architecture-decision to create one]

## Engine Specialists

<!-- Written by /setup-engine when engine is configured. -->
<!-- Read by /code-review, /architecture-decision, /architecture-review, and team skills -->
<!-- to know which specialist to spawn for engine-specific validation. -->

- **Primary**: godot-specialist
- **Language/Code Specialist**: godot-gdscript-specialist（所有 .gd 文件）
- **Shader Specialist**: godot-shader-specialist（.gdshader 文件、VisualShader 资源）
- **UI Specialist**: godot-specialist（无独立 UI specialist——主 specialist 覆盖所有 UI）
- **Additional Specialists**: godot-gdextension-specialist（仅在引入 GDExtension / 原生 C++ 绑定时使用）
- **Routing Notes**: 架构决策、ADR 校验、跨切关注点的代码评审 → 主 specialist。代码质量、信号架构、静态类型、GDScript 习语 → GDScript specialist。材质与 shader 代码 → shader specialist。仅在涉及原生扩展时调 GDExtension specialist。

### File Extension Routing

<!-- Skills use this table to select the right specialist per file type. -->
<!-- If a row says [TO BE CONFIGURED], fall back to Primary for that file type. -->

| File Extension / Type | Specialist to Spawn |
|-----------------------|---------------------|
| Game code (.gd files) | godot-gdscript-specialist |
| Shader / material files (.gdshader, VisualShader) | godot-shader-specialist |
| UI / screen files (Control nodes, CanvasLayer) | godot-specialist |
| Scene / prefab / level files (.tscn, .tres) | godot-specialist |
| Native extension / plugin files (.gdextension, C++) | godot-gdextension-specialist |
| General architecture review | godot-specialist |
