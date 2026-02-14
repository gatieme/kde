# -*- coding: utf-8 -*-

import os
import sys
import re
import datetime
import subprocess
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import Annotated, List, Dict, Any, Optional
from dataclasses import dataclass, field
from tqdm import tqdm

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model import ModelInference, ModelRequest
from lkml.lkml_agent import run_lkml_agent

@dataclass
class CGitAgentState:
    messages: Annotated[List[Dict[str, Any]], add_messages]
    commit_id: str = ""
    level: str = "simple"
    work_dir: str = ""
    commit_file: str = ""
    date: str = ""
    author: str = ""
    email: str = ""
    subject: str = ""
    web_url: str = ""
    content: str = ""
    summary: str = "TODO"
    analysis: str = ""
    patchset_link: str = ""
    has_patchset: bool = False
    verbose: int = 0

def fetch_commit(state: CGitAgentState) -> CGitAgentState:
    if state.verbose >= 2:
        print("=== 下载 commit 信息 ===\n")

    # 创建工作目录
    if not state.work_dir:
        state.work_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), state.commit_id)
    os.makedirs(state.work_dir, exist_ok=True)

    # 切换到工作目录
    original_dir = os.getcwd()
    os.chdir(state.work_dir)

    try:
        # 下载 commit 补丁
        commit_url = f"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/patch/?id={state.commit_id}"
        state.commit_file = os.path.join(state.work_dir, state.commit_id)

        command = ["wget", commit_url, "-O", state.commit_id]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # 打印状态消息（无 -v 时）
        if state.verbose < 1:
            print("下载 commit 信息中...")

        if state.verbose >= 3:
            for line in process.stdout:
                print(line, end='')
        elif state.verbose >= 1:
            # 使用 tqdm 显示进度条
            with tqdm(total=100, desc="下载进度", unit="%") as pbar:
                # 读取输出并更新进度条
                for line in process.stdout:
                    # 这里简单地模拟进度，实际可以根据 wget 的输出解析真实进度
                    if "%" in line:
                        # 尝试从 wget 输出中提取进度百分比
                        try:
                            progress = int(re.search(r'(\d+)%', line).group(1))
                            pbar.n = progress
                            pbar.refresh()
                        except:
                            pass
                    else:
                        # 如果没有百分比信息，就模拟进度
                        pbar.update(1)
                # 确保进度条显示到 100%
                pbar.n = 100
                pbar.refresh()
        else:
            # 静默执行，只捕获返回码
            output = process.communicate()[0]

        returncode = process.wait()
        if returncode != 0:
            print(f"命令执行失败，返回码: {returncode}")
            if state.verbose >= 3:
                print(output)
            raise Exception(f"下载 commit 失败，返回码: {returncode}")

        if state.verbose >= 2:
            print(f"成功下载 commit: {state.commit_id}")

    finally:
        # 恢复原目录
        os.chdir(original_dir)

    return state

