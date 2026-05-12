# Patchwork Agent Brainstorming

**日期**: 2026-05-12
**任务**: 在 patchwork 目录下基于 LangGraph 实现一个 patchwork AGENT

---

## 需求概览

基于现有的 shell 脚本（`get_patchwork_series.sh`），实现一个基于 LangGraph 的 patchwork agent，支持：

1. 获取指定日期、指定项目 ID 的所有补丁列表
2. 通过 LKML agent 进行分析（detail 模式）
3. 格式沿用 LKML agent 的输出格式（simple 和 detail）
4. 支持两级分析模式（simple/detail）
5. 支持测试用例补齐

---

## 设计决策

### 1. 与 LKML agent 的集成方式

**决策**: 两级分析模式（simple/detail）

- **simple 模式**: 只提取和展示 patchwork API 的基本信息
- **detail 模式**: 提取基本信息 + 调用 LKML agent 进行深度分析

---

### 2. 日期参数的灵活性

**决策**: 支持三种日期模式

- **单日期**: `--date 2022-01-24`（获取该天的补丁）
- **日期范围**: `--date 2022-01-24 --end-date 2022-01-26`（获取范围内所有补丁）
- **最近 N 天**: `--days 7`（获取最近 7 天的补丁，自动计算日期范围）

---

### 3. 输出格式

**决策**: 完全沿用 LKML agent 的输出格式

**表格格式**:
```
| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |
|:---:|:----:|:---:|:----:|:---------:|:----:|
| 2022/01/24 | Author <email> | [Subject](web_url) | Summary | v1 ☐☑✓ | [LORE](archive_url) |
```

- **simple 模式**: 摘要使用 patchwork API 的简要描述
- **detail 模式**: 调用 LKML agent 生成完整摘要和详细分析

---

### 4. 补丁列表的获取和排序

**决策**: 支持限制数量 + 分页

- `--max-series N`: 限制最多获取 N 个 series（类似 RSS agent 的 `--max-articles`）
- 默认不限制，获取日期范围内的所有 series
- 按时间倒序排列（最新的先显示）

---

### 5. 并发处理和错误处理

**决策**: 可配置并行度 + 完善错误处理

- 新增参数 `--max-parallel` 控制并行度，默认为 1（串行）
- 并行度超过 1 时，并发处理
- 每个 series 独立处理，失败不影响其他 series
- 显示进度条（如 `[1/10] Processing series 123456...`）
- 失败时记录错误但继续处理其他 series

---

### 6. 缓存机制

**决策**: 完整缓存机制

- 缓存目录: `output/patchwork/<project_id>/<date>/`
- 缓存内容: series JSON 文件、patch 文件、分析结果
- 支持缓存重用: 如果已缓存则跳过重复下载和分析
- detail 模式下，LKML agent 的缓存也存储在各自的 `output/lkml/<message-id>/` 中

---

### 7. 项目参数的灵活性

**决策**: 支持多种指定方式

- 项目 ID: `--project 365`（单项目）
- 多项目 ID: `--project 365 367 399`（多项目）
- 项目名称: `--project "Linux MM"`（通过名称查找 ID）
- 支持组合使用: ID 和名称可以混用

---

## 实现方案

### 方案选择: 完全基于 LangGraph 的 Agent

**架构设计**:
```
patchwork_agent.py
├── 状态定义: PatchworkAgentState（包含所有输入参数和中间结果）
├── 工作流节点:
│   ├── fetch_project_info     # 解析项目参数（ID/名称转 ID）
│   ├── calculate_date_range   # 计算日期范围（单日期/范围/最近 N 天）
│   ├── fetch_series_list      # 从 Patchwork API 获取 series 列表
│   ├── filter_and_sort        # 应用数量限制和排序
│   ├── process_series         # 核心节点：并行处理每个 series
│   ├── aggregate_results      # 汇聚所有 series 的输出
│   ├── output_results         # 输出最终结果（Markdown 表格）
│   └── cache_results          # 缓存到文件系统
```

