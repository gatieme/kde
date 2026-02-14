# -*- coding: utf-8 -*-

import os
import sys
import re
import datetime
import subprocess
import time
import select
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import Annotated, List, Dict, Any, Optional
from dataclasses import dataclass, field
from tqdm import tqdm

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model import ModelInference, ModelRequest

@dataclass
class LKMLAgentState:
    messages: Annotated[List[Dict[str, Any]], add_messages]
    lkml_id: str = ""
    level: str = "simple"
    work_dir: str = ""
    cover_file: str = ""
    mbx_file: str = ""
    date: str = ""
    author: str = ""
    email: str = ""
    version: str = ""
    subject: str = ""
    web_url: str = ""
    archive_url: str = ""
    current: str = ""
    total: str = ""
    summary: str = "TODO"
    content: str = ""
    analysis: str = ""
    verbose: int = 0

def fetch_patch(state: LKMLAgentState) -> LKMLAgentState:
    if state.verbose >= 2:
        print("=== 下载 LKML 补丁 ===\n")

    if not state.work_dir:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_root = os.path.join(repo_root, "output", "lkml")
        state.work_dir = os.path.join(cache_root, state.lkml_id)
    os.makedirs(state.work_dir, exist_ok=True)

    # 切换到工作目录
    original_dir = os.getcwd()
    os.chdir(state.work_dir)

    try:
        command = ["b4", "am", state.lkml_id]

        if state.verbose >= 2:
            print(f"执行命令: {' '.join(command)}")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        if state.verbose < 1:
            print("下载补丁中...")

        if state.verbose >= 3:
            for line in process.stdout:
                print(line, end='')
            for line in process.stderr:
                print(line, end='', file=sys.stderr)
        elif state.verbose >= 1:
            with tqdm(total=100, desc="LKML 补丁下载进度", unit="%") as pbar:
                last_progress = 0
                no_output_count = 0
                max_no_output_count = 2
                select_timeout = 5

                import select

                while True:
                    try:
                        readable, _, _ = select.select([process.stdout], [], [], select_timeout)
                        if not readable:
                            no_output_count += 1
                            if state.verbose >= 2:
                                print(f"警告: {(no_output_count * select_timeout)} 秒无输出，检查进程状态。[尝试次数 {no_output_count}/{max_no_output_count}]...")
                            if no_output_count >= max_no_output_count:
                                print(f"警告: 连续 {(no_output_count * select_timeout)} 秒无输出，任务即将终止...")
                                if process.poll() is not None:
                                    break
                                else:
                                    process.terminate()
                                    process.wait(timeout=5)
                                    print(f"警告: 进程已终止，可能已超时")
                                    break
                            continue

                        line = process.stdout.readline()
                        if not line:
                            no_output_count += 1
                            if state.verbose >= 2:
                                print(f"警告: {(no_output_count * select_timeout)} 秒无输出，检查进程状态。[尝试次数 {no_output_count}/{max_no_output_count}]...")
                            if no_output_count >= max_no_output_count:
                                print(f"警告: 连续 {(no_output_count * select_timeout)} 秒无输出，任务即将终止...")
                                if process.poll() is not None:
                                    break
                                else:
                                    process.terminate()
                                    process.wait(timeout=5)
                                    print(f"警告: 进程已终止，可能已超时")
                                    break
                            continue

                        else:
                            no_output_count = 0
                            line = line.strip()

                            if "%" in line:
                                try:
                                    progress = int(re.search(r'(\d+)%', line).group(1))
                                    if progress > last_progress:
                                        pbar.update(progress - last_progress)
                                        last_progress = progress
                                except:
                                    pbar.update(0.5)
                            elif "Download" in line or "Fetch" in line or "Applying" in line:
                                pbar.update(0.5)
                    except subprocess.TimeoutExpired:
                        if process.poll() is not None:
                            break
                        else:
                            process.terminate()
                            process.wait(timeout=5)
                            print(f"警告: 读取输出超时，进程已终止")
                            break
                    except Exception as e:
                        if process.poll() is not None:
                            break
                        else:
                            if state.verbose >= 2:
                                print(f"警告: 读取输出时发生错误: {e}")
                            break

                pbar.n = 100
                pbar.refresh()
        else:
            try:
                output = process.communicate(timeout=300)[0]
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
                raise Exception(f"下载补丁超时（300秒），进程已终止")

        returncode = process.wait()
        if returncode != 0:
            print(f"命令执行失败，返回码: {returncode}")
            if state.verbose >= 3 and 'output' in locals():
                print(output)
            raise Exception(f"下载补丁失败，返回码: {returncode}")

        # 查找下载的文件
        files = os.listdir(state.work_dir)
        cover_files = [f for f in files if f.endswith('.cover')]
        mbx_files = [f for f in files if f.endswith('.mbx')]

        if cover_files:
            state.cover_file = os.path.join(state.work_dir, cover_files[0])
            if state.verbose >= 2:
                print(f"找到 Cover 文件: {state.cover_file}")

        if mbx_files:
            state.mbx_file = os.path.join(state.work_dir, mbx_files[0])
            if state.verbose >= 2:
                print(f"找到 MailBox 文件: {state.mbx_file}")

    finally:
        # 恢复原目录
        os.chdir(original_dir)

    return state

