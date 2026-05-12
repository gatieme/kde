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

    Args:
        series: Series JSON data from Patchwork API

    Returns:
        Subject string
    """
    # Prefer series name
    name = series.get("name", "")
    if name:
        return name

    # Fallback to first patch name
    patches = series.get("patches", [])
    if patches and len(patches) > 0:
        return patches[0].get("name", "")

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
# Workflow Functions - Placeholder for subsequent user stories
# =============================================================================

def build_patchwork_agent():
    """Build Patchwork agent workflow - placeholder"""
    pass


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
    """Run Patchwork agent - placeholder"""
    pass


# =============================================================================
# Test Code for US-003 Field Extraction Functions
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test field extraction functions")
    parser.add_argument("--test", action="store_true", help="Run field extraction tests")
    parser.add_argument("--series-id", type=int, default=608868, help="Series ID to test")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Verbosity level")
    args = parser.parse_args()

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
        print("All tests passed!")
        print("=" * 60)