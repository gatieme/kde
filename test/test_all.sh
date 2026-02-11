#!/bin/bash

# 一键式测试所有 agent 的脚本

# 获取项目根目录
PROJECT_ROOT=$(dirname "$(dirname "$(realpath "$0")")")

# 测试脚本列表
test_scripts=(
    "test_lkml.sh"
    "test_rss.sh"
)

# 运行单个测试脚本
run_test_script() {
    local script_name=$1
    local script_path="$(realpath "$0" | xargs dirname)/$script_name"

    echo "\n=================================================="
    echo "运行测试脚本: $script_name"
    echo "脚本路径: $script_path"
    echo "=================================================="

    if [ -f "$script_path" ]; then
        if [ -x "$script_path" ]; then
            "$script_path"
        else
            chmod +x "$script_path"
            "$script_path"
        fi
    else
        echo "错误: 测试脚本 $script_path 不存在!"
    fi

    echo "=================================================="
    echo "测试脚本 $script_name 运行完成"
    echo "==================================================\n"

    # 测试间隔，避免请求过于频繁
    sleep 3
}

# 主测试函数
main() {
    echo "开始运行所有测试脚本...\n"
    echo "项目根目录: $PROJECT_ROOT"
    echo "测试脚本数量: ${#test_scripts[@]}"

    # 运行所有测试脚本
    for script_name in "${test_scripts[@]}"; do
        run_test_script "$script_name"
    done

    echo "所有测试脚本运行完成！"
}

# 运行主测试函数
main
