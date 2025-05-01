# -*- coding: utf-8 -*-
import sys
from lkml import LKML
from model import ModelInference, ModelRequest


def chinese_to_english_punctuation(text):
    # 定义中文标点和对应的英文标点
    chinese_punctuation = '，。！？；：“”‘’（）【】《》'
    english_punctuation = ',.!?;:""\'\'()[]<>'
    # 创建转换表
    translation_table = str.maketrans(chinese_punctuation, english_punctuation)
    # 进行替换
    return text.translate(translation_table)


def add_space_after_punctuation(text):
    punctuations = '.,!?;:"\'()[]<>，。！？；：“”‘’（）【】《》'
    result = ""
    for char in text:
        if char in punctuations:
            result += char + " "
        else:
            result += char
    return result

def replace_newline_with_br(text):
    # 替换换行符为 <br>
    return text.replace('\n', '<br>')


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("请提供一个参数")

    # Download LKML Message
    lkml = LKML(work_dir = "/home/chengjian/Work/GitHub/people/kde/lkml", lkml_id = sys.argv[1])
    lkml.cover_series()

    # Model Request
    model_req = ModelRequest("summary", lkml.get_content())
    messages = model_req.get_messages()

    # User Qwen3 Model for Inference
    model_infer = ModelInference()
    model_infer.inference(messages)

    summary = replace_newline_with_br(add_space_after_punctuation(chinese_to_english_punctuation(model_infer.get_answer())))
    #summary = model_infer.get_answer()
    lkml.set_summary(summary)
    lkml.show()
