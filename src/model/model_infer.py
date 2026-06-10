# -*- coding: utf-8 -*-

import os
from openai import OpenAI, RateLimitError
from tqdm import tqdm

# 模型 fallback 链：主模型额度耗尽时依次尝试备选模型
FALLBACK_MODELS = [
    'Qwen/Qwen3-235B-A22B',          # 主模型：Qwen3-235B-A22B
    'deepseek-ai/DeepSeek-V4-Pro',   # 第一备选：DeepSeek-V4-Pro
    'deepseek-ai/DeepSeek-V4-Flash', # 第二备选：DeepSeek-V4-Flash
]


class ModelInference:
    def __init__(self, content = None, verbose=0, fallback_models=None):
        self.client = OpenAI(
            base_url = 'https://api-inference.modelscope.cn/v1/',
            api_key = os.getenv("OPENAI_API_KEY"), # ModelScope API KEY
        )

        # set extra_body for thinking control
        self.extra_body = {
            # enable thinking, set to False to disable
            "enable_thinking": False,
            # use thinking_budget to contorl num of tokens used for thinking
            # "thinking_budget": 4096
        }

        self.fallback_models = fallback_models or FALLBACK_MODELS
        self.current_model = self.fallback_models[0]  # 当前实际使用的模型
        self.response = None
        self.answer = None
        self.verbose = verbose

    def inference(self, messages):
        """推理请求，支持 429 额度耗尽时自动 fallback 到备选模型"""
        for i, model in enumerate(self.fallback_models):
            try:
                self.current_model = model
                return self._try_inference(model, messages)
            except RateLimitError as e:
                # 429 额度耗尽，尝试 fallback
                if i < len(self.fallback_models) - 1:
                    next_model = self.fallback_models[i + 1]
                    print(f"模型 {model} 额度耗尽(429)，切换到 {next_model}")
                else:
                    # 所有模型都额度耗尽
                    print(f"所有模型额度耗尽，无法继续推理")
                    raise

    def _try_inference(self, model, messages):
        """尝试使用指定模型进行推理"""
        if self.verbose >= 1:
            print(f"使用模型: {model}")

        self.response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0,
            top_p=1,
            presence_penalty=0,
            frequency_penalty=0,
            extra_body=self.extra_body
        )
        
        answer = ""
        done_thinking = False
        
        if self.verbose >= 1 and self.verbose < 2:
            with tqdm(total=100, desc="模型推理进度", unit="%") as pbar:
                answer, done_thinking = self._process_stream(self.response, answer, done_thinking, pbar)
        else:
            answer, done_thinking = self._process_stream(self.response, answer, done_thinking, None)
        
        if self.verbose >= 2:
            print("\n")
        self.answer = answer
        return self.answer

    def _process_stream(self, response, answer, done_thinking, pbar):
        """处理流式响应，兼容不同模型的 delta 字段差异"""
        for chunk in response:
            delta = chunk.choices[0].delta
            # 不同模型的 reasoning_content 可能为 None 或不存在
            thinking_chunk = getattr(delta, 'reasoning_content', None) or ''
            answer_chunk = getattr(delta, 'content', None) or ''
            
            if thinking_chunk:
                if self.verbose >= 2:
                    print(thinking_chunk, end='', flush=True)
                answer += thinking_chunk
                if pbar and pbar.n < pbar.total:
                    pbar.update(1)
            elif answer_chunk:
                if not done_thinking:
                    done_thinking = True
                if self.verbose >= 2:
                    print(answer_chunk, end='', flush=True)
                answer += answer_chunk
                if pbar and pbar.n < pbar.total:
                    pbar.update(1)
        
        if pbar:
            pbar.n = 100
            pbar.refresh()
        
        return answer, done_thinking

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
