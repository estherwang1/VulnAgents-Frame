# -*- coding: utf-8 -*-
"""
System Handler
系统命令处理函数
"""

from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.process_runner import run_command
from utils.security import is_command_safe


async def handle_execute_internal(command: str) -> Dict[str, Any]:
    """
    执行系统命令（受白名单限制）
    """
    if not command:
        return {"success": False, "error": "命令不能为空"}
    
    # 安全检查（由路由器配置层已检查，这里再检查一次）
    is_safe, reason = is_command_safe(command)
    if not is_safe:
        return {"success": False, "error": f"安全拦截: {reason}"}
    
    result = await run_command(command)
    return {
        "success": result["success"],
        "output": result["stdout"] or result["stderr"] or "(无输出)",
        "return_code": result["return_code"]
    }


# 别名
execute_internal = handle_execute_internal

__all__ = [
    "handle_execute_internal",
    "execute_internal",
]
