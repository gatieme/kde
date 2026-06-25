# Patchwork Integration

## 项目介绍

Patchwork 模块提供与 kernel.org Patchwork 系统的集成，用于获取和管理 Linux 内核补丁集合。

## 项目架构

### 整体架构图

![Patchwork Integration Architecture](../diagrams/patchwork.svg)

**手绘风格架构图**：

如需查看手绘风格的架构图，请打开 `../diagrams/patchwork.excalidraw.json` 文件：

1. 访问 https://excalidraw.com
2. 点击 "Open" 或拖放文件
3. 或使用 Excalidraw VS Code 扩展

**ASCII 架构图**：

```
+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                 "Patchwork Integration"                                                                                                                  |
|                                                                                                                                                                                                                                                          |
|                                                                                                                                                                                                                                                          |
| +-------------------------------------------------------------------------------------+     +-----------------------------------------------------------------------------------------------------------+     +----------------------------------------+ |
| |                                                                                     |     |                                                                                                           |     |                                        | |
| | "get_patchwork_project.sh                                                                           |---->| "get_patchwork_series.sh                                                                            |---->| "batch.sh                                                                 | |
| |  Get all project lists                                                                              |     |   Get patch series by project                                                                          |     |   Batch processing: script               | |
| |  Output to projects_list.md"                                                                        |     |   Filter by date                                                                                      |     |                                        | |
| |                                                                                     |     |   Output to date directory                                                                            |     |                                        | |
| +-------------------------------------------------------------------------------------+     +-----------------------------------------------------------------------------------------------------------+     +----------------------------------------+ |
|                                                                                                                                                                                                                                                          |
+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
```

### 核心组件

```
patchwork/
├── patchwork_agent.py          # LangGraph 工作流实现（1518行）
├── __init__.py                 # 模块初始化，导出 run_patchwork_agent、build_patchwork_agent
├── get_patchwork_project.sh    # 获取项目列表（43行）
├── get_patchwork_series.sh     # 获取补丁系列（231行）
├── batch.sh                    # 批量处理脚本（18行）
├── project/                    # 项目数据目录
│   ├── projects_list.md        # 项目列表
│   └── projects_list.json      # 项目列表 JSON
└── README.md                   # 本文件
```

## 功能说明

### 脚本描述

| 脚本 | 描述 |
|:----:|:----:|
| `get_patchwork_project.sh` | 获取 patchwork 上所有的 project 列表（id 和 name 信息），输出到 `project/projects_list.md` 中 |
| `get_patchwork_series.sh` | 获取 patchwork 上指定 project ID（-p 指定）上指定日期（-d 指定）的所有提交的补丁以及补丁集合 series。输出到对应日期的目录中 |
| `batch.sh` | 批量处理脚本 |

## 使用方法

### 获取项目列表

```bash
bash ./get_patchwork_project.sh
cat project/projects_list.md
```

### 获取补丁系列

```bash
bash get_patchwork_series.sh -p 365 -d 2022-01-24
cat 2022-01-24/2022-01-24.md
```

### 脚本参数说明

#### get_patchwork_series.sh

| 参数 | 说明 |
|:----:|:----:|
| `-p` | 指定 project ID |
| `-d` | 指定日期（格式：YYYY-MM-DD） |

## 支支持的项目

以下是 Patchwork 上支持的主要项目：

