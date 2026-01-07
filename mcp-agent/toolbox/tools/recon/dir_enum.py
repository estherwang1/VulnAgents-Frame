#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""目录枚举工具"""

import urllib.request
import urllib.error
import concurrent.futures
import re
from typing import List, Dict

# 内置字典
WORDLISTS = {
    "common": [
        "admin", "login", "api", "backup", "config", "test", "dev", "debug",
        "uploads", "upload", "images", "img", "js", "css", "static", "assets",
        "includes", "lib", "vendor", "admin.php", "login.php", "config.php",
        "index.php", "info.php", "robots.txt", "sitemap.xml", ".git", ".env",
        ".htaccess", "web.config", "README.md", "wp-admin", "wp-login.php",
        "phpmyadmin", "pma", "mysql", "database", "console", "dashboard",
        "panel", "manager", "user", "users", "account", "profile", "register",
        "flag", "flag.txt", "flag.php", "secret", "private", "hidden",
    ],
    "api": [
        "api", "api/v1", "api/v2", "api/v3", "rest", "graphql",
        "api/users", "api/user", "api/login", "api/auth", "api/token",
        "api/admin", "api/config", "api/debug", "swagger", "swagger.json",
        "api-docs", "openapi.json", "health", "status", "metrics",
    ],
    "backup": [
        "backup", "backups", "bak", "old", "temp", "tmp", "backup.zip",
        "backup.tar.gz", "backup.sql", "db.sql", "www.zip", "site.zip",
        ".bak", "index.php.bak", "config.php.bak", "web.config.bak",
    ],
}


def check_flag(content: str) -> str:
    """检查 flag"""
    for pattern in [r'flag\{[^}]+\}', r'FLAG\{[^}]+\}', r'ctf\{[^}]+\}']:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group()
    return None


def check_path(base_url: str, path: str, timeout: int) -> Dict:
    """检查单个路径"""
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response = urllib.request.urlopen(req, timeout=timeout)
        content = response.read().decode('utf-8', errors='ignore')
        result = {
            "path": f"/{path}",
            "status": response.getcode(),
            "size": len(content),
        }
        flag = check_flag(content)
        if flag:
            result["flag"] = flag
        return result
    except urllib.error.HTTPError as e:
        if e.code in [401, 403]:
            return {"path": f"/{path}", "status": e.code, "size": 0}
        return None
    except:
        return None


def run(url: str, wordlist: str = "common", extensions: str = "", 
        threads: int = 10, timeout: int = 5, **kwargs) -> dict:
    """
    执行目录枚举
    """
    # 获取字典
    if wordlist == "full":
        paths = WORDLISTS["common"] + WORDLISTS["api"] + WORDLISTS["backup"]
    else:
        paths = WORDLISTS.get(wordlist, WORDLISTS["common"])
    
    # 添加扩展名
    if extensions:
        ext_list = [e.strip() for e in extensions.split(',') if e.strip()]
        expanded = []
        for path in paths:
            expanded.append(path)
            for ext in ext_list:
                expanded.append(f"{path}.{ext}")
        paths = expanded
    
    paths = list(set(paths))
    found = []
    flag = None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(check_path, url, p, timeout): p for p in paths}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result and result.get("status"):
                found.append(result)
                if result.get("flag"):
                    flag = result["flag"]
    
    found.sort(key=lambda x: (x["status"], x["path"]))
    
    return {
        "url": url,
        "found": found,
        "total_checked": len(paths),
        "total_found": len(found),
        "flag": flag
    }
