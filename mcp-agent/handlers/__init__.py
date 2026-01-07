# -*- coding: utf-8 -*-
"""
Handlers Package
MCP 请求处理函数包

模块说明:
    - stamp.py    : 任务戳管理（generate_stamp, get_stamp_info, ...）
    - task.py     : 任务执行（deploy_and_run, get_task_status, ...）
    - file.py     : 文件操作（list_workspace_files, read_workspace_file）
    - toolbox.py  : 工具库调用（list_tools, run_tool, get_tool_schema）
    - system.py   : 系统命令（execute_internal）

配置文件（config/tools.yaml）中的 handler 路径格式:
    handler: module.function
    
例如:
    handler: stamp.generate_stamp  -> handlers.stamp.handle_generate_stamp
    handler: task.deploy_and_run   -> handlers.task.handle_deploy_and_run
"""

# 导出所有处理函数
from .stamp import *
from .task import *
from .file import *
from .toolbox import *
from .system import *
