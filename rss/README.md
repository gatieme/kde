# RSS 分析智能体

基于 LangGraph 开发的智能 RSS 分析工具，用于自动获取、分析和总结 LWN 和 Phoronix 的技术文章。

## 项目介绍

本项目是一个使用 LangGraph 框架构建的智能体系统，能够：

- 自动检测网站的防爬虫机制
- 使用多种方法（requests、httpx、Playwright）规避防爬虫保护
- 获取 LWN 和 Phoronix 的 RSS 订阅内容
- 分析文章是否涉及 Linux 内核
- 提取邮件列表补丁链接
- 使用 AI 生成文章摘要（内核文章详细总结，普通文章简洁总结）
- 以 Markdown 格式输出分析结果
- 显示进度条和详细日志（通过 verbose 参数控制）

### 主要特性

- **智能防爬虫检测**：自动检测并选择最佳访问方式
- **多源支持**：支持 Phoronix 和 LWN 两个技术新闻源
- **内核识别**：自动识别涉及 Linux 内核的文章
- **补丁链接提取**：提取邮件列表中的补丁相关链接
- **AI 摘要生成**：使用 OpenAI API 生成高质量摘要
- **灵活配置**：支持命令行参数自定义
- **进度条显示**：在 verbose 模式下显示操作进度
- **详细日志控制**：通过 verbose 级别控制日志输出的详细程度

## 项目实现架构

### 技术栈

- **Python 3.13.5**：主要编程语言
- **LangGraph 1.2.9**：智能体工作流框架
- **LangChain 1.2.9**：AI 应用开发框架
- **OpenAI API**：摘要生成
- **Playwright**：浏览器自动化
- **feedparser**：RSS 解析
- **requests/httpx**：HTTP 请求
- **BeautifulSoup4**：HTML 解析
- **tqdm**：进度条显示

### 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                     RSS 分析智能体                            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph 工作流                         │
├─────────────────────────────────────────────────────────────────┤
│  1. detect_protection     - 检测防爬虫机制            │
│  2. fetch_rss_feeds       - 获取 RSS 内容              │
│  3. fetch_article_content  - 获取文章完整内容           │
│  4. analyze_articles       - 分析文章内容               │
│  5. generate_summaries     - 生成摘要                   │
│  6. output_results        - 输出结果                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AgentState 状态管理                       │
├─────────────────────────────────────────────────────────────────┤
│  - messages: 消息列表                                      │
│  - articles: 文章列表                                      │
│  - summaries: 摘要列表                                     │
│  - protection_info: 防爬虫信息                             │
└─────────────────────────────────────────────────────────────────┘
```

### 核心模块

#### 1. 防爬虫检测模块 (`detect_protection`)

检测网站防爬虫机制，包括：
- Cloudflare 保护
- Turnstile 验证码
- User-Agent 验证
- TLS 指纹验证

#### 2. RSS 获取模块 (`fetch_rss_feeds`)

根据检测结果选择最佳方法获取 RSS：
- **requests**：基础 HTTP 请求
- **httpx**：HTTP/2 + 完整浏览器头
- **Playwright**：真实浏览器模拟
- **进度条显示**：在 verbose 模式下显示获取进度

#### 3. 文章分析模块 (`analyze_articles`)

分析文章内容：
- 检测是否涉及 Linux 内核
- 提取邮件列表补丁链接
- 识别内核相关关键词

#### 4. 摘要生成模块 (`generate_summaries`)

使用 OpenAI API 生成摘要：
- **内核文章**：详细总结，包含技术细节
- **普通文章**：简洁总结，≤300 字
- **进度条显示**：在 verbose 模式下显示模型推理进度

#### 5. 结果输出模块 (`output_results`)

以 Markdown 格式输出结果：
- 文章标题和链接
- 发布时间
- 内核相关标识
- 摘要内容
- 补丁链接

## 项目运行方式

### 环境准备

#### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

或使用 Python 3.13.5：

```bash
python3.13 -m pip install -r requirements.txt
```

#### 2. 安装 Playwright 浏览器

```bash
playwright install chromium
```

#### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 运行方式

#### 查看帮助信息

```bash
python rss_agent.py
```

或

```bash
python rss_agent.py --help
```

#### 通过 kde.py 调用

RSS 分析智能体可以通过项目根目录的 kde.py 脚本调用：

```bash
# 分析 Phoronix 文章（默认 3 篇）
python ../kde.py rss phoronix

# 分析 LWN 文章，限制 5 篇
python ../kde.py rss lwn 5

