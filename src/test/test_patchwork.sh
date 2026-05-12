#!/bin/bash

# Patchwork agent 测试脚本

# 获取项目根目录
PROJECT_ROOT=$(dirname "$(dirname "$(realpath "$0")")")

# 测试命令列表
test_commands=(
    # Test 1: simple mode through kde.py
    "python3 \"$PROJECT_ROOT/kde.py\" --patchwork 365 --date 2022-01-27 --level simple --max-series 2 -v"

    # Test 2: detail mode through kde.py (without LKML agent call for speed)
    "python3 \"$PROJECT_ROOT/kde.py\" --patchwork 365 --date 2022-01-27 --level simple --max-series 1 -v"

    # Test 3: direct call to patchwork_agent.py
    "python3 \"$PROJECT_ROOT/patchwork/patchwork_agent.py\" --project 365 --date 2022-01-27 --level simple --max-series 2 -v"

    # Test 4: recent N days mode
    "python3 \"$PROJECT_ROOT/kde.py\" --patchwork 365 --days 1 --level simple --max-series 1 -v"

    # Test 5: multiple projects
    "python3 \"$PROJECT_ROOT/kde.py\" --patchwork 365 366 --date 2022-01-27 --level simple --max-series 1 -v"

    # Test 6: project by name
    "python3 \"$PROJECT_ROOT/kde.py\" --patchwork 'Linux MM' --date 2022-01-27 --level simple --max-series 1 -v"

    # Test 7: parallel processing
    "python3 \"$PROJECT_ROOT/kde.py\" --patchwork 365 --date 2022-01-27 --level simple --max-series 3 --max-parallel 2 -v"

    # Test 8: verbose level 2
    "python3 \"$PROJECT_ROOT/kde.py\" --patchwork 365 --date 2022-01-27 --level simple --max-series 1 -vv"

    # Test 9: field extraction tests
    "python3 \"$PROJECT_ROOT/patchwork/patchwork_agent.py\" --test -v"
)

# 测试名称列表
test_names=(
    "Patchwork 简单模式测试（通过 kde.py）"
    "Patchwork 简单模式测试（通过 kde.py，单 series）"
    "Patchwork 简单模式测试（直接调用）"
    "Patchwork 最近 N 天模式测试"
    "Patchwork 多项目测试"
    "Patchwork 项目名称测试"
    "Patchwork 并发处理测试"
    "Patchwork verbose 模式测试"
    "Patchwork 字段提取函数测试"
)

# 测试描述列表
test_descriptions=(
    "通过 kde.py 测试 Patchwork agent 的简单模式分析，处理 2 个 series"
    "通过 kde.py 测试 Patchwork agent 的简单模式分析，处理 1 个 series"
    "直接调用 patchwork_agent.py 测试简单模式分析"
    "测试最近 N 天模式获取 series"
    "测试同时处理多个项目"
    "测试通过项目名称查找项目 ID"
    "测试并发处理 series（2 个线程）"
    "测试 verbose 级别 2 输出详细日志"
    "测试字段提取函数的正确性"
)

# 运行单个测试
run_test() {
    local index=$1
    local name="${test_names[$index]}"
    local description="${test_descriptions[$index]}"
    local command="${test_commands[$index]}"

    echo ""
    echo "=================================================="
    echo "测试: $name"
    echo "描述: $description"
    echo "命令: $command"
    echo "=================================================="

    # 运行命令
    local start_time=$(date +%s)
    eval "$command"
    local return_code=$?
    local end_time=$(date +%s)
    local execution_time=$((end_time - start_time))

    # 打印结果
    echo ""
    echo "执行时间: $execution_time 秒"
    echo "返回码: $return_code"

    if [ $return_code -eq 0 ]; then
        echo ""
        echo "✓ 测试通过!"
    else
        echo ""
        echo "✗ 测试失败!"
    fi

    echo "=================================================="
    echo ""

    # 测试间隔，避免请求过于频繁
    sleep 2
}

# 主测试函数
main() {
    echo "开始测试 Patchwork agent..."
    echo ""
    echo "项目根目录: $PROJECT_ROOT"
    echo "测试命令数量: ${#test_commands[@]}"

    # 运行所有测试
    for ((i=0; i<${#test_commands[@]}; i++)); do
        run_test $i
    done

    echo "Patchwork agent 测试完成！"
}

# 运行主测试函数
main