**选择理由**:
- 与现有 lkml_agent、cgit_agent、rss_agent 架构完全一致
- LangGraph 的状态管理和流程控制非常清晰
- 便于调试和扩展
- 可以复用现有的 utils、model 等模块

---

## 详细设计

### 第一部分: 状态定义和输入参数

#### PatchworkAgentState 定义

```python
@dataclass
class PatchworkAgentState:
    messages: Annotated[List[Dict[str, Any]], add_messages]

    # 输入参数
    projects: List[str] = field(default_factory=list)  # 项目列表（ID 或名称）
    date: Optional[str] = None                        # 单日期：YYYY-MM-DD
    end_date: Optional[str] = None                    # 结束日期（用于日期范围）
    days: Optional[int] = None                        # 最近 N 天
    level: str = "simple"                             # 分析级别：simple/detail
    max_series: Optional[int] = None                  # 最大 series 数量
    max_parallel: int = 1                             # 并行度
    verbose: int = 0                                  # 详细级别

    # 中间状态
    project_ids: List[int] = field(default_factory=list)  # 解析后的项目 ID
    date_range: Dict[str, str] = field(default_factory=dict)  # 实际日期范围
    series_list: List[int] = field(default_factory=list)  # 获取的 series ID 列表
    series_details: Dict[int, Dict] = field(default_factory=dict)  # series 详细信息

    # 输出结果
    processed_results: List[Dict[str, Any]] = field(default_factory=list)  # 处理后的结果列表
    output_lines: List[str] = field(default_factory=list)  # 输出的表格行

    # 工作目录和缓存
    work_dir: str = ""
    cache_dir: str = ""
```

#### 输入参数说明

| 参数 | 类型 | 说明 | 示例 |
|:----:|:----:|:----:|:----:|
| `--project` | List[str] | 项目 ID 或名称，支持多值 | `365` 或 `"Linux MM"` 或 `365 367` |
| `--date` | str | 单日期 | `2022-01-24` |
| `--end-date` | str | 结束日期（配合 `--date`） | `2022-01-26` |
| `--days` | int | 最近 N 天（替代 `--date`） | `7` |
| `--level` | str | 分析级别 | `simple` / `detail` |
| `--max-series` | int | 最大 series 数量 | `10` |
| `--max-parallel` | int | 并行度 | `3` |
| `--verbose` | int | 详细级别 | `0/1/2/3` |

---

### 第二部分: 工作流节点设计

#### 完整工作流图

```
fetch_project_info → calculate_date_range → fetch_series_list → filter_and_sort
→ process_series → aggregate_results → output_results → cache_results → END
```

#### 各节点详细设计

##### 1. `fetch_project_info` 节点

**功能**: 解析项目参数（支持 ID、名称、混合）

**实现逻辑**:
```python
def fetch_project_info(state: PatchworkAgentState) -> PatchworkAgentState:
    """解析项目参数，将名称转换为 ID"""

    # 加载项目列表（从 projects_list.md 或 API）
    projects_map = load_projects_list()  # {name: id, id: id}

    project_ids = []
    for project in state.projects:
        if project.isdigit():
            # 直接是 ID
            project_ids.append(int(project))
        else:
            # 是名称，查找对应的 ID
            matched_id = find_project_id_by_name(project, projects_map)
            if matched_id:
                project_ids.append(matched_id)
            else:
                print(f"警告: 未找到项目 '{project}'，跳过")

    state.project_ids = project_ids
    return state
```

**输出**: `state.project_ids = [365, 367, ...]`

---

##### 2. `calculate_date_range` 节点

**功能**: 计算实际的日期范围

**实现逻辑**:
```python
def calculate_date_range(state: PatchworkAgentState) -> PatchworkAgentState:
    """计算日期范围"""

    if state.days:
        # 最近 N 天模式
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=state.days - 1)
        state.date_range = {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d")
        }
    elif state.date and state.end_date:
        # 日期范围模式
        state.date_range = {
            "start": state.date,
            "end": state.end_date
        }
    elif state.date:
        # 单日期模式
        state.date_range = {
            "start": state.date,
            "end": state.date
        }
    else:
        # 默认：今天
        today = datetime.date.today().strftime("%Y-%m-%d")
        state.date_range = {"start": today, "end": today}

    return state
```

