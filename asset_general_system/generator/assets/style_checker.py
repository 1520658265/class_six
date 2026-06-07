"""
风格一致性检查工具。

分析同主题素材的视觉一致性，确保生成的对象风格统一。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..assets.asset_library import AssetLibrary
    from ..models.asset_metadata import AssetMetadata


class StyleConsistencyChecker:
    """
    检查生成素材的风格一致性。
    """

    def __init__(self, asset_library: "AssetLibrary"):
        """
        初始化风格检查器。

        Args:
            asset_library: 素材库
        """
        self.asset_library = asset_library

    def check_theme_consistency(self, theme: str) -> dict:
        """
        检查指定主题下素材的风格一致性。

        Args:
            theme: 主题名称

        Returns:
            一致性报告
        """
        assets = self.asset_library.search_by_theme([theme])

        if len(assets) < 2:
            return {
                "theme": theme,
                "asset_count": len(assets),
                "consistency_score": 1.0,
                "issues": [],
                "status": "insufficient_data",
            }

        # 分析各项一致性指标
        color_analysis = self._analyze_color_consistency(assets)
        resolution_analysis = self._analyze_resolution_consistency(assets)
        size_analysis = self._analyze_size_consistency(assets)

        # 计算总体一致性分数
        consistency_score = (
            color_analysis["score"] * 0.4 +
            resolution_analysis["score"] * 0.3 +
            size_analysis["score"] * 0.3
        )

        issues = []
        issues.extend(color_analysis.get("issues", []))
        issues.extend(resolution_analysis.get("issues", []))
        issues.extend(size_analysis.get("issues", []))

        status = "good" if consistency_score >= 0.8 else "needs_review" if consistency_score >= 0.6 else "poor"

        return {
            "theme": theme,
            "asset_count": len(assets),
            "consistency_score": consistency_score,
            "color_analysis": color_analysis,
            "resolution_analysis": resolution_analysis,
            "size_analysis": size_analysis,
            "issues": issues,
            "status": status,
        }

    def _analyze_color_consistency(self, assets: list["AssetMetadata"]) -> dict:
        """分析色调一致性。"""
        # 在没有真实图像的情况下，基于 metadata 做启发式检查
        # 真实实现需要用 PIL 分析图像主色调

        # 检查是否都有生成信息
        generated_count = sum(1 for a in assets if a.generated)

        if generated_count == 0:
            return {"score": 1.0, "issues": []}

        # 检查是否使用相同的生成模型
        models = set()
        for asset in assets:
            if asset.generated:
                models.add(asset.generated.model)

        if len(models) > 1:
            return {
                "score": 0.7,
                "issues": [f"使用了 {len(models)} 个不同的生成模型"],
                "models": list(models),
            }

        return {"score": 1.0, "issues": []}

    def _analyze_resolution_consistency(self, assets: list["AssetMetadata"]) -> dict:
        """分析分辨率一致性。"""
        tile_sizes = set()
        for asset in assets:
            tile_sizes.add(asset.tile_size)

        if len(tile_sizes) == 1:
            return {"score": 1.0, "issues": []}

        return {
            "score": 0.5,
            "issues": [f"检测到 {len(tile_sizes)} 种不同的 tile 尺寸"],
            "tile_sizes": [list(ts) for ts in tile_sizes],
        }

    def _analyze_size_consistency(self, assets: list["AssetMetadata"]) -> dict:
        """分析对象尺寸一致性。"""
        footprints = {}
        for asset in assets:
            if asset.footprint:
                fp = asset.footprint
                if fp not in footprints:
                    footprints[fp] = []
                footprints[fp].append(asset.asset_id)

        # 尺寸多样性是合理的，只要同类对象尺寸相近
        if len(footprints) <= 4:
            return {"score": 1.0, "issues": []}

        return {
            "score": 0.8,
            "issues": [f"对象尺寸种类较多 ({len(footprints)} 种)"],
            "footprints": {str(k): len(v) for k, v in footprints.items()},
        }

    def check_all_themes(self) -> dict:
        """
        检查所有主题的一致性。

        Returns:
            完整一致性报告
        """
        stats = self.asset_library.get_stats()
        themes = list(stats.get("by_theme", {}).keys())

        theme_reports = {}
        overall_issues = []

        for theme in themes:
            report = self.check_theme_consistency(theme)
            theme_reports[theme] = report

            if report["status"] != "good":
                overall_issues.append(f"主题 '{theme}' 一致性 {report['status']}")

        # 计算总体平均分
        scores = [r["consistency_score"] for r in theme_reports.values() if r["consistency_score"] is not None]
        avg_score = sum(scores) / len(scores) if scores else 1.0

        return {
            "total_themes": len(themes),
            "average_consistency": avg_score,
            "theme_reports": theme_reports,
            "overall_issues": overall_issues,
            "recommendation": self._generate_recommendation(avg_score, overall_issues),
        }

    def _generate_recommendation(self, avg_score: float, issues: list[str]) -> str:
        """生成改进建议。"""
        if avg_score >= 0.9:
            return "素材风格一致性良好，无需调整。"
        elif avg_score >= 0.7:
            return "素材风格基本一致，建议检查以下问题：\n" + "\n".join(f"  - {i}" for i in issues)
        else:
            return "素材风格一致性较差，建议重新生成以下主题的素材：\n" + "\n".join(f"  - {i}" for i in issues)

    def analyze_image_style(self, image_path: str | Path) -> dict:
        """
        分析单个图像的风格特征（需要 PIL）。

        Args:
            image_path: 图像文件路径

        Returns:
            风格分析结果
        """
        try:
            from PIL import Image
        except ImportError:
            return {"error": "PIL 不可用"}

        try:
            img = Image.open(image_path)
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # 分析主色调
            colors = self._extract_dominant_colors(img)

            # 分析线条风格（像素风 vs 手绘风）
            style_type = self._detect_style_type(img)

            return {
                "image_path": str(image_path),
                "size": img.size,
                "mode": img.mode,
                "dominant_colors": colors,
                "style_type": style_type,
            }

        except Exception as e:
            return {"error": str(e)}

    def _extract_dominant_colors(self, img, num_colors: int = 5):
        """提取主要颜色（简化版）。"""
        # 简化实现：采样部分像素
        pixels = list(img.getdata())
        opaque_pixels = [p[:3] for p in pixels if len(p) >= 4 and p[3] > 128]

        if not opaque_pixels:
            return []

        # 粗略统计（真实实现应使用聚类算法）
        from collections import Counter
        color_counts = Counter(opaque_pixels)
        return [{"rgb": list(c), "count": count} for c, count in color_counts.most_common(num_colors)]

    def _detect_style_type(self, img) -> str:
        """检测风格类型。"""
        # 简化实现：基于尺寸和清晰度启发式判断
        width, height = img.size

        if width <= 64 and height <= 64:
            return "pixel_art"
        elif width <= 128 and height <= 128:
            return "low_res"
        else:
            return "high_res"
