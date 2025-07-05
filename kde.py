# -*- coding: utf-8 -*-
import sys
import argparse

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


def lkml_run(lkml_message_id, level):
    # Download LKML Message
    print("=====================")
    print("#Step 1: Download LKML Mesage")
    print("=====================")
    lkml = LKML(work_dir = "/home/chengjian/Work/GitHub/people/kde/lkml", lkml_id = lkml_message_id)
    lkml.cover_series()
    lkml.show()

    print("=====================")
    print("#Step 2: Summary LKML (Cover) Message")
    print("=====================")
    # Model Request
    model_req = ModelRequest("summary", lkml.get_content(file_type = "cover"))
    messages = model_req.get_messages()

    # User Qwen3 Model for Inference
    model_infer = ModelInference()
    model_infer.inference(messages)
    #model_infer.show()

    summary = replace_newline_with_br(add_space_after_punctuation(chinese_to_english_punctuation(model_infer.get_answer())))
    #summary = model_infer.get_answer()
    lkml.set_summary(summary)
    lkml.show()

    if level == 'simple':
        return

    print("=====================")
    print("#Step 3: Analysis LKML (Cover) Message")
    print("=====================")
    model_req.set_request("analysis", lkml.get_content(file_type = "cover"))
    messages = model_req.get_messages()
    model_infer.inference(messages)
    #model_infer.show()

    print("=====================")
    print("#Step 4: Analysis LKML (Cover and MailBox) Message")
    print("=====================")
    model_req.set_request("analysis", lkml.get_content(file_type = "both"))
    messages = model_req.get_messages()
    model_infer.inference(messages)
    #model_infer.show()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='执行不同级别的操作')
    group = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument('--lkml', type=str, help='设置URL参数')
    group.add_argument('--simple', action='store_const', dest='level', const='simple', help='简化分析补丁, 只执行 SUMMARY')
    group.add_argument('--detail', action='store_const', dest='level', const='detail', help='详细分析补丁, 将先执行 SUMMARY, 然后对邮件 COVER 和 LETTER 分别进行总结')
    args = parser.parse_args()

    print(args.level)
    lkml_run(lkml_message_id = args.lkml, level = args.level)
