#!/usr/bin/env python3
"""
生成PWA图标
使用Pillow生成不同尺寸的图标
"""

import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("请安装Pillow: pip install Pillow")
    exit(1)

# 图标配置
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
OUTPUT_DIR = Path("app/static/icons")

# 颜色配置
PRIMARY_COLOR = (26, 115, 232)  # #1a73e8
SECONDARY_COLOR = (255, 255, 255)  # 白色
BACKGROUND_COLOR = (26, 115, 232)  # 蓝色背景

def create_icon(size, output_path):
    """创建指定尺寸的图标"""
    # 创建画布
    img = Image.new('RGBA', (size, size), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    
    # 计算文字大小
    font_size = size // 3
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            # 使用默认字体
            font = ImageFont.load_default()
    
    # 绘制文字 "CA"
    text = "CA"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 居中绘制
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - size // 10
    
    draw.text((x, y), text, fill=SECONDARY_COLOR, font=font)
    
    # 绘制装饰线条
    line_y = y + text_height + size // 20
    line_width = size // 3
    line_x = (size - line_width) // 2
    draw.line([(line_x, line_y), (line_x + line_width, line_y)], 
              fill=SECONDARY_COLOR, width=max(2, size // 50))
    
    # 保存图片
    img.save(output_path, 'PNG')
    print(f"[OK] Generated icon: {output_path} ({size}x{size})")

def main():
    """主函数"""
    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成各尺寸图标
    for size in ICON_SIZES:
        output_path = OUTPUT_DIR / f"icon-{size}x{size}.png"
        create_icon(size, output_path)
    
    print(f"\n[DONE] All icons generated, saved in: {OUTPUT_DIR}")
    print(f"  Total: {len(ICON_SIZES)} icons")

if __name__ == "__main__":
    main()
