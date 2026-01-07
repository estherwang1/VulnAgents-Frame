# -*- coding: utf-8 -*-
"""
Stamp Handler Aliases
任务戳处理函数别名

配置文件中使用 handler: stamp.xxx 格式
路由器会查找 handlers.stamp 模块中的 handle_xxx 函数
"""

from .stamp_handler import (
    handle_generate_stamp,
    handle_get_stamp_info,
    handle_list_stamps,
    handle_associate_task,
    handle_add_finding,
    handle_add_event,
    handle_update_stamp_status,
    handle_archive_stamp,
    handle_get_history,
)

# 导出别名（配合配置文件中的 handler 路径）
generate_stamp = handle_generate_stamp
get_stamp_info = handle_get_stamp_info
list_stamps = handle_list_stamps
associate_task = handle_associate_task
add_finding = handle_add_finding
add_event = handle_add_event
update_stamp_status = handle_update_stamp_status
archive_stamp = handle_archive_stamp
get_history = handle_get_history

__all__ = [
    # 原始函数
    "handle_generate_stamp",
    "handle_get_stamp_info",
    "handle_list_stamps",
    "handle_associate_task",
    "handle_add_finding",
    "handle_add_event",
    "handle_update_stamp_status",
    "handle_archive_stamp",
    "handle_get_history",
    # 别名
    "generate_stamp",
    "get_stamp_info",
    "list_stamps",
    "associate_task",
    "add_finding",
    "add_event",
    "update_stamp_status",
    "archive_stamp",
    "get_history",
]
