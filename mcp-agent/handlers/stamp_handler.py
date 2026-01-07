# -*- coding: utf-8 -*-
"""
Stamp Handler
处理任务戳相关的 MCP 请求
"""

from typing import Dict, Any, Optional, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.stamp_manager import stamp_manager
from utils.security import sanitize_stamp


async def handle_generate_stamp(
    mission_name: str,
    target: str,
    operator: str = "shadow_commander",
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    处理生成任务戳请求
    """
    if not mission_name:
        return {"success": False, "error": "任务名称不能为空"}
    if not target:
        return {"success": False, "error": "目标不能为空"}
    
    result = stamp_manager.generate(
        mission_name=mission_name,
        target=target,
        operator=operator,
        tags=tags
    )
    return result


async def handle_get_stamp_info(stamp: str) -> Dict[str, Any]:
    """
    处理获取任务戳信息请求
    """
    is_valid, reason = sanitize_stamp(stamp)
    if not is_valid:
        return {"success": False, "error": reason}
    
    result = stamp_manager.get_info(stamp)
    return result


async def handle_list_stamps() -> Dict[str, Any]:
    """
    处理列出任务戳请求
    """
    result = stamp_manager.list_active()
    return result


async def handle_associate_task(stamp: str, task_id: str) -> Dict[str, Any]:
    """
    处理关联任务请求
    """
    is_valid, reason = sanitize_stamp(stamp)
    if not is_valid:
        return {"success": False, "error": reason}
    
    if not task_id:
        return {"success": False, "error": "任务ID不能为空"}
    
    result = stamp_manager.associate_task(stamp, task_id)
    return result


async def handle_add_finding(
    stamp: str,
    vuln_type: str,
    severity: str,
    description: str,
    evidence: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    处理添加漏洞发现请求
    """
    is_valid, reason = sanitize_stamp(stamp)
    if not is_valid:
        return {"success": False, "error": reason}
    
    if not vuln_type:
        return {"success": False, "error": "漏洞类型不能为空"}
    if not severity:
        return {"success": False, "error": "严重程度不能为空"}
    if severity not in ["critical", "high", "medium", "low", "info"]:
        return {"success": False, "error": "严重程度必须是 critical/high/medium/low/info"}
    if not description:
        return {"success": False, "error": "描述不能为空"}
    
    result = stamp_manager.add_finding(
        stamp=stamp,
        vuln_type=vuln_type,
        severity=severity,
        description=description,
        evidence=evidence
    )
    return result


async def handle_add_event(
    stamp: str,
    event_type: str,
    message: str,
    data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    处理添加事件请求
    """
    is_valid, reason = sanitize_stamp(stamp)
    if not is_valid:
        return {"success": False, "error": reason}
    
    if not event_type:
        return {"success": False, "error": "事件类型不能为空"}
    if not message:
        return {"success": False, "error": "消息不能为空"}
    
    result = stamp_manager.add_event(
        stamp=stamp,
        event_type=event_type,
        message=message,
        data=data
    )
    return result


async def handle_update_stamp_status(
    stamp: str,
    status: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    处理更新任务戳状态请求
    """
    is_valid, reason = sanitize_stamp(stamp)
    if not is_valid:
        return {"success": False, "error": reason}
    
    if status not in ["active", "completed", "failed", "paused"]:
        return {"success": False, "error": "状态必须是 active/completed/failed/paused"}
    
    result = stamp_manager.update_status(stamp, status, notes)
    return result


async def handle_archive_stamp(stamp: str) -> Dict[str, Any]:
    """
    处理归档任务戳请求
    """
    is_valid, reason = sanitize_stamp(stamp)
    if not is_valid:
        return {"success": False, "error": reason}
    
    result = stamp_manager.archive(stamp)
    return result


async def handle_get_history(
    stamp: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    处理获取历史记录请求
    """
    if stamp:
        is_valid, reason = sanitize_stamp(stamp)
        if not is_valid:
            return {"success": False, "error": reason}
    
    result = stamp_manager.get_history(stamp, limit)
    return result