**输出**: `state.date_range = {"start": "2022-01-24", "end": "2022-01-26"}`

---

##### 3. `fetch_series_list` 节点

**功能**: 从 Patchwork API 获取所有项目的 series 列表

**实现逻辑**:
```python
def fetch_series_list(state: PatchworkAgentState) -> PatchworkAgentState:
    """从 Patchwork API 获取 series 列表"""

    all_series_ids = []

    for project_id in state.project_ids:
        # 构造 API URL
        start_date = state.date_range["start"]
        end_date = state.date_range["end"]

        # 对每个日期循环（Patchwork API 只支持单日期查询）
        current_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_datetime = datetime.datetime.strptime(end_date, "%Y-%m-%d")

        while current_date <= end_datetime:
            date_str = current_date.strftime("%Y-%m-%d")

            # API URL
            url = f"https://patchwork.kernel.org/api/series/?project={project_id}&archive=both&format=json&before={date_str}T23%3A59%3A59&since={date_str}T00%3A00%3A00"

            # 获取并解析（使用缓存）
            series_json = fetch_with_cache(url, state.cache_dir)
            series_ids = [s["id"] for s in series_json]

            all_series_ids.extend(series_ids)
            current_date += datetime.timedelta(days=1)

    state.series_list = all_series_ids
    return state
```

**输出**: `state.series_list = [607689, 607709, ...]`

---

##### 4. `filter_and_sort` 节点

**功能**: 应用数量限制和排序

**实现逻辑**:
```python
def filter_and_sort(state: PatchworkAgentState) -> PatchworkAgentState:
    """过滤和排序 series 列表"""

    # 去重（多项目可能有相同的 series）
    unique_series_ids = list(set(state.series_list))

    # 按时间倒序排列（需要先获取每个 series 的日期）
    series_with_date = []
    for series_id in unique_series_ids:
        detail = fetch_series_basic_detail(series_id, state.cache_dir)
        series_with_date.append({
            "id": series_id,
            "date": detail.get("date", "")
        })

    # 排序：最新的先显示
    series_with_date.sort(key=lambda x: x["date"], reverse=True)

    # 应用数量限制
    if state.max_series:
        series_with_date = series_with_date[:state.max_series]

    state.series_list = [s["id"] for s in series_with_date]
    state.series_details = {s["id"]: s for s in series_with_date}

    return state
```

**输出**: 排序并限制后的 `state.series_list`

---

##### 5. `process_series` 节点（核心节点）

**功能**: 处理所有 series，支持并发

