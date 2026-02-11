# -*- coding: utf-8 -*-

import os
import sys
import feedparser
import requests
import httpx
import argparse
from bs4 import BeautifulSoup
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import Annotated, List, Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin, urlparse

# 导入模型推理模块
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from model import ModelInference, ModelRequest

load_dotenv()

ALL_RSS_SOURCES = [
    {
        "name": "Phoronix",
        "url": "https://www.phoronix.com/rss.php",
        "has_cloudflare": True
    },
    {
        "name": "LWN",
        "url": "https://lwn.net/headlines/newrss",
        "has_cloudflare": False
    }
]

RSS_SOURCES = ALL_RSS_SOURCES.copy()
MAX_ARTICLES = None

@dataclass
class AgentState:
    messages: Annotated[List[Dict[str, Any]], add_messages]
    articles: List[Dict[str, Any]] = field(default_factory=list)
    summaries: List[Dict[str, Any]] = field(default_factory=list)
    protection_info: Dict[str, Any] = field(default_factory=dict)

KERNEL_KEYWORDS = [
    "kernel", "linux kernel", "linux-kernel", "内核",
    "Linux 内核", "LKML", "linux-kernel mailing list"
]

PATCH_KEYWORDS = [
    "patch", "mailing", "lkml", "linux-kernel", "kernel.org",
    "lore.kernel.org", "git.kernel.org"
]

def detect_protection(state: AgentState) -> AgentState:
    print("=== 检测网站防爬虫机制 ===\n")

    protection_info = {}

    for source in RSS_SOURCES:
        print(f"检测 {source['name']}: {source['url']}")
        result = check_url_protection(source["url"])
        protection_info[source["name"]] = result
        print(f"  结果: {result['status']}")
        if result.get("method_used"):
            print(f"  可用方法: {result['method_used']}")
        print()

    state.protection_info = protection_info
    state.messages.append({"role": "system", "content": f"防爬虫检测完成: {protection_info}"})

    return state

def check_url_protection(url: str) -> Dict[str, Any]:
    result = {
        "status": "unknown",
        "has_cloudflare": False,
        "has_turnstile": False,
        "has_verification": False,
        "available_methods": [],
        "method_used": None
    }

    methods = [
        ("requests", fetch_with_requests),
        ("httpx", fetch_with_httpx),
        ("playwright", fetch_with_playwright)
    ]

    for method_name, method_func in methods:
        try:
            content = method_func(url, check_only=True)
            if content and len(content) > 100:
                result["available_methods"].append(method_name)
                if not result["method_used"]:
                    result["method_used"] = method_name

                if 'cloudflare' in content.lower():
                    result["has_cloudflare"] = True
                if 'turnstile' in content.lower():
                    result["has_turnstile"] = True
                if 'verifying you are human' in content.lower():
                    result["has_verification"] = True

                if '<rss' in content or '<feed' in content:
                    result["status"] = "accessible"
                    break
        except Exception as e:
            continue

    if result["status"] == "unknown":
        if result["available_methods"]:
            result["status"] = "protected_but_accessible"
        else:
            result["status"] = "blocked"

    return result

def fetch_with_requests(url: str, check_only: bool = False) -> Optional[str]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.text

def fetch_with_httpx(url: str, check_only: bool = False) -> Optional[str]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Host': urlparse(url).netloc,
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"'
    }

    with httpx.Client(headers=headers, timeout=15, follow_redirects=True, http2=True, verify=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text

def fetch_with_playwright(url: str, check_only: bool = False) -> Optional[str]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=100)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(url, timeout=15000)
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)
        content = page.content()
        browser.close()
        return content

def fetch_rss_feeds(state: AgentState) -> AgentState:
    print("=== 获取 RSS 订阅 ===\n")

    all_articles = []

    for source in RSS_SOURCES:
        print(f"获取 {source['name']} RSS: {source['url']}")

        protection = state.protection_info.get(source["name"], {})
        available_methods = protection.get("available_methods", [])

        articles = []
        for method in available_methods:
            print(f"  尝试使用 {method}...")
            articles = fetch_rss_with_method(source["url"], source["name"], method)
            if articles:
                print(f"  ✅ 成功获取 {len(articles)} 篇文章")
                break

        if not articles:
            print(f"  ❌ 无法获取 {source['name']} RSS")

        all_articles.extend(articles)

    if MAX_ARTICLES and len(all_articles) > MAX_ARTICLES:
        print(f"\n限制文章数量到 {MAX_ARTICLES} 篇")
        all_articles = all_articles[:MAX_ARTICLES]

    print(f"\n总共获取 {len(all_articles)} 篇文章")
    state.articles = all_articles
    state.messages.append({"role": "system", "content": f"已获取 {len(all_articles)} 篇文章"})

    return state