# 分析 Phoronix 文章，显示进度条
python ../kde.py rss phoronix 5 -v

# 分析 Phoronix 文章，显示最详细的日志
python ../kde.py rss phoronix 5 -vvv
```

#### 直接调用

```bash
# 获取所有源的所有文章
python rss_agent.py --resource Phoronix LWN

# 只获取 Phoronix 的文章
python rss_agent.py --resource Phoronix

# 只获取 LWN 的文章
python rss_agent.py --resource LWN

# 限制获取的文章数量
python rss_agent.py --max-articles 5

# 组合使用
python rss_agent.py --resource Phoronix --max-articles 10
```

### 命令行参数说明

| 参数 | 短参数 | 说明 | 可选值 | 默认值 |
|------|--------|------|--------|--------|
| `--resource` | `-r` | 指定 RSS 源 | Phoronix, LWN | Phoronix, LWN |
| `--max-articles` | `-n` | 限制获取的文章数量 | 整数 | 无限制 |
| `-v, --verbose` | `-v` | 详细模式，显示进度条和详细日志 | 多次使用增加详细程度 | 0 |

### 输出示例

#### 普通模式输出

```
# RSS 分析结果

**总文章数:** 45  
**内核相关:** 8 篇  
**来源:** Phoronix, LWN  

---

1. [LWN] [API changes for the futex robust list](https://lwn.net/Articles/1056387/)  
   **发布时间:** Wed, 04 Feb 2026 17:48:10 +0000  
   **内核相关:** ✅ 是  
   **摘要:** 本文探讨了Linux内核中futex稳健列表（robust futex ABI）的API改进方案。现有API通过用户空间...  

   **详情:**  
   **邮件相关链接:**  
   - [https://docs.kernel.org/locking/robust-futex-ABI.html](https://docs.kernel.org/locking/robust-futex-ABI.html)  

2. [Phoronix] [Linux 6.13 Kernel Performance Improvements](https://www.phoronix.com/...)  
   **发布时间:** ...  
   **内核相关:** ✅ 是  
   **摘要:** Linux 6.13 内核带来了多项性能改进，包括调度器优化、内存管理增强和IO性能提升...  
```

#### 详细模式输出（带进度条）

当使用 `-v` 参数时，会显示操作进度条和详细日志：

```
=== 检测网站防爬虫机制 ===

检测 Phoronix: https://www.phoronix.com/rss.php
  结果: accessible
  可用方法: requests, httpx, playwright
检测 LWN: https://lwn.net/headlines/newrss
  结果: accessible
  可用方法: requests, httpx, playwright

=== 获取 RSS 订阅 ===

获取 RSS 订阅中...
获取 RSS 订阅: 100%|████████████████████████████████████████████████████████| 2/2 [00:05<00:00,  2.50s/个]

总共获取 45 篇文章

=== 获取文章完整内容 ===

获取文章内容中...
获取文章内容: 100%|████████████████████████████████████████████████████████| 45/45 [01:30<00:00,  2.00s/篇]

=== 分析文章内容 ===

=== 生成文章摘要 ===

模型思考中...
模型推理进度: 100%|████████████████████████████████████████████████████████| 100/100 [00:03<00:00, 33.33%/s]

# RSS 分析结果

**总文章数:** 45  
**内核相关:** 8 篇  
**来源:** Phoronix, LWN  

---

1. [LWN] [API changes for the futex robust list](https://lwn.net/Articles/1056387/)  
   **发布时间:** Wed, 04 Feb 2026 17:48:10 +0000  
   **内核相关:** ✅ 是  
   **摘要:** 本文探讨了Linux内核中futex稳健列表（robust futex ABI）的API改进方案。现有API通过用户空间...  
```

## 项目文件说明

- `rss_agent.py` - 主程序文件，包含完整的智能体实现
- `dual_rss_agent.py` - 旧版本的双 RSS 源智能体
- `detect_anti_crawler.py` - 防爬虫检测工具
- `requirements.txt` - Python 依赖列表
- `.env.example` - 环境变量配置模板
- `README.md` - 项目说明文档

## 注意事项

1. **网络连接**：确保网络连接正常，能够访问 Phoronix 和 LWN
2. **API 配置**：确保 OpenAI API 密钥正确配置
3. **防爬虫限制**：某些网站可能限制自动化访问，建议合理设置请求间隔
4. **文章数量**：大量文章获取可能需要较长时间，建议使用 `--max-articles` 限制数量
5. **进度条显示**：使用 `-v` 参数可以查看操作进度，适合长时间运行的任务

## 许可证

本项目仅供学习和研究使用。