def parse_patch(state: LKMLAgentState) -> LKMLAgentState:
    if state.verbose >= 2:
        print("=== 解析补丁信息 ===\n")

    # 选择要解析的文件
    file_to_parse = state.cover_file if state.cover_file else state.mbx_file
    if not file_to_parse:
        raise Exception("没有找到可解析的补丁文件")

    try:
        with open(file_to_parse, 'r', encoding='utf-8') as file:
            content = file.read()

        # 提取主题
        subject_match = re.search(r'Subject: \[PATCH.*\] (.*)', content)
        if subject_match:
            state.subject = subject_match.group(1)

        # 提取版本
        version_match = re.search(r'Subject:.*v([0-9]{1,}).*', content)
        if version_match:
            state.version = version_match.group(1)
            if len(state.version) > 10:
                state.version = "1"
        else:
            state.version = "1"

        # 提取当前补丁编号和总补丁编号
        patch_match = re.search(r'Subject: \[PATCH.*([0-9]{1,})/([0-9]{1,})\] (.*)', content)
        if patch_match:
            state.current = patch_match.group(1)
            state.total = patch_match.group(2)
            if len(state.current) > 10:
                state.current = ""
            if len(state.total) > 10:
                state.total = ""

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

        # 提取消息 ID
        message_id_match = re.search(r'Message-Id: <(.*)>', content)
        if message_id_match:
            message_id = message_id_match.group(1)
            state.web_url = f"https://lore.kernel.org/all/{message_id}"
            state.archive_url = state.web_url

        # 提取内容
        state.content = content

        if state.verbose >= 2:
            print(f"作者: {state.author} <{state.email}>")
            print(f"日期: {state.date}")
            print(f"主题: {state.subject}")
            print(f"版本: v{state.version}")
            if state.total:
                print(f"补丁: {state.current}/{state.total}")
            print(f"链接: {state.web_url}")

    except Exception as e:
        print(f"解析补丁失败: {e}")
        raise

    return state

def analyze_patch(state: LKMLAgentState) -> LKMLAgentState:
    if state.verbose >= 2:
        print("=== 分析补丁内容 ===\n")

    # 只有 detail 级别才进行详细分析
    if state.level != "detail":
        return state

    try:
        # 分析 cover 文件
        if state.cover_file:
            if state.verbose >= 2:
                print("分析 Cover 文件...")
            with open(state.cover_file, 'r', encoding='utf-8') as file:
                cover_content = file.read()

            model_req = ModelRequest("analysis", cover_content)
            messages = model_req.get_messages()

            model_infer = ModelInference(verbose=state.verbose)
            model_infer.inference(messages)

            state.analysis = model_infer.get_answer()
            if state.verbose >= 2:
                print("Cover 文件分析完成")

        # 分析 cover 和 mailbox
        if state.cover_file and state.mbx_file:
            if state.verbose >= 2:
                print("\n分析 Cover 和 MailBox 文件...")
            with open(state.cover_file, 'r', encoding='utf-8') as file:
                cover_content = file.read()

            with open(state.mbx_file, 'r', encoding='utf-8') as file:
                mbx_content = file.read()

            combined_content = cover_content + "\n" + mbx_content
            model_req.set_request("analysis", combined_content)
            messages = model_req.get_messages()

            model_infer = ModelInference(verbose=state.verbose)
            model_infer.inference(messages)

            if state.verbose >= 2:
                print("Cover 和 MailBox 文件分析完成")

    except Exception as e:
        print(f"分析补丁失败: {e}")

    return state

