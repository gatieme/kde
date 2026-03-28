#!/usr/bin/env python3
"""
修复 Excalidraw JSON 文件的对齐问题并重新生成 SVG
"""

import json
import os
import sys
from pathlib import Path

def fix_text_alignment(elements):
    """
    修复文本框的对齐问题
    - 文本应该居中于对应的矩形框内
    """
    # 首先收集所有矩形框
    rectangles = {}
    for el in elements:
        if el['type'] == 'rectangle' and 'id' in el:
            rectangles[el['id']] = {
                'x': el['x'],
                'y': el['y'],
                'width': el['width'],
                'height': el['height']
            }

    # 修复文本框
    fixed_texts = []
    for el in elements:
        if el['type'] == 'text' and 'id' in el:
            # 检查是否有关联的矩形框（通过 ID 命名约定）
            rect_id = el['id'].replace('-text', '')
            if rect_id in rectangles:
                rect = rectangles[rect_id]

                # 计算居中位置
                center_x = rect['x'] + rect['width'] / 2
                center_y = rect['y'] + rect['height'] / 2

                # 文本框的 x,y 应该是左上角，所以需要减去宽高的一半
                new_x = center_x - el['width'] / 2
                new_y = center_y - el['height'] / 2

                if abs(el['x'] - new_x) > 1 or abs(el['y'] - new_y) > 1:
                    fixed_texts.append({
                        'id': el['id'],
                        'old': (el['x'], el['y']),
                        'new': (new_x, new_y)
                    })
                    el['x'] = new_x
                    el['y'] = new_y

    return fixed_texts

def fix_arrow_coordinates(elements):
    """
    修复箭头坐标问题
    - 确保箭头正确连接到矩形框的边缘
    """
    # 收集所有形状的位置信息
    shapes = {}
    for el in elements:
        if el['type'] in ['rectangle', 'ellipse', 'diamond']:
            shapes[el['id']] = {
                'x': el['x'],
                'y': el['y'],
                'width': el['width'],
                'height': el['height'],
                'type': el['type']
            }

    fixed_arrows = []
    for el in elements:
        if el['type'] == 'arrow':
            # 检查是否有绑定
            if 'startBinding' in el and 'endBinding' in el:
                start_id = el['startBinding'].get('elementId')
                end_id = el['endBinding'].get('elementId')

                if start_id in shapes and end_id in shapes:
                    start_shape = shapes[start_id]
                    end_shape = shapes[end_id]

                    # 计算正确的起点和终点
                    # 对于垂直布局，箭头从上一个形状的底部到下一个形状的顶部
                    start_x = start_shape['x'] + start_shape['width'] / 2
                    start_y = start_shape['y'] + start_shape['height']
                    end_x = end_shape['x'] + end_shape['width'] / 2
                    end_y = end_shape['y']

                    # 计算相对坐标
                    new_x = start_x
                    new_y = start_y
                    new_points = [[0, 0], [end_x - start_x, end_y - start_y]]

                    if (abs(el['x'] - new_x) > 1 or
                        abs(el['y'] - new_y) > 1 or
                        abs(el['points'][1][0] - new_points[1][0]) > 1 or
                        abs(el['points'][1][1] - new_points[1][1]) > 1):

                        fixed_arrows.append({
                            'id': el['id'],
                            'old': (el['x'], el['y'], el['points']),
                            'new': (new_x, new_y, new_points)
                        })
                        el['x'] = new_x
                        el['y'] = new_y
                        el['points'] = new_points

    return fixed_arrows

