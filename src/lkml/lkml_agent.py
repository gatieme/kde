# -*- coding: utf-8 -*-

import os
import sys
import re
import datetime
import subprocess
import time
import select
import mailbox
import html as html_module
import gzip
import shutil
import urllib.request
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import Annotated, List, Dict, Any, Optional
from dataclasses import dataclass, field
from tqdm import tqdm

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import format_text_for_markdown, monitor_process_with_progress, handle_process_timeout
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


@dataclass
class DiscussionAgentState:
    """Discussion workflow state for analyzing non-patch email threads"""
    messages: Annotated[List[Dict[str, Any]], add_messages]
    lkml_id: str = ""              # Original message-id
    level: str = "simple"          # simple / detail
    work_dir: str = ""             # Cache working directory output/lkml/<id>/
    mbx_file: str = ""             # b4 mbox downloaded .mbx file path
    thread_emails: List[Dict] = field(default_factory=list)  # All parsed emails
    subject: str = ""              # Discussion subject
    author: str = ""               # Original email author
    email: str = ""                # Original author email
    date: str = ""                 # Original email date
    web_url: str = ""              # lore.kernel.org link
    archive_url: str = ""          # Archive link
    reply_count: int = 0           # Number of replies
    summary: str = "TODO"          # AI-generated discussion summary
    analysis: str = ""             # AI detailed analysis (only detail level)
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

        if state.verbose >= 3:
            for line in process.stdout:
                print(line, end='')
        elif state.verbose >= 1:
            with tqdm(total=100, desc="LKML 补丁下载进度", unit="%") as pbar:
                monitor_process_with_progress(process, pbar, state.verbose)
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

        # 提取主题：优先提取 PATCHSET 标题，回退从所有 Subject 行中找原始标题（不含 Re:/Fwd:）
        subject_match = re.search(r'Subject: \[PATCH.*\] (.*)', content)
        if subject_match:
            state.subject = subject_match.group(1)
        else:
            # 从所有 Subject 行中优先选择不含回复前缀的原始标题
            all_subjects = re.findall(r'Subject: (.*)', content)
            for subj in all_subjects:
                subj_stripped = subj.strip()
                if not re.match(r'^(\s*(Re|Fwd|回复|转发)\s*:\s*)+', subj_stripped):
                    state.subject = subj_stripped
                    break
            # 若全部都是回复帖，取第一个并剥离前缀
            if not state.subject and all_subjects:
                state.subject = re.sub(r'^(\s*(Re|Fwd|回复|转发)\s*:\s*)+', '', all_subjects[0]).strip()

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

        # 链接始终使用用户指定的 lkml_id（权威来源），而非从下载内容提取的 Message-Id
        # 因为 cover letter 的 Message-Id 与用户指定的 patch Message-Id 不同
        state.web_url = f"https://lore.kernel.org/all/{state.lkml_id}"
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
    print()
    print("| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |")
    print("|:---:|:----:|:---:|:----:|:---------:|:----:|")

    # Format summary for markdown table display
    formatted_summary = format_text_for_markdown(state.summary)

    if not state.total:
        print(f"| {state.date} | {state.author} <{state.email}> | [{state.subject}]({state.web_url}) | {formatted_summary} | v{state.version} ☐☑✓ | [{state.date}, LORE]({state.archive_url}) |")
    else:
        print(f"| {state.date} | {state.author} <{state.email}> | [{state.subject}]({state.web_url}) | {formatted_summary} | v{state.version} ☐☑✓ | [{state.date}, LORE v{state.version}, {state.current}/{state.total}]({state.archive_url}) |")

    # 如果是 detail 级别，打印详细分析
    # detail 模式下始终输出详细分析内容，verbose 只控制标题显示
    if state.level == "detail" and state.analysis:
        if state.verbose >= 1:
            print("\n=== 详细分析 ===\n")
        print(state.analysis)

    return state

# ============================================================================
# Discussion Workflow Functions
# ============================================================================

