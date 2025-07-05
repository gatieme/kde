# -*- coding: utf-8 -*-

from openai import OpenAI


class ModelInference:
    def __init__(self, content = None):
        self.client = OpenAI(
            base_url='https://api-inference.modelscope.cn/v1/',
            api_key='a51566bb-dfc8-472b-b643-f8dc265992a7', # ModelScope Token
        )

        # set extra_body for thinking control
        self.extra_body = {
            # enable thinking, set to False to disable
            "enable_thinking": False,
            # use thinking_budget to contorl num of tokens used for thinking
            # "thinking_budget": 4096
        }

        self.model = 'Qwen/Qwen3-235B-A22B',  # ModelScope Model-Id
        self.response = None
        self.answer = None

    def inference(self, messages):
        self.response = self.client.chat.completions.create(
            #model = 'Qwen/Qwen3-32B',  # ModelScope Model-Id
            model = 'Qwen/Qwen3-235B-A22B',  # ModelScope Model-Id
            messages = messages,
            stream = True,
            temperature = 0,    # 设置 temperature 为 0 以实现贪心解码
            top_p = 1,          # 可设置为 1，通常结合 temperature=0 可不特别关注
            #top_k = 1,          # 设置 top_k 为 1，只选择概率最高的词
            presence_penalty = 0,
            frequency_penalty = 0,
            extra_body = self.extra_body
        )
        answer = ""
        done_thinking = False
        for chunk in self.response:
            thinking_chunk = chunk.choices[0].delta.reasoning_content
            answer_chunk = chunk.choices[0].delta.content
            if thinking_chunk != '':
                print(thinking_chunk, end='', flush=True)
                answer += thinking_chunk
            elif answer_chunk != '':
                if not done_thinking:
                    #print('\n\n === Final Answer ===\n')
                    done_thinking = True
                print(answer_chunk, end='', flush=True)
                answer += answer_chunk
        print("\n")
        self.answer = answer
        return self.answer

    def show(self):
        print(self.answer)

    def get_answer(self):
        return self.answer

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

    mi = ModelInference()

    from model_request import ModelRequest

    mr = ModelRequest("summary", content)
    mr.show()
    res = mi.inference(mr.get_messages())
    mi.show()

    mr.set_request("analysis", content)
    mr.show()
    res = mi.inference(mr.get_messages())
    mi.show()
