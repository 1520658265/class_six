# Directory Structure

```text
/
├── CLAUDE.md                       # Master configuration
├── README.md                       # Project introduction (《元生的六年级》)
├── project.godot                   # Godot 4.6 project file
├── .claude/                        # Agent definitions, skills, hooks, rules, docs
├── scripts/                        # Game source code (Godot convention — not src/)
│   ├── autoload/                   # 9 autoload singletons (Sprites, GlobalState, ...)
│   ├── character/                  # Player + NPC controllers, interact zones
│   ├── level/                      # level_base, scene_door, save_point, cutscene_runner
│   ├── shared/                     # Shared resource scripts (atlas_set, portrait_set, vfx_clip)
│   └── ui/                         # UI scripts (dialogue_box, stat_panel, main_menu, ...)
├── scenes/                         # Godot scenes (.tscn)
│   ├── characters/                 # yuansheng, npc
│   ├── levels/                     # classroom_2b, corridor_stairs, dorm, cafeteria_steam
│   └── ui/                         # main_menu and other UI scenes
├── resources/                      # Godot resources (.tres) — atlas, portraits, sprite_frames, vfx
├── assets/                         # Source art and tilesets
│   ├── art/                        # Self-produced art (characters, props, UI, vfx)
│   └── tilesets/                   # Third-party tilesets (kenney/, opengameart/, itch/)
├── addons/                         # Godot addons
├── data/                           # Game data tables (dialogue/)
├── design/                         # Game design documents (template-managed)
│   ├── gdd/                        # Per-system GDDs (/design-system)
│   ├── quick-specs/                # Lightweight specs (/quick-design)
│   ├── ux/                         # UX specs (/ux-design)
│   ├── registry/                   # Entity registry (entities.yaml)
│   └── CLAUDE.md                   # Routing rules for design files
├── docs/                           # Technical and project documentation
│   ├── design/                     # ⚠️ Legacy design specs (-spec.md). /adopt will reconcile with design/gdd/.
│   ├── reference/                  # Story line and creative source material
│   ├── journal/                    # Daily work journals (YYYY-MM-DD.md)
│   ├── superpowers/                # Existing dated review specs
│   ├── architecture/               # ADRs and architecture documents
│   ├── engine-reference/           # Curated engine API snapshots (godot/, unity/, unreal/)
│   ├── examples/                   # Workflow walkthrough examples
│   ├── registry/                   # Architecture registry (tr-registry.yaml, etc.)
│   ├── ccgs-template-meta/         # CCGS template's own OSS meta files (CONTRIBUTING, LICENSE, ...)
│   ├── CLAUDE.md                   # Routing rules for docs files
│   ├── COLLABORATIVE-DESIGN-PRINCIPLE.md
│   └── WORKFLOW-GUIDE.md
├── tests/                          # Test suites
│   ├── unit/                       # Unit tests
│   └── fixtures/                   # Test fixtures
├── tools/                          # Build and pipeline tools
│   ├── ai/                         # AI generation/audit scripts (Python)
│   ├── godot_bake/                 # Import/bake helpers
│   ├── godot.cmd                   # Godot CLI wrapper
│   └── private/                    # Local-only (gitignored)
├── prototypes/                     # Throwaway prototypes (created on demand by /prototype)
└── production/                     # Production management
    ├── session-state/              # Ephemeral session state (active.md — gitignored)
    └── session-logs/               # Session audit trail (gitignored)
```

## Path Conventions for Skills

This project predates the CCGS template adoption. Two path differences from the
default template structure:

| Default template | This project | Reason |
|---|---|---|
| `src/` | `scripts/` | Godot convention. `project.godot` references `res://scripts/`. |
| `design/gdd/` | both `design/gdd/` AND `docs/design/` (legacy) | Existing `-spec.md` files live in `docs/design/`. Run `/adopt` to reconcile. |

**For skill authors and agents**:
- When a skill references `src/`, treat it as `scripts/` in this project.
- When reading existing design specs, check both `design/gdd/` and `docs/design/`.
- When writing new GDDs via `/design-system`, write to `design/gdd/` per template convention.
