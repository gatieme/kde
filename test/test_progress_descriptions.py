#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试各个 agent 中进度条描述的改进
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_progress_descriptions():
    print("=== 检查进度条描述改进 ===\n")

    results = []

    lkml_file = "lkml/lkml_agent.py"
    with open(lkml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    if "LKML 补丁下载进度" in content:
        results.append((lkml_file, "LKML 补丁下载进度", True))
    else:
        results.append((lkml_file, "LKML 补丁下载进度", False))

    cgit_file = "cgit/cgit_agent.py"
    with open(cgit_file, 'r', encoding='utf-8') as f:
        content = f.read()

    if "CGit commit" in content and "下载进度" in content:
        results.append((cgit_file, "CGit commit 下载进度", True))
    else:
        results.append((cgit_file, "CGit commit 下载进度", False))

    rss_file = "rss/rss_agent.py"
    with open(rss_file, 'r', encoding='utf-8') as f:
        content = f.read()

    rss_checks = [
        ("获取 RSS 源列表进度", "RSS"),
        ("获取文章完整内容进度", "文章"),
        ("下载文章内容", "文章")
    ]

    for desc, keyword in rss_checks:
        if desc in content:
            results.append((rss_file, desc, True))
        else:
            results.append((rss_file, desc, False))

    all_passed = True
    for file, desc, passed in results:
        status = "✓" if passed else "✗"
        print(f"{status} {file}: {desc}")
        if not passed:
            all_passed = False

    print("\n=== 测试结果 ===")
    if all_passed:
        print("✓ 所有进度条描述已改进，包含上下文信息")
        return True
    else:
        print("✗ 部分进度条描述仍需改进")
        return False

if __name__ == "__main__":
    success = check_progress_descriptions()
    sys.exit(0 if success else 1)
