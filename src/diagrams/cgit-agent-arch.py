#!/usr/bin/env python3
"""生成 CGit Agent 架构图 HTML 文件 (Style 1 Flat Icon, 深色/浅色主题切换)"""

import os

# ===== 样式参数 =====
STYLE = {
    # 浅色主题
    "light": {
        "bg": "#ffffff",
        "box_fill": "#ffffff",
        "box_stroke": "#d1d5db",
        "text_primary": "#111827",
        "text_secondary": "#6b7280",
    },
    # 深色主题
    "dark": {
        "bg": "#0f0f1a",
        "box_fill": "#1a1a2e",
        "box_stroke": "#4a4a6a",
        "text_primary": "#e0e0e0",
        "text_secondary": "#8888aa",
    },
}

# 色标颜色 (不随主题变化)
COLORS = {
    "blue": "#2563eb",       # 主流程 / 模型调用
    "red": "#dc2626",        # 跨 Agent 调用
    "green": "#16a34a",      # 数据输出
    "purple": "#9333ea",     # 外部工具 / Link 提取
    "orange": "#ea580c",     # 外部工具 wget
}

FONT = "'Helvetica Neue', Helvetica, Arial, 'PingFang SC', sans-serif"

# ===== SVG 尺寸 =====
VB_W = 960
VB_H = 700

# ===== 布局参数 =====
# 主 workflow 节点 (居中, x=330, width=220)
MAIN_X = 330
MAIN_W = 220
NODE_H = 48
NODE_GAP = 14  # 节点间纵向间距 (含箭头)

# 各节点 y 坐标
nodes = [
    ("fetch_commit",    "wget 从 git.kernel.org 下载 patch",          COLORS["orange"]),
    ("parse_commit",    "正则提取 Subject / Date / From",             COLORS["blue"]),
    ("analyze_commit",  "ModelInference → summary + analysis",        COLORS["blue"]),
    ("output_results",  "Markdown 表格输出",                           COLORS["green"]),
    ("check_patchset",  "提取 Link 字段 (lore.kernel.org URL)",       COLORS["purple"]),
    ("run_lkml_analysis", "跨 Agent → run_lkml_agent()",              COLORS["red"]),
]

# 计算各节点 y
TITLE_Y = 24
node_ys = []
y_start = TITLE_Y + 26
for i in range(len(nodes)):
    node_ys.append(y_start + i * (NODE_H + NODE_GAP))

# LKML 缩略框位置 (右侧)
LKML_X = 620
LKML_Y = node_ys[5] - 5
LKML_W = 260
LKML_H = 60

# END 圆圈位置 (在 run_lkml_analysis 下方)
END_Y = node_ys[5] + NODE_H + 26

# 依赖层 (底部, 在 END 之后留出足够空间)
DEP_Y = END_Y + 30
dep_items = [
    ("wget (CLI)",             COLORS["orange"]),
    ("ModelInference",         COLORS["blue"]),
    ("ModelRequest",           COLORS["blue"]),
    ("format_text_for_markdown", COLORS["green"]),
    ("clean_email_subject",    COLORS["green"]),
    ("monitor_process",        COLORS["purple"]),
    ("lkml.lkml_agent",       COLORS["red"]),
]

DEP_W = 110
DEP_H = 36
DEP_GAP = 12
dep_total_w = len(dep_items) * (DEP_W + DEP_GAP) - DEP_GAP
dep_x_start = (VB_W - dep_total_w) // 2

# 图例位置
LEGEND_Y = DEP_Y + DEP_H + 20

# ===== 构建 SVG 行 =====
lines = []

lines.append(f'<svg id="archSvg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VB_W} {VB_H}" width="{VB_W}" height="{VB_H}">')

