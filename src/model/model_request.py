# -*- coding: utf-8 -*-

from openai import OpenAI


model_request_type = ["summary", "analysis", "discussion_summary", "discussion_analysis"]


messages_summary = [
    {
        'role': 'system',
        #'content': '你是一位专业的 Linux 社区邮件列表补丁分析专家，对 Linux 相关技术和补丁机制有深入了解。你的任务是对用户提供的 Linux 社区邮件列表补丁进行全面、细致的分析，涵盖补丁的功能目的、涉及的代码范围、可能产生的影响（包括对系统性能、稳定性、兼容性等方面）、潜在的风险以及是否符合 Linux 社区的开发规范和代码风格等方面。如果补丁存在问题或需要改进的地方，要准确指出并给出合理的建议。',
        'content': '你是一位专业的 Linux 领域内容总结专家，对 Linux 社区相关技术、术语和开发流程有深入了解。你的任务是对用户提供的 Linux 社区邮件进行准确、精炼的总结，突出关键信息，涵盖邮件的核心主题、主要观点、涉及的重要技术点或行动事项等，且总结内容控制在 300 字以内。',
    },
    {
        'role': 'user',
        'content': '''以下是具体的 Linux 社区邮件内容，请按照系统设定的要求，用中文对该邮件进行总结，字数控制在 300 字以内。'''
    }
]


messages_analysis = [
    {
        'role': 'system',
        #'content': '你是一位专业的 Linux 社区邮件列表补丁分析专家，对 Linux 相关技术和补丁机制有深入了解。你的任务是对用户提供的 Linux 社区邮件列表补丁进行全面、细致的分析，涵盖补丁的功能目的、涉及的代码范围、可能产生的影响（包括对系统性能、稳定性、兼容性等方面）、潜在的风险以及是否符合 Linux 社区的开发规范和代码风格等方面。如果补丁存在问题或需要改进的地方，要准确指出并给出合理的建议。',
        'content': '你是一位专业的 Linux 社区邮件列表补丁分析专家，对 Linux 相关技术和补丁机制有深入了解。你的任务是对用户提供的 Linux 社区邮件列表补丁进行全面、细致的分析，涵盖补丁的功能目的、实现思路、涉及的代码范围、可能产生的影响（包括对系统性能、稳定性、兼容性等方面）。如果补丁存在问题或需要改进的地方，要准确指出并给出合理的建议。',
    },
    {
        'role': 'user',
        'content': '''以下是具体的 Linux 社区邮件列表补丁，请按照系统设定的要求，用中文对该补丁进行分析。'''
    }
]


messages_discussion_summary = [
    {
        'role': 'system',
        'content': '你是 Linux 内核社区讨论分析专家。请根据以下 LKML 邮件线程内容，总结讨论的主题、各专家的关键观点、以及最终结论或共识/分歧。要求：1) 明确说明讨论的核心议题 2) 列出主要参与者的立场和关键论据 3) 总结讨论结果（达成共识或仍存分歧）4) 300 字以内',
    },
    {
        'role': 'user',
        'content': '''以下是 LKML 邮件线程的完整内容，请按照系统设定的要求，用中文对该讨论进行总结，字数控制在 300 字以内。'''
    }
]


messages_discussion_analysis = [
    {
        'role': 'system',
        'content': '你是 Linux 内核社区讨论深度分析专家。请根据以下 LKML 那件线程内容，进行全面深入的分析：1) 讨论的核心议题和背景 2) 每个关键参与者的观点、论据和立场 3) 技术层面的争议焦点 4) 讨论中的共识和分歧点 5) 最终走向和建议 6) 对内核开发的影响评估',
    },
    {
        'role': 'user',
        'content': '''以下是 LKML 那件线程的完整内容，请按照系统设定的要求，用中文对该讨论进行全面深入的分析。'''
    }
]


messages_mapping = {
    "summary" : messages_summary,
    "analysis" : messages_analysis,
    "discussion_summary" : messages_discussion_summary,
    "discussion_analysis" : messages_discussion_analysis,
}

class ModelRequest:
    def __init__(self, request = "summary", content = None):
        self.request = None
        self.content = None
        self.messages = []
        if (request != None and content != None):
            self.set_request(request, content)
        else:
            print("Init Error")

    def set_content(self, content):
        if self.request == None:
            return
        #self.request = request
        self.content = content
        self.messages = messages_mapping[self.request].copy()
        self.messages.append({
            'role': 'user',
            'content': self.content
        })
    def set_request(self, request, content):
        if self.request != request:
            self.request = request
            self.messages = messages_mapping[self.request].copy()
        if content != None:
            self.set_content(content)

    def get_messages(self):
        return self.messages

    def show(self):
        print(self.messages)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("请提供一个参数")

    try:
    # 打开文件
        with open('/home/chengjian/Work/GitHub/people/kde/lkml/cover.1745199017.git.yu.c.chen@intel.com/20250421_yu_c_chen_sched_introduce_cache_aware_scheduling.cover', 'r', encoding='utf-8') as file:
            # 读取文件全部内容到字符串
            content = file.read()
            print(content)
    except FileNotFoundError:
        print("文件未找到，请检查文件路径。")
    except Exception as e:
        print(f"发生错误: {e}")

    mr = ModelRequest("summary", content)
    mr.show()
    mr.set_content("Linux list 应该怎么实现?")
    mr.show()
    mr.set_request("analysis", "Linux list 应该怎么实现?")
    mr.show()
