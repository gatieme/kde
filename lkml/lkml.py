# -*- coding: utf-8 -*-

import os
import re
import datetime
import subprocess
from tqdm import tqdm


class LKML:
    def __init__(self, work_dir = None, lkml_id = None):
        # input
        self.lkml_id = lkml_id

        # work dir
        if work_dir != None:
            self.work_dir = work_dir
        else:
            self.work_dir = os.getcwd()
        self.work_folder = os.path.join(self.work_dir, lkml_id)
        os.makedirs(self.work_folder, exist_ok = True)
        os.chdir(self.work_folder)
        self.cover_file = None
        self.mbx_file = None

        # lkml information
        self.date = None
        self.author = None
        self.email = None
        self.version = None
        self.subject = None

        # lkml url
        self.web_url = None
        self.archive_url = None

        self.current = None
        self.total = None

        self.summary = "TODO"

    def set_summary(self, summary):
        self.summary = summary

    # 通过 LKML message id 使用 b4 将补丁的 cover 和 mailbox 下载到本地
    def b4_am(self):
        try:
            command = ["b4", "am", self.lkml_id]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            for line in process.stdout:
                print(line, end='')

            returncode = process.wait()
            if returncode != 0:
                print(f"命令执行失败，返回码: {returncode}")
        except Exception as e:
            print(f"发生错误: {e}")

    # 获取下载到本地的 cover 和 mailbox 路径
    def cover_mbx(self):
        # 列出当前目录下的文件
        cover_files = [f for f in os.listdir(self.work_folder) if f.endswith('.cover')]
        if cover_files:
            self.cover_file = os.path.join(self.work_folder, cover_files[0])
            print(f"Downloading Cover File: {self.cover_file}")
        else:
            self.cover_file = None

        mbx_files = [f for f in os.listdir(self.work_folder) if f.endswith('.mbx')]
        if mbx_files:
            self.mbx_file = os.path.join(self.work_folder, mbx_files[0])
            print(f"Downloading MailBox File: {self.mbx_file}")
        else:
            self.mbx_file = None

        if self.cover_file != None:
            return self.cover_file
        elif self.mbx_file != None:
            return self.mbx_file
        else:
            return None

    # 根据 cover 获取 LKML 补丁的相关信息
    def get_series(self):
        with open(self.cover_file, 'r') as file:
            content = file.read()

        # 提取主题
        subject_match = re.search(r'Subject: \[PATCH.*\] (.*)', content)
        if subject_match:
            self.subject = subject_match.group(1)
        else:
            subject = ""

        # 提取版本
        version_match = re.search(r'Subject:.*v([0-9]{1,}).*', content)
        if version_match:
            self.version = version_match.group(1)
            if len(self.version) > 10:
                self.version = "1"
        else:
            self.version = "1"

        # 提取当前补丁编号和总补丁编号
        patch_match = re.search(r'Subject: \[PATCH.*([0-9]{1,})/([0-9]{1,})\] (.*)', content)
        if patch_match:
            self.current = patch_match.group(1)
            self.total = patch_match.group(2)
            if len(self.current) > 10:
                self.current = ""
            if len(self.total) > 10:
                self.total = ""
        else:
            self.current = ""
            self.total = ""

        # 提取日期
        date_str_match = re.search(r'Date: (.*) [-|+]([0-9]{1,}).*', content)
        if date_str_match:
            date_str = date_str_match.group(1)
            date_value = int(datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S').timestamp())
            self.date = datetime.datetime.fromtimestamp(date_value).strftime('%Y/%m/%d')
        else:
            self.date = ""

        # 提取作者
        author_match = re.search(r'From: (.*) <(.*)>', content)
        if author_match:
            self.author = author_match.group(1)
        else:
            self.author = ""

        # 提取邮箱
        email_match = re.search(r'From: (.*) <(.*)>', content)
        if email_match:
            self.email = email_match.group(2)
        else:
            self.email = ""

        # 提取消息 ID
        message_id_match = re.search(r'Message-Id: <(.*)>', content)
        if message_id_match:
            self.message_id = message_id_match.group(1)
            self.web_url = self.message_id_to_url(self.message_id)
            self.archive_url = self.web_url
        else:
            self.message_id = ""
            self.web_url = ""
            self.archive_url = ""

    def show(self):
            print("| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |")
            print("|:---:|:----:|:---:|:----:|:---------:|:----:|")
            if not self.total:
                print(f"| {self.date} | {self.author} <{self.email}> | [{self.subject}]({self.web_url}) | {self.summary} | v{self.version} ☐☑✓ | [LORE]({self.archive_url}) |")
            else:
                print(f"| {self.date} | {self.author} <{self.email}> | [{self.subject}]({self.web_url}) | {self.summary} | v{self.version} ☐☑✓ | [{self.date}, LORE v{self.version}, 0/{self.total}]({self.archive_url}) |")

    def write(self):
        self.file = self.message_id + ".md"
        with open(f"{self.file}", 'w') as md_file:
            md_file.write("---\n")
            md_file.write("| 时间 | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |\n")
            md_file.write("|:---:|:----:|:---:|:----:|:---------:|:----:|\n")
            if not self.total:
                md_file.write(f"| {self.date} | {self.author} <{self.email}> | [{self.subject}]({self.web_url}) | {self.summary} | v{self.version} ☐☑✓ | [LORE]({self.archive_url}) |\n")
            else:
                md_file.write(f"| {self.date} | {self.author} <{self.email}> | [{self.subject}]({self.web_url}) | {self.summary} | v{self.version} ☐☑✓ | [{date}, LORE v{self.version}, 0/{self.total}]({self.archive_url}) |\n")

    def cover_series(self):
        if self.cover_mbx() != None:
            print("Already Downloaded LKML (Cover and MailBox) Message")
        else:
            print("Use B4 Downloading LKML (Cover and MailBox) Message")
            self.b4_am()
            self.cover_mbx()
        self.get_series()
        #self.show()

    def get_content(self, file_type = "both"):
        files_to_read = []
        if file_type == "both":
            files_to_read = [self.cover_file, self.mbx_file]
        elif file_type == "cover":
            files_to_read = [self.cover_file]
        elif file_type == "mbx":
            files_to_read = [self.mbx_file]
        else:
            files_to_read = [self.cover_file]

        content = ""
        for file_path in files_to_read:
            try:
                print("Read File ", file_path)
                # 打开文件
                with open(file_path, 'r', encoding='utf-8') as file:
                    # 读取文件全部内容到字符串
                    content += file.read() + "\n"
            except FileNotFoundError:
                print("文件未找到，请检查文件路径。")
            except Exception as e:
                print(f"发生错误: {e}")
        return content

    def message_id_to_url(self, message_id):
        return f"https://lore.kernel.org/all/{self.message_id}"

    def url_to_message_id(self, url):
        return f"https://lore.kernel.org/all/{self.message_id}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("请提供一个参数")

    lkml_1 = LKML(lkml_id = sys.argv[1])
    lkml_1.cover_series()
    print(lkml_1.get_content("cover"))

    lkml_2 = LKML(work_dir = "/home/chengjian/Work/GitHub/people/kde/lkml", lkml_id = sys.argv[1])
    lkml_2.cover_series()
    print(lkml_2.get_content("both"))
