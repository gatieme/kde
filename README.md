# Kernel Development Explorer (KDE)

> 基于 AI 的 Linux 内核开发分析工具集

KDE 是一个基于 LangGraph 构建的智能 Linux 内核开发分析系统,集成 ModelScope Qwen3-235B-A22B 模型,提供以下核心能力:

- **LKML 补丁分析** - 分析 Linux Kernel Mailing List 补丁,支持补丁和讨论两种模式
- **LKML Discussion 分析** - 分析 LKML 讨论线程,提取关键观点和共识
- **CGit Commit 分析** - 分析 Linux 内核 Git 提交,自动关联 patchset
- **Patchwork Series 分析** - 分析 Patchwork 补丁系列,支持多项目和并发处理
- **RSS 文章分析** - 分析 Phoronix 和 LWN 等技术网站文章,智能绕过反爬虫

## 核心特性

✨ **智能分析** - 基于 Qwen3-235B-A22B 模型的深度分析能力  
🔄 **状态机工作流** - LangGraph StateGraph 实现可扩展工作流  
🛡️ **反爬虫绕过** - 支持 Cloudflare、Turnstile 检测和真实浏览器模拟  
⚡ **并发处理** - ThreadPoolExecutor 并发处理多个 series  
💾 **磁盘缓存** - 统一缓存机制,持久化存储结果  
📊 **进度可视化** - tqdm 进度条和多级 verbose 日志控制  

## 快速开始

### 安装依赖

```bash
# Python 依赖
pip install langgraph requests beautifulsoup4 playwright tqdm feedparser httpx python-dotenv openai b4 cloudflare

# 安装 Playwright 浏览器
playwright install

# 系统依赖
sudo apt-get install wget  # CGit 需要
```

### 配置环境

创建 `.env` 文件:

```bash
# ModelScope API Key
OPENAI_API_KEY=your-modelscope-api-key
```

### 运行示例

```bash
cd src

# LKML 补丁分析
python kde.py --lkml 20260122161647.142704-2-realwujing@gmail.com --level detail -v

# LKML Discussion 分析
python kde.py --lkml 20260122161647.142704-2-realwujing@gmail.com --mode discussion --level simple

# CGit Commit 分析
python kde.py --cgit 53439363c0a111f11625982b69c88ee2ce8608ec --level detail -v

# Patchwork Series 分析
python kde.py --patchwork 365 --date 2022-01-27 --level simple --max-series 5 -v

# RSS 文章分析
python kde.py --rss phoronix --level 5 -v
```

## 文档导航

📚 **详细文档**: 请查看 [src/README.md](src/README.md) 获取完整的项目介绍、架构图、工作流程、技术细节等。

### 模块文档

| 模块 | 文档 | 功能 |
|:-----|:-----|:-----|
| lkml | [src/lkml/README.md](src/lkml/README.md) | LKML 补丁和讨论分析 |
| rss | [src/rss/README.md](src/rss/README.md) | RSS 文章分析,支持反爬虫绕过 |
| cgit | [src/cgit/README.md](src/cgit/README.md) | CGit commit 分析 |
| patchwork | [src/patchwork/README.md](src/patchwork/README.md) | Patchwork series 分析 |
| model | [src/model/README.md](src/model/README.md) | AI 模型集成层 |
| test | [src/test/README.md](src/test/README.md) | 测试套件 |

## 架构概览

```
kde/
├── src/
│   ├── kde.py                  # CLI 统一入口
│   ├── lkml/                   # LKML 补丁/讨论分析模块
│   ├── rss/                    # RSS 文章分析模块
│   ├── cgit/                   # CGit commit 分析模块
│   ├── patchwork/              # Patchwork series 分析模块
│   ├── model/                  # AI 模型集成模块
│   ├── utils/                  # 工具模块
│   ├── test/                   # 测试套件
│   ├── output/                 # 统一缓存目录
│   └── diagrams/               # 架构图
│       ├── lkml/               # LKML Agent 架构图
│       ├── rss/                # RSS Agent 架构图
│       ├── cgit/               # CGit Agent 架构图
│       ├── patchwork/          # Patchwork 架构图
│       └── (系统级图)          # architecture / kde-overview / cache-system 等
└── README.md                   # 本文件
```

## 命令参考

### LKML Agent

```bash
# 补丁分析模式（默认）
python kde.py --lkml <message-id> --level [simple|detail] --mode patch -v

# Discussion 分析模式
python kde.py --lkml <message-id> --level [simple|detail] --mode discussion -v
```

### CGit Agent

```bash
python kde.py --cgit <commit-id> --level [simple|detail] -v
```

### Patchwork Agent

```bash
# 单日期
python kde.py --patchwork <project-id|name> --date YYYY-MM-DD --level simple -v

# 日期范围
python kde.py --patchwork <project-id|name> --date YYYY-MM-DD --end-date YYYY-MM-DD -v

# 最近 N 天
python kde.py --patchwork <project-id|name> --days 7 -v

# 并发处理
python kde.py --patchwork <project-id|name> --date YYYY-MM-DD --max-parallel 3 -v
```

### RSS Agent

```bash
# 分析特定源
python kde.py --rss [phoronix|lwn] --level <文章数> -v

# 分析所有源
python kde.py --rss -v
```

## 测试

```bash
cd src/test
./test_all.sh  # 运行所有测试
```

## Verbose 级别

| 级别 | 参数 | 行为 |
|------|------|------|
| 0 | 无 | 仅显示简洁状态 |
| 1 | `-v` | 显示进度条和基本日志 |
| 2 | `-vv` | 显示详细处理信息 |
| 3 | `-vvv` | 显示最详细的调试信息 |

## 技术栈

- **LangGraph** - 状态机工作流管理
- **ModelScope** - Qwen3-235B-A22B AI 模型
- **Playwright** - 真实浏览器模拟和反爬虫绕过
- **Cloudflare SDK** - Cloudflare 绕过
- **tqdm** - 进度条可视化
- **ThreadPoolExecutor** - 并发处理

## 许可证

MIT License

## 更多信息

完整的架构图、工作流程、API 说明、代码规范和扩展计划请查看 [src/README.md](src/README.md)。