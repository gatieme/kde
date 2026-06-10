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
from utils import format_text_for_markdown, clean_email_subject
from model import ModelInference, ModelRequest
from lkml.lkml_agent import run_lkml_agent


@dataclass
class PatchworkAgentState:
    """State for Patchwork agent workflow"""
    messages: Annotated[List[Dict[str, Any]], add_messages]

    # Input parameters
    projects: List[str] = field(default_factory=list)
    date: Optional[str] = None
    end_date: Optional[str] = None
    days: Optional[int] = None
    level: str = "simple"
    max_series: Optional[int] = None
    max_parallel: int = 1
    verbose: int = 0

    # Intermediate state
    project_ids: List[int] = field(default_factory=list)
    date_range: Dict[str, str] = field(default_factory=dict)
    series_list: List[int] = field(default_factory=list)
    series_details: Dict[int, Dict] = field(default_factory=dict)

    # Output results
    processed_results: List[Dict[str, Any]] = field(default_factory=list)
    output_lines: List[str] = field(default_factory=list)

    # Working directory and cache
    work_dir: str = ""
    cache_dir: str = ""


# =============================================================================
# Helper Functions - Project List Loading and Cache Mechanism (US-002)
# =============================================================================

def fetch_with_cache(url: str, cache_dir: str = "", verbose: int = 0) -> Any:
    """Fetch HTTP response with local cache support

    Args:
        url: The URL to fetch
        cache_dir: Cache directory path, defaults to output/patchwork/cache/
        verbose: Verbosity level for logging

    Returns:
        JSON data from cache or API response
    """
    if not cache_dir:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(repo_root, "output", "patchwork", "cache")

    # Use MD5 hash of URL as cache filename
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    cache_file = os.path.join(cache_dir, f"{url_hash}.json")

    # Check cache first
    if os.path.exists(cache_file):
        if verbose >= 2:
            print(f"从缓存读取: {cache_file}")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Fetch from API
    if verbose >= 2:
        print(f"请求 URL: {url}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Save to cache
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if verbose >= 2:
            print(f"缓存保存到: {cache_file}")

        return data
    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return None


def load_projects_list() -> Dict[str, int]:
    """Load projects list from local file or API

    Returns:
        Dict mapping project name/id string to numeric project id
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects_file = os.path.join(repo_root, "patchwork", "project", "projects_list.md")

    if not os.path.exists(projects_file):
        return fetch_projects_from_api()

    # Parse Markdown table format: | ID | PROJECT | EMAIL |
    projects_map: Dict[str, int] = {}
    with open(projects_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[2:]:  # Skip header rows
            if line.strip():
                parts = line.split("|")
                if len(parts) >= 3:
                    id_str = parts[1].strip()
                    name = parts[2].strip()
                    if id_str.isdigit():
                        project_id = int(id_str)
                        # Map both numeric id and name to project_id
                        projects_map[str(project_id)] = project_id
                        projects_map[name] = project_id

    return projects_map


def fetch_projects_from_api() -> Dict[str, int]:
    """Fetch projects list from Patchwork API

    Returns:
        Dict mapping project name/id string to numeric project id
    """
    url = "https://patchwork.kernel.org/api/projects/"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        projects = response.json()

        projects_map: Dict[str, int] = {}
        for project in projects:
            project_id = project["id"]
            name = project["name"]
            # Map both numeric id and name to project_id
            projects_map[str(project_id)] = project_id
            projects_map[name] = project_id

        return projects_map
    except requests.RequestException as e:
        print(f"获取项目列表失败: {e}")
        return {}


def find_project_id_by_name(name: str, projects_map: Dict[str, int]) -> Optional[int]:
    """Find project ID by name with exact and fuzzy matching

    Args:
        name: Project name or numeric ID string
        projects_map: Dict mapping names/ids to numeric project ids

    Returns:
        Numeric project ID or None if not found
    """
    # Exact match first
    if name in projects_map:
        return projects_map[name]

    # Fuzzy match (partial case-insensitive match)
    name_lower = name.lower()
    for key, project_id in projects_map.items():
        if name_lower in key.lower():
            return project_id

    return None


# =============================================================================
# Field Extraction Functions (US-003)
# =============================================================================

def extract_date(series: Dict[str, Any]) -> str:
    """Extract date from series data, format as YYYY/MM/DD

    Args:
        series: Series JSON data from Patchwork API

    Returns:
        Date string in YYYY/MM/DD format
    """
    date_str = series.get("date", "")
    if not date_str:
        return ""

    # Parse ISO format: "2022-01-27T00:07:24"
    try:
        dt = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y/%m/%d")
    except (ValueError, AttributeError):
        return date_str[:10].replace("-", "/")


def extract_author(series: Dict[str, Any]) -> str:
    """Extract author name from series submitter

    Args:
        series: Series JSON data from Patchwork API

    Returns:
        Author name string
    """
    submitter = series.get("submitter", {})
    return submitter.get("name", "")


def extract_email(series: Dict[str, Any]) -> str:
    """Extract email from series submitter

    Args:
        series: Series JSON data from Patchwork API

    Returns:
        Email address string
    """
    submitter = series.get("submitter", {})
    return submitter.get("email", "")


def extract_subject(series: Dict[str, Any]) -> str:
    """Extract subject from series name or first patch name

    Uses clean_email_subject to strip Re:/Fwd: but keep [PATCH...] intact.

    Args:
        series: Series JSON data from Patchwork API

    Returns:
        Cleaned subject string with [PATCH...] preserved
    """
    # Prefer series name
    name = series.get("name", "")
    if name:
        return clean_email_subject(name)

    # Fallback to first patch name
    patches = series.get("patches", [])
    if patches and len(patches) > 0:
        return clean_email_subject(patches[0].get("name", ""))

    return ""


def extract_version(series: Dict[str, Any]) -> str:
    """Extract version from series, handle long version numbers

    Args:
        series: Series JSON data from Patchwork API

    Returns:
        Version string like "v1", "v2", "v3"
    """
    version = series.get("version", 1)
    if version is None:
        version = 1
    return f"v{version}"


def extract_web_url(series: Dict[str, Any]) -> str:
    """Extract web URL from cover_letter or first patch

    Args:
        series: Series JSON data from Patchwork API

    Returns:
        Web URL string for browsing the patch
    """
    # Prefer cover_letter web_url
    cover_letter = series.get("cover_letter")
    if cover_letter:
        url = cover_letter.get("web_url", "")
        if url:
            return url

    # Fallback to first patch web_url
    patches = series.get("patches", [])
    if patches and len(patches) > 0:
        return patches[0].get("web_url", "")

    # Fallback to series web_url
    return series.get("web_url", "")


def extract_archive_url(series: Dict[str, Any]) -> str:
    """Extract list archive URL from cover_letter or first patch

    Args:
        series: Series JSON data from Patchwork API

    Returns:
        Lore.kernel.org archive URL
    """
    # Prefer cover_letter list_archive_url
    cover_letter = series.get("cover_letter")
    if cover_letter:
        url = cover_letter.get("list_archive_url", "")
        if url:
            return url

    # Fallback to first patch list_archive_url
    patches = series.get("patches", [])
    if patches and len(patches) > 0:
        return patches[0].get("list_archive_url", "")

    return ""


def extract_message_id_from_cover(archive_url: str) -> str:
    """Extract message ID from lore.kernel.org URL

    Supports three URL formats:
    - https://lore.kernel.org/r/{message_id}
    - https://lore.kernel.org/{list}/{message_id}
    - https://lore.kernel.org/all/{message_id}

    Args:
        archive_url: URL from lore.kernel.org

    Returns:
        Message ID string, empty if extraction fails
    """
    if not archive_url:
        return ""

    # Pattern: lore.kernel.org/r/{message_id}
    match = re.search(r"lore\.kernel\.org/r/([^/]+)", archive_url)
    if match:
        return match.group(1)

    # Pattern: lore.kernel.org/{list}/{message_id}
    match = re.search(r"lore\.kernel\.org/[^/]+/([^/]+)", archive_url)
    if match:
        return match.group(1)

    # Pattern: lore.kernel.org/all/{message_id}
    match = re.search(r"lore\.kernel\.org/all/([^/]+)", archive_url)
    if match:
        return match.group(1)

    return ""


def fetch_series_detail(series_id: int, cache_dir: str = "", verbose: int = 0) -> Dict[str, Any]:
    """Fetch series detail from Patchwork API with cache

    Args:
        series_id: Series ID to fetch
        cache_dir: Cache directory path
        verbose: Verbosity level

    Returns:
        Series JSON data
    """
    url = f"https://patchwork.kernel.org/api/series/{series_id}/?format=json&archive=both"
    return fetch_with_cache(url, cache_dir, verbose) or {}


# =============================================================================
# Workflow Nodes (US-004)
# =============================================================================

def fetch_project_info(state: PatchworkAgentState) -> PatchworkAgentState:
    """Fetch project info and convert project names/IDs to numeric IDs

    Args:
        state: Current workflow state

    Returns:
        Updated state with project_ids populated
    """
    # Load projects mapping
    projects_map = load_projects_list()

    project_ids: List[int] = []
    for project in state.projects:
        # If numeric string, convert directly
        if project.isdigit():
            project_ids.append(int(project))
        else:
            # Look up by name
            pid = find_project_id_by_name(project, projects_map)
            if pid:
                project_ids.append(pid)
            elif state.verbose >= 1:
                print(f"警告: 项目 '{project}' 未找到")

    if state.verbose >= 2:
        print(f"解析项目: {state.projects} -> IDs: {project_ids}")

    # Update state
    state.project_ids = project_ids
    return state


def calculate_date_range(state: PatchworkAgentState) -> PatchworkAgentState:
    """Calculate date range based on input parameters

    Supports three modes:
    1. Single date: --date specified
    2. Date range: --date and --end-date specified
    3. Recent N days: --days specified
    4. Default: today

    Args:
        state: Current workflow state

    Returns:
        Updated state with date_range populated (dict with 'start' and 'end')
    """
    today = datetime.date.today()

    if state.days is not None and state.days > 0:
        # Mode 3: Recent N days
        start_date = today - datetime.timedelta(days=state.days)
        end_date = today
        if state.verbose >= 2:
            print(f"日期范围（最近 {state.days} 天）: {start_date} -> {end_date}")
    elif state.date and state.end_date:
        # Mode 2: Date range
        start_date = datetime.date.fromisoformat(state.date)
        end_date = datetime.date.fromisoformat(state.end_date)
        if state.verbose >= 2:
            print(f"日期范围: {start_date} -> {end_date}")
    elif state.date:
        # Mode 1: Single date
        start_date = datetime.date.fromisoformat(state.date)
        end_date = start_date
        if state.verbose >= 2:
            print(f"单一日期: {start_date}")
    else:
        # Mode 4: Default to today
        start_date = today
        end_date = today
        if state.verbose >= 2:
            print(f"默认日期: 今天 ({today})")

    state.date_range = {
        "start": start_date.isoformat(),
        "end": end_date.isoformat()
    }

    return state


# =============================================================================
# Workflow Nodes (US-005)
# =============================================================================

def fetch_series_list(state: PatchworkAgentState) -> PatchworkAgentState:
    """Fetch series list from Patchwork API for all projects and dates

    API URL format:
    https://patchwork.kernel.org/api/series/?project={id}&archive=both&format=json&before={date}T23:59:59&since={date}T00:00:00

    Args:
        state: Current workflow state with project_ids and date_range

    Returns:
        Updated state with series_list populated (list of series IDs)
    """
    all_series_ids: List[int] = []

    # Iterate over each date in the date range
    start_date = datetime.date.fromisoformat(state.date_range["start"])
    end_date = datetime.date.fromisoformat(state.date_range["end"])

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.isoformat()

        # Iterate over each project
        for project_id in state.project_ids:
            url = (
                f"https://patchwork.kernel.org/api/series/"
                f"?project={project_id}&archive=both&format=json"
                f"&before={date_str}T23:59:59&since={date_str}T00:00:00"
            )

            if state.verbose >= 2:
                print(f"请求 URL: {url}")

            data = fetch_with_cache(url, state.cache_dir, state.verbose)
            if data:
                # Extract series IDs from response
                for series in data:
                    series_id = series.get("id")
                    if series_id:
                        all_series_ids.append(series_id)

                if state.verbose >= 1:
                    print(f"项目 {project_id} 日期 {date_str}: 获取 {len(data)} 个 series")

        current_date += datetime.timedelta(days=1)

    if state.verbose >= 1:
        print(f"总共获取 {len(all_series_ids)} 个 series ID")

    state.series_list = all_series_ids
    return state


def filter_and_sort(state: PatchworkAgentState) -> PatchworkAgentState:
    """Filter, sort and limit series list

    Steps:
    1. Remove duplicates
    2. Get date for each series (need to fetch details)
    3. Sort by date descending (newest first)
    4. Apply max_series limit if specified

    Args:
        state: Current workflow state with series_list

    Returns:
        Updated state with series_list filtered and sorted
    """
    # Step 1: Remove duplicates
    unique_series_ids = list(set(state.series_list))

    if state.verbose >= 1:
        print(f"去重后: {len(unique_series_ids)} 个 series")

    # Step 2: Get date for each series and sort
    series_with_dates: List[tuple] = []  # (series_id, date)

    for series_id in unique_series_ids:
        series = fetch_series_detail(series_id, state.cache_dir, state.verbose)
        if series:
            date_str = series.get("date", "")
            series_with_dates.append((series_id, date_str))

    # Step 3: Sort by date descending
    series_with_dates.sort(key=lambda x: x[1], reverse=True)

    sorted_ids = [sid for sid, _ in series_with_dates]

    if state.verbose >= 2:
        print(f"按日期倒序排列: {sorted_ids[:10]}...")

    # Step 4: Apply max_series limit
    if state.max_series is not None and state.max_series > 0:
        sorted_ids = sorted_ids[:state.max_series]
        if state.verbose >= 1:
            print(f"应用 max_series 限制: {len(sorted_ids)} 个 series")

    state.series_list = sorted_ids
    return state


# =============================================================================
# Workflow Nodes (US-006)
# =============================================================================

def process_single_series(
    series_id: int,
    level: str,
    cache_dir: str,
    verbose: int
) -> Dict[str, Any]:
    """Process a single series: fetch detail, extract fields, call LKML agent if detail mode

    Args:
        series_id: Series ID to process
        level: Analysis level ("simple" or "detail")
        cache_dir: Cache directory path
        verbose: Verbosity level

    Returns:
        Dict containing series info and analysis results
    """
    try:
        # Fetch series detail
        series = fetch_series_detail(series_id, cache_dir, verbose)
        if not series:
            return {"series_id": series_id, "error": "Failed to fetch series detail"}

        # Extract fields
        result = {
            "series_id": series_id,
            "date": extract_date(series),
            "author": extract_author(series),
            "email": extract_email(series),
            "subject": extract_subject(series),
            "version": extract_version(series),
            "total": series.get("total", 1),
            "web_url": extract_web_url(series),
            "archive_url": extract_archive_url(series),
            "lkml_result": None
        }

        # Call LKML agent in detail mode
        if level == "detail":
            archive_url = extract_archive_url(series)
            message_id = extract_message_id_from_cover(archive_url)

            if message_id:
                if verbose >= 1:
                    print(f"    调用 LKML agent 分析 {message_id}...")

                try:
                    lkml_result = run_lkml_agent(
                        message_id=message_id,
                        level=level,
                        work_dir=None,
                        verbose=verbose
                    )
                    result["lkml_result"] = lkml_result
                except Exception as e:
                    if verbose >= 1:
                        print(f"    LKML agent 处理失败: {e}")
                    result["lkml_error"] = str(e)

        return result

    except Exception as e:
        return {"series_id": series_id, "error": str(e)}


def process_series(state: PatchworkAgentState) -> PatchworkAgentState:
    """Process all series in the list, support parallel processing

    Args:
        state: Current workflow state with series_list

    Returns:
        Updated state with processed_results populated
    """
    total = len(state.series_list)
    results: List[Dict[str, Any]] = []

    if total == 0:
        if state.verbose >= 1:
            print("没有 series 需要处理")
        state.processed_results = results
        return state

    if state.verbose >= 1:
        print(f"开始处理 {total} 个 series...")

    # Serial processing (max_parallel=1)
    if state.max_parallel <= 1:
        for i, series_id in enumerate(state.series_list, 1):
            if state.verbose >= 1:
                print(f"[{i}/{total}] 处理 series {series_id}...")

            result = process_single_series(
                series_id,
                state.level,
                state.cache_dir,
                state.verbose
            )
            results.append(result)

    # Parallel processing
    else:
        with ThreadPoolExecutor(max_workers=state.max_parallel) as executor:
            # Submit all tasks
            future_to_id = {
                executor.submit(
                    process_single_series,
                    series_id,
                    state.level,
                    state.cache_dir,
                    state.verbose
                ): series_id
                for series_id in state.series_list
            }

            # Collect results with progress tracking
            for i, future in enumerate(as_completed(future_to_id), 1):
                series_id = future_to_id[future]
                if state.verbose >= 1:
                    print(f"[{i}/{total}] 完成 series {series_id}")

                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    if state.verbose >= 1:
                        print(f"    处理失败: {e}")
                    results.append({"series_id": series_id, "error": str(e)})

    # Sort results by series_id order to maintain consistency
    results.sort(key=lambda x: x.get("series_id", 0))

    if state.verbose >= 1:
        success_count = sum(1 for r in results if "error" not in r)
        print(f"处理完成: {success_count}/{total} 成功")

    state.processed_results = results
    return state


# =============================================================================
# Workflow Nodes (US-007)
# =============================================================================

def aggregate_results(state: PatchworkAgentState) -> PatchworkAgentState:
    """Generate Markdown table rows from processed results

    Table format:
    | 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |

    Args:
        state: Current workflow state with processed_results

    Returns:
        Updated state with output_lines populated
    """
    output_lines: List[str] = []

    for result in state.processed_results:
        if "error" in result:
            # Skip failed results
            if state.verbose >= 1:
                print(f"跳过失败的 series {result.get('series_id')}: {result.get('error')}")
            continue

        # Extract fields
        date = result.get("date", "")
        author = result.get("author", "")
        email = result.get("email", "")
        subject = result.get("subject", "")
        version = result.get("version", "v1")
        total = result.get("total", 1)
        web_url = result.get("web_url", "")
        archive_url = result.get("archive_url", "")
        series_id = result.get("series_id", "")

        # Format author with email
        author_str = f"{author} &lt;{email}&gt;" if email else author

        # Format subject as plain text (avoid double brackets from markdown link wrapping)
        subject_str = format_text_for_markdown(subject)

        # Format lore link with version and total
        lore_link = f"[LORE {version},{total}]({archive_url})" if archive_url else ""

        # Build table row
        # Format: | 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |
        row = f"| {date} | {author_str} | {subject_str} | {series_id} | {version} ☐ | {lore_link} |"
        output_lines.append(row)

    if state.verbose >= 1:
        print(f"生成 {len(output_lines)} 行表格")

    state.output_lines = output_lines
    return state


def output_results(state: PatchworkAgentState) -> PatchworkAgentState:
    """Print results as Markdown table

    Args:
        state: Current workflow state with output_lines

    Returns:
        State unchanged (just prints output)
    """
    # Print table header
    print("\n| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |")
    print("|:----:|:----:|:----:|:----:|:------------:|:----:|")

    # Print table rows
    for line in state.output_lines:
        print(line)

    # In detail mode, also print LKML analysis
    if state.level == "detail":
        for result in state.processed_results:
            if "lkml_result" in result and result["lkml_result"]:
                lkml = result["lkml_result"]
                print(f"\n### Series {result.get('series_id')} - LKML 分析")
                if isinstance(lkml, dict):
                    # Print summary if available
                    summary = lkml.get("summary", "")
                    if summary:
                        print(f"\n**摘要:**\n{summary}")
                    # Print analysis if available
                    analysis = lkml.get("analysis", "")
                    if analysis:
                        print(f"\n**详细分析:**\n{analysis}")

    return state


def cache_results(state: PatchworkAgentState) -> PatchworkAgentState:
    """Cache results to file system

    Cache location: output/patchwork/<project>/<date>/summary.md
    Detail mode: additionally cache series_*_detail.md

    Args:
        state: Current workflow state with output_lines and processed_results

    Returns:
        State unchanged (just writes files)
    """
    # Determine cache directory
    if not state.work_dir:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        state.work_dir = os.path.join(repo_root, "output", "patchwork")

    # Use first project ID for directory name
    project_id = state.project_ids[0] if state.project_ids else "unknown"
    project_dir = os.path.join(state.work_dir, str(project_id))

    # Use first date from date_range for directory name
    date_dir = state.date_range.get("start", datetime.date.today().isoformat())
    cache_dir = os.path.join(project_dir, date_dir)

    # Create directory
    os.makedirs(cache_dir, exist_ok=True)

    # Write summary.md
    summary_file = os.path.join(cache_dir, "summary.md")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("# Patchwork Series Summary\n\n")
        f.write("| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |\n")
        f.write("|:----:|:----:|:----:|:----:|:------------:|:----:|\n")
        for line in state.output_lines:
            f.write(line + "\n")

    if state.verbose >= 1:
        print(f"缓存保存到: {summary_file}")

    # In detail mode, cache detailed analysis for each series
    if state.level == "detail":
        for result in state.processed_results:
            if "lkml_result" in result and result["lkml_result"]:
                series_id = result.get("series_id")
                detail_file = os.path.join(cache_dir, f"series_{series_id}_detail.md")

                lkml = result["lkml_result"]
                with open(detail_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Series {series_id} - LKML 分析\n\n")
                    f.write(f"**主题:** {result.get('subject', '')}\n\n")
                    f.write(f"**作者:** {result.get('author', '')} &lt;{result.get('email', '')}&gt;\n\n")

                    if isinstance(lkml, dict):
                        summary = lkml.get("summary", "")
                        if summary:
                            f.write(f"## 摘要\n\n{summary}\n\n")
                        analysis = lkml.get("analysis", "")
                        if analysis:
                            f.write(f"## 详细分析\n\n{analysis}\n\n")

                if state.verbose >= 1:
                    print(f"详细分析缓存到: {detail_file}")

    return state


# =============================================================================
# Workflow Functions (US-008)
# =============================================================================

def build_patchwork_agent():
    """Build Patchwork agent workflow using StateGraph

    Workflow node order:
    fetch_project_info → calculate_date_range → fetch_series_list →
    filter_and_sort → process_series → aggregate_results →
    output_results → cache_results → END

    Returns:
        StateGraph workflow
    """
    workflow = StateGraph(PatchworkAgentState)

    # Add nodes
    workflow.add_node("fetch_project_info", fetch_project_info)
    workflow.add_node("calculate_date_range", calculate_date_range)
    workflow.add_node("fetch_series_list", fetch_series_list)
    workflow.add_node("filter_and_sort", filter_and_sort)
    workflow.add_node("process_series", process_series)
    workflow.add_node("aggregate_results", aggregate_results)
    workflow.add_node("output_results", output_results)
    workflow.add_node("cache_results", cache_results)

    # Add edges
    workflow.add_edge("fetch_project_info", "calculate_date_range")
    workflow.add_edge("calculate_date_range", "fetch_series_list")
    workflow.add_edge("fetch_series_list", "filter_and_sort")
    workflow.add_edge("filter_and_sort", "process_series")
    workflow.add_edge("process_series", "aggregate_results")
    workflow.add_edge("aggregate_results", "output_results")
    workflow.add_edge("output_results", "cache_results")
    workflow.add_edge("cache_results", END)

    # Set entry point
    workflow.set_entry_point("fetch_project_info")

    return workflow.compile()


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
) -> Dict[str, Any]:
    """Run Patchwork agent workflow

    Args:
        projects: List of project IDs or names
        date: Single date or start date (YYYY-MM-DD)
        end_date: End date for date range (YYYY-MM-DD)
        days: Number of recent days to include
        level: Analysis level ("simple" or "detail")
        max_series: Maximum number of series to process
        max_parallel: Maximum parallel processing threads
        work_dir: Working directory for output
        verbose: Verbosity level (0-3)

    Returns:
        Dict containing workflow results
    """
    # Build workflow
    agent = build_patchwork_agent()

    # Initialize state
    initial_state = PatchworkAgentState(
        messages=[],
        projects=projects,
        date=date,
        end_date=end_date,
        days=days,
        level=level,
        max_series=max_series,
        max_parallel=max_parallel,
        work_dir=work_dir or "",
        verbose=verbose
    )

    # Run workflow
    result_dict = agent.invoke(initial_state)

    # LangGraph returns a dict, extract fields
    return {
        "series_count": len(result_dict.get("processed_results", [])),
        "output_lines": result_dict.get("output_lines", []),
        "processed_results": result_dict.get("processed_results", []),
        "work_dir": result_dict.get("work_dir", "")
    }


def parse_args():
    """Parse command line arguments

    Returns:
        argparse.Namespace with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Patchwork Agent - Fetch and analyze Linux kernel patch series",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python patchwork_agent.py --project 365 --date 2022-01-24 --level simple --max-series 2 -v
  python patchwork_agent.py --project "Linux MM" --days 7 --level detail
  python patchwork_agent.py --project 365 366 --date 2022-01-24 --end-date 2022-01-27
        """
    )

    parser.add_argument(
        "--project",
        nargs="+",
        required=True,
        help="Project IDs or names (e.g., 365, 'Linux MM')"
    )
    parser.add_argument(
        "--date",
        help="Single date or start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        help="End date for date range (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--days",
        type=int,
        help="Number of recent days to include"
    )
    parser.add_argument(
        "--level",
        choices=["simple", "detail"],
        default="simple",
        help="Analysis level (default: simple)"
    )
    parser.add_argument(
        "--max-series",
        type=int,
        help="Maximum number of series to process"
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=1,
        help="Maximum parallel processing threads (default: 1)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Verbosity level (-v, -vv, -vvv)"
    )

    return parser.parse_args()


# =============================================================================
# Main Entry Point (US-008)
# =============================================================================

# =============================================================================
# Test Code for US-003 to US-008
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test field extraction functions")
    parser.add_argument("--test", action="store_true", help="Run field extraction tests")
    parser.add_argument("--test-us004", action="store_true", help="Run US-004 workflow node tests")
    parser.add_argument("--test-us005", action="store_true", help="Run US-005 workflow node tests")
    parser.add_argument("--test-us006", action="store_true", help="Run US-006 workflow node tests")
    parser.add_argument("--test-us007", action="store_true", help="Run US-007 workflow node tests")
    parser.add_argument("--test-us008", action="store_true", help="Run US-008 workflow tests")
    parser.add_argument("--series-id", type=int, default=608868, help="Series ID to test")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Verbosity level")

    # Parse known args first, leave rest for main agent if no test flags
    args, remaining = parser.parse_known_args()

    # If no test flags, run as main agent with remaining args
    if not any([args.test, args.test_us004, args.test_us005, args.test_us006, args.test_us007, args.test_us008]):
        # Parse remaining arguments for main agent
        import sys
        sys.argv = [sys.argv[0]] + remaining
        main_args = parse_args()

        result = run_patchwork_agent(
            projects=main_args.project,
            date=main_args.date,
            end_date=main_args.end_date,
            days=main_args.days,
            level=main_args.level,
            max_series=main_args.max_series,
            max_parallel=main_args.max_parallel,
            verbose=main_args.verbose
        )

        if main_args.verbose >= 1:
            print(f"\n完成: 处理 {result['series_count']} 个 series")

        exit(0)

    # Test code below
    if args.test:
        print("=" * 60)
        print("Testing Field Extraction Functions (US-003)")
        print("=" * 60)

        # Test with real series data
        print(f"\nFetching series {args.series_id}...")
        series = fetch_series_detail(args.series_id, verbose=args.verbose)

        if not series:
            print("ERROR: Failed to fetch series data")
            exit(1)

        print(f"Series ID: {series.get('id')}")

        # Test extract_date
        date = extract_date(series)
        print(f"\n[extract_date]")
        print(f"  Input: {series.get('date')}")
        print(f"  Output: {date}")
        print(f"  Expected: 2022/01/27")
        assert date == "2022/01/27", f"Date extraction failed: {date}"

        # Test extract_author
        author = extract_author(series)
        print(f"\n[extract_author]")
        print(f"  Input: {series.get('submitter')}")
        print(f"  Output: {author}")
        print(f"  Expected: Ariadne Conill")
        assert author == "Ariadne Conill", f"Author extraction failed: {author}"

        # Test extract_email
        email = extract_email(series)
        print(f"\n[extract_email]")
        print(f"  Input: {series.get('submitter')}")
        print(f"  Output: {email}")
        print(f"  Expected: ariadne@dereferenced.org")
        assert email == "ariadne@dereferenced.org", f"Email extraction failed: {email}"

        # Test extract_subject
        subject = extract_subject(series)
        print(f"\n[extract_subject]")
        print(f"  Input name: {series.get('name')}")
        print(f"  Output: {subject}")
        print(f"  Expected: [v3] fs/exec: require argv[0] presence in do_execveat_common()")
        assert subject == "[v3] fs/exec: require argv[0] presence in do_execveat_common()", f"Subject extraction failed: {subject}"

        # Test extract_version
        version = extract_version(series)
        print(f"\n[extract_version]")
        print(f"  Input: {series.get('version')}")
        print(f"  Output: {version}")
        print(f"  Expected: v3")
        assert version == "v3", f"Version extraction failed: {version}"

        # Test extract_web_url
        web_url = extract_web_url(series)
        print(f"\n[extract_web_url]")
        print(f"  Output: {web_url}")
        print(f"  Expected: https://patchwork.kernel.org/project/linux-mm/patch/20220127000724.15106-1-ariadne@dereferenced.org/")
        assert web_url != "", f"Web URL extraction failed"

        # Test extract_archive_url
        archive_url = extract_archive_url(series)
        print(f"\n[extract_archive_url]")
        print(f"  Output: {archive_url}")
        print(f"  Expected: https://lore.kernel.org/r/20220127000724.15106-1-ariadne@dereferenced.org")
        assert archive_url != "", f"Archive URL extraction failed"

        # Test extract_message_id_from_cover
        message_id = extract_message_id_from_cover(archive_url)
        print(f"\n[extract_message_id_from_cover]")
        print(f"  Input: {archive_url}")
        print(f"  Output: {message_id}")
        print(f"  Expected: 20220127000724.15106-1-ariadne@dereferenced.org")
        assert message_id == "20220127000724.15106-1-ariadne@dereferenced.org", f"Message ID extraction failed: {message_id}"

        # Test with series that has cover_letter (series 609110)
        print("\n" + "=" * 60)
        print("Testing series with cover_letter (609110)")
        print("=" * 60)

        series_with_cover = fetch_series_detail(609110, verbose=args.verbose)
        if series_with_cover:
            cover_letter = series_with_cover.get("cover_letter")
            print(f"\n[cover_letter]")
            print(f"  Present: {cover_letter is not None}")
            print(f"  web_url: {extract_web_url(series_with_cover)}")
            print(f"  archive_url: {extract_archive_url(series_with_cover)}")
            print(f"  version: {extract_version(series_with_cover)}")
            print(f"  total: {series_with_cover.get('total')}")

        print("\n" + "=" * 60)
        print("All US-003 tests passed!")
        print("=" * 60)

    if args.test_us004:
        print("\n" + "=" * 60)
        print("Testing Workflow Nodes (US-004)")
        print("=" * 60)

        # Test fetch_project_info node
        print("\n[fetch_project_info]")

        # Test case 1: Numeric ID
        state1 = PatchworkAgentState(messages=[], projects=["365"], verbose=args.verbose)
        state1 = fetch_project_info(state1)
        print(f"  Input: ['365']")
        print(f"  Output: {state1.project_ids}")
        print(f"  Expected: [365]")
        assert state1.project_ids == [365], f"Project ID conversion failed: {state1.project_ids}"

        # Test case 2: Project name
        state2 = PatchworkAgentState(messages=[], projects=["Linux MM"], verbose=args.verbose)
        state2 = fetch_project_info(state2)
        print(f"\n  Input: ['Linux MM']")
        print(f"  Output: {state2.project_ids}")
        print(f"  Expected: [365]")
        assert state2.project_ids == [365], f"Project name lookup failed: {state2.project_ids}"

        # Test case 3: Multiple projects
        state3 = PatchworkAgentState(messages=[], projects=["365", "Linux MM"], verbose=args.verbose)
        state3 = fetch_project_info(state3)
        print(f"\n  Input: ['365', 'Linux MM']")
        print(f"  Output: {state3.project_ids}")
        print(f"  Expected: [365, 365]")
        assert state3.project_ids == [365, 365], f"Multiple projects failed: {state3.project_ids}"

        # Test calculate_date_range node
        print("\n[calculate_date_range]")

        today = datetime.date.today().isoformat()

        # Test case 1: Single date
        state4 = PatchworkAgentState(messages=[], date="2022-01-27", verbose=args.verbose)
        state4 = calculate_date_range(state4)
        print(f"  Input: date='2022-01-27'")
        print(f"  Output: {state4.date_range}")
        print(f"  Expected: start='2022-01-27', end='2022-01-27'")
        assert state4.date_range["start"] == "2022-01-27", f"Single date start failed"
        assert state4.date_range["end"] == "2022-01-27", f"Single date end failed"

        # Test case 2: Date range
        state5 = PatchworkAgentState(messages=[], date="2022-01-24", end_date="2022-01-27", verbose=args.verbose)
        state5 = calculate_date_range(state5)
        print(f"\n  Input: date='2022-01-24', end_date='2022-01-27'")
        print(f"  Output: {state5.date_range}")
        print(f"  Expected: start='2022-01-24', end='2022-01-27'")
        assert state5.date_range["start"] == "2022-01-24", f"Date range start failed"
        assert state5.date_range["end"] == "2022-01-27", f"Date range end failed"

        # Test case 3: Recent N days
        state6 = PatchworkAgentState(messages=[], days=7, verbose=args.verbose)
        state6 = calculate_date_range(state6)
        expected_start = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        print(f"\n  Input: days=7")
        print(f"  Output: {state6.date_range}")
        print(f"  Expected: start='{expected_start}', end='{today}'")
        assert state6.date_range["start"] == expected_start, f"Recent N days start failed"
        assert state6.date_range["end"] == today, f"Recent N days end failed"

        # Test case 4: Default (today)
        state7 = PatchworkAgentState(messages=[], verbose=args.verbose)
        state7 = calculate_date_range(state7)
        print(f"\n  Input: (no date params - default)")
        print(f"  Output: {state7.date_range}")
        print(f"  Expected: start='{today}', end='{today}'")
        assert state7.date_range["start"] == today, f"Default start failed"
        assert state7.date_range["end"] == today, f"Default end failed"

        print("\n" + "=" * 60)
        print("All US-004 tests passed!")
        print("=" * 60)

    if args.test_us005:
        print("\n" + "=" * 60)
        print("Testing Workflow Nodes (US-005)")
        print("=" * 60)

        # Test fetch_series_list and filter_and_sort with real data
        # Use a known date with existing series (2022-01-27, Linux MM project 365)

        print("\n[fetch_series_list]")
        print("  Testing with project=365, date=2022-01-27")

        state1 = PatchworkAgentState(
            messages=[],
            projects=["365"],
            verbose=args.verbose
        )
        state1 = fetch_project_info(state1)
        state1 = calculate_date_range(state1)
        # Override date to 2022-01-27 for testing
        state1.date_range = {"start": "2022-01-27", "end": "2022-01-27"}
        state1 = fetch_series_list(state1)

        print(f"  Output: {len(state1.series_list)} series IDs")
        print(f"  Series IDs: {state1.series_list[:10]}...")
        assert len(state1.series_list) > 0, f"fetch_series_list should return series IDs"

        print("\n[filter_and_sort]")
        print("  Testing deduplication, sorting, and max_series limit")

        # Test without max_series limit
        state2 = PatchworkAgentState(
            messages=[],
            projects=["365"],
            date_range={"start": "2022-01-27", "end": "2022-01-27"},
            verbose=args.verbose
        )
        state2 = fetch_project_info(state2)
        state2 = fetch_series_list(state2)
        original_count = len(state2.series_list)
        state2 = filter_and_sort(state2)

        print(f"  Input count: {original_count}")
        print(f"  Output count: {len(state2.series_list)}")
        print(f"  Series IDs (sorted): {state2.series_list[:5]}...")
        # Check deduplication (count should be <= original)
        assert len(state2.series_list) <= original_count, f"Deduplication failed"

        # Test with max_series limit
        state3 = PatchworkAgentState(
            messages=[],
            projects=["365"],
            date_range={"start": "2022-01-27", "end": "2022-01-27"},
            max_series=3,
            verbose=args.verbose
        )
        state3 = fetch_project_info(state3)
        state3 = fetch_series_list(state3)
        state3 = filter_and_sort(state3)

        print(f"\n  With max_series=3:")
        print(f"  Output count: {len(state3.series_list)}")
        print(f"  Series IDs: {state3.series_list}")
        assert len(state3.series_list) == 3, f"max_series limit failed: {len(state3.series_list)}"

        print("\n" + "=" * 60)
        print("All US-005 tests passed!")
        print("=" * 60)

    if args.test_us006:
        print("\n" + "=" * 60)
        print("Testing Workflow Nodes (US-006)")
        print("=" * 60)

        # Test process_single_series with known series (608868)
        print("\n[process_single_series]")

        result1 = process_single_series(608868, "simple", "", args.verbose)

        print(f"  Series ID: {result1.get('series_id')}")
        print(f"  Date: {result1.get('date')}")
        print(f"  Author: {result1.get('author')}")
        print(f"  Email: {result1.get('email')}")
        print(f"  Subject: {result1.get('subject')}")
        print(f"  Version: {result1.get('version')}")
        print(f"  Total: {result1.get('total')}")
        print(f"  Web URL: {result1.get('web_url')}")
        print(f"  Archive URL: {result1.get('archive_url')}")

        assert result1.get("series_id") == 608868, f"Series ID mismatch"
        assert result1.get("date") == "2022/01/27", f"Date mismatch"
        assert result1.get("author") == "Ariadne Conill", f"Author mismatch"
        assert "error" not in result1, f"Processing failed: {result1.get('error')}"

        # Test process_series node in simple mode
        print("\n[process_series] - simple mode")

        state2 = PatchworkAgentState(
            messages=[],
            series_list=[608868, 609110],
            level="simple",
            max_parallel=1,
            verbose=args.verbose
        )
        state2 = process_series(state2)

        print(f"  Processed {len(state2.processed_results)} series")
        for r in state2.processed_results:
            print(f"    - Series {r.get('series_id')}: {r.get('subject', '')[:50]}...")

        assert len(state2.processed_results) == 2, f"Should process 2 series"
        assert all("error" not in r for r in state2.processed_results), f"Processing errors"

        print("\n" + "=" * 60)
        print("All US-006 tests passed!")
        print("=" * 60)

    if args.test_us007:
        print("\n" + "=" * 60)
        print("Testing Workflow Nodes (US-007)")
        print("=" * 60)

        # Prepare test data
        test_results = [
            {
                "series_id": 608868,
                "date": "2022/01/27",
                "author": "Ariadne Conill",
                "email": "ariadne@dereferenced.org",
                "subject": "[v3] fs/exec: require argv[0] presence in do_execveat_common()",
                "version": "v3",
                "total": 1,
                "web_url": "https://patchwork.kernel.org/project/linux-mm/patch/xxx/",
                "archive_url": "https://lore.kernel.org/r/xxx"
            },
            {
                "series_id": 609110,
                "date": "2022/01/27",
                "author": "Karolina Drobnik",
                "email": "karolinadrobnik@gmail.com",
                "subject": "Introduce memblock simulator",
                "version": "v1",
                "total": 16,
                "web_url": "https://patchwork.kernel.org/project/linux-mm/cover/yyy/",
                "archive_url": "https://lore.kernel.org/r/yyy"
            }
        ]

        # Test aggregate_results
        print("\n[aggregate_results]")

        state1 = PatchworkAgentState(
            messages=[],
            processed_results=test_results,
            level="simple",
            verbose=args.verbose
        )
        state1 = aggregate_results(state1)

        print(f"  Output lines: {len(state1.output_lines)}")
        for line in state1.output_lines:
            print(f"    {line}")

        assert len(state1.output_lines) == 2, f"Should have 2 table rows"
        assert "2022/01/27" in state1.output_lines[0], f"Date should be in row"

        # Test output_results
        print("\n[output_results]")

        state2 = PatchworkAgentState(
            messages=[],
            output_lines=state1.output_lines,
            processed_results=test_results,
            level="simple",
            verbose=args.verbose
        )
        state2 = output_results(state2)

        print("  (Output printed above)")

        # Test cache_results
        print("\n[cache_results]")

        state3 = PatchworkAgentState(
            messages=[],
            project_ids=[365],
            date_range={"start": "2022-01-27", "end": "2022-01-27"},
            output_lines=state1.output_lines,
            processed_results=test_results,
            level="simple",
            verbose=args.verbose
        )
        state3 = cache_results(state3)

        # Check if cache file exists
        import tempfile
        cache_dir = os.path.join(state3.work_dir, "365", "2022-01-27")
        summary_file = os.path.join(cache_dir, "summary.md")

        print(f"  Cache directory: {cache_dir}")
        print(f"  Summary file: {summary_file}")

        assert os.path.exists(summary_file), f"Summary file should exist"

        # Read and verify content
        with open(summary_file, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"  Content preview:\n{content[:200]}...")
        assert "| 时间 |" in content, f"Table header should exist"

        print("\n" + "=" * 60)
        print("All US-007 tests passed!")
        print("=" * 60)

    if args.test_us008:
        print("\n" + "=" * 60)
        print("Testing Workflow Functions (US-008)")
        print("=" * 60)

        # Test build_patchwork_agent
        print("\n[build_patchwork_agent]")

        agent = build_patchwork_agent()
        print(f"  Workflow built successfully")
        print(f"  Nodes: {list(agent.nodes.keys())}")
        assert agent is not None, f"Agent should be built"

        # Test run_patchwork_agent with real data
        print("\n[run_patchwork_agent] - simple mode, max_series=2")

        result = run_patchwork_agent(
            projects=["365"],
            date="2022-01-27",
            level="simple",
            max_series=2,
            max_parallel=1,
            verbose=args.verbose
        )

        print(f"  Series count: {result['series_count']}")
        print(f"  Output lines: {len(result['output_lines'])}")
        print(f"  Work dir: {result['work_dir']}")

        assert result['series_count'] == 2, f"Should process 2 series (max_series=2)"
        assert len(result['output_lines']) == 2, f"Should have 2 output lines"
        assert result['work_dir'] != "", f"Work directory should be set"

        # Test command line parsing (simulate)
        print("\n[parse_args] simulation")

        # Simulate args
        test_args = {
            "project": ["365"],
            "date": "2022-01-27",
            "level": "simple",
            "max_series": 2,
            "verbose": 1
        }
        print(f"  Simulated args: {test_args}")

        print("\n" + "=" * 60)
        print("All US-008 tests passed!")
        print("=" * 60)