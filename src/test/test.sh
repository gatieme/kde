#!/bin/bash

# 测试脚本，用于一键式测试所有可能的命令组合

# 获取项目根目录
PROJECT_ROOT=$(dirname "$(dirname "$(realpath "$0")")")

# 测试命令列表
test_commands=(
    # LKML 相关测试（通过 kde.py）
    "python3 \"$PROJECT_ROOT/kde.py\" --level=simple --lkml 20260122161647.142704-2-realwujing@gmail.com"
    "python3 \"$PROJECT_ROOT/kde.py\" --level=detail --lkml 20260122161647.142704-2-realwujing@gmail.com"

    # LKML 相关测试（直接调用 lkml_agent.py）
    "python3 \"$PROJECT_ROOT/lkml/lkml_agent.py\" --message_id=20260122161647.142704-2-realwujing@gmail.com --level=simple"
    "python3 \"$PROJECT_ROOT/lkml/lkml_agent.py\" --message_id=20260122161647.142704-2-realwujing@gmail.com --level=detail"

    # RSS 相关测试（通过 kde.py）
    "python3 \"$PROJECT_ROOT/kde.py\" --rss"
    "python3 \"$PROJECT_ROOT/kde.py\" --rss=LWN"
    "python3 \"$PROJECT_ROOT/kde.py\" --rss=Phoronix"
    "python3 \"$PROJECT_ROOT/kde.py\" --rss=LWN --level=2"
    "python3 \"$PROJECT_ROOT/kde.py\" --rss=Phoronix --level=3"

    # RSS 相关测试（直接调用 rss_agent.py）
    "python3 \"$PROJECT_ROOT/rss/rss_agent.py\" --help"

    # 帮助信息测试
    "python3 \"$PROJECT_ROOT/kde.py\" --help"
)

# 测试名称列表
test_names=(
    "LKML 简单模式测试（通过 kde.py）"
    "LKML 详细模式测试（通过 kde.py）"
    "LKML 简单模式测试（直接调用）"
    "LKML 详细模式测试（直接调用）"
    "RSS 所有源测试"
    "RSS LWN 源测试"
    "RSS Phoronix 源测试"
    "RSS LWN 源限制文章数测试"
    "RSS Phoronix 源限制文章数测试"
    "RSS agent 帮助信息测试"
    "帮助信息测试"
)

# 测试描述列表
test_descriptions=(
    "通过 kde.py 测试 LKML agent 的简单模式分析"
    "通过 kde.py 测试 LKML agent 的详细模式分析"
    "直接调用 lkml_agent.py 测试简单模式分析"
    "直接调用 lkml_agent.py 测试详细模式分析"
    "测试 RSS agent 分析所有源的文章"
    "测试 RSS agent 分析 LWN 源的文章"
    "测试 RSS agent 分析 Phoronix 源的文章"
    "测试 RSS agent 分析 LWN 源的 2 篇文章"
    "测试 RSS agent 分析 Phoronix 源的 3 篇文章"
    "测试 RSS agent 的帮助信息显示"
    "测试显示帮助信息"
)

# 运行单个测试
run_test() {
    local index=$1
    local name="${test_names[$index]}"
    local description="${test_descriptions[$index]}"
    local command="${test_commands[$index]}"

    echo "\n=================================================="
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
    echo "\n执行时间: $execution_time 秒"
    echo "返回码: $return_code"

    if [ $return_code -eq 0 ]; then
        echo "\n✓ 测试通过!"
    else
        echo "\n✗ 测试失败!"
    fi

    echo "==================================================\n"

    # 测试间隔，避免请求过于频繁
    sleep 2
}

# 主测试函数
main() {
    echo "开始测试所有命令组合...\n"
    echo "项目根目录: $PROJECT_ROOT"
    echo "测试命令数量: ${#test_commands[@]}"

    # 运行所有测试
    for ((i=0; i<${#test_commands[@]}; i++)); do
        run_test $i
    done

    echo "所有测试完成！"
}

# 运行主测试函数
main