**实现逻辑**:
```python
def process_series(state: PatchworkAgentState) -> PatchworkAgentState:
    """处理所有 series，支持并发"""

    def process_single_series(series_id: int) -> Dict[str, Any]:
        """处理单个 series（独立函数，支持并发调用）"""
        try:
            # 1. 获取 series 详细信息
            detail = fetch_series_detail(series_id, state.cache_dir, state.verbose)

            # 2. 提取基本信息
            result = {
                "series_id": series_id,
                "date": extract_date(detail),
                "author": extract_author(detail),
                "email": extract_email(detail),
                "subject": extract_subject(detail),
                "version": extract_version(detail),
                "web_url": extract_web_url(detail),
                "archive_url": extract_archive_url(detail),
                "total": extract_total(detail),
                "current": extract_current(detail),
                "summary": "",  # 默认为空
            }

            # 3. detail 模式：调用 LKML agent
            if state.level == "detail":
                message_id = extract_message_id_from_cover(detail)
                if message_id:
                    try:
                        # 调用 LKML agent
                        lkml_result = run_lkml_agent(
                            lkml_id=message_id,
                            level=state.level,
                            verbose=state.verbose
                        )
                        # 提取摘要
                        result["summary"] = lkml_result.get("summary", "")
                        result["analysis"] = lkml_result.get("analysis", "")
                    except Exception as e:
                        print(f"警告: series {series_id} 的 LKML agent 分析失败: {e}")
                        result["summary"] = "分析失败"

            # 4. simple 模式：使用 patchwork API 的简要描述
            elif state.level == "simple":
                result["summary"] = extract_brief_summary(detail)

            return result

        except Exception as e:
            # 单个 series 失败不影响其他
            print(f"处理 series {series_id} 失败: {e}")
            return None

    # 根据并行度选择处理方式
    if state.max_parallel == 1:
        # 串行处理
        results = []
        for i, series_id in enumerate(state.series_list, 1):
            print(f"[{i}/{len(state.series_list)}] 处理 series {series_id}...")
            result = process_single_series(series_id)
            if result:
                results.append(result)
    else:
        # 并发处理
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = []
        with ThreadPoolExecutor(max_workers=state.max_parallel) as executor:
            futures = {executor.submit(process_single_series, sid): sid
                      for sid in state.series_list}

            for i, future in enumerate(as_completed(futures), 1):
                series_id = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        print(f"[{i}/{len(state.series_list)}] series {series_id} 处理完成")
                except Exception as e:
                    print(f"[{i}/{len(state.series_list)}] series {series_id} 失败: {e}")
                    continue

    state.processed_results = results
    return state
```

**输出**: `state.processed_results = [{series_id, date, author, ...}, ...]`

---

### 第三部分: 输出和缓存节点设计

#### 6. `aggregate_results` 节点

**功能**: 汇聚处理结果，生成 Markdown 表格行（完全沿用 LKML agent 格式）

**实现逻辑**:
```python
def aggregate_results(state: PatchworkAgentState) -> PatchworkAgentState:
    """汇聚处理结果，生成 Markdown 表格行"""

    output_lines = []

    for result in state.processed_results:
        # 格式化摘要（用于表格显示）
        formatted_summary = format_text_for_markdown(result.get("summary", ""))

        # 提取字段
        date = result["date"]
        author = result["author"]
        email = result["email"]
        subject = result["subject"]
        web_url = result["web_url"]
        archive_url = result["archive_url"]
        version = result["version"]

        # 提取补丁数量信息（如果有）
        total = result.get("total", "")
        current = result.get("current", "")

        # 完全沿用 LKML agent 的表格行格式
        if not total:
            # 单补丁格式
            line = f"| {date} | {author} <{email}> | [{subject}]({web_url}) | {formatted_summary} | v{version} ☐☑✓ | [LORE]({archive_url}) |"
        else:
            # 补丁集格式
            line = f"| {date} | {author} <{email}> | [{subject}]({web_url}) | {formatted_summary} | v{version} ☐☑✓ | [{date}, LORE v{version}, {current}/{total}]({archive_url}) |"

        output_lines.append(line)

    state.output_lines = output_lines
    return state
```

---

#### 7. `output_results` 节点

**功能**: 输出最终的 Markdown 表格和详细分析（完全沿用 LKML agent）

**实现逻辑**:
```python
def output_results(state: PatchworkAgentState) -> PatchworkAgentState:
    """输出最终结果（完全沿用 LKML agent 格式）"""

    # 打印基本信息
    print()
    print("| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |")
    print("|:---:|:----:|:---:|:----:|:---------:|:----:|")

    # 打印表格行
    for line in state.output_lines:
        print(line)

    # detail 模式：打印详细分析（沿用 LKML agent）
    if state.level == "detail":
        for result in state.processed_results:
            if result.get("analysis"):
                if state.verbose >= 2:
                    print(f"\n=== Series {result['series_id']} 详细分析 ===\n")
                if state.verbose >= 3:
                    print(result["analysis"])

    return state
```

---

#### 8. `cache_results` 节点

**功能**: 缓存结果到文件系统

