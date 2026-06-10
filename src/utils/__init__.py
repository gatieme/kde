# -*- coding: utf-8 -*-
"""Utility modules for KDE project"""

# Text formatting utilities
from .text_formatter import (
    chinese_to_english_punctuation,
    add_space_after_punctuation,
    replace_newline_with_br,
    clean_email_subject,
    format_text_for_markdown
)

# Process monitoring utilities
from .process_monitor import (
    monitor_process_with_progress,
    handle_process_timeout,
)

# HTTP fetching utilities
from .http_fetcher import (
    fetch_article_with_method,
)

__all__ = [
    # Text formatting
    'chinese_to_english_punctuation',
    'add_space_after_punctuation',
    'replace_newline_with_br',
    'clean_email_subject',
    'format_text_for_markdown',
    # Process monitoring
    'monitor_process_with_progress',
    'handle_process_timeout',
    # HTTP fetching
    'fetch_article_with_method',
]