def generate_svg_from_excalidraw(json_file, svg_file):
    """
    从 Excalidraw JSON 生成正确的 SVG
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    elements = data.get('elements', [])

    # 计算边界
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')

    for el in elements:
        if el['type'] in ['rectangle', 'ellipse', 'text']:
            x = el['x']
            y = el['y']
            w = el.get('width', 0)
            h = el.get('height', 0)

            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)

        elif el['type'] == 'arrow':
            # 计算箭头的实际端点
            start_x = el['x']
            start_y = el['y']
            end_x = el['x'] + el['points'][1][0]
            end_y = el['y'] + el['points'][1][1]

            min_x = min(min_x, start_x, end_x)
            min_y = min(min_y, start_y, end_y)
            max_x = max(max_x, start_x, end_x)
            max_y = max(max_y, start_y, end_y)

    # 添加边距
    margin = 50
    width = max_x - min_x + 2 * margin
    height = max_y - min_y + 2 * margin
    view_x = min_x - margin
    view_y = min_y - margin

    # 生成 SVG
    svg_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_x} {view_y} {width} {height}" width="{width}" height="{height}">',
        '  <style>',
        '    .handwritten { font-family: "Comic Sans MS", "Chalkboard SE", "Marker Felt", cursive; }',
        '    .rectangle { fill: #ffffff; stroke: #000000; stroke-width: 2; }',
        '    .ellipse { fill: #ffffff; stroke: #000000; stroke-width: 2; }',
        '    .diamond { fill: #ffffff; stroke: #000000; stroke-width: 2; }',
        '    .arrow { stroke: #000000; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }',
        '    .text { fill: #000000; font-size: 16px; }',
        '  </style>',
        '  <defs>',
        '    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">',
        '      <polygon points="0 0, 10 3, 0 6" fill="#000000"/>',
        '    </marker>',
        '  </defs>'
    ]

    # 按顺序渲染元素
    for el in elements:
        if el['type'] == 'rectangle':
            fill = el.get('backgroundColor', '#ffffff')
            stroke = el.get('strokeColor', '#000000')
            stroke_width = el.get('strokeWidth', 2)
            svg_lines.append(
                f'  <rect x="{el["x"]}" y="{el["y"]}" width="{el["width"]}" height="{el["height"]}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
            )

        elif el['type'] == 'ellipse':
            fill = el.get('backgroundColor', '#ffffff')
            stroke = el.get('strokeColor', '#000000')
            stroke_width = el.get('strokeWidth', 2)
            cx = el['x'] + el['width'] / 2
            cy = el['y'] + el['height'] / 2
            rx = el['width'] / 2
            ry = el['height'] / 2
            svg_lines.append(
                f'  <ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
            )

        elif el['type'] == 'text':
            text = el.get('text', '').replace('\n', '<br/>')
            fill = el.get('strokeColor', '#000000')
            font_size = el.get('fontSize', 16)
            # 计算文本的基线位置（垂直居中）
            baseline = el['y'] + el['height'] / 2 + font_size / 3
            svg_lines.append(
                f'  <text x="{el["x"]}" y="{baseline}" class="handwritten" '
                f'fill="{fill}" font-size="{font_size}px">{text}</text>'
            )

        elif el['type'] == 'arrow':
            stroke = el.get('strokeColor', '#000000')
            stroke_width = el.get('strokeWidth', 2)
            # 计算实际的起点和终点
            start_x = el['x']
            start_y = el['y']
            end_x = el['x'] + el['points'][1][0]
            end_y = el['y'] + el['points'][1][1]
            svg_lines.append(
                f'  <path d="M {start_x} {start_y} L {end_x} {end_y}" '
                f'stroke="{stroke}" stroke-width="{stroke_width}" fill="none" marker-end="url(#arrowhead)"/>'
            )

    svg_lines.append('</svg>')

    with open(svg_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg_lines))

def fix_excalidraw_file(json_path):
    """
    修复单个 Excalidraw JSON 文件
    """
    print(f"\n处理文件: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    elements = data.get('elements', [])

    # 修复文本对齐
    fixed_texts = fix_text_alignment(elements)
    if fixed_texts:
        print(f"  修复了 {len(fixed_texts)} 个文本框的对齐:")
        for fix in fixed_texts:
            print(f"    - {fix['id']}: ({fix['old'][0]:.1f}, {fix['old'][1]:.1f}) -> ({fix['new'][0]:.1f}, {fix['new'][1]:.1f})")
    else:
        print("  文本框对齐正常，无需修复")

    # 修复箭头坐标
    fixed_arrows = fix_arrow_coordinates(elements)
    if fixed_arrows:
        print(f"  修复了 {len(fixed_arrows)} 个箭头的坐标:")
        for fix in fixed_arrows:
            print(f"    - {fix['id']}: ({fix['old'][0]:.1f}, {fix['old'][1]:.1f}) -> ({fix['new'][0]:.1f}, {fix['new'][1]:.1f})")
    else:
        print("  箭头坐标正常，无需修复")

    # 保存修复后的 JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # 生成 SVG
    svg_path = str(json_path).replace('.json', '.svg')
    generate_svg_from_excalidraw(str(json_path), svg_path)
    print(f"  生成 SVG: {svg_path}")

    return len(fixed_texts) + len(fixed_arrows)

def main():
    diagrams_dir = Path('/home/chengjian/Work/GitHub/people/kde/diagrams')

    # 查找所有 .excalidraw.json 文件
    json_files = list(diagrams_dir.glob('*.excalidraw.json'))

    if not json_files:
        print("未找到任何 .excalidraw.json 文件")
        return

    print(f"找到 {len(json_files)} 个 Excalidraw 文件")

    total_fixes = 0
    for json_file in sorted(json_files):
        try:
            fixes = fix_excalidraw_file(json_file)
            total_fixes += fixes
        except Exception as e:
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n总计: 修复了 {total_fixes} 个元素")

if __name__ == '__main__':
    main()
