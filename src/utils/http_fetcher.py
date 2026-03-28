# -*- coding: utf-8 -*-
"""HTTP 请求获取的公共函数"""

import requests
import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from typing import Optional, Dict, Any


def fetch_article_with_method(article: Dict[str, Any], method: str, verbose: int = 0) -> Optional[str]:
    """使用指定方法获取文章内容
    
    Args:
        article: 文章信息字典，包含 link 等字段
        method: 使用的 HTTP 方法 (requests, httpx, playwright)
        verbose: 详细级别 (0-3)
    
    Returns:
        str: 文章内容，失败返回 None
    """
    try:
        if method == "requests":
            return _fetch_with_requests(article, verbose)
        elif method == "httpx":
            return _fetch_with_httpx(article, verbose)
        elif method == "playwright":
            return _fetch_with_playwright(article, verbose)
        else:
            return None
    except Exception as e:
        if verbose >= 2:
            print(f"    使用 {method} 获取失败: {e}")
        return None


def _fetch_with_requests(article: Dict[str, Any], verbose: int = 0) -> Optional[str]:
    """使用 requests 获取文章内容"""
    response = requests.get(
        article["link"],
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },
        timeout=15
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    return _extract_article_body(soup)


def _fetch_with_httpx(article: Dict[str, Any], verbose: int = 0) -> Optional[str]:
    """使用 httpx 获取文章内容"""
    with httpx.Client(timeout=15, follow_redirects=True) as client:
        response = client.get(article["link"])
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        return _extract_article_body(soup)


def _fetch_with_playwright(article: Dict[str, Any], verbose: int = 0) -> Optional[str]:
    """使用 Playwright 获取文章内容"""
    if verbose >= 1:
        print(f"  使用 playwright 打开: {article['title'][:60]}...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            slow_mo=200,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            permissions=["geolocation"],
            geolocation={"latitude": 37.7749, "longitude": -122.4194},
            locale="en-US",
            timezone_id="America/New_York"
        )
        
        page = context.new_page()
        page.goto(article["link"], timeout=30000)
        page.wait_for_load_state("networkidle", timeout=30000)
        
        # 检查是否有验证码
        if "captcha" in page.content().lower() or "verify" in page.content().lower():
            if verbose >= 1:
                print("检测到验证码，尝试等待用户交互...")
            page.wait_for_timeout(5000)
        
        soup = BeautifulSoup(page.content(), "html.parser")
        context.close()
        browser.close()
        
        return _extract_article_body(soup)


def _extract_article_body(soup: BeautifulSoup) -> Optional[str]:
    """从 BeautifulSoup 对象中提取文章正文
    
    Args:
        soup: BeautifulSoup 对象
    
    Returns:
        str: 文章正文，未找到返回 None
    """
    # 尝试多种选择器
    selectors = [
        ("div", "content"),
        ("div", None, "content"),
        ("article",),
        ("main",)
    ]
    
    for selector in selectors:
        if len(selector) == 2:
            element = soup.find(selector[0], class_=selector[1])
        elif len(selector) == 3:
            element = soup.find(selector[0], id=selector[1])
        else:
            element = soup.find(selector[0])
        
        if element:
            return element.get_text(strip=True)
    
    return None