**实现逻辑**:
```python
def cache_results(state: PatchworkAgentState) -> PatchworkAgentState:
    """缓存结果到文件系统"""

    # 设置缓存目录
    if not state.cache_dir:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        state.cache_dir = os.path.join(repo_root, "output", "patchwork")

    # 根据项目和日期创建子目录
    project_str = "_".join(map(str, state.project_ids))
    date_str = state.date_range["start"]
    cache_subdir = os.path.join(state.cache_dir, project_str, date_str)
    os.makedirs(cache_subdir, exist_ok=True)

    # 缓存汇总结果文件
    summary_file = os.path.join(cache_subdir, "summary.md")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("# Patchwork Analysis Summary\n\n")
        f.write(f"**项目:** {project_str}\n\n")
        f.write(f"**日期范围:** {state.date_range['start']} - {state.date_range['end']}\n\n")
        f.write(f"**分析级别:** {state.level}\n\n")
        f.write(f"**Series数量:** {len(state.processed_results)}\n\n")
        f.write("---\n\n")

        # 写入表格
        f.write("| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |\n")
        f.write("|:---:|:----:|:---:|:----:|:---------:|:----:|\n")
        for line in state.output_lines:
            f.write(line + "\n")

    # detail 模式：缓存详细分析结果
    if state.level == "detail":
        for result in state.processed_results:
            if result.get("analysis"):
                detail_file = os.path.join(cache_subdir, f"series_{result['series_id']}_detail.md")
                with open(detail_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Series {result['series_id']} 详细分析\n\n")
                    f.write(f"**日期:** {result['date']}\n\n")
                    f.write(f"**作者:** {result['author']} <{result['email']}\n\n")
                    f.write(f"**主题:** {result['subject']}\n\n")
                    f.write(f"**摘要:** {result['summary']}\n\n")
                    if result.get("analysis"):
                        f.write("\n## 详细分析\n\n")
                        f.write(result["analysis"])

    if state.verbose >= 2:
        print(f"\n结果已缓存到: {cache_subdir}")

    return state
```

---

### 第四部分: 辅助函数和工具函数设计

#### 核心辅助函数

##### 1. `fetch_with_cache` 函数

**功能**: 带缓存的 HTTP 请求函数

**实现逻辑**:
```python
def fetch_with_cache(url: str, cache_dir: str, verbose: int = 0) -> Any:
    """带缓存的 HTTP 请求"""

    # 计算缓存文件名（基于 URL 的 hash）
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    cache_file = os.path.join(cache_dir, f"{url_hash}.json")

    # 检查缓存
    if os.path.exists(cache_file):
        if verbose >= 2:
            print(f"从缓存读取: {cache_file}")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    # 发起请求
    if verbose >= 2:
        print(f"请求 URL: {url}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        # 保存缓存
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if verbose >= 2:
            print(f"缓存保存到: {cache_file}")

        return data
    except Exception as e:
        print(f"请求失败: {e}")
        return None
```

---

##### 2. `fetch_series_detail` 函数

**功能**: 获取单个 series 的详细信息（带缓存）

**实现逻辑**:
```python
def fetch_series_detail(series_id: int, cache_dir: str, verbose: int = 0) -> Dict:
    """获取 series 详细信息"""

    url = f"https://patchwork.kernel.org/api/series/{series_id}/?format=json&archive=both"

    # 使用缓存机制
    detail = fetch_with_cache(url, cache_dir, verbose)

    if not detail:
        raise Exception(f"无法获取 series {series_id} 的详细信息")

    return detail
```

---

##### 3. 字段提取函数系列

**功能**: 从 series detail JSON 中提取各种字段

