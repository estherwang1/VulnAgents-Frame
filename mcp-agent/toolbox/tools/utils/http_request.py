#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用 HTTP 请求工具"""

import urllib.request
import urllib.parse
import urllib.error
import json
import ssl
import re


def check_flag(content: str) -> str:
    """检查 flag"""
    for pattern in [r'flag\{[^}]+\}', r'FLAG\{[^}]+\}', r'ctf\{[^}]+\}']:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group()
    return None


def run(url: str, method: str = "GET", data: str = "", json_body: str = "",
        headers: str = "", timeout: int = 10, **kwargs) -> dict:
    """
    发送 HTTP 请求
    """
    method = method.upper()
    
    # 构建请求头
    req_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    if headers:
        for pair in headers.split(';'):
            if ':' in pair:
                k, v = pair.split(':', 1)
                req_headers[k.strip()] = v.strip()
    
    # 构建请求体
    body = None
    if json_body:
        body = json_body.encode('utf-8')
        req_headers['Content-Type'] = 'application/json'
    elif data:
        body = data.encode('utf-8')
        if 'Content-Type' not in req_headers:
            req_headers['Content-Type'] = 'application/x-www-form-urlencoded'
    
    # SSL 上下文（忽略证书验证）
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
        response = urllib.request.urlopen(req, timeout=timeout, context=ssl_context)
        
        status = response.getcode()
        content = response.read().decode('utf-8', errors='ignore')
        resp_headers = dict(response.headers)
        
    except urllib.error.HTTPError as e:
        status = e.code
        content = e.read().decode('utf-8', errors='ignore') if e.fp else ""
        resp_headers = dict(e.headers) if e.headers else {}
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    
    flag = check_flag(content)
    
    return {
        "status": status,
        "length": len(content),
        "headers": resp_headers,
        "body": content[:2000],
        "flag": flag
    }
