# Test Suite

## 项目介绍

Test Suite 是 KDE 项目的测试框架，包含完整的测试脚本用于验证所有 agent 的功能和正确性。

## 项目架构

### 测试框架架构

```
┌──────────────────────────────────────────────────────────────┐
│                      Test Suite 架构                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Shell Script 测试框架                     │  │
│  │  - test_all.sh (主测试脚本）                          │  │
│  │  - test_lkml.sh (LKML 测试）                           │  │
│  │  - test_rss.sh (RSS 测试）                             │  │
│  │  - test_cgit.sh (CGit 测试）                           │  │
│  │  - test_verbose.sh (详细模式测试）                     │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                  │
│                         ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Python 测试框架                          │  │
│  │  - test_all_commands.py (Python 测试框架）            │  │
│  │  - test_cgit_workflow_order.py (工作流顺序测试）      │  │
│  │  - test_cache_directories.py (缓存目录测试）          │  │
│  │  - test_b4_robustness.py (B4 鲁棒性测试）             │  │
│  │  - test_b4_timeout.py (B4 超时测试）                  │  │
│  │  - test_progress_descriptions.py (进度描述测试）        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 核心组件

```
test/
├── test_all.sh              # 主测试脚本
├── test_lkml.sh             # LKML agent 专门测试
├── test_rss.sh              # RSS agent 专门测试
├── test_cgit.sh             # CGit agent 专门测试
├── test_verbose.sh          # 详细模式（verbose）测试
├── test.sh                  # 通用测试脚本
├── test_all_commands.py     # Python 测试框架
├── test_cgit_workflow_order.py
├── test_cache_directories.py
├── test_b4_robustness.py
├── test_b4_timeout.py
├── test_progress_descriptions.py
└── README.md               # 本文件
```

## 测试内容

### 1. LKML 相关测试

- **LKML 简单模式测试（通过 kde.py）** - 通过 kde.py 测试 LKML agent 的简单模式分析
- **LKML 详细模式测试（通过 kde.py）** - 通过 kde.py 测试 LKML agent 的详细模式分析
- **LKML 详细模式 verbose 测试（通过 kde.py）** - 通过 kde.py 测试 LKML agent 的详细模式分析（带进度条）
- **LKML 简单模式测试（直接调用）** - 直接调用 lkml_agent.py 测试简单模式分析
- **LKML 详细模式测试（直接调用）** - 直接调用 lkml_agent.py 测试详细模式分析

### 2. CGit 相关测试

- **CGit 简单模式测试（通过 kde.py）** - 通过 kde.py 测试 CGit agent 的简单模式分析
- **CGit 详细模式测试（通过 kde.py）** - 通过 kde.py 测试 CGit agent 的详细模式分析
- **CGit 详细模式。verbose 测试（通过 kde.py）** - 通过 kde.py 测试 CGit agent 的详细模式分析（带进度条）

### 3. RSS 相关测试

- **RSS 所有源测试** - 测试 RSS agent 分析所有源的文章
- **RSS LWN 源测试** - 测试 RSS agent 分析 LWN 源的文章
- **RSS Phoronix 源测试** - 测试 RSS agent 分析 Phoronix 源的文章
- **RSS LWN 源限制文章数测试** - 测试 RSS agent 分析 LWN 源的 2 篇文章
- **RSS Phoronix 源限制文章数测试** - 测试 RSS agent 分析 Phoronix 源的 3 篇文章
- **RSS Phoronix 源 verbose 测试** - 测试 RSS agent 分析 Phoronix 源的文章（带进度条）
- **RSS agent 帮助信息测试** - 测试 RSS agent 的帮助信息显示

### 4. 详细模式（verbose）测试

- **LKML verbose 测试** - 测试 LKML agent 的详细模式输出
- **CGit verbose 测试** - 测试 CGit agent 的详细模式输出
- **RSS verbose 测试** - 测试 RSS agent 的详细模式输出
- **不同级别 verbose 测试** - 测试不同级别的详细模式输出（-v, -vv, -vvv）

### 5. 帮助信息测试

- **帮助信息测试** - 测试显示帮助信息

## 使用方法

### 运行所有测试

#### 使用 Python 脚本：

```bash
cd test
python3 test_all_commands.py
```

#### 使用 Bash 脚本：

```bash
cd test
chmod +x test.sh
./test.sh
```

#### 使用一键式总测试脚本：

```bash
cd test
chmod +x test_all.sh test_lkml.sh test_rss.sh test_cgit.sh test_verbose.sh
./test_all.sh
```

### 运行专项测试

#### 运行 LKML agent 专项测试：

```bash
cd test
chmod +x test_lkml.sh
./test_lkml.sh
```

#### 运行 CGit agent 专项测试：

```bash
cd test
chmod +x test_cgit.sh
./test_cgit.sh
```

#### 运行 RSS agent 专项测试：

```bash
cd test
chmod +x test_rss.sh
./test_rss.sh
```

#### 运行详细模式专项测试：

```bash
cd test
chmod +x test_verbose.sh
./test_verbose.sh
```

### 运行集成测试

```bash
cd test
python3 test_cgit_workflow_order.py
python3 test_cache_directories.py
python3 test_b4_robustness.py
python3 test_b4_timeout.py
python3 test_progress_descriptions.py
```

### 运行单个测试

如果需要运行单个测试，可以修改 `test_all_commands.py` 文件，注释掉不需要的测试命令，然后运行脚本。

## 测试结果说明

测试脚本会为每个测试命令显示以下信息：

- 测试名称和描述
- 执行的命令
- 执行时间
- 返回码

- 标准输出和标准错误

测试通过会显示 `✓ 测试通过!`，测试失败会显示 `✗ 测试失败!`，测试异常会显示 `✗ 测试异常:`。

## 测试框架特点

### Shell 脚本测试

- 使用 bash 数组定义测试命令
- 使用 eval 执行测试命令
- 双语言注释（中文为主）
- 自动计算执行时间
- 支持测试结果统计

### Python 测试框架

- 基于 subprocess 的测试执行
- 支持测试结果统计
- 详细的错误信息输出
- 支持测试超时控制

## 注意事项

1. **网络连接** - 测试需要网络连接，因为需要下载补丁、commit 和文章内容
2. **API 密钥** - 确保 `.env` 文件中配置了正确的 ModelScope API 密钥
3. **执行时间** - 完整测试可能需要较长时间，因为需要下载和分析多个补丁、commit 和文章
4. **请求频率** - 测试脚本会在每个测试之间添加 2 秒的间隔，以避免请求过于频繁
5. **进度条显示** - 使用 `-v` 参数的测试会显示进度条，这是正常的测试行为
6. **详细模式输出** - 使用不同级别的 `-v` 参数会显示不同详细程度的输出：
   - `-v` - 显示基本进度条和状态信息
   - `-vv` - 显示更详细的处理信息
   - `-vvv` - 显示最详细的调试信息

## 故障排除

如果测试失败，可以检查以下几点：

1. 确保所有依赖已安装，包括 tqdm（用于进度条）
2. 确保 `.env` 文件配置正确
3. 确保网络连接正常
4. 确保 b4 工具已安装（用于 LKML 测试）
5. 确保 wget 工具已安装（用于 CGit 测试）
6. 确保 Playwright 浏览器已安装（用于 RSS 测试）

如果问题仍然存在，可以查看测试输出中的详细错误信息。

## 扩展计划

### 功能扩展

- 添加更多集成测试用例
- 支持测试覆盖率统计
- 添加性能基准测试
- 支持测试报告生成

### 测试框架改进

- 迁移到 pytest 框架
- 添加测试 fixtures 和 mocking
- 实现测试数据管理
- 添加 CI/CD 集成

### 用户体验

- 添加测试进度可视化
- 支持测试结果导出
- 添加测试失败重试机制
- 支持并行测试执行

## 许可证

MIT License
