#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色 Prompt 生成器
读取角色配置 JSON,自动替换模板变量,生成可直接复制到 Liblib 的完整 prompt

用法: python generate_prompts.py config.json
"""

import json
import sys
import io
from pathlib import Path
from typing import Dict, Any

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class PromptGenerator:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self._load_config()
        self.project_root = Path(__file__).parent.parent
        self.prompts_dir = self.project_root / "prompts"
        self.output_dir = self.project_root / "output" / self.config["name"]

        # 读取基础模板
        self.base_style = self._read_template("base-style.txt")
        self.negative_prompt = self._read_template("negative-prompt.txt")

    def _load_config(self) -> Dict[str, Any]:
        """加载角色配置文件"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _read_template(self, filename: str) -> str:
        """读取模板文件内容"""
        template_path = self.prompts_dir / filename
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def _replace_variables(self, template: str) -> str:
        """替换模板中的变量"""
        # 替换基础样式
        result = template.replace("{base-style.txt 内容}", self.base_style)

        # 替换角色信息（支持带说明的变量格式）
        result = result.replace("{角色名}", self.config["name"])

        # 处理角色描述（可能带说明）
        import re
        result = re.sub(r'\{角色描述[^}]*\}', self.config.get("description", ""), result)
        result = re.sub(r'\{服装描述[^}]*\}', self.config.get("outfit", ""), result)
        result = re.sub(r'\{武器描述[^}]*\}', self.config.get("weapon", ""), result)

        return result

    def _extract_prompt_section(self, content: str) -> str:
        """从模板中提取正向 prompt 部分"""
        lines = content.split("\n")
        prompt_lines = []
        in_prompt_section = False

        for line in lines:
            if "=== 正向 Prompt" in line or "=== Inpainting 正向 Prompt" in line or "=== img2img 正向 Prompt" in line:
                in_prompt_section = True
                continue
            if in_prompt_section:
                if line.startswith("# ==="):
                    break
                if not line.startswith("#"):
                    prompt_lines.append(line)

        return "\n".join(prompt_lines).strip()

    def _extract_liblib_params(self, content: str) -> str:
        """从模板中提取 Liblib 参数部分"""
        lines = content.split("\n")
        param_lines = []
        in_param_section = False

        for line in lines:
            if "=== Liblib 参数" in line or "=== Liblib Inpainting 参数" in line:
                in_param_section = True
                continue
            if in_param_section:
                if line.startswith("# ===") and "Liblib" not in line:
                    break
                if line.startswith("#"):
                    param_lines.append(line)

        return "\n".join(param_lines)

    def _generate_output_file(self, filename: str, positive_prompt: str, params: str):
        """生成输出文件"""
        output_path = self.output_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# ========================================\n")
            f.write(f"# {filename}\n")
            f.write("# ========================================\n\n")
            f.write("## 正向 Prompt（可直接复制）\n\n")
            f.write(positive_prompt)
            f.write("\n\n")
            f.write("## 负向 Prompt\n\n")
            f.write(self.negative_prompt)
            f.write("\n\n")
            f.write("## Liblib 参数\n\n")
            f.write(params)
            f.write("\n")

        print(f"[OK] 生成: {output_path}")

    def generate_portrait(self):
        """生成立绘 prompt"""
        template = self._read_template("hero/portrait.txt")
        prompt = self._extract_prompt_section(template)
        prompt = self._replace_variables(prompt)
        params = self._extract_liblib_params(template)

        self._generate_output_file("portrait.txt", prompt, params)

    def generate_walk(self):
        """生成行走图 prompt"""
        template = self._read_template("hero/walk.txt")
        prompt = self._extract_prompt_section(template)
        prompt = self._replace_variables(prompt)
        params = self._extract_liblib_params(template)

        self._generate_output_file("walk.txt", prompt, params)

    def generate_battle_prompts(self):
        """生成所有战斗图 prompt"""
        battle_files = [
            "battle-attack.txt",
            "battle-charge.txt",
            "battle-critical-hurt.txt",
            "battle-dead.txt",
            "battle-dodge.txt",
            "battle-guard.txt",
            "battle-hurt.txt",
            "battle-idle.txt",
            "battle-low-hp.txt",
            "battle-skill.txt",
            "battle-victory.txt",
            "battle-walk-in.txt",
        ]

        for battle_file in battle_files:
            template = self._read_template(f"hero/{battle_file}")
            prompt = self._extract_prompt_section(template)
            prompt = self._replace_variables(prompt)
            params = self._extract_liblib_params(template)

            self._generate_output_file(battle_file, prompt, params)

    def generate_expression(self):
        """生成表情差分 prompt"""
        template = self._read_template("hero/expression.txt")
        prompt = self._extract_prompt_section(template)
        prompt = self._replace_variables(prompt)
        params = self._extract_liblib_params(template)

        self._generate_output_file("expression.txt", prompt, params)

    def generate_face_icon(self):
        """生成头像 prompt"""
        template = self._read_template("hero/face-icon.txt")
        prompt = self._extract_prompt_section(template)
        prompt = self._replace_variables(prompt)
        params = self._extract_liblib_params(template)

        self._generate_output_file("face-icon.txt", prompt, params)

    def generate_all(self):
        """生成所有 prompt"""
        print(f"\n开始为角色 '{self.config['name']}' 生成 prompt...\n")

        self.generate_portrait()
        self.generate_walk()
        self.generate_battle_prompts()
        self.generate_expression()
        self.generate_face_icon()

        print(f"\n[OK] 完成! 所有文件已生成到: {self.output_dir}\n")


def main():
    if len(sys.argv) != 2:
        print("用法: python generate_prompts.py config.json")
        print("\n示例配置文件格式:")
        print(json.dumps({
            "name": "hero01",
            "description": "short black hair, tan skin, lean build",
            "outfit": "light leather armor, brown cloak, belt with pouches",
            "weapon": "holding longsword in right hand"
        }, indent=2, ensure_ascii=False))
        sys.exit(1)

    config_path = Path(sys.argv[1])
    if not config_path.exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    try:
        generator = PromptGenerator(config_path)
        generator.generate_all()
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

