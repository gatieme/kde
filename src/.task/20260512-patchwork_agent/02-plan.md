# Patchwork Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现基于 LangGraph 的 Patchwork agent，支持获取和分析 Linux 内核补丁系列，集成 LKML agent 进行深度分析，补齐测试用例。

**Architecture:** 使用 LangGraph StateGraph 构建顺序工作流，包含 8 个节点：解析项目参数 → 计算日期范围 → 获取 series 列表 → 过滤排序 → 并发处理 series → 汇聚结果 → 输出表格 → 缓存结果。支持两级分析模式（simple/detail），可配置并发度。

**Tech Stack:** Python, LangGraph, requests, concurrent.futures.ThreadPoolExecutor, tqdm, model.ModelInference

---

## Task 1: 创建模块基础结构和状态定义

**Files:**
- Create: `patchwork/__init__.py`
- Create: `patchwork/patchwork_agent.py:1-60`

**Step 1: 创建 __init__.py**

```python
# -*- coding: utf-8 -*-
"""
Patchwork Agent Module

LangGraph-based agent for analyzing Linux kernel patch series from Patchwork API.
"""

from .patchwork_agent import run_patchwork_agent, build_patchwork_agent

__all__ = ['run_patchwork_agent', 'build_patchwork_agent']
```

**Step 2: 创建 patchwork_agent.py 文件头部和导入**

```python
# -*- coding: utf-8 -*-

import os
import sys
import re
import json
import datetime
import hashlib
import requests
from typing import Annotated, List, Dict, Any, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import format_text_for_markdown
from model import ModelInference, ModelRequest
from lkml.lkml_agent import run_lkml_agent
```

**Step 3: 定义 PatchworkAgentState 状态类**

```python
@dataclass
class PatchworkAgentState:
    messages: Annotated[List[Dict[str, Any]], add_messages]
    
    # 输入参数
    projects: List[str] = field(default_factory=list)
    date: Optional[str] = None
    end_date: Optional[str] = None
    days: Optional[int] = None
    level: str = "simple"
    max_series: Optional[int] = None
    max_parallel: int = 1
    verbose: int = 0
    
    # 中间状态
    project_ids: List[int] = field(default_factory=list)
    date_range: Dict[str, str] = field(default_factory=dict)
    series_list: List[int] = field(default_factory=list)
    series_details: Dict[int, Dict] = field(default_factory=dict)
    
    # 输出结果
    processed_results: List[Dict[str, Any]] = field(default_factory=list)
    output_lines: List[str] = field(default_factory=list)
    
    # 工作目录和缓存
    work_dir: str = ""
    cache_dir: str = ""
```

**Step 4: 验证文件创建**

Run: `ls -la patchwork/`
Expected: 看到 `__init__.py` 和 `patchwork_agent.py` 文件

**Step 5: Commit**

```bash
git add patchwork/__init__.py patchwork/patchwork_agent.py
git commit -m "feat(patchwork): create module structure and state definition"
```

---

## Task 2: 实现辅助函数 - 项目列表加载和缓存机制

**Files:**
- Modify: `patchwork/patchwork_agent.py:61-120`

**Step 1: 编写 fetch_with_cache 函数**

