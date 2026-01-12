#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLMap SQL注入工具 - 封装 sqlmap 命令"""

import subprocess
import shutil
import json
import re
import os
import tempfile
from typing import Dict, Optional


def check_sqlmap() -> bool:
    """检查 sqlmap 是否安装"""
    return shutil.which("sqlmap") is not None


def parse_sqlmap_output(output: str) -> Dict:
    """解析 sqlmap 输出"""
    result = {
        "vulnerable": False,
        "injection_types": [],
        "dbms": None,
        "databases": [],
        "tables": [],
        "data": [],
        "flags": []
    }
    
    # 检测是否存在注入
    if "is vulnerable" in output or "sqlmap identified the following injection" in output:
        result["vulnerable"] = True
    
    # 提取注入类型
    injection_patterns = [
        r"Type: ([^\n]+)",
        r"Payload: ([^\n]+)"
    ]
    for pattern in injection_patterns:
        matches = re.findall(pattern, output)
        result["injection_types"].extend(matches[:5])  # 最多5个
    
    # 提取数据库类型
    dbms_match = re.search(r"back-end DBMS: ([^\n]+)", output)
    if dbms_match:
        result["dbms"] = dbms_match.group(1).strip()
    
    # 提取数据库列表
    db_section = re.search(r"available databases.*?:\s*\n((?:\[\*\][^\n]+\n)+)", output, re.DOTALL)
    if db_section:
        dbs = re.findall(r"\[\*\]\s*(\S+)", db_section.group(1))
        result["databases"] = dbs
    
    # 提取表
    table_section = re.search(r"Database:.*?Table.*?:\s*\n((?:\[\*\][^\n]+\n)+)", output, re.DOTALL)
    if table_section:
        tables = re.findall(r"\[\*\]\s*(\S+)", table_section.group(1))
        result["tables"] = tables
    
    # 检测 flag
    flag_matches = re.findall(r'flag\{[^}]+\}', output, re.IGNORECASE)
    if flag_matches:
        result["flags"] = flag_matches
        result["flag"] = flag_matches[0]
    
    return result


def run(url: str,
        param: str = None,
        data: str = None,
        method: str = None,
        cookie: str = None,
        level: int = 1,
        risk: int = 1,
        dbs: bool = False,
        tables: str = None,
        dump: str = None,
        dump_all: bool = False,
        technique: str = None,
        batch: bool = True,
        timeout: int = 300,
        **kwargs) -> dict:
    """
    执行 SQLMap 扫描
    
    Args:
        url: 目标 URL（带参数，如 http://site.com/page?id=1）
        param: 指定测试的参数
        data: POST 数据（如 "user=admin&pass=123"）
        method: 强制指定 HTTP 方法
        cookie: Cookie 值
        level: 检测级别 1-5（越高测试越全面）
        risk: 风险级别 1-3（越高 payload 越激进）
        dbs: 是否枚举数据库
        tables: 枚举指定数据库的表（如 "mysql"）
        dump: 导出指定表的数据（格式: "db.table"）
        dump_all: 导出所有数据
        technique: 注入技术 (B/E/U/S/T/Q)
        batch: 非交互模式
        timeout: 超时时间（秒）
    
    Returns:
        扫描结果
    """
    if not check_sqlmap():
        return {"error": "sqlmap 未安装，请运行: apt install sqlmap"}
    
    # 构建命令
    cmd = ["sqlmap", "-u", url]
    
    # POST 数据
    if data:
        cmd.extend(["--data", data])
    
    # 指定参数
    if param:
        cmd.extend(["-p", param])
    
    # HTTP 方法
    if method:
        cmd.extend(["--method", method])
    
    # Cookie
    if cookie:
        cmd.extend(["--cookie", cookie])
    
    # 检测级别
    cmd.extend(["--level", str(level)])
    cmd.extend(["--risk", str(risk)])
    
    # 注入技术
    if technique:
        cmd.extend(["--technique", technique])
    
    # 枚举选项
    if dbs:
        cmd.append("--dbs")
    
    if tables:
        cmd.extend(["-D", tables, "--tables"])
    
    if dump:
        parts = dump.split(".")
        if len(parts) == 2:
            cmd.extend(["-D", parts[0], "-T", parts[1], "--dump"])
    
    if dump_all:
        cmd.append("--dump-all")
    
    # 非交互模式
    if batch:
        cmd.append("--batch")
    
    # 输出格式
    cmd.append("--flush-session")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout + result.stderr
        
        # 解析输出
        parsed = parse_sqlmap_output(output)
        parsed["command"] = " ".join(cmd)
        parsed["raw_output"] = output[-2000:] if len(output) > 2000 else output  # 截断
        
        return parsed
        
    except subprocess.TimeoutExpired:
        return {"error": f"扫描超时（{timeout}秒）", "command": " ".join(cmd)}
    except Exception as e:
        return {"error": str(e), "command": " ".join(cmd)}