def generate_summary(state: LKMLAgentState) -> LKMLAgentState:
    if state.verbose >= 2:
        print("=== 生成补丁摘要 ===\n")

    try:
        # 选择要分析的文件内容
        content_to_analyze = ""
        if state.cover_file:
            with open(state.cover_file, 'r', encoding='utf-8') as file:
                content_to_analyze = file.read()
        elif state.mbx_file:
            with open(state.mbx_file, 'r', encoding='utf-8') as file:
                content_to_analyze = file.read()

        if not content_to_analyze:
            raise Exception("没有找到可分析的内容")

        # 生成摘要
        model_req = ModelRequest("summary", content_to_analyze)
        messages = model_req.get_messages()

        model_infer = ModelInference(verbose=state.verbose)
        model_infer.inference(messages)

        state.summary = model_infer.get_answer()
        if state.verbose >= 2:
            print("摘要生成完成")
            print(f"摘要: {state.summary[:100]}...")

    except Exception as e:
        print(f"生成摘要失败: {e}")
        state.summary = "无法生成摘要"

    return state

def output_results(state: LKMLAgentState) -> LKMLAgentState:
    if state.verbose >= 2:
        print("=== 输出结果 ===\n")

    # 打印基本信息
    print("| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |")
    print("|:---:|:----:|:---:|:----:|:---------:|:----:|")

    if not state.total:
        print(f"| {state.date} | {state.author} <{state.email}> | [{state.subject}]({state.web_url}) | {state.summary} | v{state.version} ☐☑✓ | [LORE]({state.archive_url}) |")
    else:
        print(f"| {state.date} | {state.author} <{state.email}> | [{state.subject}]({state.web_url}) | {state.summary} | v{state.version} ☐☑✓ | [{state.date}, LORE v{state.version}, {state.current}/{state.total}]({state.archive_url}) |")

    # 如果是 detail 级别，打印详细分析
    if state.level == "detail" and state.analysis:
        if state.verbose >= 2:
            print("\n=== 详细分析 ===\n")
        if state.verbose >= 3:
            print(state.analysis)

    return state

def build_lkml_agent():
    workflow = StateGraph(LKMLAgentState)

    workflow.add_node("fetch_patch", fetch_patch)
    workflow.add_node("parse_patch", parse_patch)
    workflow.add_node("generate_summary", generate_summary)
    workflow.add_node("analyze_patch", analyze_patch)
    workflow.add_node("output_results", output_results)

    workflow.set_entry_point("fetch_patch")
    workflow.add_edge("fetch_patch", "parse_patch")
    workflow.add_edge("parse_patch", "generate_summary")
    workflow.add_edge("generate_summary", "analyze_patch")
    workflow.add_edge("analyze_patch", "output_results")
    workflow.add_edge("output_results", END)

    return workflow.compile()

def run_lkml_agent(lkml_id: str, level: str = "simple", work_dir: str = None, verbose: int = 0):
    agent = build_lkml_agent()

    initial_state = LKMLAgentState(
        messages=[{"role": "system", "content": "你是一个 LKML 补丁分析智能体，负责下载、解析和分析 Linux 内核邮件列表中的补丁。"}],
        lkml_id=lkml_id,
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
        description="LKML 补丁分析智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python lkml_agent.py --message_id=20250621235745.3994-1-atomlin@atomlin.co --level=simple  # 简要分析
  python lkml_agent.py --message_id=20250621235745.3994-1-atomlin@atomlin.co --level=detail  # 详细分析
"""
    )
    parser.add_argument(
        "--message_id",
        type=str,
        required=True,
        help="指定 LKML 补丁的 message-id"
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
    run_lkml_agent(args.message_id, args.level)
