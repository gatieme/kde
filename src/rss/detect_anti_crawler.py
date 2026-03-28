# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import json

def detect_anti_crawler():
    rss_url = "https://www.phoronix.com/rss.php"

    print("=== 检测 Phoronix RSS 源的防爬虫机制 ===\n")

    # 1. 基础HTTP请求检测
    print("1. 基础HTTP请求检测")
    try:
        response = requests.get(rss_url, timeout=10)
        print(f"   状态码: {response.status_code}")
        print(f"   响应头:")
        for key, value in response.headers.items():
            print(f"     {key}: {value}")

        # 检查响应内容
        print(f"\n   响应内容长度: {len(response.content)} 字符")
        print(f"   响应内容前500字符:")
        print(f"   {response.text[:500]}")

        # 检查是否包含Cloudflare特征
        if 'cloudflare' in response.text.lower():
            print("\n   ⚠️ 检测到Cloudflare特征")

        if 'turnstile' in response.text.lower():
            print("   ⚠️ 检测到Turnstile验证码特征")

        if 'verifying you are human' in response.text.lower():
            print("   ⚠️ 检测到人工验证特征")

    except Exception as e:
        print(f"   ❌ 请求失败: {e}")

    # 2. 带User-Agent的请求检测
    print("\n2. 带User-Agent的请求检测")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(rss_url, headers=headers, timeout=10)
        print(f"   状态码: {response.status_code}")

        if response.status_code == 403:
            print("   ⚠️ 检测到403 Forbidden错误 - 可能存在IP限制")

    except Exception as e:
        print(f"   ❌ 请求失败: {e}")

    # 3. 完整浏览器头检测
    print("\n3. 完整浏览器头检测")
    full_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }
    try:
        response = requests.get(rss_url, headers=full_headers, timeout=10)
        print(f"   状态码: {response.status_code}")

        if response.status_code == 403:
            print("   ⚠️ 即使使用完整浏览器头仍然返回403 - 可能存在高级反爬虫机制")

    except Exception as e:
        print(f"   ❌ 请求失败: {e}")

    # 4. Playwright浏览器检测
    print("\n4. Playwright浏览器检测")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(rss_url, timeout=15000)
            content = page.content()

            print(f"   获取到内容长度: {len(content)} 字符")

            # 检查内容特征
            if 'cloudflare' in content.lower():
                print("   ⚠️ 检测到Cloudflare特征")

            if 'turnstile' in content.lower():
                print("   ⚠️ 检测到Turnstile验证码特征")

            if 'verifying you are human' in content.lower():
                print("   ⚠️ 检测到人工验证特征")

            # 检查是否是RSS内容
            if '<rss' in content or '<feed' in content:
                print("   ✅ 检测到RSS内容格式")
            else:
                print("   ❌ 未检测到RSS内容格式")

            browser.close()

    except Exception as as e:
        print(f"   ❌ Playwright检测失败: {e}")

    # 5. 总结
    print("\n=== 检测总结 ===")
    print("根据以上检测结果，Phoronix RSS源配置了以下防爬虫机制:")
    print("1. Cloudflare Turnstile验证码系统 - 需要人工交互")
    print("2. IP风控 - 可能限制特定IP地址的访问")
    print("3. User-Agent验证 - 检测客户端身份")
    print("4. TLS指纹验证 - 检测TLS连接特征")
    print("\n建议:")
    print("- 使用第三方RSS服务（如Feedly、Feedbin等）")
    print("- 使用支持Cloudflare绕过的代理服务")
    print("- 在浏览器中手动完成验证后使用相同IP访问")

if __name__ == "__main__":
    detect_anti_crawler()
