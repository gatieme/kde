#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试各个 agent 的缓存目录配置
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_cache_directories():
    print("=== 测试缓存目录配置 ===\n")

    from cgit.cgit_agent import CGitAgentState
    test_commit_id = "test_commit_1234567890"

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    expected_cgit_cache = os.path.join(repo_root, "output", "cgit", test_commit_id)

    cgit_state = CGitAgentState(
        messages=[{"role": "system", "content": "Test"}],
        commit_id=test_commit_id
    )
    print(f"CGit Agent:")
    print(f"  期望缓存目录: {expected_cgit_cache}")
    print(f"  缓存目录存在: {os.path.exists(expected_cgit_cache)}")

    from lkml.lkml_agent import LKMLAgentState
    test_lkml_id = "20260114130528.GB831285@noisy.programming.kicks-ass.net"

    expected_lkml_cache = os.path.join(repo_root, "output", "lkml", test_lkml_id)

    lkml_state = LKMLAgentState(
        messages=[{"role": "system", "content": "Test"}],
        lkml_id=test_lkml_id
    )
    print(f"\nLKML Agent:")
    print(f"  期望缓存目录: {expected_lkml_cache}")
    print(f"  缓存目录存在: {os.path.exists(expected_lkml_cache)}")

    from rss.rss_agent import AgentState
    expected_rss_cache = os.path.join(repo_root, "output", "rss")

    rss_state = AgentState(
        messages=[{"role": "system", "content": "Test"}]
    )
    print(r"\nRSS Agent:")
    print(f"  期望缓存目录: {expected_rss_cache}")
    print(f"  缓存目录存在: {os.path.exists(expected_rss_cache)}")

    print(r"\n=== 验证 output 目录结构 ===")
    output_dir = os.path.join(repo_root, "output")
    subdirs = ["cgit", "lkml", "rss"]

    all_exist = True
    for subdir in subdirs:
        subdir_path = os. path.join(output_dir, subdir)
        exists = os.path.exists(subdir_path)
        status = "✓" if exists else "✗"
        print(f"{status} {subdir_path}")
        if not exists:
            all_exist = False

    print(r"\n=== 测试结果 ===")
    if all_exist:
        print("✓ 所有缓存目录已正确配置")
        return True
    else:
        print("✗ 部分缓存目录不存在")
        return False

if __name__ == "__main__":
    success = test_cache_directories()
    sys.exit(0 if success else 1)

