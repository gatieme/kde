## 实现计划

### 1. 创建新的智能体文件 `rss_agent.py`
基于现有代码，创建一个完整的 LangGraph 智能体，包含以下功能模块：

**核心功能：**
- 防爬虫检测模块（集成 `detect_anti_crawler.py` 的逻辑）
- RSS 获取模块（支持多种请求方式：requests、httpx、curl_cffi、playwright）
- 文章分析模块（检测内核相关内容、提取补丁链接）
- 摘要生成模块（使用 OpenAI API）
- 结果输出模块

**LangGraph 流程：**
1. `detect_protection` - 检测网站防爬虫机制
2. `fetch_rss_feeds` - 获取 RSS 内容（根据检测结果选择合适的方式）
3. `fetch_article_content` - 获取每篇文章的完整内容
4. `analyze_articles` - 分析文章内容（内核检测、补丁链接提取）
5. `generate_summaries` - 生成摘要（内核文章详细总结，普通文章简洁总结）
6. `output_results` - 输出结果

### 2. 更新 `requirements.txt`
添加必要的依赖包：
- `httpx` - HTTP/2 支持
- `curl-cffi` - TLS 指纹模拟
- `fake-useragent` - 动态 User-Agent
- `feedparser` - RSS 解析
- `playwright` - 浏览器模拟

### 3. 创建配置文件 `.env.example`
提供环境变量模板

### 4. 修复现有代码问题
- 修复 `dual_rss_agent.py` 中的语法错误（第65、204、212行）

### 技术实现要点：
- **防爬虫规避策略**：
  1. 优先尝试普通 requests 请求
  2. 失败后尝试 httpx（HTTP/2 + 完整浏览器头）
  3. 再尝试 curl_cffi（TLS 指纹模拟）
  4. 最后尝试 Playwright（真实浏览器）
  
- **内核检测关键词**：kernel, linux kernel, linux-kernel, 内核, LKML, linux-kernel mailing list
  
- **补丁链接提取**：识别包含 patch, mailing, lkml, kernel.org 等关键词的链接

- **摘要生成**：
  - 普通文章：简洁总结，≤300字
  - 内核文章：详细总结，包含技术细节和重要信息