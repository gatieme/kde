# -*- coding: utf-8 -*-
"""Text formatting utilities for markdown table display"""


def chinese_to_english_punctuation(text):
    """Convert Chinese punctuation to English punctuation"""
    chinese_punctuation = "，。！？；：''（）【】《》"
    english_punctuation = ",.!?;:\"\'()[]<>"
    translation_table = str.maketrans(chinese_punctuation, english_punctuation)
    return text.translate(translation_table)


def add_space_after_punctuation(text):
    """Add space after punctuation marks"""
    punctuations = '.,!?;:"\'()[]<>，。！？；："''（）【】《》'
    result = ""
    for char in text:
        if char in punctuations:
            result += char + " "
        else:
            result += char
    return result


def replace_newline_with_br(text):
    """Replace newline characters with <br> tag, collapse consecutive newlines into one"""
    import re
    return re.sub(r'\n+', '<br>', text)


def format_text_for_markdown(text):
    """Format text for markdown table display

    Apply all formatting functions in order:
    1. Convert Chinese punctuation to English
    2. Add space after punctuation
    3. Replace newlines with <br> (after spacing, so <br> tags won't get spaces injected)
    """
    text = chinese_to_english_punctuation(text)
    text = add_space_after_punctuation(text)
    text = replace_newline_with_br(text)
    return text
