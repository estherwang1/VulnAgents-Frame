#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nikto Web漏洞扫描工具 - 封装 nikto 命令"""

import subprocess
import shutil
import re
from typing import Dict, List


def check_nikto() -> bool:
    """检查 nikto 是否安装"""
    return shutil.which("nikto") is not None


def parse_nikto_output(output: str) -> Dict:
    """解析 nikto 输出"""
    result = {
        "target": "",
        "server": "",
        "findings": [],
        "vulnerabilities": [],
        "interesting": []
    }
    
    # 提取目标
    target_match = re.search(r'\+ Target IP:\s*(\S+)', output)
    if target_match:
        result["target"] = target_match.group(1)
    
    # 提取服务器信息
    server_match = re.search(r'\+ Server:\s*(.+)', output)
    if server_match:
        result["server"] = server_match.group(1).strip()
    
    # 提取发现
    # 格式: + /path: Description
    finding_pattern = r'\+ ([^:]+):\s*(.+)'
    for match in re.finditer(finding_pattern, output):
        path, desc = match.groups()
        if path.startswith('/') or path.startswith('OSVDB'):
            finding = {
                "path": path.strip(),
                "description": desc.strip()
            }
            
            # 分类
            desc_lower = desc.lower()
            if any(kw in desc_lower for kw in ['vulnerability', 'vulnerable', 'exploit', 'cve-', 'osvdb']):
                result["vulnerabilities"].append(finding)
            elif any(kw in desc_lower for kw in ['interesting', 'backup', 'config', 'password', 'admin']):
                result["interesting"].append(finding)
            else:
                result["findings"].append(finding)
    
    # 检测 flag
    flag_match = re.search(r'flag\{[^}]+\}', output, re.IGNORECASE)
    if flag_match:
        result["flag"] = flag_match.group()
    
    return result


def run(url: str,
        port: int = None,
        ssl: bool = False,
        plugins: str = None,
        tuning: str = None,
        timeout: int = 600,
        **kwargs) -> dict:
    """
    执行 Nikto Web 漏洞扫描
    
    Args:
        url: 目标 URL 或 IP
        port: 端口号
        ssl: 是否使用 SSL
        plugins: 指定插件（如 "tests"）
        tuning: 扫描调优（0-9,a-c）
        timeout: 超时时间（秒）
    
    Returns:
        扫描结果
    """
    if not check_nikto():
        return {"error": "nikto 未安装，请运行: apt install nikto"}
    
    # 构建命令
    cmd = ["nikto", "-h", url]
    
    # 端口
    if port:
        cmd.extend(["-p", str(port)])
    
    # SSL
    if ssl:
        cmd.append("-ssl")
    
    # 插件
    if plugins:
        cmd.extend(["-Plugins", plugins])
    
    # 调优
    if tuning:
        cmd.extend(["-Tuning", tuning])
    
    # 不显示进度
    cmd.append("-Display")
    cmd.append("1")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout + result.stderr
        
        # 解析输出
        parsed = parse_nikto_output(output)
        parsed["command"] = " ".join(cmd)
        parsed["raw_output"] = output[-3000:] if len(output) > 3000 else output
        
        return parsed
        
    except subprocess.TimeoutExpired:
        return {"error": f"扫描超时（{timeout}秒）"}
    except Exception as e:
        return {"error": str(e)}
