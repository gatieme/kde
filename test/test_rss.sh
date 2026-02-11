#!/bin/bash

# RSS agent 测试脚本

# 获取项目根目录
PROJECT_ROOT=$(dirname "$(dirname "$(realpath "$0")")")

# 测试命令列表
test_commands=(
    # 通过 kde.py 测试 RSS agent
    "python3 \"$PROJECT_ROOT/kde.py\" --rss"
    "python3 \"$PROJECT_ROOT/kde.py\" --rss=LWN"
    "python3 \"$PROJECT_ROOT/kde.py\" --rss=Phoronix"
    "python3 \"$PROJECT_ROOT/kde.py\" --rss=LWN --level=2"
    "python3 \"$PROJECT_ROOT/kde.py\" --rss=Phoronix --level=3"
    
    # 直接调用 rss_agent.py 测试
    "python3 \"$PROJECT_ROOT/rss/rss_agent.py\" --help"
)

# 测试名称列表
test_names=(
    "RSS 所有源测试"
    "RSS LWN 源测试"
    "RSS Phoronix 源测试"
    "RSS LWN 源限制文章数测试"
    "RSS Phoronix 源限制文章数测试"
    "RSS agent 帮助信息测试"
)

# 测试描述列表
test_descriptions=(
    "测试 RSS agent 分析所有源的文章"
    "测试 RSS agent 分析 LWN 源的文章"
    "测试 RSS agent 分析 Phoronix 源的文章"
    "测试 RSS agent 分析 LWN 源的 2 篇文章"
    "测试 RSS agent 分析 Phoronix 源的 3 篇文章"
    "测试 RSS agent 的帮助信息显示"
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
    echo "开始测试 RSS agent...\n"
    echo "项目根目录: $PROJECT_ROOT"
    echo "测试命令数量: ${#test_commands[@]}"
    
    # 运行所有测试
    for ((i=0; i<${#test_commands[@]}; i++)); do
        run_test $i
    done
    
    echo "RSS agent 测试完成！"
}

# 运行主测试函数
main
