#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dirsearch 目录扫描工具 - 封装 dirsearch 命令"""

import subprocess
import shutil
import re
import json
import os
from typing import Dict, List


def check_dirsearch() -> bool:
    """检查 dirsearch 是否安装"""
    # dirsearch 可能是 python 脚本或直接命令
    if shutil.which("dirsearch"):
        return True
    # 检查常见安装路径
    common_paths = [
        "/usr/share/dirsearch/dirsearch.py",
        "/opt/dirsearch/dirsearch.py",
        os.path.expanduser("~/dirsearch/dirsearch.py")
    ]
    for path in common_paths:
        if os.path.exists(path):
            return True
    return False


def get_dirsearch_cmd() -> List[str]:
    """获取 dirsearch 命令"""
    if shutil.which("dirsearch"):
        return ["dirsearch"]
    
    common_paths = [
        "/usr/share/dirsearch/dirsearch.py",
        "/opt/dirsearch/dirsearch.py",
        os.path.expanduser("~/dirsearch/dirsearch.py")
    ]
    for path in common_paths:
        if os.path.exists(path):
            return ["python3", path]
    
    return ["dirsearch"]


def parse_dirsearch_output(output: str) -> Dict:
    """解析 dirsearch 输出"""
    result = {
        "found": [],
        "total": 0
    }
    
    # 解析格式: [状态码] 大小 路径
    # 200    4KB  /admin/
    pattern = r'\[(\d+)\]\s+(\S+)\s+(\S+)'
    
    for line in output.split('\n'):
        # 简单格式
        match = re.search(r'(\d{3})\s+-\s+(\S+)\s+-\s+(\S+)', line)
        if match:
            status, size, path = match.groups()
            result["found"].append({
                "path": path,
                "status": int(status),
                "size": size
            })
            continue
        
        # 另一种格式
        match = re.search(r'\[(\d{3})\]\s+(\S+)\s+(\S+)', line)
        if match:
            status, size, path = match.groups()
            result["found"].append({
                "path": path,
                "status": int(status),
                "size": size
            })
    
    result["total"] = len(result["found"])
    
    # 检测 flag
    flag_match = re.search(r'flag\{[^}]+\}', output, re.IGNORECASE)
    if flag_match:
        result["flag"] = flag_match.group()
    
    return result


def run(url: str,
        wordlist: str = None,
        extensions: str = "php,html,txt,bak",
        threads: int = 20,
        recursive: bool = False,
        exclude_status: str = "404",
        timeout: int = 300,
        **kwargs) -> dict:
    """
    执行 Dirsearch 目录扫描
    
    Args:
        url: 目标 URL
        wordlist: 自定义字典路径
        extensions: 扩展名列表
        threads: 并发线程数
        recursive: 是否递归扫描
        exclude_status: 排除的状态码
        timeout: 超时时间
    
    Returns:
        扫描结果
    """
    if not check_dirsearch():
        return {"error": "dirsearch 未安装，请运行: pip install dirsearch 或 apt install dirsearch"}
    
    # 构建命令
    cmd = get_dirsearch_cmd()
    cmd.extend(["-u", url])
    
    # 扩展名
    if extensions:
        cmd.extend(["-e", extensions])
    
    # 字典
    if wordlist:
        cmd.extend(["-w", wordlist])
    
    # 线程
    cmd.extend(["-t", str(threads)])
    
    # 递归
    if recursive:
        cmd.append("-r")
    
    # 排除状态码
    if exclude_status:
        cmd.extend(["--exclude-status", exclude_status])
    
    # 不使用颜色，方便解析
    cmd.append("--plain-text-report=-")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout + result.stderr
        
        # 解析输出
        parsed = parse_dirsearch_output(output)
        parsed["url"] = url
        parsed["command"] = " ".join(cmd)
        
        return parsed
        
    except subprocess.TimeoutExpired:
        return {"error": f"扫描超时（{timeout}秒）"}
    except Exception as e:
        return {"error": str(e)}
