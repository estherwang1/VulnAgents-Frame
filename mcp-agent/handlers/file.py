# -*- coding: utf-8 -*-
"""
File Handler Aliases
文件处理函数别名
"""

from .task_handler import (
    handle_list_workspace_files,
    handle_read_workspace_file,
)

# 别名
list_workspace_files = handle_list_workspace_files
read_workspace_file = handle_read_workspace_file

__all__ = [
    "handle_list_workspace_files",
    "handle_read_workspace_file",
    "list_workspace_files",
    "read_workspace_file",
]
