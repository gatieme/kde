#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试脚本，用于测试所有可能的命令组合
"""

import os
import sys
import subprocess
import time

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 测试命令列表
test_commands = [
    # LKML 相关测试（通过 kde.py）
    {
        "name": "LKML 简单模式测试（通过 kde.py）",
        "command": f"python3 {os.path.join(PROJECT_ROOT, 'kde.py')} --level=simple --lkml 20260122161647.142704-2-realwujing@gmail.com",
        "description": "通过 kde.py 测试 LKML agent 的简单模式分析"
    },
    {
        "name": "LKML 详细模式测试（通过 kde.py）",
        "command": f"python3 {os.path.join(PROJECT_ROOT, 'kde.py')} --level=detail --lkml 20260122161647.142704-2-realwujing@gmail.com",
        "description": "通过 kde.py 测试 LKML agent 的详细模式分析"
    },

    # LKML 相关测试（直接调用 lkml_agent.py）
    {
        "name": "LKML 简单模式测试（直接调用）",
        "command": f"python3 {os.path.join(PROJECT_ROOT, 'lkml', 'lkml_agent.py')} --message_id=20260122161647.142704-2-realwujing@gmail.com --level=simple",
        "description": "直接调用 lkml_agent.py 测试简单模式分析"
    },
    {
        "name": "LKML 详细模式测试（直接调用）",
        "command": f"python3 {os.path.join(PROJECT_ROOT, 'lkml', 'lkml_agent.py')} --message_id=20260122161647.142704-2-realwujing@gmail.com --level=detail",
        "description": "直接调用 lkml_agent.py 测试详细模式分析"
    },

    # RSS 相关测试（通过 kde.py）
    {
        "name": "RSS 所有源测试",
        "command": f"python3 {os.path.join(PROJECT_ROOT, 'kde.py')} --rss",
        "description": "测试 RSS agent 分析所有源的文章"
    },
    {
        "name": "RSS LWN 源测试",
        "command": f"python3 {os.path.join(PROJECT_ROOT, 'kde.py')} --rss=LWN",
        "description": "测试 RSS agent 分析 LWN 源的文章"
    },
    {
        "name": "RSS Phoronix 源测试",
        "command": f"python3 {os.path.join(PROJECT_ROOT, 'kde.py')} --rss=Phoronix",
        "description": "测试 RSS agent 分析 Phoronix 源的文章"
    },
    {
        "name": "RSS LWN 源限制文章数测试",
        "command": f"python3 {os.path.join(PROJECT_ROOT, 'kde.py')} --rss=LWN --level=2",
        "description": "测试 RSS agent 分析 LWN 源的 2 篇文章"
    },
    {
        "name": "RSS Phoronix 源限制文章数测试",
        "command": f"python3 {os.path.join(PROJECT_ROOT, 'kde.py')} --rss=Phoronix --level=3",
        "description": "测试 RSS agent 分析 Phoronix 源的 3 篇文章"
    },

    # RSS 相关测试（直接调用 rss_agent.py）
    {
        "name": "RSS agent 帮助信息测试",
        "command": f"python3 {os.path.join(PROJECT_ROOT, 'rss', 'rss_agent.py')} --help",
        "description": "测试 RSS agent 的帮助信息显示"
    },

    # 帮助信息测试
    {
        "name": "帮助信息测试",
        "command": f"python3 {os.path.join(PROJECT_ROOT, 'kde.py')} --help",
        "description": "测试显示帮助信息"
    }
]

def run_test(command_info):
    """运行单个测试命令"""
    print(f"\n{'='*80}")
    print(f"测试: {command_info['name']}")
    print(f"描述: {command_info['description']}")
    print(f"命令: {command_info['command']}")
    print(f"{'='*80}")

    try:
        # 运行命令
        start_time = time.time()
        result = subprocess.run(
            command_info['command'],
            shell=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        end_time = time.time()

        # 打印结果
        print(f"\n执行时间: {end_time - start_time:.2f} 秒")
        print(f"返回码: {result.returncode}")

        if result.returncode == 0:
            print("\n✓ 测试通过!")
            # 打印部分输出（最多 50 行）
            output_lines = result.stdout.split('\n')
            if len(output_lines) > 50:
                print("\n输出（前 50 行）:")
                for line in output_lines[:50]:
                    print(line)
                print("... (输出被截断)")
            else:
                print("\n输出:")
                print(result.stdout)
        else:
            print("\n✗ 测试失败!")
            print("\n标准输出:")
            print(result.stdout)
            print("\n标准错误:")
            print(result.stderr)

    except Exception as e:
        print(f"\n✗ 测试异常: {e}")

    print(f"{'='*80}\n")
    # 测试间隔，避免请求过于频繁
    time.sleep(2)

def main():
    """主测试函数"""
    print("开始测试所有命令组合...\n")
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"测试命令数量: {len(test_commands)}")

    # 运行所有测试
    for command_info in test_commands:
        run_test(command_info)

    print("所有测试完成！")

if __name__ == "__main__":
    main()