def fetch_rss_with_method(url: str, source_name: str, method: str) -> List[Dict]:
    try:
        if method == "requests":
            content = fetch_with_requests(url)
        elif method == "httpx":
            content = fetch_with_httpx(url)
        elif method == "playwright":
            content = fetch_with_playwright(url)
        else:
            return []

        feed = feedparser.parse(content)

        articles = []
        for entry in feed.entries:
            article = {
                "source": source_name,
                "title": entry.title,
                "link": entry.link,
                "published": entry.get("published", ""),
                "summary": entry.get("summary", ""),
                "content": entry.get("content", [{}])[0].get("value", "")
            }
            articles.append(article)

        return articles

    except Exception as e:
        print(f"    使用 {method} 获取失败: {e}")
        return []

def fetch_article_content(state: AgentState) -> AgentState:
    print("\n=== 获取文章完整内容 ===\n")

    for i, article in enumerate(state.articles):
        print(f"[{i+1}/{len(state.articles)}] 获取: {article['title'][:60]}...")

        if article["content"]:
            print("  已有内容，跳过")
            continue

        protection = state.protection_info.get(article["source"], {})
        available_methods = protection.get("available_methods", ["requests"])

        full_content = None
        for method in available_methods:
            try:
                if method == "requests":
                    response = requests.get(article["link"], headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }, timeout=15)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, "html.parser")
                elif method == "httpx":
                    with httpx.Client(timeout=15, follow_redirects=True) as client:
                        response = client.get(article["link"])
                        response.raise_for_status()
                        soup = BeautifulSoup(response.content, "html.parser")
                elif method == "playwright":
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        page = browser.new_page()
                        page.goto(article["link"], timeout=15000)
                        page.wait_for_load_state("domcontentloaded", timeout=15000)
                        soup = BeautifulSoup(page.content(), "html.parser")
                        browser.close()

                article_body = soup.find("div", class_="content")
                if not article_body:
                    article_body = soup.find("div", id="content")
                if not article_body:
                    article_body = soup.find("article")
                if not article_body:
                    article_body = soup.find("main")

                if article_body:
                    full_content = article_body.get_text(strip=True)
                    break

            except Exception as e:
                continue

        if full_content:
            article["content"] = full_content
            print(f"  ✅ 获取成功 ({len(full_content)} 字符)")
        else:
            article["content"] = article["summary"]
            print(f"  ⚠️ 使用摘要替代")

    state.messages.append({"role": "system", "content": "文章内容获取完成"})
    return state

def analyze_articles(state: AgentState) -> AgentState:
    print("\n=== 分析文章内容 ===\n")

    summaries = []

    for i, article in enumerate(state.articles):
        print(f"[{i+1}/{len(state.articles)}] 分析: {article['title'][:60]}...")

        content = article["content"] or article["summary"]
        title = article["title"]

        involves_kernel = check_involves_kernel(title, content)
        patch_links = extract_patch_links(content, article["link"])

        summaries.append({
            "source": article["source"],
            "title": title,
            "link": article["link"],
            "published": article["published"],
            "involves_kernel": involves_kernel,
            "patch_links": patch_links,
            "content": content
        })

        print(f"  内核相关: {'是' if involves_kernel else '否'}")
        if patch_links:
            print(f"  补丁链接: {len(patch_links)} 个")

    state.summaries = summaries
    state.messages.append({"role": "system", "content": "文章分析完成"})

    return state

def check_involves_kernel(title: str, content: str) -> bool:
    text = (title + " " + content).lower()
    for keyword in KERNEL_KEYWORDS:
        if keyword.lower() in text:
            return True
    return False