```python
def extract_date(detail: Dict) -> str:
    """提取日期"""
    # 从 patches[0] 或 cover_letter 中提取日期
    date_str = detail.get("patches", [{}])[0].get("date", "")
    if not date_str:
        date_str = detail.get("cover_letter", {}).get("date", "")

    if date_str:
        # 转换为 YYYY/MM/DD 格式
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
            return dt.strftime("%Y/%m/%d")
        except:
            return date_str[:10].replace("-", "/")
    return ""

def extract_author(detail: Dict) -> str:
    """提取作者"""
    return detail.get("submitter", {}).get("name", "Unknown")

def extract_email(detail: Dict) -> str:
    """提取邮箱"""
    return detail.get("submitter", {}).get("email", "unknown@example.com")

def extract_subject(detail: Dict) -> str:
    """提取主题"""
    # 优先使用 name，其次使用 patches[0].name
    subject = detail.get("name", "")
    if not subject:
        subject = detail.get("patches", [{}])[0].get("name", "")
    return subject

def extract_version(detail: Dict) -> str:
    """提取版本"""
    version = detail.get("version", "1")
    if len(str(version)) > 10:
        return "1"
    return str(version)

def extract_web_url(detail: Dict) -> str:
    """提取 web URL"""
    # 优先使用 cover_letter.web_url，其次使用 patches[0].web_url
    url = detail.get("cover_letter", {}).get("web_url", "")
    if not url:
        url = detail.get("patches", [{}])[0].get("web_url", "")
    return url

def extract_archive_url(detail: Dict) -> str:
    """提取 archive URL"""
    # 优先使用 cover_letter.list_archive_url，其次使用 patches[0].list_archive_url
    url = detail.get("cover_letter", {}).get("list_archive_url", "")
    if not url:
        url = detail.get("patches", [{}])[0].get("list_archive_url", "")
    return url

def extract_total(detail: Dict) -> str:
    """提取总补丁数"""
    return str(detail.get("total", ""))

def extract_current(detail: Dict) -> str:
    """提取当前补丁编号"""
    # 通常为 0 或 1，表示 cover letter 或第一个补丁
    return "0"

def extract_message_id_from_cover(detail: Dict) -> str:
    """从 cover_letter 提取 message-id（用于调用 LKML agent）"""
    # 从 list_archive_url 中提取 message-id
    archive_url = extract_archive_url(detail)

    # 格式: https://lore.kernel.org/r/20220124025205.329752-1-liupeng256@huawei.com
    # 或: https://lore.kernel.org/linux-mm/20220124025205.329752-1-liupeng256@huawei.com/

    match = re.search(r'lore\.kernel\.org/[^/]+/([^/]+)', archive_url)
    if match:
        return match.group(1)

    # 尝试其他格式
    match = re.search(r'/([0-9]{8,}[^/]+)', archive_url)
    if match:
        return match.group(1)

    return None

def extract_brief_summary(detail: Dict) -> str:
    """提取简要摘要（用于 simple 模式）"""
    # 使用 subject 作为简要摘要
    return extract_subject(detail)
```

---

##### 4. `load_projects_list` 函数

**功能**: 加载项目列表（从 projects_list.md）

**实现逻辑**:
```python
def load_projects_list() -> Dict[str, int]:
    """加载项目列表"""

    # 从 projects_list.md 文件读取
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects_file = os.path.join(repo_root, "patchwork", "project", "projects_list.md")

    if not os.path.exists(projects_file):
        # 文件不存在，从 API 获取
        return fetch_projects_from_api()

    # 解析 Markdown 表格
    projects_map = {}
    with open(projects_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[2:]:  # 跳过表头和分隔行
            if line.strip():
                parts = line.split("|")
                if len(parts) >= 3:
                    id_str = parts[1].strip()
                    name = parts[2].strip()
                    if id_str.isdigit():
                        id = int(id_str)
                        projects_map[str(id)] = id
                        projects_map[name] = id

    return projects_map

def fetch_projects_from_api() -> Dict[str, int]:
    """从 Patchwork API 获取项目列表"""

    url = "https://patchwork.kernel.org/api/projects/"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        projects = response.json()

        projects_map = {}
        for project in projects:
            id = project["id"]
            name = project["name"]
            projects_map[str(id)] = id
            projects_map[name] = id

        return projects_map
    except Exception as e:
        print(f"获取项目列表失败: {e}")
        return {}

def find_project_id_by_name(name: str, projects_map: Dict[str, int]) -> Optional[int]:
    """根据名称查找项目 ID"""

    # 精确匹配
    if name in projects_map:
        return projects_map[name]

    # 模糊匹配（部分匹配）
    for key, id in projects_map.items():
        if name.lower() in key.lower():
            return id

    return None
```

