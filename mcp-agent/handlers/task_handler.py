# -*- coding: utf-8 -*-
"""
Task Handler
处理任务相关的 MCP 请求
"""

from typing import Dict, Any, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.task_manager import task_manager
from services.workspace_manager import workspace_manager
from utils.security import sanitize_stamp, sanitize_script_name


async def handle_deploy_and_run(
    stamp: str,
    script_name: str,
    script_content: str
) -> Dict[str, Any]:
    """
    处理部署并运行任务请求
    
    Args:
        stamp: 任务戳 ID
        script_name: 脚本文件名
        script_content: 脚本内容（新增！关键改动）
    """
    # 1. 验证参数
    is_valid, reason = sanitize_stamp(stamp)
    if not is_valid:
        return {"success": False, "error": reason}
    
    is_valid, reason = sanitize_script_name(script_name)
    if not is_valid:
        return {"success": False, "error": reason}
    
    if not script_content or len(script_content.strip()) == 0:
        return {"success": False, "error": "脚本内容不能为空"}
    
    # 2. 调用任务管理器
    result = await task_manager.deploy_and_run(
        stamp=stamp,
        script_name=script_name,
        script_content=script_content
    )
    
    return result


async def handle_get_task_status(
    stamp: Optional[str] = None,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    处理获取任务状态请求
    """
    if stamp:
        is_valid, reason = sanitize_stamp(stamp)
        if not is_valid:
            return {"success": False, "error": reason}
    
    result = await task_manager.get_task_status(stamp=stamp, task_id=task_id)
    return result


async def handle_get_task_result(
    stamp: str,
    task_id: str,
    tail_lines: int = 50
) -> Dict[str, Any]:
    """
    处理获取任务结果请求
    """
    is_valid, reason = sanitize_stamp(stamp)
    if not is_valid:
        return {"success": False, "error": reason}
    
    result = await task_manager.get_task_result(
        stamp=stamp,
        task_id=task_id,
        tail_lines=tail_lines
    )
    return result


async def handle_cancel_task(stamp: str, task_id: str) -> Dict[str, Any]:
    """
    处理取消任务请求
    """
    is_valid, reason = sanitize_stamp(stamp)
    if not is_valid:
        return {"success": False, "error": reason}
    
    result = await task_manager.cancel_task(stamp=stamp, task_id=task_id)
    return result


async def handle_list_workspace_files(stamp: str) -> Dict[str, Any]:
    """
    处理列出工作空间文件请求
    """
    is_valid, reason = sanitize_stamp(stamp)
    if not is_valid:
        return {"success": False, "error": reason}
    
    files = workspace_manager.list_files(stamp)
    return {
        "success": True,
        "stamp": stamp,
        "files": files
    }


async def handle_read_workspace_file(
    stamp: str,
    filename: str,
    max_lines: int = 100
) -> Dict[str, Any]:
    """
    处理读取工作空间文件请求
    """
    is_valid, reason = sanitize_stamp(stamp)
    if not is_valid:
        return {"success": False, "error": reason}
    
    content = workspace_manager.read_file(stamp, filename, max_lines)
    if content is None:
        return {
            "success": False,
            "error": f"文件 {filename} 不存在或无法读取"
        }
    
    return {
        "success": True,
        "stamp": stamp,
        "filename": filename,
        "content": content
    }
