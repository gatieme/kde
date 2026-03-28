#!/bin/bash

# 测试 --verbose 参数功能

echo "=== 测试 --verbose 参数功能 ==="
echo ""

# 测试 lkml agent 的 verbose 参数
echo "1. 测试 lkml agent 的 verbose 参数"
echo "命令: python kde.py --lkml 20250621235745.3994-1-atomlin@atomlin.co --level=simple --verbose"
echo ""

# 测试 cgit agent 的 verbose 参数
echo "2. 测试 cgit agent 的 verbose 参数"
echo "命令: python kde.py --cgit 53439363c0a111f11625982b69c88ee2ce8608ec --level=simple --verbose"
echo ""

# 测试 rss agent 的 verbose 参数
echo "3. 测试 rss agent 的 verbose 参数"
echo "命令: python kde.py --rss phoronix --level=2 --verbose"
echo ""

# 测试不同级别的 verbose 参数
echo "4. 测试不同级别的 verbose 参数"
echo "命令: python kde.py --cgit 53439363c0a111f11625982b69c88ee2ce8608ec --level=simple -vv"
echo ""
echo "命令: python kde.py --cgit 53439363c0a111f11625982b69c88ee2ce8608ec --level=simple -vvv"
echo ""

# 提示用户如何运行测试
echo "要运行测试，请执行以下命令:"
echo "  ./test_verbose.sh"