---

### 第五部分: 工作流构建和入口函数

#### 1. `build_patchwork_agent` 函数

**功能**: 构建 LangGraph 工作流

**实现逻辑**:
```python
def build_patchwork_agent():
    """构建 Patchwork agent 工作流"""

    workflow = StateGraph(PatchworkAgentState)

    # 添加节点
    workflow.add_node("fetch_project_info", fetch_project_info)
    workflow.add_node("calculate_date_range", calculate_date_range)
    workflow.add_node("fetch_series_list", fetch_series_list)
    workflow.add_node("filter_and_sort", filter_and_sort)
    workflow.add_node("process_series", process_series)
    workflow.add_node("aggregate_results", aggregate_results)
    workflow.add_node("output_results", output_results)
    workflow.add_node("cache_results", cache_results)

    # 设置入口点
    workflow.set_entry_point("fetch_project_info")

    # 添加边（顺序执行）
    workflow.add_edge("fetch_project_info", "calculate_date_range")
    workflow.add_edge("calculate_date_range", "fetch_series_list")
    workflow.add_edge("fetch_series_list", "filter_and_sort")
    workflow.add_edge("filter_and_sort", "process_series")
    workflow.add_edge("process_series", "aggregate_results")
    workflow.add_edge("aggregate_results", "output_results")
    workflow.add_edge("output_results", "cache_results")
    workflow.add_edge("cache_results", END)

    return workflow.compile()
```

---

#### 2. `run_patchwork_agent` 主运行函数

**功能**: 运行 Patchwork agent

**实现逻辑**:
```python
def run_patchwork_agent(
    projects: List[str],
    date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: Optional[int] = None,
    level: str = "simple",
    max_series: Optional[int] = None,
    max_parallel: int = 1,
    work_dir: str = None,
    verbose: int = 0
):
    """运行 Patchwork agent"""

    # 打印初始日志
    if verbose >= 1:
        print()
        print("---------------------")
        print(f"运行 Patchwork agent (级别: {level})")
        print(f"项目: {', '.join(projects)}")

        # 打印日期模式
        if days:
            print(f"日期: 最近 {days} 天")
        elif date and end_date:
            print(f"日期: {date} 至 {end_date}")
        elif date:
            print(f"日期: {date}")
        else:
            print(f"日期: 今天")

        if max_series:
            print(f"最大 series 数量: {max_series}")
        if max_parallel > 1:
            print(f"并行度: {max_parallel}")
        print("---------------------")
        print()

    # 构建工作流
    agent = build_patchwork_agent()

    # 初始化状态
    initial_state = PatchworkAgentState(
        messages=[{
            "role": "system",
            "content": "你是一个 Patchwork 补丁分析智能体，负责从 Patchwork API 获取和分析 Linux 内核补丁系列。"
        }],
        projects=projects,
        date=date,
        end_date=end_date,
        days=days,
        level=level,
        max_series=max_series,
        max_parallel=max_parallel,
        work_dir=work_dir,
        verbose=verbose
    )

    # 运行工作流
    result = agent.invoke(initial_state)

    return result
```

---

#### 3. `parse_args` 命令行参数解析

**功能**: 解析命令行参数

