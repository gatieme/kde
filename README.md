# Kernel Development Explorer (KDE)

Kernel Development Explorer (KDE) 是一个用于分析 Linux 内核开发相关内容的工具集合，包括 LKML (Linux Kernel Mailing List) 补丁分析和技术 RSS 源文章分析。

## 项目结构

```
kde/
├── kde.py              # 项目主入口点
├── lkml/               # LKML 补丁分析模块
│   ├── __init__.py
│   ├── lkml.py         # 原始 LKML 分析脚本
│   ├── lkml_agent.py   # 基于 langgraph 的 LKML 分析代理
│   ├── cvt_lkml_to_lore.sh
│   └── get_b4_series.sh
├── rss/                # RSS 文章分析模块
│   ├── __init__.py
│   ├── rss_agent.py    # RSS 分析代理
│   ├── dual_rss_agent.py
│   └── detect_anti_crawler.py
├── model/              # AI 模型集成模块
│   ├── __init__.py
│   ├── model_api.py
│   ├── model_infer.py
│   └── model_request.py
├── test/               # 测试脚本
│   ├── test_all.sh     # 运行所有测试
│   ├── test_lkml.sh    # LKML 代理测试
│   └── test_rss.sh     # RSS 代理测试
├── cgit/               # cgit 相关脚本
├── patchwork/          # Patchwork 相关脚本
├── .env                # 环境配置文件
└── .gitignore
```

## 核心功能

### 1. LKML 补丁分析
- 基于 langgraph 构建的工作流，支持补丁下载、解析和分析
- 支持简单和详细两种分析级别
- 提供补丁内容摘要、关键修改点和技术影响分析

### 2. RSS 文章分析
- 支持分析 Phoronix 和 LWN 等技术网站的 RSS 源
- 使用 Playwright 模拟真实浏览器行为，绕过反爬虫机制
- 提供文章摘要、技术亮点提取和分类

### 3. 统一命令行入口
- 通过 `kde.py` 提供统一的命令行界面
- 支持参数化配置，方便集成到其他脚本或工作流中

## 安装依赖

### 系统依赖
- Python 3.8+
- Git
- B4 工具 (用于 LKML 补丁下载)
- Playwright (用于 RSS 分析)

### Python 依赖
```bash
pip install langgraph requests beautifulsoup4 playwright
playwright install
```

## 使用方法

### LKML 补丁分析
```bash
# 简单分析模式
python kde.py lkml <message-id> simple

# 详细分析模式
python kde.py lkml <message-id> detail
```

### RSS 文章分析
```bash
# 分析 Phoronix 文章 (默认 3 篇)
python kde.py rss phoronix

# 分析 LWN 文章，限制 5 篇
python kde.py rss lwn 5
```

## 技术实现

### 1. 基于 Langgraph 的 LKML 代理
LKML 代理使用 Langgraph 构建状态机工作流，包括以下节点：
- `fetch_patch`: 下载补丁内容
- `parse_patch`: 解析补丁结构和修改内容
- `generate_summary`: 生成补丁摘要
- `analyze_patch`: 分析补丁技术影响
- `output_results`: 输出分析结果

### 2. 增强的 RSS 代理
RSS 代理使用 Playwright 模拟真实浏览器行为，包括：
- 模拟真实浏览器指纹
- 实现鼠标移动、滚动等交互
- 多步骤导航 (先访问 Google，再跳转目标网站)
- Cookie 和 localStorage 模拟

### 3. AI 模型集成
项目集成了 AI 模型用于文本分析和摘要生成，支持：
- 补丁内容理解和分析
- 技术文章摘要和分类
- 自然语言处理和格式化

## 测试

项目包含完整的测试脚本：
```bash
# 运行所有测试
./test/test_all.sh

# 单独运行 LKML 测试
./test/test_lkml.sh

# 单独运行 RSS 测试
./test/test_rss.sh
```

## 技术亮点

1. **模块化设计**: 清晰的目录结构和职责分离
2. **状态机工作流**: 使用 Langgraph 构建可扩展的分析工作流
3. **反爬虫绕过**: 高级 Playwright 技术模拟真实浏览器行为
4. **统一入口点**: 简化用户交互和集成
5. **全面的测试覆盖**: 确保功能稳定性和可靠性

## 未来发展建议

1. **扩展支持的 RSS 源**: 添加更多技术网站和博客
2. **增强补丁分析能力**: 支持更复杂的补丁系列分析
3. **添加可视化界面**: 提供 Web 界面或 GUI 工具
4. **集成更多 AI 模型**: 探索不同模型在代码分析中的应用
5. **添加贡献指南**: 方便社区参与和扩展

## 许可证

MIT License