```python
def fetch_with_cache(url: str, cache_dir: str, verbose: int = 0) -> Any:
    """带缓存的 HTTP 请求"""
    
    if not cache_dir:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(repo_root, "output", "patchwork", "cache")
    
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

**Step 2: 编写 load_projects_list 函数**

```python
def load_projects_list() -> Dict[str, int]:
    """加载项目列表"""
    
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects_file = os.path.join(repo_root, "patchwork", "project", "projects_list.md")
    
    if not os.path.exists(projects_file):
        return fetch_projects_from_api()
    
    # 解析 Markdown 表格
    projects_map = {}
    with open(projects_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[2:]:
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

**Step 3: 编写测试验证函数**

```python
# 测试代码（临时添加到文件末尾）
if __name__ == "__main__":
    # 测试项目列表加载
    projects_map = load_projects_list()
    print(f"加载了 {len(projects_map)} 个项目")
    
    # 测试查找
    id = find_project_id_by_name("Linux MM", projects_map)
    print(f"Linux MM 项目 ID: {id}")
    
    # 测试缓存
    url = "https://patchwork.kernel.org/api/series/607689/?format=json"
    data = fetch_with_cache(url, "", verbose=2)
    print(f"获取 series 数据: {data.get('id', 'N/A')}")
```

**Step 4: 运行测试验证**

Run: `python patchwork/patchwork_agent.py`
Expected: 
- 成功加载项目列表
- 正确找到 Linux MM 的 ID（365）
- 成功获取 series 数据并缓存

**Step 5: 移除测试代码并 Commit**

```bash
# 移除测试代码
git add patchwork/patchwork_agent.py
git commit -m "feat(patchwork): implement project list loader and cache functions"
```

---

## Task 3: 实现字段提取函数系列

**Files:**
- Modify: `patchwork/patchwork_agent.py:121-200`

**Step 1: 编写字段提取函数**

```python
def extract_date(detail: Dict) -> str:
    """提取日期"""
    date_str = detail.get("patches", [{}])[0].get("date", "")
    if not date_str:
        date_str = detail.get("cover_letter", {}).get("date", "")
    
    if date_str:
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
    url = detail.get("cover_letter", {}).get("web_url", "")
    if not url:
        url = detail.get("patches", [{}])[0].get("web_url", "")
    return url

def extract_archive_url(detail: Dict) -> str:
    """提取 archive URL"""
    url = detail.get("cover_letter", {}).get("list_archive_url", "")
    if not url:
        url = detail.get("patches", [{}])[0].get("list_archive_url", "")
    return url

def extract_total(detail: Dict) -> str:
    """提取总补丁数"""
    return str(detail.get("total", ""))

def extract_current(detail: Dict) -> str:
    """提取当前补丁编号"""
    return "0"

def extract_message_id_from_cover(detail: Dict) -> Optional[str]:
    """从 cover_letter 提取 message-id"""
    archive_url = extract_archive_url(detail)
    
    if not archive_url:
        return None
    
    # 格式1: https://lore.kernel.org/r/20220124025205.329752-1-liupeng256@huawei.com
    match = re.search(r'lore\.kernel\.org/r/([^/]+)', archive_url)
    if match:
        return match.group(1)
    
    # 格式2: https://lore.kernel.org/linux-mm/20220124025205.329752-1-liupeng256@huawei.com/
    match = re.search(r'lore\.kernel\.org/[^/]+/([^/]+)', archive_url)
    if match:
        return match.group(1)
    
    # 格式3: https://patch.msgid.link/xxx
    match = re.search(r'patch\.msgid\.link/([^/]+)', archive_url)
    if match:
        return match.group(1)
    
    return None

def extract_brief_summary(detail: Dict) -> str:
    """提取简要摘要"""
    return extract_subject(detail)

def fetch_series_detail(series_id: int, cache_dir: str, verbose: int = 0) -> Dict:
    """获取 series 详细信息"""
    url = f"https://patchwork.kernel.org/api/series/{series_id}/?format=json&archive=both"
    
    detail = fetch_with_cache(url, cache_dir, verbose)
    
    if not detail:
        raise Exception(f"无法获取 series {series_id} 的详细信息")
    
    return detail
```

**Step 2: 编写测试验证**

```python
# 测试代码（临时）
if __name__ == "__main__":
    # 获取一个真实的 series 进行测试
    url = "https://patchwork.kernel.org/api/series/607689/?format=json"
    detail = fetch_with_cache(url, "")
    
    print(f"Date: {extract_date(detail)}")
    print(f"Author: {extract_author(detail)}")
    print(f"Email: {extract_email(detail)}")
    print(f"Subject: {extract_subject(detail)}")
    print(f"Version: {extract_version(detail)}")
    print(f"Web URL: {extract_web_url(detail)}")
    print(f"Archive URL: {extract_archive_url(detail)}")
    print(f"Message ID: {extract_message_id_from_cover(detail)}")
    print(f"Total: {extract_total(detail)}")
```

**Step 3: 运行测试验证**

Run: `python patchwork/patchwork_agent.py`
Expected: 成功提取所有字段，输出符合预期

**Step 4: Commit**

```bash
git add patchwork/patchwork_agent.py
git commit -m "feat(patchwork): implement field extraction functions"
```

---

## Task 4: 实现工作流节点 - fetch_project_info 和 calculate_date_range

**Files:**
- Modify: `patchwork/patchwork_agent.py:201-280`

**Step 1: 实现 fetch_project_info 节点**

```python
def fetch_project_info(state: PatchworkAgentState) -> PatchworkAgentState:
    """解析项目参数，将名称转换为 ID"""
    
    if state.verbose >= 2:
        print("=== 解析项目参数 ===\n")
    
    projects_map = load_projects_list()
    
    project_ids = []
    for project in state.projects:
        if project.isdigit():
            project_ids.append(int(project))
            if state.verbose >= 2:
                print(f"项目 ID: {project}")
        else:
            matched_id = find_project_id_by_name(project, projects_map)
            if matched_id:
                project_ids.append(matched_id)
                if state.verbose >= 2:
                    print(f"项目名称 '{project}' -> ID: {matched_id}")
            else:
                print(f"警告: 未找到项目 '{project}'，跳过")
    
    if not project_ids:
        raise Exception("没有有效的项目 ID")
    
    state.project_ids = project_ids
    
    if state.verbose >= 1:
        print(f"解析后的项目 ID: {', '.join(map(str, project_ids))}")
    
    return state
```

**Step 2: 实现 calculate_date_range 节点**

```python
def calculate_date_range(state: PatchworkAgentState) -> PatchworkAgentState:
    """计算日期范围"""
    
    if state.verbose >= 2:
        print("=== 计算日期范围 ===\n")
    
    if state.days:
        # 最近 N 天模式
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=state.days - 1)
        state.date_range = {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d")
        }
        if state.verbose >= 2:
            print(f"最近 {state.days} 天: {state.date_range['start']} 至 {state.date_range['end']}")
    
    elif state.date and state.end_date:
        # 日期范围模式
        state.date_range = {
            "start": state.date,
            "end": state.end_date
        }
        if state.verbose >= 2:
            print(f"日期范围: {state.date_range['start']} 至 {state.date_range['end']}")
    
    elif state.date:
        # 单日期模式
        state.date_range = {
            "start": state.date,
            "end": state.date
        }
        if state.verbose >= 2:
            print(f"单日期: {state.date_range['start']}")
    
    else:
        # 默认：今天
        today = datetime.date.today().strftime("%Y-%m-%d")
        state.date_range = {"start": today, "end": today}
        if state.verbose >= 2:
            print(f"默认（今天）: {today}")
    
    return state
```

**Step 3: 编写单元测试验证**

```python
# 测试代码（临时）
if __name__ == "__main__":
    # 测试 fetch_project_info
    state1 = PatchworkAgentState(
        messages=[],
        projects=["365", "Linux MM"],
        verbose=2
    )
    state1 = fetch_project_info(state1)
    print(f"项目 IDs: {state1.project_ids}")
    
    # 测试 calculate_date_range - 各种模式
    # 单日期
    state2 = PatchworkAgentState(
        messages=[],
        date="2022-01-24",
        verbose=2
    )
    state2 = calculate_date_range(state2)
    print(f"单日期范围: {state2.date_range}")
    
    # 日期范围
    state3 = PatchworkAgentState(
        messages=[],
        date="2022-01-24",
        end_date="2022-01-26",
        verbose=2
    )
    state3 = calculate_date_range(state3)
    print(f"日期范围: {state3.date_range}")
    
    # 最近 N 天
    state4 = PatchworkAgentState(
        messages=[],
        days=7,
        verbose=2
    )
    state4 = calculate_date_range(state4)
    print(f"最近 7 天: {state4.date_range}")
```

**Step 4: 运行测试验证**

Run: `python patchwork/patchwork_agent.py`
Expected: 
- 成功解析项目 ID 和名称
- 各种日期模式正确计算

**Step 5: Commit**

```bash
git add patchwork/patchwork_agent.py
git commit -m "feat(patchwork): implement fetch_project_info and calculate_date_range nodes"
```

---

## Task 5: 实现工作流节点 - fetch_series_list 和 filter_and_sort

**Files:**
- Modify: `patchwork/patchwork_agent.py:281-380`

**Step 1: 实现 fetch_series_list 节点**

```python
def fetch_series_list(state: PatchworkAgentState) -> PatchworkAgentState:
    """从 Patchwork API 获取 series 列表"""
    
    if state.verbose >= 2:
        print("=== 获取 series 列表 ===\n")
    
    # 设置缓存目录
    if not state.cache_dir:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        state.cache_dir = os.path.join(repo_root, "output", "patchwork", "cache")
    
    all_series_ids = []
    
    for project_id in state.project_ids:
        start_date = state.date_range["start"]
        end_date = state.date_range["end"]
        
        # 对每个日期循环
        current_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_datetime = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        
        while current_date <= end_datetime:
            date_str = current_date.strftime("%Y-%m-%d")
            
            # API URL
            url = f"https://patchwork.kernel.org/api/series/?project={project_id}&archive=both&format=json&before={date_str}T23%3A59%3A59&since={date_str}T00%3A00%3A00"
            
            if state.verbose >= 2:
                print(f"获取项目 {project_id} 在 {date_str} 的 series...")
            
            # 获取并解析
            series_json = fetch_with_cache(url, state.cache_dir, state.verbose)
            
            if series_json:
                series_ids = [s["id"] for s in series_json]
                all_series_ids.extend(series_ids)
                
                if state.verbose >= 2:
                    print(f"  找到 {len(series_ids)} 个 series")
            
            current_date += datetime.timedelta(days=1)
    
    state.series_list = all_series_ids
    
    if state.verbose >= 1:
        print(f"\n总共找到 {len(all_series_ids)} 个 series")
    
    return state
```

**Step 2: 实现 filter_and_sort 节点**

```python
def filter_and_sort(state: PatchworkAgentState) -> PatchworkAgentState:
    """过滤和排序 series 列表"""
    
    if state.verbose >= 2:
        print("=== 过滤和排序 series ===\n")
    
    # 去重
    unique_series_ids = list(set(state.series_list))
    
    if state.verbose >= 2:
        print(f"去重后: {len(unique_series_ids)} 个 series")
    
    # 获取每个 series 的日期用于排序
    series_with_date = []
    for series_id in unique_series_ids:
        try:
            detail = fetch_series_detail(series_id, state.cache_dir, state.verbose)
            date_str = extract_date(detail)
            series_with_date.append({
                "id": series_id,
                "date": date_str
            })
        except Exception as e:
            print(f"警告: 无法获取 series {series_id} 的日期: {e}")
    
    # 按时间倒序排列
    series_with_date.sort(key=lambda x: x["date"], reverse=True)
    
    if state.verbose >= 2:
        print(f"排序完成")
    
    # 应用数量限制
    if state.max_series:
        series_with_date = series_with_date[:state.max_series]
        if state.verbose >= 2:
            print(f"限制数量到 {state.max_series} 个")
    
    state.series_list = [s["id"] for s in series_with_date]
    state.series_details = {s["id"]: s for s in series_with_date}
    
    if state.verbose >= 1:
        print(f"最终处理 {len(state.series_list)} 个 series")
    
    return state
```

**Step 3: 编写测试验证**

```python
# 测试代码（临时）
if __name__ == "__main__":
    # 测试完整流程：项目解析 -> 日期计算 -> 获取 series -> 过滤排序
    state = PatchworkAgentState(
        messages=[],
        projects=["365"],
        date="2022-01-24",
        max_series=5,
        verbose=2
    )
    
    print("\n=== 测试完整流程 ===\n")
    
    state = fetch_project_info(state)
    state = calculate_date_range(state)
    state = fetch_series_list(state)
    state = filter_and_sort(state)
    
    print(f"\n最终 series IDs: {state.series_list}")
```

**Step 4: 运行测试验证**

Run: `python patchwork/patchwork_agent.py`
Expected:
- 成功获取 series 列表
- 正确排序和过滤

**Step 5: Commit**

```bash
git add patchwork/patchwork_agent.py
git commit -m "feat(patchwork): implement fetch_series_list and filter_and_sort nodes"
```

---

## Task 6: 实现核心节点 - process_series（并发处理）

**Files:**
- Modify: `patchwork/patchwork_agent.py:381-500`

**Step 1: 实现 process_series 节点**

```python
def process_series(state: PatchworkAgentState) -> PatchworkAgentState:
    """处理所有 series，支持并发"""
    
    if state.verbose >= 2:
        print("=== 处理 series ===\n")
    
    def process_single_series(series_id: int) -> Dict[str, Any]:
        """处理单个 series"""
        try:
            # 1. 获取详细信息
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
                "summary": "",
                "analysis": "",
            }
            
            # 3. detail 模式：调用 LKML agent
            if state.level == "detail":
                message_id = extract_message_id_from_cover(detail)
                if message_id:
                    try:
                        if state.verbose >= 2:
                            print(f"    调用 LKML agent 分析: {message_id}")
                        
                        lkml_result = run_lkml_agent(
                            lkml_id=message_id,
                            level=state.level,
                            verbose=0  # 避免嵌套 verbose 输出
                        )
                        
                        # 提取摘要和分析
                        if isinstance(lkml_result, dict):
                            result["summary"] = lkml_result.get("summary", "")
                            result["analysis"] = lkml_result.get("analysis", "")
                        else:
                            result["summary"] = "分析完成"
                        
                    except Exception as e:
                        print(f"警告: series {series_id} 的 LKML agent 分析失败: {e}")
                        result["summary"] = "分析失败"
            
            # 4. simple 模式：使用简要描述
            elif state.level == "simple":
                result["summary"] = extract_brief_summary(detail)
            
            return result
            
        except Exception as e:
            print(f"处理 series {series_id} 失败: {e}")
            return None
    
    # 根据并行度选择处理方式
    results = []
    
    if state.max_parallel == 1:
        # 串行处理
        for i, series_id in enumerate(state.series_list, 1):
            print(f"[{i}/{len(state.series_list)}] 处理 series {series_id}...")
            result = process_single_series(series_id)
            if result:
                results.append(result)
    else:
        # 并发处理
        print(f"并发处理 {len(state.series_list)} 个 series（并行度: {state.max_parallel})...")
        
        with ThreadPoolExecutor(max_workers=state.max_parallel) as executor:
            futures = {executor.submit(process_single_series, sid): sid 
                      for sid in state.series_list}
            
            completed = 0
            for future in as_completed(futures):
                series_id = futures[future]
                completed += 1
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        print(f"[{completed}/{len(state.series_list)}] series {series_id} 完成")
                except Exception as e:
                    print(f"[{completed}/{len(state.series_list)}] series {series_id} 失败: {e}")
                    continue
    
    state.processed_results = results
    
    if state.verbose >= 1:
        print(f"\n成功处理 {len(results)} 个 series")
    
    return state
```

**Step 2: 编写测试验证**

```python
# 测试代码（临时）
if __name__ == "__main__":
    # 测试完整流程包括 process_series
    state = PatchworkAgentState(
        messages=[],
        projects=["365"],
        date="2022-01-24",
        level="simple",
        max_series=3,
        max_parallel=1,
        verbose=2
    )
    
    print("\n=== 测试完整流程（simple 模式） ===\n")
    
    state = fetch_project_info(state)
    state = calculate_date_range(state)
    state = fetch_series_list(state)
    state = filter_and_sort(state)
    state = process_series(state)
    
    print(f"\n处理结果数: {len(state.processed_results)}")
    for result in state.processed_results[:2]:
        print(f"  Series {result['series_id']}: {result['subject']}")
```

**Step 3: 运行测试验证**

Run: `python patchwork/patchwork_agent.py`
Expected:
- 成功处理 series
- 提取正确的基本信息

**Step 4: Commit**

```bash
git add patchwork/patchwork_agent.py
git commit -m "feat(patchwork): implement process_series node with parallel processing"
```

---

## Task 7: 实现输出和缓存节点 - aggregate_results, output_results, cache_results

**Files:**
- Modify: `patchwork/patchwork_agent.py:501-600`

**Step 1: 实现 aggregate_results 节点**

```python
def aggregate_results(state: PatchworkAgentState) -> PatchworkAgentState:
    """汇聚处理结果，生成 Markdown 表格行"""
    
    if state.verbose >= 2:
        print("=== 汇聚结果 ===\n")
    
    output_lines = []
    
    for result in state.processed_results:
        # 格式化摘要
        formatted_summary = format_text_for_markdown(result.get("summary", ""))
        
        # 提取字段
        date = result["date"]
        author = result["author"]
        email = result["email"]
        subject = result["subject"]
        web_url = result["web_url"]
        archive_url = result["archive_url"]
        version = result["version"]
        total = result.get("total", "")
        current = result.get("current", "")
        
        # 沿用 LKML agent 格式
        if not total:
            line = f"| {date} | {author} <{email}> | [{subject}]({web_url}) | {formatted_summary} | v{version} ☐☑✓ | [LORE]({archive_url}) |"
        else:
            line = f"| {date} | {author} <{email}> | [{subject}]({web_url}) | {formatted_summary} | v{version} ☐☑✓ | [{date}, LORE v{version}, {current}/{total}]({archive_url}) |"
        
        output_lines.append(line)
    
    state.output_lines = output_lines
    
    if state.verbose >= 2:
        print(f"生成了 {len(output_lines)} 个输出行")
    
    return state
```

**Step 2: 实现 output_results 节点**

```python
def output_results(state: PatchworkAgentState) -> PatchworkAgentState:
    """输出最终结果"""
    
    if state.verbose >= 2:
        print("=== 输出结果 ===\n")
    
    # 打印表头
    print()
    print("| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |")
    print("|:---:|:----:|:---:|:----:|:---------:|:----:|")
    
    # 打印表格行
    for line in state.output_lines:
        print(line)
    
    # detail 模式：打印详细分析
    if state.level == "detail":
        for result in state.processed_results:
            if result.get("analysis"):
                if state.verbose >= 2:
                    print(f"\n=== Series {result['series_id']} 详细分析 ===\n")
                if state.verbose >= 3:
                    print(result["analysis"])
    
    return state
```

**Step 3: 实现 cache_results 节点**

```python
def cache_results(state: PatchworkAgentState) -> PatchworkAgentState:
    """缓存结果到文件系统"""
    
    if state.verbose >= 2:
        print("=== 缓存结果 ===\n")
    
    # 设置缓存目录
    if not state.cache_dir:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        state.cache_dir = os.path.join(repo_root, "output", "patchwork")
    
    # 创建子目录
    project_str = "_".join(map(str, state.project_ids))
    date_str = state.date_range["start"]
    cache_subdir = os.path.join(state.cache_dir, project_str, date_str)
    os.makedirs(cache_subdir, exist_ok=True)
    
    # 缓存汇总文件
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
    
    # detail 模式：缓存详细分析
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
                    f.write("\n## 详细分析\n\n")
                    f.write(result["analysis"])
    
    if state.verbose >= 2:
        print(f"缓存保存到: {cache_subdir}")
    
    return state
```

**Step 4: 编写完整测试验证**

```python
# 测试代码（临时）
if __name__ == "__main__":
    # 测试完整流程
    state = PatchworkAgentState(
        messages=[],
        projects=["365"],
        date="2022-01-24",
        level="simple",
        max_series=3,
        verbose=2
    )
    
    print("\n=== 测试完整流程 ===\n")
    
    state = fetch_project_info(state)
    state = calculate_date_range(state)
    state = fetch_series_list(state)
    state = filter_and_sort(state)
    state = process_series(state)
    state = aggregate_results(state)
    state = output_results(state)
    state = cache_results(state)
    
    print("\n=== 测试完成 ===")
```

**Step 5: 运行完整测试验证**

Run: `python patchwork/patchwork_agent.py`
Expected:
- 成功运行完整流程
- 输出正确的 Markdown 表格
- 缓存文件正确保存

**Step 6: Commit**

```bash
git add patchwork/patchwork_agent.py
git commit -m "feat(patchwork): implement output and cache nodes"
```

---

## Task 8: 实现工作流构建和主入口函数

**Files:**
- Modify: `patchwork/patchwork_agent.py:601-700`

**Step 1: 实现 build_patchwork_agent 函数**

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
    
    # 添加边
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

**Step 2: 实现 run_patchwork_agent 函数**

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

**Step 3: 实现 parse_args 函数**

```python
def parse_args():
    """解析命令行参数"""
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Patchwork 补丁分析智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python patchwork_agent.py --project 365 --level simple
  python patchwork_agent.py --project 365 --date 2022-01-24 --level detail
  python patchwork_agent.py --project 365 19 --days 7 --level simple
  python patchwork_agent.py --project "Linux MM" --days 7 --max-series 10
  python patchwork_agent.py --project 365 --date 2022-01-24 --end-date 2022-01-26 --max-parallel 3
"""
    )
    
    parser.add_argument("--project", type=str, nargs="+", required=True,
                       help="项目 ID 或名称（支持多值）")
    parser.add_argument("--date", type=str, help="开始日期（YYYY-MM-DD）")
    parser.add_argument("--end-date", type=str, help="结束日期（配合 --date）")
    parser.add_argument("--days", type=int, help="最近 N 天")
    parser.add_argument("--level", type=str, choices=["simple", "detail"], default="simple",
                       help="分析级别")
    parser.add_argument("--max-series", type=int, help="最大 series 数量")
    parser.add_argument("--max-parallel", type=int, default=1, help="并行度")
    parser.add_argument("--verbose", "-v", action="count", default=0, help="详细程度")
    
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

**Step 4: 测试命令行调用**

Run: `python patchwork/patchwork_agent.py --project 365 --date 2022-01-24 --level simple --max-series 2 -v`
Expected:
- 成功运行并输出表格
- 缓存文件保存正确

**Step 5: Commit**

```bash
git add patchwork/patchwork_agent.py
git commit -m "feat(patchwork): implement workflow builder and main entry function"
```

---

## Task 9: 集成到 kde.py 主入口

**Files:**
- Modify: `kde.py:10-60`
- Modify: `kde.py:52-109`

**Step 1: 添加 patchwork 导入**

```python
# 在 kde.py 顶部导入区域添加
from patchwork.patchwork_agent import run_patchwork_agent
```

**Step 2: 实现 patchwork_run 函数**

```python
def patchwork_run(projects, date=None, end_date=None, days=None, level="simple",
                  max_series=None, max_parallel=1, verbose=0):
    """运行 Patchwork agent 分析补丁系列"""
    try:
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
```

**Step 3: 添加 argparse 参数**

```python
# 在互斥组中添加
group.add_argument('--patchwork', type=str, nargs='+',
                   help='运行 Patchwork agent，指定项目 ID 或名称')

# 在 if __name__ == "__main__" 中添加处理逻辑
elif args.patchwork:
    # 运行 Patchwork agent
    level = args.level if args.level in ['simple', 'detail'] else 'simple'
    
    print(f"运行 Patchwork agent (级别: {level})")
    print(f"项目: {', '.join(args.patchwork)}")
    print()
    
    patchwork_run(
        projects=args.patchwork,
        date=args.date if hasattr(args, 'date') else None,
        end_date=args.end_date if hasattr(args, 'end_date') else None,
        days=args.days if hasattr(args, 'days') else None,
        level=level,
        max_series=args.max_series if hasattr(args, 'max_series') else None,
        max_parallel=args.max_parallel if hasattr(args, 'max_parallel') else 1,
        verbose=args.verbose
    )
```

**Step 4: 需要添加额外的 argparse 参数**

```python
# 在 argparse 中添加 patchwork 相关参数
parser.add_argument('--date', type=str, help='日期或开始日期')
parser.add_argument('--end-date', type=str, help='结束日期')
parser.add_argument('--days', type=int, help='最近 N 天')
parser.add_argument('--max-series', type=int, help='最大 series 数量')
parser.add_argument('--max-parallel', type=int, default=1, help='并行度')
```

**Step 5: 测试通过 kde.py 调用**

Run: `python kde.py --patchwork 365 --date 2022-01-24 --level simple --max-series 2 -v`
Expected:
- 成功调用并输出结果

**Step 6: Commit**

```bash
git add kde.py
git commit -m "feat(kde): integrate patchwork agent into main entry point"
```

---

## Task 10: 创建测试脚本 test_patchwork.sh

**Files:**
- Create: `test/test_patchwork.sh`

**Step 1: 创建测试脚本框架**

```bash
#!/bin/bash

# Patchwork agent 测试脚本

# 获取项目根目录
PROJECT_ROOT=$(dirname "$(dirname "$(realpath "$0")")")

# 测试命令列表
test_commands=(
    # 通过 kde.py 测试 Patchwork agent - simple 模式
    "python3 \"$PROJECT_ROOT/kde.py\" --patchwork 365 --date 2022-01-24 --level simple --max-series 2"
    
    # 通过 kde.py 测试 Patchwork agent - detail 模式
    "python3 \"$PROJECT_ROOT/kde.py\" --patchwork 365 --date 2022-01-24 --level detail --max-series 1"
    
    # 直接调用 patchwork_agent.py - simple 模式
    "python3 \"$PROJECT_ROOT/patchwork/patchwork_agent.py\" --project 365 --date 2022-01-24 --level simple --max-series 2"
    
    # 直接调用 patchwork_agent.py - detail 模式
    "python3 \"$PROJECT_ROOT/patchwork/patchwork_agent.py\" --project 365 --date 2022-01-24 --level detail --max-series 1"
    
    # 测试最近 N 天模式
    "python3 \"$PROJECT_ROOT/patchwork/patchwork_agent.py\" --project 365 --days 1 --level simple --max-series 3"
    
    # 测试多项目
    "python3 \"$PROJECT_ROOT/patchwork/patchwork_agent.py\" --project 365 19 --date 2022-01-24 --level simple --max-series 3"
    
    # 测试项目名称
    "python3 \"$PROJECT_ROOT/patchwork/patchwork_agent.py\" --project \"Linux MM\" --date 2022-01-24 --level simple --max-series 2"
    
    # 测试并发处理
    "python3 \"$PROJECT_ROOT/patchwork/patchwork_agent.py\" --project 365 --date 2022-01-24 --level simple --max-series 5 --max-parallel 2"
    
    # 测试 verbose 模式
    "python3 \"$PROJECT_ROOT/patchwork/patchwork_agent.py\" --project 365 --date 2022-01-24 --level simple --max-series 1 -v"
)

# 测试名称列表
test_names=(
    "Patchwork simple 模式测试（通过 kde.py）"
    "Patchwork detail 模式测试（通过 kde.py）"
    "Patchwork simple 模式测试（直接调用）"
    "Patchwork detail 模式测试（直接调用）"
    "Patchwork 最近 N 天模式测试"
    "Patchwork 多项目测试"
    "Patchwork 项目名称测试"
    "Patchwork 并发处理测试"
    "Patchwork verbose 模式测试"
)

# 测试描述列表
test_descriptions=(
    "通过 kde.py 测试 Patchwork agent 的 simple 模式分析"
    "通过 kde.py 测试 Patchwork agent 的 detail 模式分析（调用 LKML agent）"
    "直接调用 patchwork_agent.py 测试 simple 模式分析"
    "直接调用 patchwork_agent.py 测试 detail 模式分析"
    "测试最近 N 天模式的日期计算"
    "测试多项目 ID 的处理"
    "测试通过项目名称查找 ID"
    "测试并发处理多个 series"
    "测试 verbose 输出模式"
)

# 运行单个测试
run_test() {
    local index=$1
    local name="${test_names[$index]}"
    local description="${test_descriptions[$index]}"
    local command="${test_commands[$index]}"
    
    echo "\n=================================================="
    echo "测试: $name"
    echo "描述: $description"
    echo "命令: $command"
    echo "=================================================="
    
    # 运行命令
    local start_time=$(date +%s)
    eval "$command"
    local return_code=$?
    local end_time=$(date +%s)
    local execution_time=$((end_time - start_time))
    
    # 打印结果
    echo "\n执行时间: $execution_time 秒"
    echo "返回码: $return_code"
    
    if [ $return_code -eq 0 ]; then
        echo "\n✓ 测试通过!"
    else
        echo "\n✗ 测试失败!"
    fi
    
    echo "==================================================\n"
    
    # 测试间隔
    sleep 2
}

# 主测试函数
main() {
    echo "开始测试 Patchwork agent...\n"
    echo "项目根目录: $PROJECT_ROOT"
    echo "测试命令数量: ${#test_commands[@]}"
    
    # 运行所有测试
    for ((i=0; i<${#test_commands[@]}; i++)); do
        run_test $i
    done
    
    echo "Patchwork agent 测试完成！"
}

# 运行主测试函数
main
```

**Step 2: 添加测试脚本执行权限**

Run: `chmod +x test/test_patchwork.sh`

**Step 3: 运行测试脚本验证**

Run: `./test/test_patchwork.sh`
Expected:
- 所有测试通过
- 输出正确的表格格式

**Step 4: Commit**

```bash
git add test/test_patchwork.sh
git commit -m "test(patchwork): create comprehensive test script for patchwork agent"
```

---

## Task 11: 更新 test_all.sh 包含 patchwork 测试

**Files:**
- Modify: `test/test_all.sh`

**Step 1: 添加 patchwork 测试调用**

```bash
# 在 test_all.sh 中添加 patchwork 测试

echo "\n=== 测试 Patchwork Agent ===\n"
bash "$PROJECT_ROOT/test/test_patchwork.sh"
```

**Step 2: 运行总测试脚本验证**

Run: `./test/test_all.sh`
Expected:
- LKML、CGit、RSS、Patchwork 所有测试通过

**Step 3: Commit**

```bash
git add test/test_all.sh
git commit -m "test: add patchwork tests to test_all.sh"
```

---

## Task 12: 更新文档 - patchwork/README.md

**Files:**
- Modify: `patchwork/README.md`

**Step 1: 添加 patchwork_agent 使用说明**

在 README.md 的末尾添加新的章节：

```markdown
## Patchwork Agent（LangGraph 实现）

### 概述

基于 LangGraph 的 Patchwork 补丁分析智能体，支持从 Patchwork API 获取和分析 Linux 内核补丁系列。

### 功能特性

- **两级分析模式**: simple（简要分析）和 detail（详细分析，调用 LKML agent）
- **灵活的日期模式**: 单日期、日期范围、最近 N 天
- **多项目支持**: 支持项目 ID、项目名称、多项目组合
- **并发处理**: 可配置并行度，提升处理效率
- **完整缓存机制**: 缓存 API 数据和分析结果，避免重复请求
- **完善的错误处理**: 单个 series 失败不影响其他 series

### 使用方法

#### 通过 kde.py 运行

```bash
# Simple 模式（简要分析）
python kde.py --patchwork 365 --date 2022-01-24 --level simple --max-series 10

# Detail 模式（详细分析，调用 LKML agent）
python kde.py --patchwork 365 --date 2022-01-24 --level detail --max-series 5

# 最近 7 天的补丁
python kde.py --patchwork 365 --days 7 --level simple

# 多项目
python kde.py --patchwork 365 19 --date 2022-01-24 --level simple

# 使用项目名称
python kde.py --patchwork "Linux MM" --days 7 --level simple

# 并发处理（并行度 3）
python kde.py --patchwork 365 --date 2022-01-24 --level simple --max-parallel 3
```

#### 直接调用 patchwork_agent.py

```bash
python patchwork/patchwork_agent.py --project 365 --date 2022-01-24 --level simple
python patchwork/patchwork_agent.py --project "Linux MM" --days 7 --max-series 10 -v
```

### 参数说明

| 参数 | 说明 | 示例 |
|:----:|:----:|:----:|
| `--project` | 项目 ID 或名称（支持多值） | `365` 或 `"Linux MM"` 或 `365 19` |
| `--date` | 单日期 | `2022-01-24` |
| `--end-date` | 结束日期（配合 `--date`） | `2022-01-26` |
| `--days` | 最近 N 天 | `7` |
| `--level` | 分析级别 | `simple` 或 `detail` |
| `--max-series` | 最大 series 数量 | `10` |
| `--max-parallel` | 并行度 | `3` |
| `--verbose` | 详细级别 | `-v` / `-vv` / `-vvv` |

### 输出格式

沿用 LKML agent 的 Markdown 表格格式：

```
| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 铩接 |
|:---:|:----:|:---:|:----:|:---------:|:----:|
| 2022/01/24 | Author <email> | [Subject](url) | Summary | v1 ☐☑✓ | [LORE](url) |
```

### 缓存位置

- API 缓存: `output/patchwork/cache/*.json`
- 分析结果: `output/patchwork/<project>/<date>/summary.md`
- 详细分析: `output/patchwork/<project>/<date>/series_*_detail.md`

### 测试

运行测试脚本：

```bash
./test/test_patchwork.sh
./test/test_all.sh
```

### 架构

LangGraph 工作流：

```
fetch_project_info → calculate_date_range → fetch_series_list → filter_and_sort 
→ process_series → aggregate_results → output_results → cache_results → END
```

### 与 Shell 脚本的区别

| 特性 | Shell 脚本 | LangGraph Agent |
|:----:|:----:|:----:|
| 分析模式 | 仅提取信息 | simple/detail 两级分析 |
| LKML 集成 | 无 | detail 模式调用 LKML agent |
| 并发处理 | 无 | 可配置并行度 |
| 错误处理 | 基础 | 完善（单个失败不影响其他） |
| 缓存机制 | 无 | 完整缓存（API + 分析结果） |
| 输出格式 | 固定表格 | 沿用 LKML agent 格式 |

### 注意事项

1. **网络连接**: 需要网络连接访问 patchwork.kernel.org
2. **API 限制**: 注意 API 请求频率，建议使用缓存
3. **Detail 模式**: 会调用 LKML agent，耗时较长，建议限制 `--max-series`
4. **并发处理**: `--max-parallel > 1` 时请注意 API 限流风险
```

**Step 2: Commit**

```bash
git add patchwork/README.md
git commit -m "docs(patchwork): add comprehensive documentation for patchwork agent"
```

---

## Task 13: 最终验证和清理

**Files:**
- All project files

**Step 1: 清理测试代码**

检查 patchwork_agent.py，移除所有临时测试代码（if __name__ == "__main__" 块中的测试代码，保留正式的命令行调用）

**Step 2: 运行完整测试套件**

Run: `./test/test_all.sh`
Expected:
- 所有测试通过（LKML、CGit、RSS、Patchwork）
- 无错误输出

**Step 3: 测试缓存清理**

Run: `git clean -fdX`（清理 output 目录中的缓存）
Expected:
- output 目录被清理

**Step 4: 再次运行测试验证**

Run: `python kde.py --patchwork 365 --date 2022-01-24 --level simple --max-series 3 -v`
Expected:
- 成功运行并输出表格
- 缓存重新创建

**Step 5: 最终 Commit**

```bash
git add .
git commit -m "feat(patchwork): complete implementation with tests and documentation

- Implement LangGraph-based patchwork agent
- Support simple/detail two-level analysis
- Integrate LKML agent for detail mode
- Support multiple date modes (single/range/recent days)
- Support project ID/name/multi-project
- Implement parallel processing with configurable concurrency
- Add comprehensive cache mechanism
- Create test suite (test_patchwork.sh)
- Update test_all.sh to include patchwork tests
- Update README.md with usage documentation"
```

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-12-patchwork-agent.md`. 

**执行选项：**

**1. Subagent-Driven（本会话）** - 我逐个任务分派给 subagent，每个任务完成后进行 code review，快速迭代

**2. Parallel Session（单独会话）** - 打开新会话使用 executing-plans skill，批量执行并有检查点

你希望采用哪种执行方式？