def extract_patch_links(content: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(content, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        href_lower = href.lower()

        for keyword in PATCH_KEYWORDS:
            if keyword in href_lower:
                if not href.startswith("http"):
                    href = urljoin(base_url, href)
                if href not in links:
                    links.append(href)
                break

    return links

def generate_summaries(state: AgentState) -> AgentState:
    print("\n=== 生成文章摘要 ===\n")

    for i, summary in enumerate(state.summaries):
        print(f"[{i+1}/{len(state.summaries)}] 生成摘要: {summary['title'][:60]}...")

        summary_text = generate_summary_text(summary)
        summary["summary"] = summary_text

        print(f"  ✅ 摘要长度: {len(summary_text)} 字符")

    state.messages.append({"role": "system", "content": "摘要生成完成"})
    return state

def generate_summary_text(article: Dict[str, Any]) -> str:
    title = article["title"]
    content = article["content"][:3000]
    involves_kernel = article["involves_kernel"]

    if involves_kernel:
        prompt = f"""请详细总结以下 Linux 内核相关文章，包括主要内容、技术细节和重要信息：

标题：{title}
内容：{content}

要求：
1. 详细总结，覆盖关键技术点
2. 突出内核相关的重要信息
3. 如果有性能数据或技术改进，请重点说明
4. 保持在 300 字以内
"""
    else:
        prompt = f"""请总结以下文章，保持简洁明了：

标题：{title}
内容：{content}

要求：
1. 概括文章主要内容
2. 保持在 300 字以内
"""

    try:
        # 使用 ModelRequest 构建请求
        model_req = ModelRequest("summary", prompt)
        messages = model_req.get_messages()

        # 使用 ModelInference 进行推理
        model_infer = ModelInference()
        model_infer.inference(messages)

        return model_infer.get_answer().strip()
    except Exception as e:
        print(f"    API 调用失败: {e}")
        return f"{title[:100]}..."

def output_results(state: AgentState) -> AgentState:
    print("\n# RSS 分析结果\n")

    if not state.summaries:
        print("没有分析结果")
        return state

    kernel_count = sum(1 for s in state.summaries if s["involves_kernel"])
    sources = ', '.join(set(s['source'] for s in state.summaries))

    print(f"**总文章数:** {len(state.summaries)}  \n")
    print(f"**内核相关:** {kernel_count} 篇  \n")
    print(f"**来源:** {sources}  \n")
    print("---\n")

    for i, summary in enumerate(state.summaries, 1):
        print(f"{i}. [{summary['source']}] [{summary['title']}]({summary['link']})  \n")
        print(f"   **发布时间:** {summary['published']}  \n")
        print(f"   **内核相关:** {'✅ 是' if summary['involves_kernel'] else '否'}  \n")
        print(f"   **摘要:** {summary['summary']}  \n")

        if summary['patch_links']:
            print(f"   **详情:**  \n")
            print(f"   **邮件相关链接:**  \n")
            for link in summary['patch_links']:
                print(f"   - [{link}]({link})  \n")
        print()

    state.messages.append({"role": "system", "content": "分析结果已输出"})
    return state

def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("detect_protection", detect_protection)
    workflow.add_node("fetch_rss_feeds", fetch_rss_feeds)
    workflow.add_node("fetch_article_content", fetch_article_content)
    workflow.add_node("analyze_articles", analyze_articles)
    workflow.add_node("generate_summaries", generate_summaries)
    workflow.add_node("output_results", output_results)

    workflow.set_entry_point("detect_protection")
    workflow.add_edge("detect_protection", "fetch_rss_feeds")
    workflow.add_edge("fetch_rss_feeds", "fetch_article_content")
    workflow.add_edge("fetch_article_content", "analyze_articles")
    workflow.add_edge("analyze_articles", "generate_summaries")
    workflow.add_edge("generate_summaries", "output_results")
    workflow.add_edge("output_results", END)

    return workflow.compile()

def parse_args():
    parser = argparse.ArgumentParser(
        description="RSS 分析智能体 - 分析 LWN 和 Phoronix 的技术文章",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python rss_agent.py --help              显示帮助信息
  python rss_agent.py --resource Phoronix  只获取 Phoronix
  python rss_agent.py -r LWN              只获取 LWN
  python rss_agent.py -n 5                限制获取 5 篇文章
  python rss_agent.py -r Phoronix -n 10    获取 Phoronix 的 10 篇文章
"""
    )
    parser.add_argument(
        "--resource", "-r",
        type=str,
        nargs="+",
        choices=["Phoronix", "LWN"],
        default=["Phoronix", "LWN"],
        help="指定 RSS 源，可多选: Phoronix, LWN"
    )
    parser.add_argument(
        "--max-articles", "-n",
        type=int,
        default=None,
        help="限制获取的文章数量"
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    RSS_SOURCES = [s for s in ALL_RSS_SOURCES if s["name"] in args.resource]
    MAX_ARTICLES = args.max_articles

    print(f"配置: RSS 源 = {', '.join(args.resource)}")
    if MAX_ARTICLES:
        print(f"配置: 最大文章数 = {MAX_ARTICLES}")
    print()

    agent = build_graph()

    initial_state = AgentState(messages=[
        {"role": "system", "content": "你是一个 RSS 分析智能体，负责读取、分析和总结 LWN 和 Phoronix 的技术文章。"}
    ])

    result = agent.invoke(initial_state)

    print("\n=== 智能体运行完成 ===")