# SVG 内嵌 CSS (用 CSS 变量实现主题切换)
lines.append('<style>')
lines.append(f'  text {{ font-family: {FONT}; }}')
lines.append('  /* 主题 CSS 变量 */')
lines.append('  .theme-light {')
lines.append(f'    --bg: {STYLE["light"]["bg"]};')
lines.append(f'    --box-fill: {STYLE["light"]["box_fill"]};')
lines.append(f'    --box-stroke: {STYLE["light"]["box_stroke"]};')
lines.append(f'    --text-primary: {STYLE["light"]["text_primary"]};')
lines.append(f'    --text-secondary: {STYLE["light"]["text_secondary"]};')
lines.append('  }')
lines.append('  .theme-dark {')
lines.append(f'    --bg: {STYLE["dark"]["bg"]};')
lines.append(f'    --box-fill: {STYLE["dark"]["box_fill"]};')
lines.append(f'    --box-stroke: {STYLE["dark"]["box_stroke"]};')
lines.append(f'    --text-primary: {STYLE["dark"]["text_primary"]};')
lines.append(f'    --text-secondary: {STYLE["dark"]["text_secondary"]};')
lines.append('  }')
lines.append('  .svg-bg { fill: var(--bg); }')
lines.append('  .node-box { fill: var(--box-fill); stroke: var(--box-stroke); stroke-width: 1.5; }')
lines.append('  .node-text { fill: var(--text-primary); }')
lines.append('  .node-desc { fill: var(--text-secondary); }')
lines.append('  .lkml-box-bg { fill: var(--box-fill); }')
lines.append('  .lkml-box-stroke { stroke: var(--box-stroke); }')
lines.append('  .dep-box { fill: var(--box-fill); stroke: var(--box-stroke); stroke-width: 1; }')
lines.append('  .legend-bg { fill: var(--box-fill); stroke: var(--box-stroke); }')
lines.append('  .legend-text { fill: var(--text-secondary); }')
lines.append('  .legend-title { fill: var(--text-primary); }')
lines.append('</style>')

# defs: 箭头 marker
lines.append('<defs>')
for color_name, color_val in COLORS.items():
    marker_id = f"arrow-{color_name}"
    lines.append(f'  <marker id="{marker_id}" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">')
    lines.append(f'    <polygon points="0 0, 10 3.5, 0 7" fill="{color_val}"/>')
    lines.append(f'  </marker>')
# 红色虚线箭头
lines.append(f'  <marker id="arrow-red-dash" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">')
lines.append(f'    <polygon points="0 0, 10 3.5, 0 7" fill="{COLORS["red"]}"/>')
lines.append(f'  </marker>')
lines.append('</defs>')

# 背景
lines.append(f'<rect class="svg-bg" x="0" y="0" width="{VB_W}" height="{VB_H}" rx="8"/>')

# 标题
lines.append(f'<text class="node-text" x="{VB_W // 2}" y="{TITLE_Y}" font-size="18" font-weight="700" text-anchor="middle">CGit Agent 架构</text>')
lines.append(f'<text class="node-desc" x="{VB_W // 2}" y="{TITLE_Y + 16}" font-size="11" text-anchor="middle">LangGraph Workflow — 7 Nodes + 跨 Agent 联动</text>')

# ===== 主 Workflow 节点 =====
for i, (name, desc, color) in enumerate(nodes):
    y = node_ys[i]
    cx = MAIN_X + MAIN_W // 2

    # 节点外框
    lines.append(f'<g>')
    lines.append(f'  <rect class="node-box" x="{MAIN_X}" y="{y}" width="{MAIN_W}" height="{NODE_H}" rx="8"/>')
    # 色标条 (左侧 4px 宽色带)
    lines.append(f'  <rect x="{MAIN_X}" y="{y}" width="4" height="{NODE_H}" rx="2" fill="{color}"/>')
    # 节点名
    lines.append(f'  <text class="node-text" x="{cx + 2}" y="{y + 20}" font-size="13" font-weight="600" text-anchor="middle">{name}</text>')
    # 描述
    lines.append(f'  <text class="node-desc" x="{cx + 2}" y="{y + 38}" font-size="10" text-anchor="middle">{desc}</text>')
    lines.append(f'</g>')

# ===== 主流程箭头 (蓝色) =====
for i in range(len(nodes) - 1):
    y1 = node_ys[i] + NODE_H
    y2 = node_ys[i + 1]
    cx = MAIN_X + MAIN_W // 2
    lines.append(f'<line x1="{cx}" y1="{y1}" x2="{cx}" y2="{y2}" stroke="{COLORS["blue"]}" stroke-width="2" marker-end="url(#arrow-blue)"/>')

# ===== 特殊标注 =====
# output_results → check_patchset 之间标注 "先输出再检查"
arrow_y_mid = (node_ys[3] + NODE_H + node_ys[4]) // 2
lines.append(f'<text class="node-desc" x="{MAIN_X + MAIN_W // 2 + 12}" y="{arrow_y_mid}" font-size="9" text-anchor="start" fill="{COLORS["green"]}">先输出再检查</text>')

