# -*- coding: utf-8 -*-
"""
Task Handler Aliases
任务处理函数别名
"""

from .task_handler import (
    handle_deploy_and_run,
    handle_get_task_status,
    handle_get_task_result,
    handle_cancel_task,
    handle_list_workspace_files,
    handle_read_workspace_file,
)

# 别名
deploy_and_run = handle_deploy_and_run
get_task_status = handle_get_task_status
get_task_result = handle_get_task_result
cancel_task = handle_cancel_task

__all__ = [
    "handle_deploy_and_run",
    "handle_get_task_status",
    "handle_get_task_result",
    "handle_cancel_task",
    "handle_list_workspace_files",
    "handle_read_workspace_file",
    "deploy_and_run",
    "get_task_status",
    "get_task_result",
    "cancel_task",
]
