#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hydra 密码爆破工具 - 封装 hydra 命令"""

import subprocess
import shutil
import re
import os
import tempfile
from typing import Dict, List, Optional


def check_hydra() -> bool:
    """检查 hydra 是否安装"""
    return shutil.which("hydra") is not None


# 内置常用密码
COMMON_PASSWORDS = [
    "admin", "123456", "password", "12345678", "admin123",
    "root", "toor", "pass", "passwd", "123123",
    "admin888", "admin666", "test", "test123", "guest",
    "1234", "12345", "123456789", "qwerty", "abc123",
    "letmein", "welcome", "monkey", "dragon", "master",
    "login", "passw0rd", "shadow", "sunshine", "princess",
    "hack", "hacker", "shell", "webshell", "backdoor",
    "P@ssw0rd", "Admin123", "Root123",
]

COMMON_USERS = ["admin", "root", "administrator", "user", "test", "guest"]


def parse_hydra_output(output: str) -> Dict:
    """解析 hydra 输出"""
    result = {
        "found_credentials": [],
        "attempts": 0,
        "success": False
    }
    
    # 提取成功的凭据
    # 格式: [80][http-post-form] host: 192.168.1.1   login: admin   password: 123456
    cred_pattern = r'\[(\d+)\]\[([^\]]+)\].*?login:\s*(\S+)\s+password:\s*(\S+)'
    matches = re.findall(cred_pattern, output)
    
    for match in matches:
        result["found_credentials"].append({
            "port": match[0],
            "service": match[1],
            "username": match[2],
            "password": match[3]
        })
        result["success"] = True
    
    # 简单格式: host: x.x.x.x   login: admin   password: 123
    simple_pattern = r'host:.*?login:\s*(\S+)\s+password:\s*(\S+)'
    simple_matches = re.findall(simple_pattern, output)
    for match in simple_matches:
        cred = {"username": match[0], "password": match[1]}
        if cred not in [{"username": c["username"], "password": c["password"]} 
                        for c in result["found_credentials"]]:
            result["found_credentials"].append(cred)
            result["success"] = True
    
    # 提取尝试次数
    attempts_match = re.search(r'(\d+)\s+valid password', output)
    if attempts_match:
        result["attempts"] = int(attempts_match.group(1))
    
    # 检测 flag
    flag_match = re.search(r'flag\{[^}]+\}', output, re.IGNORECASE)
    if flag_match:
        result["flag"] = flag_match.group()
    
    return result


def run(target: str,
        service: str,
        username: str = None,
        usernames: List[str] = None,
        password: str = None,
        passwords: List[str] = None,
        userfile: str = None,
        passfile: str = None,
        port: int = None,
        ssl: bool = False,
        threads: int = 4,
        timeout: int = 300,
        # HTTP 特定参数
        http_path: str = None,
        http_method: str = "POST",
        http_form: str = None,
        http_fail: str = None,
        **kwargs) -> dict:
    """
    执行 Hydra 密码爆破
    
    Args:
        target: 目标 IP 或域名
        service: 服务类型 (ssh/ftp/http-post-form/mysql/smb/rdp 等)
        username: 单个用户名
        usernames: 用户名列表
        password: 单个密码
        passwords: 密码列表
        userfile: 用户名字典文件路径
        passfile: 密码字典文件路径
        port: 端口号
        ssl: 是否使用 SSL
        threads: 并发线程数
        timeout: 超时时间
        http_path: HTTP 表单路径
        http_method: HTTP 方法 (GET/POST)
        http_form: HTTP 表单参数 (如 "user=^USER^&pass=^PASS^")
        http_fail: 登录失败标识字符串
    
    Returns:
        爆破结果
    """
    if not check_hydra():
        return {"error": "hydra 未安装，请运行: apt install hydra"}
    
    # 创建临时文件
    temp_files = []
    
    try:
        # 构建命令
        cmd = ["hydra"]
        
        # 用户名
        if username:
            cmd.extend(["-l", username])
        elif usernames:
            user_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            user_file.write('\n'.join(usernames))
            user_file.close()
            temp_files.append(user_file.name)
            cmd.extend(["-L", user_file.name])
        elif userfile:
            cmd.extend(["-L", userfile])
        else:
            # 默认用户
            user_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            user_file.write('\n'.join(COMMON_USERS[:3]))
            user_file.close()
            temp_files.append(user_file.name)
            cmd.extend(["-L", user_file.name])
        
        # 密码
        if password:
            cmd.extend(["-p", password])
        elif passwords:
            pass_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            pass_file.write('\n'.join(passwords))
            pass_file.close()
            temp_files.append(pass_file.name)
            cmd.extend(["-P", pass_file.name])
        elif passfile:
            cmd.extend(["-P", passfile])
        else:
            # 默认密码
            pass_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            pass_file.write('\n'.join(COMMON_PASSWORDS))
            pass_file.close()
            temp_files.append(pass_file.name)
            cmd.extend(["-P", pass_file.name])
        
        # 线程
        cmd.extend(["-t", str(threads)])
        
        # SSL
        if ssl:
            cmd.append("-S")
        
        # 端口
        if port:
            cmd.extend(["-s", str(port)])
        
        # 目标和服务
        if service.startswith("http"):
            # HTTP 表单爆破
            if http_path and http_form:
                form_string = f"{http_path}:{http_form}"
                if http_fail:
                    form_string += f":F={http_fail}"
                cmd.extend([target, service, form_string])
            else:
                return {"error": "HTTP 表单爆破需要 http_path 和 http_form 参数"}
        else:
            cmd.extend([target, service])
        
        # 执行
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout + result.stderr
        
        # 解析输出
        parsed = parse_hydra_output(output)
        parsed["command"] = " ".join(cmd)
        parsed["raw_output"] = output[-1500:] if len(output) > 1500 else output
        
        return parsed
        
    except subprocess.TimeoutExpired:
        return {"error": f"爆破超时（{timeout}秒）"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        # 清理临时文件
        for f in temp_files:
            try:
                os.unlink(f)
            except:
                pass