# run_lkml_analysis 旁标注条件 (在节点和 END 之间的区域)
cond_y = node_ys[5] + NODE_H + 6
lines.append(f'<text class="node-desc" x="{MAIN_X}" y="{cond_y}" font-size="9" text-anchor="start" fill="{COLORS["red"]}" font-style="italic">if has_patchset=True</text>')
lines.append(f'<text class="node-desc" x="{MAIN_X + MAIN_W}" y="{cond_y}" font-size="9" text-anchor="end" fill="{COLORS["red"]}" font-style="italic">无 patchset → END</text>')

# ===== LKML Agent 缩略框 (右侧) =====
lkml_inner_x = LKML_X + 12
lkml_inner_y = LKML_Y + 22
lkml_mini_w = 50
lkml_mini_h = 22
lkml_mini_gap = 14

lines.append(f'<g>')
lines.append(f'  <rect class="lkml-box-bg" x="{LKML_X}" y="{LKML_Y}" width="{LKML_W}" height="{LKML_H}" rx="10" stroke="{COLORS["red"]}" stroke-width="1.5" stroke-dasharray="6,3"/>')
lines.append(f'  <text class="node-text" x="{LKML_X + LKML_W // 2}" y="{LKML_Y + 14}" font-size="11" font-weight="600" text-anchor="middle" fill="{COLORS["red"]}">LKML Agent (被 CGit 联动触发)</text>')

# LKML 内部小节点
mini_nodes = ["fetch", "parse", "analyze", "output"]
mini_colors = [COLORS["blue"], COLORS["blue"], COLORS["blue"], COLORS["green"]]
mini_x_positions = []
for j, mn in enumerate(mini_nodes):
    mc = mini_colors[j]
    mx = lkml_inner_x + j * (lkml_mini_w + lkml_mini_gap)
    mini_x_positions.append(mx)
    lines.append(f'  <rect x="{mx}" y="{lkml_inner_y}" width="{lkml_mini_w}" height="{lkml_mini_h}" rx="4" fill="var(--box-fill)" stroke="{mc}" stroke-width="1"/>')
    lines.append(f'  <text class="node-desc" x="{mx + lkml_mini_w // 2}" y="{lkml_inner_y + 15}" font-size="8" text-anchor="middle" fill="{mc}">{mn}</text>')

# LKML 小箭头
for j in range(len(mini_nodes) - 1):
    ax1 = mini_x_positions[j] + lkml_mini_w
    ax2 = mini_x_positions[j + 1]
    ay = lkml_inner_y + lkml_mini_h // 2
    lines.append(f'  <line x1="{ax1}" y1="{ay}" x2="{ax2}" y2="{ay}" stroke="{COLORS["blue"]}" stroke-width="1" marker-end="url(#arrow-blue)"/>')

lines.append(f'</g>')

# ===== 红色虚线箭头: run_lkml_analysis → LKML Agent =====
arrow_start_x = MAIN_X + MAIN_W
arrow_start_y = node_ys[5] + NODE_H // 2
arrow_end_x = LKML_X
arrow_end_y = LKML_Y + LKML_H // 2
lines.append(f'<line x1="{arrow_start_x}" y1="{arrow_start_y}" x2="{arrow_end_x}" y2="{arrow_end_y}" stroke="{COLORS["red"]}" stroke-width="2" stroke-dasharray="6,3" marker-end="url(#arrow-red-dash)"/>')
lines.append(f'<text class="node-desc" x="{(arrow_start_x + arrow_end_x) // 2}" y="{arrow_start_y - 8}" font-size="9" text-anchor="middle" fill="{COLORS["red"]}">跨 Agent 联动</text>')

# ===== 依赖层 (底部) =====
dep_section_title_y = DEP_Y
lines.append(f'<text class="node-text" x="{VB_W // 2}" y="{dep_section_title_y}" font-size="12" font-weight="600" text-anchor="middle">依赖层</text>')
# 分隔线
lines.append(f'<line x1="60" y1="{dep_section_title_y + 6}" x2="{VB_W - 60}" y2="{dep_section_title_y + 6}" stroke="var(--box-stroke)" stroke-width="0.5" stroke-dasharray="4,2"/>')