def parse_commit(state: CGitAgentState) -> CGitAgentState:
    if state.verbose >= 2:
        print("=== 解析 commit 信息 ===\n")

    if not state.commit_file:
        raise Exception("没有找到可解析的 commit 文件")

    try:
        with open(state.commit_file, 'r', encoding='utf-8') as file:
            content = file.read()

        # 提取主题
        subject_match = re.search(r'Subject: (.*)', content)
        if subject_match:
            state.subject = subject_match.group(1)

        # 提取日期
        date_str_match = re.search(r'Date: (.*) [-|+]([0-9]{1,}).*', content)
        if date_str_match:
            date_str = date_str_match.group(1)
            date_value = int(datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S').timestamp())
            state.date = datetime.datetime.fromtimestamp(date_value).strftime('%Y/%m/%d')

        # 提取作者
        author_match = re.search(r'From: (.*) <(.*)>', content)
        if author_match:
            state.author = author_match.group(1)
            state.email = author_match.group(2)

        # 提取链接
        state.web_url = f"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id={state.commit_id}"

        # 提取内容
        state.content = content

        if state.verbose >= 2:
            print(f"作者: {state.author} <{state.email}>")
            print(f"日期: {state.date}")
            print(f"主题: {state.subject}")
            print(f"链接: {state.web_url}")

    except Exception as e:
        print(f"解析 commit 失败: {e}")
        raise

    return state

def analyze_commit(state: CGitAgentState) -> CGitAgentState:
    if state.verbose >= 2:
        print("=== 分析 commit 内容 ===\n")

    try:
        # 生成摘要
        model_req = ModelRequest("summary", state.content)
        messages = model_req.get_messages()

        model_infer = ModelInference(verbose=state.verbose)
        model_infer.inference(messages)

        state.summary = model_infer.get_answer()
        if state.verbose >= 2:
            print("摘要生成完成")
            print(f"摘要: {state.summary[:100]}...")

        # 只有 detail 级别才进行详细分析
        if state.level == "detail":
            if state.verbose >= 2:
                print("进行详细分析...")
            model_req = ModelRequest("analysis", state.content)
            messages = model_req.get_messages()

            model_infer = ModelInference(verbose=state.verbose)
            model_infer.inference(messages)

            state.analysis = model_infer.get_answer()
            if state.verbose >= 2:
                print("详细分析完成")

    except Exception as e:
        print(f"分析 commit 失败: {e}")
        state.summary = "无法生成摘要"

    return state

def check_patchset(state: CGitAgentState) -> CGitAgentState:
    if state.verbose >= 2:
        print("=== 检查 patchset 链接 ===\n")

    try:
        # 从 commit 内容中提取 Link 字段（支持带尖括号和不带尖括号两种格式）
        link_match = re.search(r'Link:\s*(?:<)?(https?://[^>\s]+)(?:>)?', state.content)
        if link_match:
            state.patchset_link = link_match.group(1)
            state.has_patchset = True
            if state.verbose >= 2:
                print(f"找到 patchset 链接: {state.patchset_link}")
        else:
            # 尝试从其他字段中提取
            if state.verbose >= 2:
                print("未找到 Link 字段，尝试从其他字段提取...")
            # 检查是否有 Lore 链接
            lore_match = re.search(r'https?://lore\.kernel\.org/.*', state.content)
            if lore_match:
                state.patchset_link = lore_match.group(0)
                state.has_patchset = True
                if state.verbose >= 2:
                    print(f"找到 Lore 链接: {state.patchset_link}")
            else:
                # 检查是否有其他类型的补丁链接
                other_match = re.search(r'https?://.*patch.*', state.content)
                if other_match:
                    state.patchset_link = other_match.group(0)
                    state.has_patchset = True
                    if state.verbose >= 2:
                        print(f"找到其他补丁链接: {state.patchset_link}")
                else:
                    if state.verbose >= 2:
                        print("未找到 patchset 链接")
                    state.has_patchset = False

    except Exception as e:
        print(f"检查 patchset 失败: {e}")
        state.has_patchset = False

    return state

def run_lkml_analysis(state: CGitAgentState) -> CGitAgentState:
    if state.verbose >= 2:
        print("=== 运行 LKML 代理分析 patchset ===\n")

    try:
        if state.has_patchset and state.patchset_link:
            if state.verbose >= 2:
                print(f"使用 {state.level} 级别分析 patchset")

            # 从 patchset 链接中提取 message-id
            # 格式1: https://lore.kernel.org/all/20250621235745.3994-1-atomlin@atomlin.co
            message_id_match = re.search(r'https?://lore\.kernel\.org/all/(.*)', state.patchset_link)
            if message_id_match:
                message_id = message_id_match.group(1)
                if state.verbose >= 2:
                    print(f"从 Lore 链接提取 message-id: {message_id}")
                # 运行 LKML 代理分析
                try:
                    if state.verbose >= 2:
                        print("尝试运行 LKML 代理...")
                    run_lkml_agent(lkml_id=message_id, level=state.level, verbose=state.verbose)
                    if state.verbose >= 2:
                        print("LKML 代理运行成功")
                except Exception as e:
                    print(f"运行 LKML 代理失败: {e}")
                    if state.verbose >= 3:
                        import traceback
                        traceback.print_exc()
            else:
                # 格式2: https://patch.msgid.link/20260114130528.GB831285@noisy.programming.kicks-ass.net
                msgid_match = re.search(r'https?://[^/]+/(.*)', state.patchset_link)
                if msgid_match:
                    message_id = msgid_match.group(1)
                    if state.verbose >= 2:
                        print(f"从补丁链接提取 message-id: {message_id}")
                    # 运行 LKML 代理分析
                    try:
                        if state.verbose >= 2:
                            print("尝试运行 LKML 代理...")
                        run_lkml_agent(lkml_id=message_id, level=state.level, verbose=state.verbose)
                        if state.verbose >= 2:
                            print("LKML 代理运行成功")
                    except Exception as e:
                        print(f"运行 LKML 代理失败: {e}")
                        if state.verbose >= 3:
                            import traceback
                            traceback.print_exc()
                else:
                    # 尝试直接使用链接作为 message-id
                    if state.verbose >= 2:
                        print(f"尝试直接使用链接作为 message-id: {state.patchset_link}")
                    try:
                        if state.verbose >= 2:
                            print("尝试运行 LKML 代理...")
                        run_lkml_agent(lkml_id=state.patchset_link, level=state.level, verbose=state.verbose)
                        if state.verbose >= 2:
                            print("LKML 代理运行成功")
                    except Exception as e:
                        print(f"直接使用链接失败: {e}")
                        if state.verbose >= 3:
                            import traceback
                            traceback.print_exc()
                        if state.verbose >= 2:
                            print("无法从 patchset 链接提取 message-id")
        else:
            if state.verbose >= 2:
                print("没有 patchset 链接，跳过 LKML 代理分析")

    except Exception as e:
        print(f"运行 LKML 代理失败: {e}")
        if state.verbose >= 3:
            import traceback
            traceback.print_exc()

    if state.verbose >= 2:
        print("\n=== LKML 代理分析完成 ===\n")
    return state

def output_results(state: CGitAgentState) -> CGitAgentState:
    if state.verbose >= 2:
        print("=== 输出结果 ===\n")

    # 打印分析级别
    if state.verbose >= 1:
        print(f"分析级别: {state.level}")
        print()

    # 打印 Markdown 表格（与原始脚本格式一致）
    print("---")
    print("| 时间  | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |")
    print("|:-----:|:----:|:----:|:----:|:------------:|:----:|")

    # 提取版本信息（如果有）
    version = "1"
    version_match = re.search(r'Subject:.*v([0-9]{1,}).*', state.content)
    if version_match:
        version = version_match.group(1)
        if len(version) > 10:
            version = "1"

    # 打印表格行
    print(f"| {state.date} | {state.author} <{state.email}> | [{state.subject}]({state.web_url}) | {state.summary} | v{version} ☐☑✓ | [CGIT]({state.web_url}) |")

    # 如果是 detail 级别，打印详细分析
    if state.level == "detail" and state.analysis:
        if state.verbose >= 2:
            print("\n=== 详细分析 ===\n")
        if state.verbose >= 3:
            print(state.analysis)

    # 打印 patchset 信息
    if state.has_patchset:
        if state.verbose >= 2:
            print("\n=== Patchset 信息 ===\n")
            print(f"Patchset 链接: {state.patchset_link}")
            print(f"已触发 LKML 代理使用 {state.level} 级别分析 patchset")
    else:
        if state.verbose >= 2:
            print("\n=== Patchset 信息 ===\n")
            print("未找到 patchset 链接")
            if state.level == "detail":
                print("只对当前 commit 进行了详细分析")

    return state

def build_cgit_agent():
    workflow = StateGraph(CGitAgentState)

    workflow.add_node("fetch_commit", fetch_commit)
    workflow.add_node("parse_commit", parse_commit)
    workflow.add_node("analyze_commit", analyze_commit)
    workflow.add_node("check_patchset", check_patchset)
    workflow.add_node("run_lkml_analysis", run_lkml_analysis)
    workflow.add_node("output_results", output_results)

    workflow.set_entry_point("fetch_commit")
    workflow.add_edge("fetch_commit", "parse_commit")
    workflow.add_edge("parse_commit", "analyze_commit")
    workflow.add_edge("analyze_commit", "output_results")
    workflow.add_edge("output_results", "check_patchset")
    workflow.add_edge("check_patchset", "run_lkml_analysis")
    workflow.add_edge("run_lkml_analysis", END)

    return workflow.compile()

def run_cgit_agent(commit_id: str, level: str = "simple", work_dir: str = None, verbose: int = 0):
    agent = build_cgit_agent()

    initial_state = CGitAgentState(
        messages=[{"role": "system", "content": "你是一个 CGit commit 分析智能体，负责下载、解析和分析 Linux 内核的 commit 信息。"}],
        commit_id=commit_id,
        level=level,
        work_dir=work_dir,
        verbose=verbose
    )

    result = agent.invoke(initial_state)
    return result

def parse_args():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(
        description="CGit commit 分析智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cgit_agent.py --commit_id=1234567890abcdef --level=simple  # 简要分析
  python cgit_agent.py --commit_id=1234567890abcdef --level=detail  # 详细分析
"""
    )
    parser.add_argument(
        "--commit_id",
        type=str,
        required=True,
        help="指定 Linux 内核的 commit ID"
    )
    parser.add_argument(
        "--level",
        type=str,
        choices=["simple", "detail"],
        default="simple",
        help="分析级别: simple (简要分析) 或 detail (详细分析)"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    run_cgit_agent(args.commit_id, args.level)
