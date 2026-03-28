# -*- coding: utf-8 -*-

import os
import feedparser
import requests
from bs4 import BeautifulSoup
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import Annotated, List, Dict, Any
from dataclasses import dataclass, field
from openai import OpenAI
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# 加载环境变量
load_dotenv()

# 初始化OpenAI客户端
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

# 定义状态结构
@dataclass
class AgentState:
    messages: Annotated[List[Dict[str, Any]], add_messages]
    articles: List[Dict[str, Any]] = field(default_factory=list)
    summaries: List[Dict[str, Any]] = field(default_factory=list)

# 读取RSS订阅
def fetch_rss_feeds(state: AgentState) -> AgentState:
    rss_sources = [
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

    all_articles = []

    for source in rss_sources:
        print(f"\n正在获取 {source['name']} RSS: {source['url']}")

        if source["has_cloudflare"]:
            # 尝试获取Phoronix RSS（可能会遇到Cloudflare保护）
            articles = fetch_phoronix_rss(source["url"])
        else:
            # 获取LWN RSS
            articles = fetch_normal_rss(source["url"], source["name"])

        if articles:
            print(f"成功获取 {source['name']} {len(articles)} 篇文章")
            all_articles.extend(articles)
        else:
            print(f"无法获取 {source['name']} RSS内容")

    print(f"\n总共获取 {len(all_articles)} 篇文章")
    state.articles = all_articles
    state.messages.append({"role": "system", "content": f"已获取 {len(all_articles)} 篇文章"})

    return state

# 获取普通RSS（LWN）
def fetch_normal_rss(url: str, source_name: str) -> List[Dict]:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        feed = feedparser.parse(response.content)

        articles = []
        for entry in feed.entries:
            article = {
                "source": source_name,
                "title": entry.title,
                "link": entry.link,
                "published": entry.published,
                "summary": entry.summary,
                "content": entry.get("content", [{}])[0].get("value", "")
            }
            articles.append(article)

        return articles

    except Exception as e:
        print(f"获取 {source_name} RSS失败: {e}")
        return []

# 尝试获取Phoronix RSS（可能会遇到Cloudflare保护）
def fetch_phoronix_rss(url: str) -> List[Dict]:
    try:
        # 尝试直接获取
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        feed = feedparser.parse(response.content)

        articles = []
        for entry in feed.entries:
            article = {
                "source": "Phoronix",
                "title": entry.title,
                "link": entry.link,
                "published": entry.published,
                "summary": entry.summary,
                "content": entry.get("content", [{}])[0].get("value", "")
            }
            articles.append(article)

        return articles

    except Exception as e:
        print(f"直接获取Phoronix RSS失败: {e}")

        # 尝试使用Playwright
        print("尝试使用Playwright获取Phoronix RSS...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, slow_mo=100)
                page = browser.new_page()

                page.set_viewport_size({"width": 1920, "height": 1080})

                page.goto(url, timeout=15000)
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                page.wait_for_timeout(2000)

                rss_content = page.content()
                browser.close()

                feed = feedparser.parse(rss_content)

                articles = []
                for entry in feed.entries:
                    article = {
                        "source": "Phoronix",
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.published,
                        "summary": entry.summary,
                        "content": entry.get("content", [{}])[0].get("value", "")
                    }
                    articles.append(article)

                return articles

        except Exception as e2:
            print(f"Playwright获取Phoronix RSS失败: {e2}")
            print("Phoronix RSS受到Cloudflare保护，无法自动获取")
            return []

# 分析文章内容
def analyze_articles(state: AgentState) -> AgentState:
    print("\n正在分析文章内容...")
    summaries = []

    if not state.articles:
        print("没有文章可分析")
        state.messages.append({"role": "system", "content": "没有文章可分析"})
        return state

    for article in state.articles:
        # 获取完整内容（如果需要）
        full_content = article["content"]
        if not full_content:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                response = requests.get(article["link"], headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")

                # 尝试提取文章正文
                article_body = soup.find("div", class_="content")
                if not article_body:
                    article_body = soup.find("div", id="content")

                if article_body:
                    full_content = article_body.get_text()
                else:
                    full_content = article["summary"]

            except Exception as e:
                print(f"获取文章 {article['title'][:50]} 内容失败: {e}")
                full_content = article["summary"]

        # 分析是否涉及内核
        involves_kernel = False
        kernel_keywords = ["kernel", "linux kernel", "linux-kernel", "内核", "Linux 内核", "LKML", "linux-kernel mailing list"]
        for keyword in kernel_keywords:
            if keyword.lower() in full_content.lower() or keyword.lower() in article["title"].lower():
                involves_kernel = True
                break

        # 分析是否包含邮件列表补丁链接
        patch_links = []
        if involves_kernel:
            soup = BeautifulSoup(full_content, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ("patch" in href.lower() or "mailing" in href.lower() or "lkml" in href
