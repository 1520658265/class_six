from __future__ import annotations

from collections import deque

from ..models import TilemapData, ValidationIssue, ValidationReport


class Validator:
    def validate(self, tilemap: TilemapData) -> ValidationReport:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        spawn = self._spawn(tilemap)
        reachable = set()

        if not spawn:
            errors.append(ValidationIssue(code="SPAWN_WALKABLE", message="Missing player spawn event."))
        elif not self._is_walkable(tilemap, spawn.x, spawn.y):
            errors.append(
                ValidationIssue(
                    code="SPAWN_WALKABLE",
                    message="Player spawn is not walkable.",
                    position=[spawn.x, spawn.y],
                    target=spawn.id,
                )
            )
        else:
            reachable = self._reachable_from(tilemap, (spawn.x, spawn.y))

        for event in tilemap.events:
            if event.type == "npc_spawn" and not self._is_walkable(tilemap, event.x, event.y):
                errors.append(
                    ValidationIssue(
                        code="NPC_SPAWN_WALKABLE",
                        message=f"NPC spawn {event.id} is not walkable.",
                        position=[event.x, event.y],
                        target=event.id,
                    )
                )

        reachable_key_regions = 0
        key_regions = [region for region in tilemap.regions if region.type not in {"river"}]
        for region in key_regions:
            access = tuple(region.access)
            if access in reachable:
                reachable_key_regions += 1
            else:
                errors.append(
                    ValidationIssue(
                        code="KEY_REGIONS_REACHABLE",
                        message=f"Key region {region.id} is not reachable from spawn.",
                        position=region.access,
                        target=region.id,
                    )
                )

        for obj in tilemap.objects:
            if not self._in_bounds(tilemap, obj.x, obj.y):
                errors.append(
                    ValidationIssue(
                        code="OBJECTS_PLACEABLE",
                        message=f"Object {obj.id} is out of bounds.",
                        position=[obj.x, obj.y],
                        target=obj.id,
                    )
                )
                continue
            if obj.type == "door" and not self._has_walkable_neighbor(tilemap, obj.x, obj.y):
                errors.append(
                    ValidationIssue(
                        code="NO_BLOCKED_DOORS",
                        message=f"Door {obj.id} has no walkable adjacent tile.",
                        position=[obj.x, obj.y],
                        target=obj.id,
                    )
                )
            if obj.type in {"door", "chest", "market_stall", "campfire"} and not self._has_walkable_neighbor(tilemap, obj.x, obj.y):
                errors.append(
                    ValidationIssue(
                        code="INTERACTABLE_REACHABLE",
                        message=f"Interactable object {obj.id} has no walkable adjacent tile.",
                        position=[obj.x, obj.y],
                        target=obj.id,
                    )
                )

        walkable_count = sum(1 for value in tilemap.layers["collision"] if value == 0)
        total = tilemap.map.width * tilemap.map.height
        walkable_ratio = walkable_count / total if total else 0
        if walkable_ratio < 0.25:
            warnings.append(
                ValidationIssue(
                    code="WALKABLE_RATIO",
                    severity="warning",
                    message=f"Walkable ratio is low: {walkable_ratio:.2f}.",
                )
            )

        return ValidationReport(
            passed=not errors,
            errors=errors,
            warnings=warnings,
            metrics={
                "walkable_ratio": round(walkable_ratio, 4),
                "reachable_key_regions": reachable_key_regions,
                "total_key_regions": len(key_regions),
                "object_count": len(tilemap.objects),
                "event_count": len(tilemap.events),
            },
        )

    def _spawn(self, tilemap: TilemapData):
        return next((event for event in tilemap.events if event.type == "player_spawn"), None)

    def _reachable_from(self, tilemap: TilemapData, start: tuple[int, int]) -> set[tuple[int, int]]:
        width, height = tilemap.map.width, tilemap.map.height
        queue = deque([start])
        seen = {start}
        while queue:
            x, y = queue.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen and self._is_walkable(tilemap, nx, ny):
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        return seen

    def _has_walkable_neighbor(self, tilemap: TilemapData, x: int, y: int) -> bool:
        return any(self._in_bounds(tilemap, nx, ny) and self._is_walkable(tilemap, nx, ny) for nx, ny in self._neighbors(x, y))

    def _neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]

    def _is_walkable(self, tilemap: TilemapData, x: int, y: int) -> bool:
        return tilemap.layers["collision"][y * tilemap.map.width + x] == 0

    def _in_bounds(self, tilemap: TilemapData, x: int, y: int) -> bool:
        return 0 <= x < tilemap.map.width and 0 <= y < tilemap.map.height