**实现逻辑**:
```python
def parse_args():
    """解析命令行参数"""

    import argparse

    parser = argparse.ArgumentParser(
        description="Patchwork 补丁分析智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析 Linux MM 项目今天的补丁（simple 模式）
  python patchwork_agent.py --project 365 --level simple

  # 分析 Linux MM 项目指定日期的补丁（detail 模式）
  python patchwork_agent.py --project 365 --date 2022-01-24 --level detail

  # 分析 Linux MM 和 Linux BTRFS 项目最近 7 天的补丁
  python patchwork_agent.py --project 365 19 --days 7 --level simple

  # 使用项目名称
  python patchwork_agent.py --project "Linux MM" --days 7 --max-series 10

  # 日期范围 + 并发处理
  python patchwork_agent.py --project 365 --date 2022-01-24 --end-date 2022-01-26 --max-parallel 3
"""
    )

    parser.add_argument(
        "--project",
        type=str,
        nargs="+",
        required=True,
        help="项目 ID 或名称（支持多值）"
    )

    parser.add_argument(
        "--date",
        type=str,
        help="开始日期（格式：YYYY-MM-DD）"
    )

    parser.add_argument(
        "--end-date",
        type=str,
        help="结束日期（配合 --date 使用）"
    )

    parser.add_argument(
        "--days",
        type=int,
        help="最近 N 天（替代 --date）"
    )

    parser.add_argument(
        "--level",
        type=str,
        choices=["simple", "detail"],
        default="simple",
        help="分析级别：simple（简要分析）或 detail（详细分析）"
    )

    parser.add_argument(
        "--max-series",
        type=int,
        help="最大 series 数量限制"
    )

    parser.add_argument(
        "--max-parallel",
        type=int,
        default=1,
        help="并发处理的最大并行度（默认：1）"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="详细程度：-v（操作），-vv（日志），-vvv（全量结果）"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    run_patchwork_agent(
        projects=args.project,
        date=args.date,
        end_date=args.end_date,
        days=args.days,
        level=args.level,
        max_series=args.max_series,
        max_parallel=args.max_parallel,
        verbose=args.verbose
    )
```

---

## 测试用例设计

### test_patchwork.sh 测试脚本

测试场景：

1. **简单模式测试**（通过 kde.py）
   - 单项目 ID + 单日期
   - 多项目 ID + 单日期
   - 项目名称 + 单日期

2. **详细模式测试**（通过 kde.py）
   - 单项目 ID + 单日期 + detail 模式

3. **日期模式测试**
   - 最近 N 天模式
   - 日期范围模式

4. **并发测试**
   - max_parallel = 1（串行）
   - max_parallel = 3（并发）

5. **限制数量测试**
   - max_series = 5

6. **直接调用测试**
   - 直接调用 patchwork_agent.py

---

## 文件结构

```
patchwork/
├── patchwork_agent.py    # 新增：基于 LangGraph 的 Patchwork agent
├── __init__.py           # 新增：模块初始化文件
├── get_patchwork_project.sh  # 保留：获取项目列表的 shell 脚本
├── get_patchwork_series.sh   # 保留：获取补丁系列的 shell 脚本
├── batch.sh              # 保留：批量处理脚本
├── project/              # 保留：项目数据目录
│   └── projects_list.md  # 保留：项目列表
└── README.md             # 需更新：更新文档，添加 agent 使用说明

test/
├── test_patchwork.sh     # 新增：Patchwork agent 测试脚本
└── test_all.sh           # 需更新：添加 patchwork 测试到总测试脚本
```

---

## 集成到 kde.py

在 kde.py 中添加 patchwork 运行入口：

```python
def patchwork_run(projects, date=None, end_date=None, days=None, level="simple",
                  max_series=None, max_parallel=1, verbose=0):
    """运行 Patchwork agent 分析补丁系列"""
    try:
        from patchwork.patchwork_agent import run_patchwork_agent
        run_patchwork_agent(
            projects=projects,
            date=date,
            end_date=end_date,
            days=days,
            level=level,
            max_series=max_series,
            max_parallel=max_parallel,
            verbose=verbose
        )
    except Exception as e:
        print(f"运行 Patchwork agent 失败: {e}")
        sys.exit(1)

# 在 argparse 中添加 patchwork 参数
group.add_argument('--patchwork', type=str, nargs='+',
                   help='运行 Patchwork agent，指定项目 ID 或名称')
```

---

## 下一步

设计文档已完成，接下来调用 `writing-plans` skill 创建详细的实现计划。