| ID | PROJECT |
|:--:|:-------:|
|  2  |  Linux ACPI  |
| 3  |  Linux SuperH Architecture Architecture mailing list  |
| 4  |  Linux V4L/DVB mailing list  |
| 5  |  Linux Kernel Build mailing list  |
| 6  |  Device Mapper Development  |
| 7  |  CIFS (Samba) Client  |
| 8  |  KVM development  |
| 9  |  Linux Sparse mailing list  |
| 10  |  Linux ARM based TI OMAP SoCs mailing list  |
| 11  |  Linux PA-RISC based architecture mailing list  |
| 12  |  Linux PCI development list  |
| 13  |  Linux DaVinci SoCs  |
| 14  |  Intel Graphics Driver  |
| 15  |  Linux Wireless Mailing List  |
| 16  |  V9FS (Plan 9) Filesystem Development Mailing List  |
| 17  |  Linux Input Mailing List  |
| 18  |  Linux RDMA and InfiniBand  |
| 19  |  Linux BTRFS  |
| 20  |  Linux SPI core/device drivers discussion  |
| 21  |  DRI Development  |
| 22  |  CEPH development  |
| 32  |  Linux MMC development  |
| 41  |  Linux NFS mailing list  |
| 51  |  Linux framebuffer layer  |
| 61  |  Linux power management  |
| 62  | .  Linux ARM Kernel Architecture  |
| 71  |  LTSI Project development  |
| 81  |  Linux Samsung SOC mailing list  |
| 91  |  OCFS2 Development  |
| 92  |  Linux ARM MSM sub-architecture  |
| 111  |  Linux DMAEngine  |
| 121  |  ALSA development  |
| 131  |  Rockchip SoC list  |
| 141  |  FSTests  |
| 151  |  Linux Crypto  |
| 161  |  DASH shell  |
| 171  |  TPM Device Driver list  |
| 181  |  ath10k  |
| 191  |  NVDIMM support in Linux  |
| 201  |  Linux FS Development  |
| 211  |  Discussions and development of Linux SCSI subsystem  |
| 221  |  Linux-Mediatek patches  |
| 231  |  x86 platform driver layer  |
| 241  |  Linux Block  |
| 251  |  Linux Audit  |
| 261  |  SELinux Development list  |
| 271  |  WPAN under Linux  |
| 281  |  XEN Development list  |
| 291  |  Linux Renesas SoC patches  |
| 301  |  QEMU patches  |
| 311  |  Linux HWMON  |
| 321  |  Linux Modules  |
| 331  |  Linux Clock framework  |
| 333  |  Security modules development  |
| 335  |  Linux Hardening  |
| 337  |  Linux amlogic  |
| 339  |  XFS devel  |
| 341  |  Linux Remoteproc  |
| 343  |  Linux Oxnas  |
| 345  |  Linux FPGA development  |
| 347  |  Intel SGX  |
| 349  |  Linux Backports  |
| 351  |  SCSI target development list  |
| 353  |  Linux fscrypt  |
| 355  |  Libteam  |
| 357  |  Linux Integrity  |
| 359  |  Linux IIO  |
| 361  |  Linux MLXSW  |
| 363  |  Linux USB  |
| 365  |  Linux MM  |
| 367  |  Kernel Selftest  |
| 369  |  Lustre software development  |
| 371  |  Git SCM  |
| 373  |  CIP Project Development  |
| 377  |  Linux RISC-V  |
| 379  |  Linux SoC  |
| 381  |  Linux MIPS  |
| 383  |  Linux I3C  |
| 385  |  Linux-Trace Development  |
| 387  |  Linux Watchdog Development  |
| 389  |  ath11k  |
| 391  |  Linux EDAC  |
| 393  |  Linux Keyrings  |
| 395  |  Bluetooth  |
| 397  |  Linux Safety  |
| 399  |  Netdev + BPF  |
| 401  |  Linux PHY  |
| 403  |  CXL  |
| 405  |  MPTCP  |

## 输出示例

### 补丁系列输出格式