dep_box_y = dep_section_title_y + 12
for i, (dep_name, dep_color) in enumerate(dep_items):
    dx = dep_x_start + i * (DEP_W + DEP_GAP)
    dcx = dx + DEP_W // 2
    lines.append(f'<g>')
    lines.append(f'  <rect class="dep-box" x="{dx}" y="{dep_box_y}" width="{DEP_W}" height="{DEP_H}" rx="6"/>')
    lines.append(f'  <rect x="{dx}" y="{dep_box_y}" width="3" height="{DEP_H}" rx="1" fill="{dep_color}"/>')
    lines.append(f'  <text class="node-desc" x="{dcx + 1}" y="{dep_box_y + DEP_H // 2 + 4}" font-size="9" text-anchor="middle">{dep_name}</text>')
    lines.append(f'</g>')

# ===== 图例 =====
legend_x = 60
legend_w = VB_W - 120
legend_h = 40
legend_box_y = LEGEND_Y

lines.append(f'<g>')
lines.append(f'  <rect class="legend-bg" x="{legend_x}" y="{legend_box_y}" width="{legend_w}" height="{legend_h}" rx="6"/>')
lines.append(f'  <text class="legend-title" x="{legend_x + 12}" y="{legend_box_y + 14}" font-size="10" font-weight="700">图例</text>')

# 图例项
legend_items = [
    ("主流程", COLORS["blue"], "solid"),
    ("跨 Agent", COLORS["red"], "dashed"),
    ("数据输出", COLORS["green"], "solid"),
    ("外部工具", COLORS["orange"], "solid"),
    ("Link 提取", COLORS["purple"], "solid"),
]

lx = legend_x + 50
for lname, lcolor, lstyle in legend_items:
    if lstyle == "solid":
        lines.append(f'  <line x1="{lx}" y1="{legend_box_y + 25}" x2="{lx + 24}" y2="{legend_box_y + 25}" stroke="{lcolor}" stroke-width="2"/>')
    else:
        lines.append(f'  <line x1="{lx}" y1="{legend_box_y + 25}" x2="{lx + 24}" y2="{legend_box_y + 25}" stroke="{lcolor}" stroke-width="2" stroke-dasharray="4,2"/>')
    lines.append(f'  <circle cx="{lx + 3}" cy="{legend_box_y + 25}" r="3" fill="{lcolor}"/>')
    lines.append(f'  <text class="legend-text" x="{lx + 30}" y="{legend_box_y + 29}" font-size="9">{lname}</text>')
    lx += 100

lines.append(f'</g>')

# ===== 状态类标注 (右上角小框) =====
state_x = 620
state_y = node_ys[0]
state_w = 260
state_h = 90

lines.append(f'<g>')
lines.append(f'  <rect class="node-box" x="{state_x}" y="{state_y}" width="{state_w}" height="{state_h}" rx="8"/>')
lines.append(f'  <rect x="{state_x}" y="{state_y}" width="3" height="{state_h}" rx="1" fill="{COLORS["blue"]}"/>')
lines.append(f'  <text class="node-text" x="{state_x + state_w // 2}" y="{state_y + 16}" font-size="11" font-weight="600" text-anchor="middle">CGitAgentState</text>')

state_fields = [
    "commit_id, commit_file, date",
    "author, email, subject, web_url",
    "content, summary, analysis",
    "patchset_link, has_patchset",
]
for si, sf in enumerate(state_fields):
    lines.append(f'  <text class="node-desc" x="{state_x + 14}" y="{state_y + 34 + si * 14}" font-size="9" text-anchor="start">{sf}</text>')

lines.append(f'</g>')

# ===== END 标记 =====
end_y = END_Y
end_cx = MAIN_X + MAIN_W // 2
# 箭头从 run_lkml_analysis 到 END
lines.append(f'<line x1="{end_cx}" y1="{node_ys[5] + NODE_H}" x2="{end_cx}" y2="{end_y - 12}" stroke="{COLORS["blue"]}" stroke-width="2" marker-end="url(#arrow-blue)"/>')
# END 圆
lines.append(f'<circle cx="{end_cx}" cy="{end_y}" r="10" fill="var(--box-fill)" stroke="{COLORS["blue"]}" stroke-width="2"/>')
lines.append(f'<text class="node-text" x="{end_cx}" y="{end_y + 4}" font-size="10" font-weight="700" text-anchor="middle">END</text>')

