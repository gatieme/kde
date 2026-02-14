#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 cgit_agent 的工作流顺序，验证 COMMIT 分析结果在 LKML 分析之前输出
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cgit.cgit_agent import build_cgit_agent

def test_workflow_order():
    print("=== 测试 CGit Agent 工作流顺序 ===\n")

    agent = build_cgit_agent()
    graph = agent.get_graph()

    print("工作流节点:")
    for node in graph.nodes.keys():
        print(f"  - {node}")

    print("\n工作流边（执行顺序）:")
    edges = list(graph.edges)

    expected_edges = [
        ('__start__', 'fetch_commit'),
        ('fetch_commit', 'parse_commit'),
        ('parse_commit', 'analyze_commit'),
        ('analyze_commit', 'output_results'),
        ('output_results', 'check_patchset'),
        ('check_patchset', 'run_lkml_analysis'),
        ('run_lkml_analysis', '__end__')
    ]

    edges_dict = {(edge.source, edge.target): edge for edge in edges}

    all_edges_present = True
    for edge in expected_edges:
        if edge in edges_dict:
            print(f"  ✓ {edge[0]} -> {edge[1]}")
        else:
            print(f"  ✗ {edge[0]} -> {edge[1]} (缺失!)")
            all_edges_present = False

    wrong_edge = ('check_patchset', 'output_results')
    if wrong_edge in edges_dict:
        print(f"\n  ✗ 发现错误的边: {wrong_edge[0]} -> {wrong_edge[1]}")
        print("     这会导致 LKML 分析在 COMMIT 输出之前执行！")
        all_edges_present = False

    wrong_edge2 = ('analyze_commit', 'check_patchset')
    if wrong_edge2 in edges_dict:
        print(f"\n  ✗ 发现错误的边: {wrong_edge2[0]} -> {wrong_edge2[1]}")
        print("     这会导致 COMMIT 分析结果在 LKML 检查之后才输出！")
        all_edges_present = False

    print("\n=== 测试结果 ===")
    if all_edges_present:
        print("✓ 所有工作流边配置正确")
        print("✓ COMMIT 分析结果将在 LKML 分析之前输出")
        return True
    else:
        print("✗ 工作流配置有误，请检查")
        return False

if __name__ == "__main__":
    success = test_workflow_order()
    sys.exit(0 if success else 1)