| 时间  | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |
|:-----:|:----:|:----:|:----:|:------------:|:----:|
| 2022/01/24 | liupeng (DM) <liupeng256@huawei.com> | [Add a module parameter to adjust kfence objects](https://patchwork.kernel.org/project/linux-mm/cover/20220124025205.329752-1-liupeng256@huawei.com/) | 607689 | v1 ☐☑ | [PatchWork v1,0/3](https://lore.kernel.org/r/20220124025205.329752-1-liupeng256@huawei.com) |
| 2022/01/24 | NeilBrown <neilb@suse.de> | [Repair SWAP-over_NFS](https://patchwork.kernel.org/project/linux-mm/cover/164299573337.26253.7538614611220034049.stgit@noble.brown/) | 607709 | v3 ☐☑ | [PatchWork v3,0/23](https://lore.kernel.org/r/164299573337.26253.7538614611220034049.stgit@noble.brown) |

## Patchwork API 概述

相关 API 接口，请查阅 [Patchwork API url](https://patchwork.kernel.org/api)

### 示例 API 调用

```bash
# 获取指定项目的补丁系列
https://patchwork.kernel.org/api/series/?project=365&archive=both&format=json&submitter=201165
```

## 依赖关系

### 系统依赖

- **curl** 或 **wget** -` 用于 HTTP 请求
- **jq** - 用于 JSON 解析（可选）

## 代码规范

### 命名约定

- **函数**: `snake_case` (Shell 脚本函数命名)
- **常量**: `UPPER_SNAKE_CASE`

### 注释风格

- **双语注释**: 英文用于代码结构，中文用于领域逻辑

## 扩展计划

### 功能扩展

- 添加更多 API 接口支持
- 支持按作者、状态等条件过滤
- 添加补丁状态跟踪
- 支持批量下载补丁

### 性能优化

- 添加请求缓存
- 支持并发请求
- 优化大数据量处理

### 用户体验

- 添加进度条显示
- 支持更多输出格式（JSON、CSV）
- 添加交互式查询

## 注意事项

1. **网络连接** - 需要网络连接访问 patchwork.kernel.org
2. **API 限制** - 注意 API 请求频率限制
3. **数据量** - 大量数据获取可能需要较长时间

---

## Patchwork Agent（LangGraph 实现）

基于 LangGraph StateGraph 实现的 Patchwork Agent，提供更强大的补丁分析能力，支持与 LKML Agent 集成进行深度分析。

### 功能特性

- **智能项目解析**: 支持项目 ID 和项目名称查询
- **灵活日期选择**: 支持单日期、日期范围、最近 N 天三种模式
- **并发处理**: 支持多线程并发处理 series
- **深度分析**: detail 模式调用 LKML Agent 进行补丁深度分析
- **缓存机制**: 自动缓存 API 响应，减少重复请求
- **标准化输出**: Markdown 表格格式输出，与 LKML Agent 保持一致

### 使用方法

#### 通过 kde.py 主入口调用

```bash
# 简单模式（推荐）
python kde.py --patchwork 365 --date 2022-01-27 --level simple --max-series 5 -v

# 详细模式（调用 LKML Agent）
python kde.py --patchwork 365 --date 2022-01-27 --level detail --max-series 2 -v

# 最近 N 天
python kde.py --patchwork 365 --days 7 --level simple --max-series 10 -v

# 日期范围
python kde.py --patchwork 365 --date 2022-01-24 --end-date 2022-01-27 --level simple -v

# 多项目
python kde.py --patchwork 365 366 --date 2022-01-27 --level simple -v

# 项目名称
python kde.py --patchwork "Linux MM" --date 2022-01-27 --level simple -v

# 并发处理
python kde.py --patchwork 365 --date 2022-01-27 --level simple --max-series 5 --max-parallel 3 -v
```

#### 直接调用 patchwork_agent.py

```bash
python patchwork/patchwork_agent.py --project 365 --date 2022-01-27 --level simple --max-series 2 -v
```

### 参数说明

| 参数 | 说明 | 默认值 |
|:----:|:----:|:------:|
| `--patchwork` | 项目 ID 或名称（支持多个） | 必需 |
| `--date` | 单日期或起始日期 (YYYY-MM-DD) | 今天 |
| `--end-date` | 结束日期 (YYYY-MM-DD) | - |
| `--days` | 最近 N 天 | - |
| `--level` | 分析级别 (simple/detail) | simple |
| `--max-series` | 最大处理 series 数量 | - |
| `--max-parallel` | 并发线程数 | 1 |
| `-v` | 详细程度 (-v/-vv/-vvv) | 0 |

### 输出格式

输出采用与 LKML Agent 相同的 Markdown 表格格式：

```
| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |
|:----:|:----:|:----:|:----:|:------------:|:----:|
| 2022/01/27 | Karolina Drobnik <karolinadrobnik@gmail.com> | [Introduce memblock simulator](https://...) | 609110 | v1 ☐ | [LORE v1,16](https://...) |
```

### 缓存位置

- API 响应缓存: `output/patchwork/cache/`
- Series 汇总: `output/patchwork/<project>/<date>/summary.md`
- 详细分析: `output/patchwork/<project>/<date>/series_*_detail.md`

### 测试

```bash
cd test
./test_patchwork.sh
```

### 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Patchwork Agent Workflow                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  fetch_project_info → calculate_date_range → fetch_series_list │
│         ↓                                                       │
│  filter_and_sort → process_series → aggregate_results          │
│         ↓                                                       │
│  output_results → cache_results → END                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 状态定义（PatchworkAgentState）

Agent 工作流的核心数据结构，贯穿所有节点：

```python
@dataclass
class PatchworkAgentState:
    messages: Annotated[List[Dict[str, Any]], add_messages]
    project_id: int = 0           # Patchwork 项目 ID
    project_name: str = ""        # 项目名称
    date: str = ""                # 单日期或起始日期
    end_date: str = ""            # 结束日期
    days: int = 0                 # 最近 N 天
    level: str = "simple"         # 分析级别
    max_series: int = 0           # 最大处理 series 数
    max_parallel: int = 1         # 并发线程数
    series_list: List[Dict] = field(default_factory=list)
    processed_results: List[Dict] = field(default_factory=list)
    summaries: List[str] = field(default_factory=list)
    verbose: int = 0
    work_dir: str = ""
```

### 工作流节点详解

| 步骤 | 函数 | 说明 |
|:----:|:----:|:----:|
| 1 | `fetch_project_info` | 加载项目列表，通过 ID 或名称查找项目 |
| 2 | `calculate_date_range` | 根据参数计算日期范围（单日期/范围/最近N天） |
| 3 | `fetch_series_list` | 调用 Patchwork API 获取 series 列表 |
| 4 | `filter_and_sort` | 过滤和排序 series |
| 5 | `process_series` | 并行处理 series（ThreadPoolExecutor），detail 模式调用 LKML Agent |
| 6 | `aggregate_results` | 汇总所有处理结果 |
| 7 | `output_results` | Markdown 表格输出 |
| 8 | `cache_results` | 缓存结果到 output/patchwork/ |

### 字段提取函数

用于从 Patchwork API 响应中提取结构化信息：

| 函数 | 说明 |
|:----:|:----:|
| `extract_date` | 提取提交日期 |
| `extract_author` | 提取作者名称 |
| `extract_email` | 提取作者邮箱 |
| `extract_subject` | 提取补丁主题/标题 |
| `extract_version` | 提取补丁版本号（如 v1, v2） |
| `extract_web_url` | 提取 Patchwork Web URL |
| `extract_archive_url` | 提取 Lore.kernel.org 归档链接 |
| `extract_message_id_from_cover` | 从 cover letter 提取 Message-ID |

### 缓存机制（fetch_with_cache）

`fetch_with_cache` 函数提供带本地 MD5 缓存的 HTTP 请求能力：

- **缓存键**: 对请求 URL 做 MD5 哈希，作为本地文件名
- **缓存路径**: `output/patchwork/cache/<md5_hash>.json`
- **缓存策略**: 先查本地文件，命中则直接返回；未命中则发起 HTTP 请求并写入缓存
- **过期控制**: 无自动过期，可通过 `git clean -fdX` 清除

### 项目列表查找机制

支持三种方式定位 Patchwork 项目：

1. **`load_projects_list()`** - 从 `project/projects_list.json` 加载本地项目列表
2. **`fetch_projects_from_api()`** - 调用 Patchwork API 远程获取项目列表并缓存
3. **`find_project_id_by_name()`** - 通过项目名称（支持模糊匹配）查找对应 ID

查找流程：优先本地加载 → 本地不存在则从 API 获取 → 用户输入名称则进行匹配。

### 并发处理说明

`process_series` 节点使用 `ThreadPoolExecutor` 实现并发：

- **线程数**: 由 `max_parallel` 参数控制，默认为 1（串行）
- **适用场景**: 大量 series 需要处理时，并发可显著缩短总耗时
- **风险提示**: 高并发可能触发 Patchwork API 限制，建议 `max_parallel ≤ 3`
- **错误隔离**: 单个 series 处理失败不影响其他 series，错误记录到 `processed_results`

### 内置测试代码

`patchwork_agent.py` 包含各阶段功能测试代码（行 1082-1518），覆盖：

| 测试编号 | 测试范围 |
|:-------:|:-------:|
| US-003 | 项目查找（ID / 名称 / 模糊匹配） |
| US-004 | 日期范围计算（单日期 / 范围 / 最近N天） |
| US-005 | Series 列表获取与过滤 |
| US-006 | 并发处理与结果聚合 |
| US-007 | 输出格式化与缓存 |
| US-008 | 完整工作流端到端测试 |

通过 `python patchwork/patchwork_agent.py --test` 可直接运行内置测试。

### 与 Shell 脚本对比

| 特性 | Shell 脚本 | LangGraph Agent |
|:----:|:----------:|:---------------:|
| 项目解析 | 仅数字 ID | ID + 名称 + 模糊匹配 |
| 日期选择 | 单日期 | 单日期/范围/最近 N 天 |
| 并发处理 | 无 | ThreadPoolExecutor |
| 深度分析 | 无 | 集成 LKML Agent |
| 缓存机制 | 无 | 自动缓存 API 响应 |
| 错误处理 | 弱 | 单个失败不影响整体 |

### 注意事项

1. **网络连接**: 需要稳定的网络访问 patchwork.kernel.org 和 lore.kernel.org
2. **API 限制**: Patchwork API 可能有请求频率限制，建议使用缓存
3. **Detail 模式耗时**: detail 模式会调用 LKML Agent，每个 series 需额外时间
4. **并发风险**: 高并发可能触发 API 限制，建议 max_parallel ≤ 3

---

## 许可证

MIT License