def fetch_thread(state: DiscussionAgentState) -> DiscussionAgentState:
    """Download thread mbox file using b4 mbox"""
    if state.verbose >= 2:
        print("=== 下载 LKML 讨论线程 ===\n")

    if not state.work_dir:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_root = os.path.join(repo_root, "output", "lkml")
        state.work_dir = os.path.join(cache_root, state.lkml_id)
    os.makedirs(state.work_dir, exist_ok=True)

    original_dir = os.getcwd()
    os.chdir(state.work_dir)

    try:
        command = ["b4", "mbox", state.lkml_id]

        if state.verbose >= 2:
            print(f"执行命令: {' '.join(command)}")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        if state.verbose >= 3:
            for line in process.stdout:
                print(line, end='')
        elif state.verbose >= 1:
            with tqdm(total=100, desc="LKML 线程下载进度", unit="%") as pbar:
                monitor_process_with_progress(process, pbar, state.verbose)
        else:
            try:
                output = process.communicate(timeout=300)[0]
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
                raise Exception("下载讨论线程超时（300秒），进程已终止")

        returncode = process.wait()
        if returncode != 0:
            # b4 mbox failed, try curl fallback
            if state.verbose >= 1:
                print(f"b4 mbox 失败（返回码: {returncode}），尝试 curl fallback...")
            mbox_url = f"https://lore.kernel.org/all/{state.lkml_id}/t.mbox.gz"
            gz_path = os.path.join(state.work_dir, "thread.mbox.gz")
            try:
                urllib.request.urlretrieve(mbox_url, gz_path)
                with gzip.open(gz_path, 'rb') as f_in:
                    mbx_path = os.path.join(state.work_dir, "thread.mbx")
                    with open(mbx_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                if state.verbose >= 1:
                    print("curl fallback 成功")
            except Exception as e:
                raise Exception(f"下载讨论线程失败: b4 mbox 返回 {returncode}, curl fallback 也失败: {e}")

        # Find downloaded .mbx file
        files = os.listdir(state.work_dir)
        mbx_files = [f for f in files if f.endswith('.mbx')]

        if mbx_files:
            state.mbx_file = os.path.join(state.work_dir, mbx_files[0])
            if state.verbose >= 2:
                print(f"找到 MailBox 文件: {state.mbx_file}")
        else:
            raise Exception("下载讨论线程失败：没有找到 .mbx 文件")

    finally:
        os.chdir(original_dir)

    return state


def _extract_email_body(msg) -> str:
    """Extract email body, removing quotes and signatures"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                charset = part.get_content_charset() or 'utf-8'
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode(charset, errors='replace')
                    break
            elif content_type == 'text/html' and not body:
                charset = part.get_content_charset() or 'utf-8'
                payload = part.get_payload(decode=True)
                if payload:
                    html_content = payload.decode(charset, errors='replace')
                    body = html_module.unescape(re.sub(r'<[^>]+>', '', html_content))
    else:
        content_type = msg.get_content_type()
        charset = msg.get_content_charset() or 'utf-8'
        payload = msg.get_payload(decode=True)
        if payload:
            decoded = payload.decode(charset, errors='replace')
            if content_type == 'text/html':
                body = html_module.unescape(re.sub(r'<[^>]+>', '', decoded))
            else:
                body = decoded

    # Remove quoted sections (lines starting with >)
    lines = body.split('\n')
    filtered = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('>'):
            continue
        filtered.append(line)
    body = '\n'.join(filtered)

    # Remove signature (content after -- separator)
    sig_idx = body.find('\n-- \n')
    if sig_idx >= 0:
        body = body[:sig_idx]

    return body.strip()


def parse_thread(state: DiscussionAgentState) -> DiscussionAgentState:
    """Parse mbox file using Python mailbox module, extract email list"""
    if state.verbose >= 2:
        print("=== 解析讨论线程 ===\n")

    if not state.mbx_file:
        raise Exception("没有找到可解析的 mbox 文件")

    mbox = mailbox.mbox(state.mbx_file)
    emails = []
    original_email = None

    for msg in mbox:
        subject = msg["Subject"] or ""
        # Remove Re: prefix to get clean subject
        clean_subject = re.sub(r'^Re:\s*', '', subject).strip()

        from_str = msg["From"] or ""
        # Extract author name and email
        from_match = re.match(r'(.*?)\s*<(.*)>', from_str)
        if from_match:
            author_name = from_match.group(1).strip()
            author_email = from_match.group(2).strip()
        else:
            author_name = from_str
            author_email = from_str

        date_str = msg["Date"] or ""
        message_id = msg["Message-Id"] or ""
        # Message-Id is usually wrapped in <>, remove them
        if message_id.startswith('<') and message_id.endswith('>'):
            message_id = message_id[1:-1]

        in_reply_to = msg.get("In-Reply-To", "") or ""
        if in_reply_to.startswith('<') and in_reply_to.endswith('>'):
            in_reply_to = in_reply_to[1:-1]

        references = msg.get("References", "") or ""

        body = _extract_email_body(msg)

        email_data = {
            "subject": clean_subject,
            "from_name": author_name,
            "from_email": author_email,
            "date": date_str,
            "message_id": message_id,
            "in_reply_to": in_reply_to,
            "references": references,
            "body": body,
        }
        emails.append(email_data)

        # 仅收集邮件数据，线程根邮件将在收集完毕后通过引用关系图确定

    if not emails:
        raise Exception("mbox 文件中没有找到任何邮件")

    state.thread_emails = emails

    # ===== 通过引用关系图识别线程根邮件 =====
    # 策略:
    # 1. 统计每个邮件被其他邮件引用的次数，被引用最多的即为线程根
    # 2. 若无明确引用关系，优先选择 cover letter ([PATCH 0/N] 模式)
    # 3. 若仍无明确候选，选择日期最早的邮件

    # 收集线程内所有 message-id
    all_msg_ids = set()
    for e in emails:
        if e["message_id"]:
            all_msg_ids.add(e["message_id"])

    # 统计引用计数：每个邮件被其他邮件的 In-Reply-To / References 引用的次数
    ref_counts = {}
    for e in emails:
        irt = e["in_reply_to"]
        if irt and irt in all_msg_ids:
            ref_counts[irt] = ref_counts.get(irt, 0) + 1
        refs_str = e.get("references", "")
        for ref_id in re.findall(r'<([^>]+)>', refs_str):
            if ref_id in all_msg_ids:
                ref_counts[ref_id] = ref_counts.get(ref_id, 0) + 1

    # 候选根邮件：In-Reply-To 为空 或指向线程外的邮件
    root_candidates = []
    for e in emails:
        irt = e["in_reply_to"]
        if not irt or irt not in all_msg_ids:
            root_candidates.append(e)

    # 优先级1：被其他邮件引用最多的候选（真正的线程根）
    original_email = None
    for candidate in root_candidates:
        mid = candidate["message_id"]
        if mid in ref_counts:
            if original_email is None or ref_counts[mid] > ref_counts.get(original_email["message_id"], 0):
                original_email = candidate

    # 优先级2：cover letter ([PATCH 0/N] 模式)
    if original_email is None:
        for candidate in root_candidates:
            if re.search(r'\[PATCH\s+0/\d+\]', candidate["subject"]):
                original_email = candidate
                break

    # 优先级3：最早的候选邮件
    if original_email is None and root_candidates:
        original_email = root_candidates[0]

    # 兜底：使用第一封邮件
    if original_email is None:
        original_email = emails[0]

    # Set original email metadata
    state.subject = original_email["subject"]
    state.author = original_email["from_name"]
    state.email = original_email["from_email"]
    state.date = original_email["date"]

    # Format date
    try:
        date_value = int(datetime.datetime.strptime(
            original_email["date"], '%a, %d %b %Y %H:%M:%S %z'
        ).timestamp())
        state.date = datetime.datetime.fromtimestamp(date_value).strftime('%Y/%m/%d')
    except (ValueError, OSError):
        # Date parsing failed, keep original string
        pass

    # 链接始终使用用户指定的 lkml_id（权威来源），而非从邮件内容提取的 message_id
    # 因为线程的原始邮件可能与用户指定的起始邮件不同
    state.web_url = f"https://lore.kernel.org/all/{state.lkml_id}"
    state.archive_url = state.web_url

    state.reply_count = len(emails) - 1  # Original email is not a reply

    if state.verbose >= 2:
        print(f"讨论主题: {state.subject}")
        print(f"原始作者: {state.author} <{state.email}>")
        print(f"日期: {state.date}")
        print(f"邮件总数: {len(emails)}")
        print(f"回复数: {state.reply_count}")
        print(f"链接: {state.web_url}")

    return state


def _format_thread_emails(thread_emails: List[Dict]) -> str:
    """Format email list into structured text for AI analysis"""
    parts = []
    for i, email_data in enumerate(thread_emails):
        if i == 0 and not email_data.get("in_reply_to"):
            # Original email
            parts.append(f"[原始邮件]")
            parts.append(f"作者: {email_data['from_name']} <{email_data['from_email']}>")
            parts.append(f"日期: {email_data['date']}")
            parts.append(f"主题: {email_data['subject']}")
            parts.append(f"内容: {email_data['body']}")
        else:
            # Reply email
            parts.append(f"\n[回复 {i}] by {email_data['from_name']} <{email_data['from_email']}> on {email_data['date']}")
            parts.append(f"内容: {email_data['body']}")
        parts.append("")  # Empty line separator

    return '\n'.join(parts)


def generate_discussion_summary(state: DiscussionAgentState) -> DiscussionAgentState:
    """AI generates discussion summary"""
    if state.verbose >= 2:
        print("=== 生成讨论摘要 ===\n")

    try:
        # Format thread emails into structured text
        formatted_thread = _format_thread_emails(state.thread_emails)

        if not formatted_thread:
            raise Exception("没有找到可分析的讨论内容")

        # Truncate long threads (only first 20 + last 3 conclusive replies)
        if len(state.thread_emails) > 23:
            truncated_emails = state.thread_emails[:20] + state.thread_emails[-3:]
            formatted_thread = _format_thread_emails(truncated_emails)

        model_req = ModelRequest("discussion_summary", formatted_thread)
        messages = model_req.get_messages()

        model_infer = ModelInference(verbose=state.verbose)
        model_infer.inference(messages)

        state.summary = model_infer.get_answer()
        if state.verbose >= 2:
            print("讨论摘要生成完成")
            print(f"摘要: {state.summary[:100]}...")

    except Exception as e:
        print(f"生成讨论摘要失败: {e}")
        state.summary = "无法生成讨论摘要"

    return state


def analyze_discussion(state: DiscussionAgentState) -> DiscussionAgentState:
    """AI detailed analysis of discussion content (only detail level)"""
    if state.verbose >= 2:
        print("=== 分析讨论内容 ===\n")

    # Only detail level performs detailed analysis
    if state.level != "detail":
        return state

    try:
        formatted_thread = _format_thread_emails(state.thread_emails)

        if len(state.thread_emails) > 23:
            truncated_emails = state.thread_emails[:20] + state.thread_emails[-3:]
            formatted_thread = _format_thread_emails(truncated_emails)

        model_req = ModelRequest("discussion_analysis", formatted_thread)
        messages = model_req.get_messages()

        model_infer = ModelInference(verbose=state.verbose)
        model_infer.inference(messages)

        state.analysis = model_infer.get_answer()
        if state.verbose >= 2:
            print("讨论分析完成")

    except Exception as e:
        print(f"分析讨论内容失败: {e}")

    return state


def output_discussion(state: DiscussionAgentState) -> DiscussionAgentState:
    """Format and output discussion results to terminal"""
    if state.verbose >= 2:
        print("=== 输出讨论结果 ===\n")

    print()
    print("| 时间 | 作者 | 主题 | 讨论摘要 | 回复数 | 链接 |")
    print("|:---:|:----:|:---:|:----:|:-----:|:----:|")

    formatted_summary = format_text_for_markdown(state.summary)

    print(f"| {state.date} | {state.author} <{state.email}> | [{state.subject}]({state.web_url}) | {formatted_summary} | {state.reply_count} | [{state.date}, LORE]({state.archive_url}) |")

    # detail level: print detailed analysis
    # detail 模式下始终输出详细分析内容，verbose 只控制标题显示
    if state.level == "detail" and state.analysis:
        if state.verbose >= 1:
            print("\n=== 详细讨论分析 ===\n")
        print(state.analysis)

    return state


def build_discussion_agent():
    """Build discussion workflow"""
    workflow = StateGraph(DiscussionAgentState)

    workflow.add_node("fetch_thread", fetch_thread)
    workflow.add_node("parse_thread", parse_thread)
    workflow.add_node("generate_discussion_summary", generate_discussion_summary)
    workflow.add_node("analyze_discussion", analyze_discussion)
    workflow.add_node("output_discussion", output_discussion)

    workflow.set_entry_point("fetch_thread")
    workflow.add_edge("fetch_thread", "parse_thread")
    workflow.add_edge("parse_thread", "generate_discussion_summary")
    workflow.add_edge("generate_discussion_summary", "analyze_discussion")
    workflow.add_edge("analyze_discussion", "output_discussion")
    workflow.add_edge("output_discussion", END)

    return workflow.compile()


def run_discussion_agent(lkml_id: str, level: str = "simple", work_dir: str = None, verbose: int = 0):
    """Run discussion agent to analyze non-patch email threads"""
    if verbose >= 1:
        print()
        print("---------------------")
        print("运行 LKML Discussion agent (级别: " + level + ")")
        print("分析 message-id: " + lkml_id)
        print("---------------------")
        print()

    agent = build_discussion_agent()

    initial_state = DiscussionAgentState(
        messages=[{"role": "system", "content": "你是一个 LKML 讨论分析智能体，负责下载、解析和分析 Linux 内核邮件列表中的讨论线程。"}],
        lkml_id=lkml_id,
        level=level,
        work_dir=work_dir,
        verbose=verbose
    )

    result = agent.invoke(initial_state)
    return result

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
    # Print initial log messages
    if verbose >= 1:
        print()
        print("---------------------")
        print("运行 LKML agent (级别: " + level + ")")
        print("分析 message-id: " + lkml_id)
        print("---------------------")
        print()

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
        description="LKML 补丁/讨论分析智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python lkml_agent.py --message_id=20250621235745.3994-1-atomlin@atomlin.co --level=simple              # 补丁简要分析
  python lkml_agent.py --message_id=20250621235745.3994-1-atomlin@atomlin.co --level=detail              # 补丁详细分析
  python lkml_agent.py --message_id=20260415000910.2h5misvwc45bdumu@airbuntu --mode=discussion --level=simple  # 讨论简要分析
  python lkml_agent.py --message_id=20260415000910.2h5misvwc45bdumu@airbuntu --mode=discussion --level=detail # 讨论详细分析
"""
    )
    parser.add_argument(
        "--message_id",
        type=str,
        required=True,
        help="指定 LKML 那件的 message-id"
    )
    parser.add_argument(
        "--level",
        type=str,
        choices=["simple", "detail"],
        default="simple",
        help="分析级别: simple (简要分析) 或 detail (详细分析)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["patch", "discussion"],
        default="patch",
        help="分析模式: patch (补丁分析) 或 discussion (讨论分析)"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.mode == "discussion":
        run_discussion_agent(args.message_id, args.level)
    else:
        run_lkml_agent(args.message_id, args.level)
