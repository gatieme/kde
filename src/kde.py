# -*- coding: utf-8 -*-
import sys
import argparse
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from lkml.lkml_agent import run_lkml_agent
from cgit.cgit_agent import run_cgit_agent
from utils import format_text_for_markdown

# Legacy functions for backward compatibility (moved to utils.py)
from utils import chinese_to_english_punctuation, add_space_after_punctuation, replace_newline_with_br
def replace_newline_with_br(text):
    """Replace newline characters with <br> tag"""
    return text.replace('\n', '<br>')
def lkml_run(lkml_message_id, level, verbose=0):
    """运行 LKML agent 分析补丁"""
    try:
        run_lkml_agent(lkml_id=lkml_message_id, level=level, verbose=verbose)
    except Exception as e:
        print(f"运行 LKML agent 失败: {e}")
        sys.exit(1)

def rss_run(source=None, max_articles=None, verbose=0):
    """运行 RSS agent 分析文章"""
    try:
        # 导入必要的模块
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'rss'))

        # 导入整个模块
        import rss.rss_agent as rss_agent

        # 调用 run_rss_agent
        rss_agent.run_rss_agent(source=source, max_articles=max_articles, verbose=verbose)

    except Exception as e:
        print(f"运行 RSS agent 失败: {e}")
        sys.exit(1)

def cgit_run(commit_id, level, verbose=0):
    """运行 CGit agent 分析 commit"""
    try:
        run_cgit_agent(commit_id=commit_id, level=level, verbose=verbose)
    except Exception as e:
        print(f"运行 CGit agent 失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import os
    parser = argparse.ArgumentParser(description='KDE 项目入口')

    # 添加互斥组，确保只能选择一种模式
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--lkml', type=str, help='指定 LKML message-id 进行分析')
    group.add_argument('--rss', type=str, nargs='?', const='all', help='运行 RSS agent 分析技术文章，可指定源 (LWN/Phoronix)')
    group.add_argument('--cgit', type=str, help='指定 Linux 内核 commit ID 进行分析')

    # 添加级别参数
    parser.add_argument('--level', '-level', type=str, default='simple',
                       help='对于 lkml: simple/detail; 对于 rss: 文章数量')

    # 添加 verbose 参数
    parser.add_argument('--verbose', '-v', action='count', default=0,
                       help='详细程度: -v (操作), -vv (日志), -vvv (全量结果)')

    args = parser.parse_args()

    if args.lkml:
        # 运行 LKML agent
        level = args.level
        if level not in ['simple', 'detail']:
            level = 'simple'

        print(f"运行 LKML agent (级别: {level})")
        print(f"分析 message-id: {args.lkml}")
        print()
        lkml_run(lkml_message_id=args.lkml, level=level, verbose=args.verbose)
    elif args.rss:
        # 运行 RSS agent
        source = args.rss if args.rss != 'all' else None

        # 解析文章数量
        max_articles = None
        try:
            max_articles = int(args.level)
        except ValueError:
            pass

        print(f"运行 RSS agent（级别：simple）")
        if source:
            print(f"源: {source}")
        if max_articles:
            print(f"最大文章数: {max_articles}")
        print()
        rss_run(source=source, max_articles=max_articles, verbose=args.verbose)
    elif args.cgit:
        # 运行 CGit agent
        level = args.level
        if level not in ['simple', 'detail']:
            level = 'simple'

        print(f"运行 CGit agent (级别: {level})")
        print(f"分析 commit ID: {args.cgit}")
        print()
        cgit_run(commit_id=args.cgit, level=level, verbose=args.verbose)
