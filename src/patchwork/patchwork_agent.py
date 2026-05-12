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