lines.append('</svg>')

svg_content = '\n'.join(lines)

# ===== 构建 HTML =====
html_lines = []
html_lines.append('<!DOCTYPE html>')
html_lines.append('<html lang="zh-CN">')
html_lines.append('<head>')
html_lines.append('<meta charset="UTF-8">')
html_lines.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
html_lines.append('<title>CGit Agent 架构 — 扁平图标风格</title>')
html_lines.append('<style>')
html_lines.append('  * { margin: 0; padding: 0; box-sizing: border-box; }')

# 浅色默认
html_lines.append('  body {')
html_lines.append(f'    background: {STYLE["light"]["bg"]};')
html_lines.append(f'    color: {STYLE["light"]["text_primary"]};')
html_lines.append(f'    font-family: {FONT};')
html_lines.append('    min-height: 100vh;')
html_lines.append('    display: flex;')
html_lines.append('    flex-direction: column;')
html_lines.append('    align-items: center;')
html_lines.append('    padding: 24px;')
html_lines.append('    transition: background 0.3s, color 0.3s;')
html_lines.append('  }')

# 深色主题
html_lines.append('  body.dark {')
html_lines.append(f'    background: {STYLE["dark"]["bg"]};')
html_lines.append(f'    color: {STYLE["dark"]["text_primary"]};')
html_lines.append('  }')

# 工具栏
html_lines.append('  .toolbar {')
html_lines.append('    display: flex;')
html_lines.append('    gap: 10px;')
html_lines.append('    margin-bottom: 16px;')
html_lines.append('    padding: 10px 16px;')
html_lines.append('    background: var(--toolbar-bg, #ffffff);')
html_lines.append('    border: 1px solid var(--toolbar-border, #e2e8f0);')
html_lines.append('    border-radius: 10px;')
html_lines.append('    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);')
html_lines.append('    width: 100%;')
html_lines.append('    max-width: 1000px;')
html_lines.append('    justify-content: center;')
html_lines.append('    transition: background 0.3s, border-color 0.3s;')
html_lines.append('  }')
html_lines.append('  body.dark .toolbar {')
html_lines.append(f'    background: {STYLE["dark"]["box_fill"]};')
html_lines.append(f'    border-color: {STYLE["dark"]["box_stroke"]};')
html_lines.append('  }')

html_lines.append('  .toolbar button {')
html_lines.append(f'    font-family: {FONT};')
html_lines.append('    font-size: 13px;')
html_lines.append('    font-weight: 500;')
html_lines.append('    padding: 8px 16px;')
html_lines.append('    border: 1px solid #d1d5db;')
html_lines.append('    border-radius: 8px;')
html_lines.append('    background: #f8fafc;')
html_lines.append('    color: #475569;')
html_lines.append('    cursor: pointer;')
html_lines.append('    transition: all 0.2s;')
html_lines.append('    display: flex;')
html_lines.append('    align-items: center;')
html_lines.append('    gap: 6px;')
html_lines.append('  }')
html_lines.append('  .toolbar button:hover {')
html_lines.append('    background: #2563eb;')
html_lines.append('    border-color: #2563eb;')
html_lines.append('    color: #ffffff;')
html_lines.append('    transform: translateY(-1px);')
html_lines.append('  }')
html_lines.append('  body.dark .toolbar button {')
html_lines.append(f'    background: {STYLE["dark"]["box_fill"]};')
html_lines.append(f'    border-color: {STYLE["dark"]["box_stroke"]};')
html_lines.append(f'    color: {STYLE["dark"]["text_primary"]};')
html_lines.append('  }')
html_lines.append('  body.dark .toolbar button:hover {')
html_lines.append('    background: #2563eb;')
html_lines.append('    color: #ffffff;')
html_lines.append('  }')

