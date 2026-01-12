# -*- coding: utf-8 -*-
"""
Security Utilities
命令安全校验
"""

import re
from typing import Tuple
from config import ServerConfig


def is_command_safe(command: str) -> Tuple[bool, str]:
    """
    检查命令是否安全
    
    Args:
        command: 要执行的命令
        
    Returns:
        (is_safe, reason): 是否安全及原因
    """
    command = command.strip()
    
    # 1. 检查危险字符
    for char in ServerConfig.DANGEROUS_CHARS:
        if char in command:
            return False, f"包含危险字符: {char}"
    
    # 2. 检查白名单命令
    for pattern in ServerConfig.COMMAND_WHITELIST:
        if re.match(pattern, command):
            return True, "白名单命令"
    
    # 3. 检查脚本执行
    # 支持 python3 和 bash 执行脚本
    script_pattern = r"^(python3|bash)\s+(.+)$"
    match = re.match(script_pattern, command)
    if match:
        script_path = match.group(2).split()[0]  # 获取脚本路径（忽略参数）
        
        # 检查脚本路径是否在允许范围内
        for allowed_prefix in ServerConfig.ALLOWED_SCRIPT_PATHS:
            if script_path.startswith(allowed_prefix):
                return True, f"允许的脚本路径: {allowed_prefix}"
        
        return False, f"脚本路径不在允许范围: {script_path}"
    
    return False, "命令不在白名单中"


def sanitize_stamp(stamp: str) -> Tuple[bool, str]:
    """
    验证任务戳格式
    
    Args:
        stamp: 任务戳 ID
        
    Returns:
        (is_valid, reason): 是否有效及原因
    """
    # 格式: SHADOW-YYYYMMDD-HHMMSS-XXXX
    pattern = r"^SHADOW-\d{8}-\d{6}-[A-F0-9]{4}$"
    
    if not stamp:
        return False, "任务戳不能为空"
    
    if not re.match(pattern, stamp):
        return False, f"任务戳格式无效: {stamp}"
    
    return True, "有效"


def sanitize_script_name(script_name: str) -> Tuple[bool, str]:
    """
    验证脚本名格式
    
    Args:
        script_name: 脚本文件名
        
    Returns:
        (is_valid, reason): 是否有效及原因
    """
    if not script_name:
        return False, "脚本名不能为空"
    
    # 只允许 .py 和 .sh 文件
    if not (script_name.endswith(".py") or script_name.endswith(".sh")):
        return False, "只支持 .py 和 .sh 脚本"
    
    # 检查路径遍历攻击
    if ".." in script_name or "/" in script_name or "\\" in script_name:
        return False, "脚本名包含非法字符"
    
    # 只允许字母、数字、下划线、短横线、点
    pattern = r"^[a-zA-Z0-9_\-\.]+$"
    if not re.match(pattern, script_name):
        return False, "脚本名包含非法字符"
    
    return True, "有效"
