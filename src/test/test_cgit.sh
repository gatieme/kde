#!/bin/bash

# 测试 cgit agent

echo "=== 测试 cgit agent ==="
echo ""

# 测试简单分析模式
echo "1. 测试简单分析模式"
echo "命令: python kde.py --cgit=1234567890abcdef --level=simple"
echo ""

# 测试详细分析模式
echo "2. 测试详细分析模式"
echo "命令: python kde.py --cgit=1234567890abcdef --level=detail"
echo ""

# 提示用户如何运行测试
echo "要运行测试，请执行以下命令:"
echo "  ./test_cgit.sh"
echo ""
echo "注意: 请替换 1234567890abcdef 为实际的 Linux 内核 commit ID"
