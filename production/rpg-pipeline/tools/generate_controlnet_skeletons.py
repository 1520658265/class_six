#!/usr/bin/env python3
"""
ControlNet 骨架模板生成器
自动生成行走图和战斗图的火柴人骨架（黑线白底）
"""

import argparse
from pathlib import Path
from PIL import Image, ImageDraw


class StickFigureGenerator:
    """火柴人骨架生成器"""

    def __init__(self, width, height, line_width=4):
        self.width = width
        self.height = height
        self.line_width = line_width
        self.center_x = width // 2
        self.center_y = height // 2

    def create_canvas(self):
        """创建白底画布"""
        img = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(img)
        return img, draw

    def draw_circle(self, draw, x, y, radius):
        """画圆（头部）"""
        draw.ellipse([x - radius, y - radius, x + radius, y + radius],
                     outline='black', width=self.line_width)

    def draw_line(self, draw, x1, y1, x2, y2):
        """画线（身体/四肢）"""
        draw.line([x1, y1, x2, y2], fill='black', width=self.line_width)

    # ========== 行走图骨架生成 ==========

    def generate_walk_down(self, frame):
        """朝下行走（面向镜头）"""
        img, draw = self.create_canvas()
        base_y = self.center_y - 50
        head_y = base_y - 60
        self.draw_circle(draw, self.center_x, head_y, 25)
        body_top = base_y - 30
        body_bottom = base_y + 40
        self.draw_line(draw, self.center_x, body_top, self.center_x, body_bottom)

        if frame == 1 or frame == 3:
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x - 30, body_top + 40)
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x + 30, body_top + 40)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 15, body_bottom + 60)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x + 15, body_bottom + 60)
        elif frame == 2:
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x - 35, body_top + 50)
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x + 25, body_top + 30)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 20, body_bottom + 70)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x + 10, body_bottom + 50)
        else:
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x - 25, body_top + 30)
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x + 35, body_top + 50)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 10, body_bottom + 50)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x + 20, body_bottom + 70)
        return img

    def generate_walk_left(self, frame):
        """朝左行走（侧面视角）"""
        img, draw = self.create_canvas()
        base_y = self.center_y - 50
        head_y = base_y - 60
        self.draw_circle(draw, self.center_x, head_y, 25)
        body_top = base_y - 30
        body_bottom = base_y + 40
        self.draw_line(draw, self.center_x, body_top, self.center_x, body_bottom)
        if frame == 1 or frame == 3:
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x - 40, body_top + 35)
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x - 35, body_top + 40)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 20, body_bottom + 60)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 15, body_bottom + 60)
        elif frame == 2:
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x - 50, body_top + 20)
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x - 30, body_top + 50)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 30, body_bottom + 70)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 10, body_bottom + 50)
        else:
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x - 30, body_top + 50)
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x - 50, body_top + 20)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 10, body_bottom + 50)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 30, body_bottom + 70)
        return img

    def generate_walk_right(self, frame):
        """朝右行走（镜像左侧）"""
        return self.generate_walk_left(frame).transpose(Image.FLIP_LEFT_RIGHT)

    def generate_walk_up(self, frame):
        """朝上行走（背面视角）"""
        img, draw = self.create_canvas()
        base_y = self.center_y - 50
        head_y = base_y - 60
        self.draw_circle(draw, self.center_x, head_y, 25)
        body_top = base_y - 30
        body_bottom = base_y + 40
        self.draw_line(draw, self.center_x, body_top, self.center_x, body_bottom)
        if frame == 1 or frame == 3:
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x - 30, body_top + 40)
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x + 30, body_top + 40)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 15, body_bottom + 60)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x + 15, body_bottom + 60)
        elif frame == 2:
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x - 25, body_top + 30)
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x + 35, body_top + 50)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 20, body_bottom + 70)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x + 10, body_bottom + 50)
        else:
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x - 35, body_top + 50)
            self.draw_line(draw, self.center_x, body_top + 10, self.center_x + 25, body_top + 30)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 10, body_bottom + 50)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x + 20, body_bottom + 70)
        return img

    # ========== 战斗图骨架生成 ==========

    def generate_battle_idle(self, frame):
        """待机动作（轻微呼吸）"""
        img, draw = self.create_canvas()
        base_y = self.center_y + (frame % 2) * 3
        head_y = base_y - 80
        self.draw_circle(draw, self.center_x, head_y, 30)
        body_top = base_y - 40
        body_bottom = base_y + 60
        self.draw_line(draw, self.center_x, body_top, self.center_x, body_bottom)
        self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 40, body_top + 70)
        self.draw_line(draw, self.center_x, body_top + 15, self.center_x + 40, body_top + 70)
        self.draw_line(draw, self.center_x, body_bottom, self.center_x - 20, body_bottom + 80)
        self.draw_line(draw, self.center_x, body_bottom, self.center_x + 20, body_bottom + 80)
        return img

    def generate_battle_walk_in(self, frame):
        """入场动作（走向战斗位置）"""
        img, draw = self.create_canvas()
        base_y = self.center_y
        head_y = base_y - 80
        self.draw_circle(draw, self.center_x, head_y, 30)
        body_top = base_y - 40
        body_bottom = base_y + 60
        self.draw_line(draw, self.center_x, body_top, self.center_x, body_bottom)
        if frame % 2 == 1:
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 50, body_top + 60)
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x + 35, body_top + 40)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 30, body_bottom + 90)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x + 15, body_bottom + 70)
        else:
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 35, body_top + 40)
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x + 50, body_top + 60)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x - 15, body_bottom + 70)
            self.draw_line(draw, self.center_x, body_bottom, self.center_x + 30, body_bottom + 90)
        return img

    def generate_battle_attack(self, frame):
        """攻击动作（挥剑/挥拳）"""
        img, draw = self.create_canvas()
        base_y = self.center_y
        head_y = base_y - 80
        self.draw_circle(draw, self.center_x, head_y, 30)
        body_top = base_y - 40
        body_bottom = base_y + 60
        self.draw_line(draw, self.center_x, body_top, self.center_x, body_bottom)
        if frame <= 2:
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 60, body_top + 20)
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x + 30, body_top + 50)
        elif frame <= 4:
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x + 70, body_top - 10)
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 30, body_top + 50)
        else:
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x + 50, body_top + 60)
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 40, body_top + 70)
        self.draw_line(draw, self.center_x, body_bottom, self.center_x - 25, body_bottom + 80)
        self.draw_line(draw, self.center_x, body_bottom, self.center_x + 25, body_bottom + 80)
        return img

    def generate_battle_charge(self, frame):
        """蓄力动作（准备技能）"""
        img, draw = self.create_canvas()
        base_y = self.center_y
        head_y = base_y - 80
        self.draw_circle(draw, self.center_x, head_y, 30)
        body_top = base_y - 40
        body_bottom = base_y + 60
        lean = -5 if frame <= 3 else -10
        self.draw_line(draw, self.center_x, body_top, self.center_x + lean, body_bottom)
        arm_spread = 50 + frame * 5
        self.draw_line(draw, self.center_x, body_top + 15, self.center_x - arm_spread, body_top + 40)
        self.draw_line(draw, self.center_x, body_top + 15, self.center_x + arm_spread, body_top + 40)
        self.draw_line(draw, self.center_x + lean, body_bottom, self.center_x - 20, body_bottom + 80)
        self.draw_line(draw, self.center_x + lean, body_bottom, self.center_x + 20, body_bottom + 80)
        return img

    def generate_battle_skill(self, frame):
        """技能释放动作（8帧完整动作）"""
        img, draw = self.create_canvas()
        base_y = self.center_y
        head_y = base_y - 80
        self.draw_circle(draw, self.center_x, head_y, 30)
        body_top = base_y - 40
        body_bottom = base_y + 60
        self.draw_line(draw, self.center_x, body_top, self.center_x, body_bottom)
        if frame <= 2:
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 40, body_top - 20)
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x + 40, body_top - 20)
        elif frame <= 5:
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 80, body_top + 10)
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x + 80, body_top + 10)
        else:
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 50, body_top + 50)
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x + 50, body_top + 50)
        self.draw_line(draw, self.center_x, body_bottom, self.center_x - 20, body_bottom + 80)
        self.draw_line(draw, self.center_x, body_bottom, self.center_x + 20, body_bottom + 80)
        return img

    def generate_battle_guard(self, frame):
        """防御动作（举盾/格挡）"""
        img, draw = self.create_canvas()
        base_y = self.center_y
        head_y = base_y - 80
        self.draw_circle(draw, self.center_x, head_y, 30)
        body_top = base_y - 40
        body_bottom = base_y + 60
        self.draw_line(draw, self.center_x, body_top, self.center_x, body_bottom)
        self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 50, body_top - 10)
        self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 45, body_top + 5)
        self.draw_line(draw, self.center_x, body_bottom, self.center_x - 30, body_bottom + 80)
        self.draw_line(draw, self.center_x, body_bottom, self.center_x + 20, body_bottom + 80)
        return img

    def generate_battle_dodge(self, frame):
        """闪避动作（侧身躲避）"""
        img, draw = self.create_canvas()
        base_y = self.center_y
        head_y = base_y - 70
        offset = -30 if frame <= 2 else 30
        self.draw_circle(draw, self.center_x + offset, head_y, 30)
        body_top = base_y - 30
        body_bottom = base_y + 60
        self.draw_line(draw, self.center_x + offset, body_top, self.center_x + offset // 2, body_bottom)
        self.draw_line(draw, self.center_x + offset, body_top + 15, self.center_x + offset - 40, body_top + 40)
        self.draw_line(draw, self.center_x + offset, body_top + 15, self.center_x + offset + 40, body_top + 40)
        self.draw_line(draw, self.center_x + offset // 2, body_bottom, self.center_x - 20, body_bottom + 80)
        self.draw_line(draw, self.center_x + offset // 2, body_bottom, self.center_x + 20, body_bottom + 80)
        return img

    def generate_battle_hurt(self, frame):
        """受击动作（后仰）"""
        img, draw = self.create_canvas()
        base_y = self.center_y
        head_y = base_y - 70
        head_offset = -10 * frame
        self.draw_circle(draw, self.center_x + head_offset, head_y, 30)
        body_top = base_y - 30
        body_bottom = base_y + 60
        self.draw_line(draw, self.center_x + head_offset, body_top, self.center_x + head_offset // 2, body_bottom)
        self.draw_line(draw, self.center_x + head_offset, body_top + 15, self.center_x + head_offset - 50, body_top + 20)
        self.draw_line(draw, self.center_x + head_offset, body_top + 15, self.center_x + head_offset + 50, body_top + 20)
        self.draw_line(draw, self.center_x + head_offset // 2, body_bottom, self.center_x - 20, body_bottom + 80)
        self.draw_line(draw, self.center_x + head_offset // 2, body_bottom, self.center_x + 20, body_bottom + 80)
        return img

    def generate_battle_critical_hurt(self, frame):
        """重击受伤（更大幅度后仰）"""
        img, draw = self.create_canvas()
        base_y = self.center_y + frame * 10
        head_y = base_y - 60
        head_offset = -15 * frame
        self.draw_circle(draw, self.center_x + head_offset, head_y, 30)
        body_top = base_y - 20
        body_bottom = base_y + 60
        self.draw_line(draw, self.center_x + head_offset, body_top, self.center_x + head_offset // 3, body_bottom)
        self.draw_line(draw, self.center_x + head_offset, body_top + 15, self.center_x + head_offset - 60, body_top + 10)
        self.draw_line(draw, self.center_x + head_offset, body_top + 15, self.center_x + head_offset + 60, body_top + 10)
        self.draw_line(draw, self.center_x + head_offset // 3, body_bottom, self.center_x - 25, body_bottom + 80)
        self.draw_line(draw, self.center_x + head_offset // 3, body_bottom, self.center_x + 25, body_bottom + 80)
        return img

    def generate_battle_low_hp(self, frame):
        """低血量状态（虚弱喘息）"""
        img, draw = self.create_canvas()
        base_y = self.center_y + 20
        head_y = base_y - 60
        self.draw_circle(draw, self.center_x, head_y, 30)
        body_top = base_y - 30
        body_bottom = base_y + 50
        self.draw_line(draw, self.center_x, body_top, self.center_x + 5, body_bottom)
        self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 30, body_bottom + 30)
        self.draw_line(draw, self.center_x, body_top + 15, self.center_x + 30, body_bottom + 30)
        self.draw_line(draw, self.center_x + 5, body_bottom, self.center_x - 20, body_bottom + 70)
        self.draw_line(draw, self.center_x + 5, body_bottom, self.center_x + 20, body_bottom + 70)
        return img

    def generate_battle_dead(self, frame):
        """死亡动作（倒地）"""
        img, draw = self.create_canvas()
        if frame <= 3:
            base_y = self.center_y + frame * 30
            rotation = frame * 20
            head_y = base_y - 60 + frame * 15
            self.draw_circle(draw, self.center_x - rotation, head_y, 30)
            body_top = base_y - 30 + frame * 10
            body_bottom = base_y + 50
            self.draw_line(draw, self.center_x - rotation, body_top, self.center_x - rotation // 2, body_bottom)
            self.draw_line(draw, self.center_x - rotation, body_top + 15, self.center_x - rotation - 40, body_top + 40)
            self.draw_line(draw, self.center_x - rotation, body_top + 15, self.center_x - rotation + 40, body_top + 40)
            self.draw_line(draw, self.center_x - rotation // 2, body_bottom, self.center_x - 30, body_bottom + 60)
            self.draw_line(draw, self.center_x - rotation // 2, body_bottom, self.center_x + 30, body_bottom + 60)
        else:
            base_y = self.center_y + 80
            self.draw_circle(draw, self.center_x - 60, base_y, 30)
            self.draw_line(draw, self.center_x - 30, base_y, self.center_x + 50, base_y)
            self.draw_line(draw, self.center_x - 20, base_y, self.center_x - 30, base_y - 40)
            self.draw_line(draw, self.center_x + 30, base_y, self.center_x + 40, base_y + 40)
            self.draw_line(draw, self.center_x + 50, base_y, self.center_x + 70, base_y + 30)
            self.draw_line(draw, self.center_x + 50, base_y, self.center_x + 80, base_y - 20)
        return img

    def generate_battle_victory(self, frame):
        """胜利动作（庆祝）"""
        img, draw = self.create_canvas()
        base_y = self.center_y
        head_y = base_y - 80
        self.draw_circle(draw, self.center_x, head_y, 30)
        body_top = base_y - 40
        body_bottom = base_y + 60
        self.draw_line(draw, self.center_x, body_top, self.center_x, body_bottom)
        if frame <= 3:
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 50, body_top - 30)
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x + 50, body_top - 30)
        else:
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x - 40, body_top + 50)
            self.draw_line(draw, self.center_x, body_top + 15, self.center_x + 40, body_top + 50)
        self.draw_line(draw, self.center_x, body_bottom, self.center_x - 20, body_bottom + 80)
        self.draw_line(draw, self.center_x, body_bottom, self.center_x + 20, body_bottom + 80)
        return img

def generate_walk_skeletons(output_dir):
    """生成行走图骨架（16张）"""
    generator = StickFigureGenerator(512, 512, line_width=4)
    directions = ['down', 'left', 'right', 'up']
    count = 0
    for direction in directions:
        for frame in range(1, 5):
            filename = f"walk-{direction}-{frame}.png"
            filepath = output_dir / filename
            if direction == 'down':
                img = generator.generate_walk_down(frame)
            elif direction == 'left':
                img = generator.generate_walk_left(frame)
            elif direction == 'right':
                img = generator.generate_walk_right(frame)
            else:
                img = generator.generate_walk_up(frame)
            img.save(filepath)
            count += 1
            print(f"  [OK] {filename}")
    return count


def generate_battle_skeletons(output_dir):
    """生成战斗图骨架（57张）"""
    generator = StickFigureGenerator(768, 768, line_width=5)
    actions = {
        'idle': 4,
        'walk-in': 4,
        'attack': 6,
        'charge': 6,
        'skill': 8,
        'guard': 3,
        'dodge': 4,
        'hurt': 3,
        'critical-hurt': 4,
        'low-hp': 4,
        'dead': 5,
        'victory': 6,
    }
    count = 0
    for action, frames in actions.items():
        for frame in range(1, frames + 1):
            filename = f"battle-{action}-{frame}.png"
            filepath = output_dir / filename
            method_name = f"generate_battle_{action.replace('-', '_')}"
            method = getattr(generator, method_name)
            img = method(frame)
            img.save(filepath)
            count += 1
            print(f"  [OK] {filename}")
    return count


def main():
    parser = argparse.ArgumentParser(
        description='生成 ControlNet 骨架模板图（火柴人风格）'
    )
    parser.add_argument(
        '--type',
        choices=['walk', 'battle', 'all'],
        default='all',
        help='生成类型：walk=行走图(16张), battle=战斗图(57张), all=全部(73张)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='输出目录（默认：../prompts/controlnet/）'
    )
    args = parser.parse_args()

    if args.output:
        output_dir = Path(args.output)
    else:
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent / 'prompts' / 'controlnet'

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"输出目录: {output_dir}")
    print(f"生成类型: {args.type}")
    print("-" * 50)

    total_count = 0

    if args.type in ['walk', 'all']:
        print("\n生成行走图骨架...")
        count = generate_walk_skeletons(output_dir)
        total_count += count
        print(f"行走图完成: {count} 张")

    if args.type in ['battle', 'all']:
        print("\n生成战斗图骨架...")
        count = generate_battle_skeletons(output_dir)
        total_count += count
        print(f"战斗图完成: {count} 张")

    print("-" * 50)
    print(f"[OK] 总计生成: {total_count} 张骨架图")
    print(f"[OK] 保存位置: {output_dir}")


if __name__ == '__main__':
    main()