#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_b4_download_robustness():
    print("=== 测试 LKML agent b4 下载健壮性 ===\n")

    test_lkml_id = "20260122161647.142704-2-realwujing@gmail.com"

    print(f"测试 message-id: {test_lkml_id}")
    print("使用 verbose=2 模式（显示命令和进度条）\n")

    try:
        from lkml.lkml_agent import run_lkml_agent

        start_time = time.time()
        result = run_lkml_agent(lkml_id=test_lkml_id, level="simple", verbose=2)
        end_time = time.time()

        print(f"\n=== 测试完成 ===")
        print(f"执行时间: {end_time - start_time:.2f} 秒")
        print(f"返回状态类型: {type(result).__name__}")

        if hasattr(result, 'work_dir'):
            print(f"工作目录: {result.work_dir}")
            if os.path.exists(result.work_dir):
                files = os.listdir(result.work_dir)
                print(f"缓存文件数: {len(files)}")
                if files:
                    print("缓存文件:")
                    for f in files[:5]:
                        print(f"  - {f}")
                    if len(files) > 5:
                        print(f"  ... 还有 {len(files) - 5} 个文件")
            else:
                print("警告: 工作目录不存在")

        return True

    except Exception as e:
        print(f"\n=== 测试失败 ===")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {e}")

        if "Timeout" in str(e) or "timeout" in str(e).lower():
            print("\n建议:")
            print("- 检查网络连接是否正常")
            print("- 检查 b4 工具是否正确安装")
            print("- 尝试增加超时时间或使用更快的网络环境")
        elif "download" in str(e).lower() or "下载" in str(e):
            print("\n建议:")
            print("- 检查 message-id 是否正确")
            print("- 检查网络连接是否正常")
            print("- 检查是否有防火墙限制")
        else:
            print("\n建议:")
            print("- 检查环境配置")
            print("- 查看详细错误信息（使用 verbose=3）")

        return False

if __name__ == "__main__":
    success = test_b4_download_robustness()
    sys.exit(0 if success else 1)