# 主题切换按钮特殊样式
html_lines.append('  .toolbar button.theme-btn {')
html_lines.append('    background: #2563eb;')
html_lines.append('    color: #ffffff;')
html_lines.append('    border-color: #2563eb;')
html_lines.append('    font-weight: 600;')
html_lines.append('  }')
html_lines.append('  .toolbar button.theme-btn:hover {')
html_lines.append('    background: #1d4ed8;')
html_lines.append('    border-color: #1d4ed8;')
html_lines.append('  }')
html_lines.append('  body.dark .toolbar button.theme-btn {')
html_lines.append('    background: #f59e0b;')
html_lines.append('    color: #111827;')
html_lines.append('    border-color: #f59e0b;')
html_lines.append('  }')
html_lines.append('  body.dark .toolbar button.theme-btn:hover {')
html_lines.append('    background: #d97706;')
html_lines.append('    border-color: #d97706;')
html_lines.append('  }')

# SVG 容器
html_lines.append('  .svg-container {')
html_lines.append('    width: 100%;')
html_lines.append('    max-width: 1000px;')
html_lines.append('    background: #ffffff;')
html_lines.append('    border: 1px solid #e2e8f0;')
html_lines.append('    border-radius: 12px;')
html_lines.append('    padding: 20px;')
html_lines.append('    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);')
html_lines.append('    transition: background 0.3s, border-color 0.3s, box-shadow 0.3s;')
html_lines.append('  }')
html_lines.append('  body.dark .svg-container {')
html_lines.append(f'    background: {STYLE["dark"]["box_fill"]};')
html_lines.append(f'    border-color: {STYLE["dark"]["box_stroke"]};')
html_lines.append('    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);')
html_lines.append('  }')
html_lines.append('  .svg-container svg {')
html_lines.append('    width: 100%;')
html_lines.append('    height: auto;')
html_lines.append('  }')

# Footer
html_lines.append('  .footer {')
html_lines.append('    margin-top: 16px;')
html_lines.append('    font-size: 12px;')
html_lines.append('    color: #6b7280;')
html_lines.append('    text-align: center;')
html_lines.append('    transition: color 0.3s;')
html_lines.append('  }')
html_lines.append('  body.dark .footer {')
html_lines.append(f'    color: {STYLE["dark"]["text_secondary"]};')
html_lines.append('  }')

# Toast
html_lines.append('  .toast {')
html_lines.append('    position: fixed;')
html_lines.append('    bottom: 30px;')
html_lines.append('    left: 50%;')
html_lines.append('    transform: translateX(-50%) translateY(100px);')
html_lines.append('    background: #ffffff;')
html_lines.append('    border: 1px solid #e2e8f0;')
html_lines.append('    border-radius: 10px;')
html_lines.append('    padding: 12px 24px;')
html_lines.append('    color: #1e293b;')
html_lines.append(f'    font-family: {FONT};')
html_lines.append('    font-size: 13px;')
html_lines.append('    z-index: 1000;')
html_lines.append('    transition: transform 0.3s, opacity 0.3s, background 0.3s;')
html_lines.append('    opacity: 0;')
html_lines.append('    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);')
html_lines.append('  }')
html_lines.append('  .toast.show {')
html_lines.append('    transform: translateX(-50%) translateY(0);')
html_lines.append('    opacity: 1;')
html_lines.append('  }')
html_lines.append('  body.dark .toast {')
html_lines.append(f'    background: {STYLE["dark"]["box_fill"]};')
html_lines.append(f'    border-color: {STYLE["dark"]["box_stroke"]};')
html_lines.append(f'    color: {STYLE["dark"]["text_primary"]};')
html_lines.append('  }')

html_lines.append('</style>')
html_lines.append('</head>')
html_lines.append('<body>')

# 工具栏
html_lines.append('<div class="toolbar">')
html_lines.append('  <button class="theme-btn" onclick="toggleTheme()" id="themeBtn" title="切换深色/浅色主题">☀️ 浅色</button>')
html_lines.append('  <button onclick="copySVG()" title="复制 SVG 到剪贴板">📋 Copy</button>')
html_lines.append('  <button onclick="exportPNG()" title="导出 PNG">🖼️ PNG</button>')
html_lines.append('  <button onclick="exportSVG()" title="导出 SVG">📄 SVG</button>')
html_lines.append('</div>')

# SVG 容器
html_lines.append('<div class="svg-container" id="svgContainer">')
html_lines.append(svg_content)
html_lines.append('</div>')

# Footer
html_lines.append('<div class="footer">')
html_lines.append('CGit Agent Architecture • Style 1 Flat Icon • LangGraph 7 Nodes + LKML 联动')
html_lines.append('</div>')

