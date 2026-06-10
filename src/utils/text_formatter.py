# -*- coding: utf-8 -*-
"""Text formatting utilities for markdown table display"""


def chinese_to_english_punctuation(text):
    """Convert Chinese punctuation to English punctuation"""
    chinese_punctuation = "，。！？；：''（）【】《》"
    english_punctuation = ",.!?;:\"\'()[]<>"
    translation_table = str.maketrans(chinese_punctuation, english_punctuation)
    return text.translate(translation_table)


def clean_bracket_spaces(text):
    """Remove stray spaces inside paired brackets.

    AI models sometimes output 'func( )' or 'name( ) ' with spaces inside
    or trailing brackets. Clean these to 'func()' and 'func() '.
    """
    import re
    # 清除括号内部的空白：( ) → (), [ ] → [], < > → <>
    text = re.sub(r'\(\s+\)', '()', text)
    text = re.sub(r'\[\s+\]', '[]', text)
    # 尖括号仅当内部全是空白时才清理（避免破坏 HTML 标签 <br> 等）
    text = re.sub(r'<\s+>', '<>', text)
    return text


def add_space_after_punctuation(text):
    """Add space after punctuation marks that need trailing spacing.

    Context-aware logic:
    - Bracket punctuation (()[]<>): no internal/trailing spaces
    - Period inside identifiers (email, domain, version): no space
    - Terminal punctuation (comma, period at sentence end, etc.): add space
    """
    # 保护标识符内部的点：邮箱 (user@host.dom)、版本号 (v1.2.3) 等
    # 规则：点的前后都是字母/数字/@时，视为标识符内部，不加空格

    result = ""
    i = 0
    while i < len(text):
        char = text[i]
        if char == '.' and i > 0 and i + 1 < len(text):
            prev_is_alnum = text[i - 1].isalnum() or text[i - 1] == '@'
            next_is_alnum = text[i + 1].isalnum()
            if prev_is_alnum and next_is_alnum:
                result += char
                i += 1
                continue
        # 通用标点后置空格逻辑（排除括号）
        spaced_punctuation = ',.!?:;"\''
        bracket_punctuation = '()[]<>'
        if char in bracket_punctuation:
            result += char
        elif char in spaced_punctuation:
            if i + 1 < len(text) and text[i + 1] not in (' ', '\n', '\t'):
                result += char + " "
            else:
                result += char
        else:
            result += char
        i += 1
    return result


def replace_newline_with_br(text):
    """Replace newline characters with <br> tag, collapse consecutive newlines into one"""
    import re
    return re.sub(r'\n+', '<br>', text)


def clean_email_subject(subject):
    """统一清理邮件标题前缀（Re:/Fwd: 等），保留 [PATCH...] 等实质内容。

    各 agent 的标题提取逻辑应统一使用此函数，确保不同模式下表现一致。
    [PATCH...] 前缀是补丁标题的实质内容，不应剥离；
    Re:/Fwd: 只是回复标记，应去除。

    Examples:
        "Re: [PATCH 1/6] sched/proxy: Remove..." -> "[PATCH 1/6] sched/proxy: Remove..."
        "Re: Re: [PATCH v2] mm: fix" -> "[PATCH v2] mm: fix"
        "[PATCH 0/6] sched/proxy: doodles" -> "[PATCH 0/6] sched/proxy: doodles"
        "Fwd: some discussion topic" -> "some discussion topic"
    """
    import re
    # 剥离所有 Re:/Fwd: 前缀（可能有多个叠加），保留其他内容
    cleaned = re.sub(r'^(\s*(Re|Fwd|回复|转发)\s*:\s*)+', '', subject)
    return cleaned.strip()


def format_text_for_markdown(text):
    """Format text for markdown table display

    Apply all formatting functions in order:
    1. Convert Chinese punctuation to English
    2. Clean stray spaces inside paired brackets (AI output artifact)
    3. Add space after punctuation (context-aware, brackets excluded)
    4. Replace newlines with <br> (after spacing, so <br> tags won't get spaces injected)
    """
    text = chinese_to_english_punctuation(text)
    text = clean_bracket_spaces(text)
    text = add_space_after_punctuation(text)
    text = replace_newline_with_br(text)
    return text
