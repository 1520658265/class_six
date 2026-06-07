"""
自动生成缺失素材的工作流。

当地图生成器需要一个不在素材库中的对象时，
自动触发生成流程并回填到库中。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..assets.asset_library import AssetLibrary
    from ..assets.object_generator import ObjectGenerator
    from ..models import TilemapData


class MissingAssetHandler:
    """
    处理缺失素材的自动生成和回填。
    """

    def __init__(
        self,
        asset_library: "AssetLibrary",
        object_generator: "ObjectGenerator",
    ):
        """
        初始化缺失素材处理器。

        Args:
            asset_library: 素材库
            object_generator: 对象生成器
        """
        self.asset_library = asset_library
        self.object_generator = object_generator

    def detect_missing_assets(self, tilemap: "TilemapData") -> list[str]:
        """
        检测地图中缺失的素材类型。

        Args:
            tilemap: 待检测的地图数据

        Returns:
            缺失的对象类型列表
        """
        missing_types = []
        seen = set()

        for obj in tilemap.objects:
            if obj.sprite_ref:
                # 已有 sprite，跳过
                continue

            obj_type = obj.type
            if obj_type in seen:
                continue
            seen.add(obj_type)

            # 搜索库中是否存在
            matches = self.asset_library.search_by_tags([obj_type], use_synonyms=True)
            if not matches:
                missing_types.append(obj_type)

        return missing_types

    def generate_missing_asset(
        self,
        object_type: str,
        seed: int | None = None,
    ) -> str | None:
        """
        生成单个缺失素材。

        Args:
            object_type: 对象类型
            seed: 随机种子

        Returns:
            生成的 asset_id，失败则返回 None
        """
        from ..assets.object_generator import ObjectGenerationRequest
        from ..assets.image_generation import ImageStyle

        # 根据类型推断描述和属性
        description, theme, footprint = self._infer_object_properties(object_type)

        request = ObjectGenerationRequest(
            object_type=object_type,
            description=description,
            style=ImageStyle.PIXEL_ART,
            footprint=footprint,
            tile_size=(32, 32),
            theme=theme,
            seed=seed,
            tags=[object_type],
        )

        result = self.object_generator.generate(request)

        if not result.success:
            return None

        # 自动加载到库中
        if result.metadata:
            self.asset_library.add_asset(result.metadata)

        return result.asset_id

    def auto_generate_and_backfill(
        self,
        tilemap: "TilemapData",
        seed_offset: int = 9000,
    ) -> dict:
        """
        自动生成所有缺失素材并回填到地图。

        Args:
            tilemap: 地图数据
            seed_offset: 种子偏移量

        Returns:
            生成报告
        """
        missing_types = self.detect_missing_assets(tilemap)

        if not missing_types:
            return {
                "total_missing": 0,
                "generated": 0,
                "failed": 0,
                "types": [],
            }

        generated = []
        failed = []

        for idx, obj_type in enumerate(missing_types):
            seed = seed_offset + idx
            asset_id = self.generate_missing_asset(obj_type, seed=seed)

            if asset_id:
                generated.append({"type": obj_type, "asset_id": asset_id})
            else:
                failed.append(obj_type)

        # 回填到地图对象
        self._backfill_to_tilemap(tilemap)

        return {
            "total_missing": len(missing_types),
            "generated": len(generated),
            "failed": len(failed),
            "generated_assets": generated,
            "failed_types": failed,
        }

    def _backfill_to_tilemap(self, tilemap: "TilemapData") -> int:
        """
        将新生成的素材引用回填到地图对象。

        Args:
            tilemap: 地图数据

        Returns:
            回填的对象数量
        """
        backfilled = 0

        for obj in tilemap.objects:
            if obj.sprite_ref:
                # 已有引用，跳过
                continue

            # 尝试从库中查找
            matches = self.asset_library.search_by_tags([obj.type], use_synonyms=True)
            if matches:
                asset = matches[0]
                obj.sprite_ref = asset.asset_id
                obj.sprite_path = asset.sprite_path

                # 更新尺寸
                if asset.footprint:
                    obj.width = asset.footprint[0]
                    obj.height = asset.footprint[1]

                backfilled += 1

        return backfilled

    def _infer_object_properties(
        self,
        object_type: str,
    ) -> tuple[str, list[str], tuple[int, int]]:
        """
        根据对象类型推断描述、主题和 footprint。

        Args:
            object_type: 对象类型

        Returns:
            (description, theme, footprint)
        """
        # 默认值
        description = f"a {object_type} for RPG game"
        theme = []
        footprint = (1, 1)

        # 树类
        if "tree" in object_type.lower():
            description = f"{object_type} with leaves and trunk"
            theme = ["forest", "village"]
            footprint = (1, 2)

        # 建筑类
        elif any(k in object_type.lower() for k in ["house", "building", "temple", "tower"]):
            description = f"{object_type} structure"
            theme = ["village", "ruins"]
            footprint = (2, 2)

        # 岩石类
        elif any(k in object_type.lower() for k in ["rock", "stone", "boulder"]):
            description = f"{object_type} natural formation"
            theme = ["mountains", "desert"]
            footprint = (1, 1)

        # 容器类
        elif any(k in object_type.lower() for k in ["chest", "barrel", "crate", "box"]):
            description = f"wooden {object_type}"
            theme = ["dungeon", "village"]
            footprint = (1, 1)

        # 装饰类
        elif any(k in object_type.lower() for k in ["lamp", "statue", "fountain", "well", "torch"]):
            description = f"decorative {object_type}"

            # 特殊处理不同装饰物的尺寸
            if "lamp" in object_type.lower() or "statue" in object_type.lower() or "torch" in object_type.lower():
                footprint = (1, 2)
                theme = ["village", "plaza"]
            else:  # fountain, well
                footprint = (2, 2)
                theme = ["village", "plaza"]

        # 标记类
        elif any(k in object_type.lower() for k in ["sign", "torch", "marker"]):
            description = f"{object_type} for navigation or lighting"
            theme = ["village", "dungeon"]
            footprint = (1, 1)

        return description, theme, footprint

    def get_generation_stats(self) -> dict:
        """
        获取素材库统计信息。

        Returns:
            统计数据
        """
        return self.asset_library.get_stats()