# Toast
html_lines.append('<div class="toast" id="toast"></div>')

# JavaScript
html_lines.append('<script>')
# 主题切换
html_lines.append('let isDark = false;')
html_lines.append('function toggleTheme() {')
html_lines.append('  isDark = !isDark;')
html_lines.append('  const body = document.body;')
html_lines.append('  const btn = document.getElementById("themeBtn");')
html_lines.append('  const svg = document.getElementById("archSvg");')
html_lines.append('  if (isDark) {')
html_lines.append('    body.classList.add("dark");')
html_lines.append('    btn.textContent = "🌙 深色";')
html_lines.append('    svg.classList.remove("theme-light");')
html_lines.append('    svg.classList.add("theme-dark");')
html_lines.append('  } else {')
html_lines.append('    body.classList.remove("dark");')
html_lines.append('    btn.textContent = "☀️ 浅色";')
html_lines.append('    svg.classList.remove("theme-dark");')
html_lines.append('    svg.classList.add("theme-light");')
html_lines.append('  }')
html_lines.append('}')

# 初始化 SVG 主题类
html_lines.append('// 初始化为浅色主题')
html_lines.append('document.getElementById("archSvg").classList.add("theme-light");')

# Toast
html_lines.append('function showToast(msg) {')
html_lines.append('  const toast = document.getElementById("toast");')
html_lines.append('  toast.textContent = msg;')
html_lines.append('  toast.classList.add("show");')
html_lines.append('  setTimeout(() => toast.classList.remove("show"), 2000);')
html_lines.append('}')

# Copy SVG
html_lines.append('function copySVG() {')
html_lines.append('  const svg = document.querySelector("svg");')
html_lines.append('  const svgData = new XMLSerializer().serializeToString(svg);')
html_lines.append('  navigator.clipboard.writeText(svgData).then(() => {')
html_lines.append('    showToast("✅ SVG 已复制到剪贴板");')
html_lines.append('  });')
html_lines.append('}')

# Export PNG
html_lines.append('function exportPNG() {')
html_lines.append('  const svg = document.querySelector("svg");')
html_lines.append('  const svgData = new XMLSerializer().serializeToString(svg);')
html_lines.append('  const canvas = document.createElement("canvas");')
html_lines.append('  canvas.width = 1920;')
html_lines.append('  canvas.height = 1400;')
html_lines.append('  const ctx = canvas.getContext("2d");')
html_lines.append('  const img = new Image();')
html_lines.append('  img.onload = function() {')
html_lines.append('    const bg = isDark ? "#0f0f1a" : "#ffffff";')
html_lines.append('    ctx.fillStyle = bg;')
html_lines.append('    ctx.fillRect(0, 0, canvas.width, canvas.height);')
html_lines.append('    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);')
html_lines.append('    const link = document.createElement("a");')
html_lines.append('    link.download = "cgit-agent-arch.png";')
html_lines.append('    link.href = canvas.toDataURL("image/png");')
html_lines.append('    link.click();')
html_lines.append('    showToast("✅ PNG 已导出");')
html_lines.append('  };')
html_lines.append('  img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgData)));')
html_lines.append('}')

# Export SVG
html_lines.append('function exportSVG() {')
html_lines.append('  const svg = document.querySelector("svg");')
html_lines.append('  const svgData = new XMLSerializer().serializeToString(svg);')
html_lines.append('  const blob = new Blob([svgData], {type: "image/svg+xml"});')
html_lines.append('  const url = URL.createObjectURL(blob);')
html_lines.append('  const link = document.createElement("a");')
html_lines.append('  link.download = "cgit-agent-arch.svg";')
html_lines.append('  link.href = url;')
html_lines.append('  link.click();')
html_lines.append('  URL.revokeObjectURL(url);')
html_lines.append('  showToast("✅ SVG 文件已导出");')
html_lines.append('}')

html_lines.append('</script>')
html_lines.append('</body>')
html_lines.append('</html>')

html_content = '\n'.join(html_lines)

# ===== 写入文件 =====
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cgit-agent-arch.html')
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ 文件已生成: {output_path}")
print(f"   SVG viewBox: 0 0 {VB_W} {VB_H}")
print(f"   节点数: {len(nodes)} + END")
print(f"   依赖数: {len(dep_items)}")
print(f"   主题切换: 浅色/深色")
