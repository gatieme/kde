# Kernel Development Explorer (KDE)

Kernel Development Explorer (KDE) 是一个用于分析 Linux 内核开发相关内容的工具集合，包括 LKML (Linux Kernel Mailing List) 补丁分析、CGit commit 分析和技术 RSS 源文章分析。

## 项目结构

```
kde/
├── kde.py              # 项目主入口点
├── lkml/               # LKML 补丁分析模块
│   ├── README.md
│   ├── __init__.py
│   ├── cvt_lkml_to_lore.sh
│   ├── get_b4_series.sh
│   ├── lkml.py
│   └── lkml_agent.py    # 基于 langgraph 的 LKML 分析代理
├── rss/                # RSS 文章分析模块
│   ├── README.md
│   ├── detect_anti_crawler.py
│   ├── dual_rss_agent.py
│   └── rss_agent.py     # 基于 langgraph 的 RSS 分析代理
├── cgit/               # CGit commit 分析模块
│   ├── cgit_agent.py    # 基于 langgraph 的 CGit 分析代理
│   └── get_cgit_patch.sh
├── model/              # AI 模型集成模块
│   ├── __init__.py
│   ├── model_api.py
│   ├── model_infer.py
│   └── model_request.py
├── test/               # 测试脚本
│   ├── README.md
│   ├── test.sh
│   ├── test_all.sh     # 运行所有测试
│   ├── test_all_commands.py
│   ├── test_cgit.sh    # CGit 代理测试
│   ├── test_lkml.sh    # LKML 代理测试
│   ├── test_rss.sh     # RSS 代理测试
│   └── test_verbose.sh # 详细模式测试
├── patchwork/          # Patchwork 相关脚本
│   ├── README.md
│   ├── project/
│   ├── batch.sh
│   ├── get_patchwork_project.sh
│   ├── get_patchwork_series.sh
│   └── projects_list.md
├── .env                # 环境配置文件
├── .gitignore
└── README.md
```

## 核心功能

### 1. LKML 补丁分析
- 基于 langgraph 构建的工作流，支持补丁下载、解析和分析
- 支持简单和详细两种分析级别
- 提供补丁内容摘要、关键修改点和技术影响分析
- 支持进度条显示和详细日志输出

### 2. CGit Commit 分析
- 基于 langgraph 构建的工作流，支持 commit 下载、解析和分析
- 支持从 commit 中提取 patchset 链接并进行关联分析
- 提供 commit 内容摘要、修改点分析和技术影响评估
- 支持进度条显示和详细日志输出

### 3. RSS 文章分析
- 支持分析 Phoronix 和 LWN 等技术网站的 RSS 源
- 使用 Playwright 模拟真实浏览器行为，绕过反爬虫机制
- 提供文章摘要、技术亮点提取和分类
- 支持进度条显示和详细日志输出

### 4. 统一命令行入口
- 通过 `kde.py` 提供统一的命令行界面
- 支持详细的参数化配置，包括 verbose 级别控制
- 方便集成到其他脚本或工作流中

### 5. 进度条和日志控制
- 当不使用 `-v` 参数时，只显示简洁的状态消息
- 当使用 `-v` 或更高级别时，显示详细的进度条和日志
- 支持多个 verbose 级别，满足不同的调试和使用需求

## 安装依赖

### 系统依赖
- Python 3.8+
- Git
- B4 工具 (用于 LKML 补丁下载)
- Playwright (用于 RSS 分析)

### Python 依赖
```bash
pip install langgraph requests beautifulsoup4 playwright tqdm
playwright install
```

## 使用方法

### LKML 补丁分析
```bash
# 简单分析模式
python kde.py lkml <message-id> simple

# 详细分析模式
python kde.py lkml <message-id> detail

# 详细分析模式，显示进度条
python kde.py lkml <message-id> detail -v

# 详细分析模式，显示最详细的日志
python kde.py lkml <message-id> detail -vvv
```

### CGit Commit 分析
```bash
# 简单分析模式
python kde.py cgit <commit-id> simple

# 详细分析模式
python kde.py cgit <commit-id> detail

# 详细分析模式，显示进度条
python kde.py cgit <commit-id> detail -v
```

### RSS 文章分析
```bash
# 分析 Phoronix 文章 (默认 3 篇)
python kde.py rss phoronix

# 分析 LWN 文章，限制 5 篇
python kde.py rss lwn 5

# 分析 Phoronix 文章，显示进度条
python kde.py rss phoronix 5 -v
```

## 技术实现

### 1. 基于 Langgraph 的代理工作流
所有代理都使用 Langgraph 构建状态机工作流：

#### LKML 代理工作流
- `fetch_patch`: 下载补丁内容
- `parse_patch`: 解析补丁结构和修改内容
- `generate_summary`: 生成补丁摘要
- `analyze_patch`: 分析补丁技术影响
- `output_results`: 输出分析结果

#### CGit 代理工作流
- `fetch_commit`: 下载 commit 内容
- `parse_commit`: 解析 commit 结构和修改内容
- `analyze_commit`: 分析 commit 技术影响
- `check_patchset`: 检查 patchset 链接
- `run_lkml_analysis`: 运行 LKML 代理分析 patchset
- `output_results`: 输出分析结果

#### RSS 代理工作流
- `detect_protection`: 检测网站反爬虫机制
- `fetch_rss_feeds`: 获取 RSS 订阅内容
- `fetch_article_content`: 获取文章完整内容
- `analyze_articles`: 分析文章内容
- `generate_summaries`: 生成文章摘要
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
- 进度条显示模型推理过程

### 4. 进度条和日志控制
项目使用 tqdm 库实现进度条功能，并通过 verbose 级别控制日志输出：
- `verbose=0`: 只显示简洁的状态消息
- `verbose=1`: 显示进度条和基本日志
- `verbose=2`: 显示更详细的日志和模型推理过程
- `verbose=3`: 显示最详细的日志，包括所有命令输出

## 测试

项目包含完整的测试脚本：
```bash
# 运行所有测试
./test/test_all.sh

# 单独运行 LKML 测试
./test/test_lkml.sh

# 单独运行 CGit 测试
./test/test_cgit.sh

# 单独运行 RSS 测试
./test/test_rss.sh

# 测试详细模式
./test/test_verbose.sh
```

## 技术亮点

1. **模块化设计**: 清晰的目录结构和职责分离
2. **状态机工作流**: 使用 Langgraph 构建可扩展的分析工作流
3. **反爬虫绕过**: 高级 Playwright 技术模拟真实浏览器行为
4. **统一入口点**: 简化用户交互和集成
5. **进度条和日志控制**: 提供直观的用户反馈和详细的调试信息
6. **全面的测试覆盖**: 确保功能稳定性和可靠性
7. **多代理集成**: 支持 LKML、CGit 和 RSS 多种数据源的分析

## 未来发展建议

1. **扩展支持的 RSS 源**: 添加更多技术网站和博客
2. **增强补丁分析能力**: 支持更复杂的补丁系列分析
3. **添加可视化界面**: 提供 Web 界面或 GUI 工具
4. **集成更多 AI 模型**: 探索不同模型在代码分析中的应用
5. **添加贡献指南**: 方便社区参与和扩展
6. **增强 CI/CD 集成**: 提供更完善的持续集成和部署支持

## 许可证

MIT License
