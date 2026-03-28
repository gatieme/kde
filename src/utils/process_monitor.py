# -*- coding: utf-8 -*-
"""进程监控和进度处理的公共函数"""

import subprocess
import select
import re
from tqdm import tqdm


def monitor_process_with_progress(process, pbar, verbose):
    """监控进程输出并更新进度条
    
    Args:
        process: 子进程对象
        pbar: tqdm 进度条对象
        verbose: 详细级别 (0-3)
    """
    last_progress = 0
    no_output_count = 0
    max_no_output_count = 6
    select_timeout = 5

    while True:
        try:
            readable, _, _ = select.select([process.stdout], [], [], select_timeout)
            if not readable:
                no_output_count += 1
                if verbose >= 2:
                    print(f"警告: {(no_output_count * select_timeout):2d} 秒无输出，检查进程状态。[尝试次数 {no_output_count}/{max_no_output_count}]...")
                if no_output_count >= max_no_output_count:
                    handle_process_timeout(process, verbose)
                    break
                continue

            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                no_output_count += 1
                if verbose >= 2:
                    print(f"警告: {(no_output_count * select_timeout):2d} 秒无输出，检查进程状态。[尝试次数 {no_output_count}/{max_no_output_count}]...")
                if no_output_count >= max_no_output_count:
                    handle_process_timeout(process, verbose)
                    break
                break

            no_output_count = 0
            line = line.strip()

            if "%" in line:
                try:
                    progress = int(re.search(r'(\d+)%', line).group(1))
                    if 0 <= progress <= 100 and progress > last_progress:
                        pbar.update(progress - last_progress)
                        last_progress = progress
                except:
                    pbar.update(0.5)
            elif "Download" in line or "Fetch" in line or "Applying" in line:
                pbar.update(0.5)
        except subprocess.TimeoutExpired:
            handle_process_timeout(process, verbose)
            break
        except Exception as e:
            if process.poll() is not None:
                break
            else:
                if verbose >= 2:
                    print(f"警告: 读取输出时发生错误: {e}")
                break

    pbar.n = 100
    pbar.refresh()


def handle_process_timeout(process, verbose):
    """处理进程超时
    
    Args:
        process: 子进程对象
        verbose: 详细级别 (0-3)
    """
    if process.poll() is not None:
        return
    else:
        print(f"警告: 连续 30 秒无输出，任务即将终止...")
        process.terminate()
        process.wait(timeout=5)
        print(f"警告: 进程已终止，可能已超时")
