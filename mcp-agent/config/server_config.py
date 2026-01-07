# -*- coding: utf-8 -*-
"""
MCP Server Configuration
配置兼容层 - 从 YAML 配置读取，提供旧接口兼容

配置优先级:
1. 环境变量（.env 文件）
2. config/tools.yaml 中的默认值
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# 加载 .env
load_dotenv()


class ServerConfig:
    """MCP 服务器配置"""
    
    # === 服务器基础配置 ===
    HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("MCP_PORT", "8000"))
    API_KEY: str = os.getenv("MCP_API_KEY", "INTERNAL_TASK_2026")
    
    # === 路径配置 ===
    MCP_AGENT_PATH: Path = Path(os.getenv("MCP_AGENT_PATH", "/root/mcp-agent"))
    WORKSPACE_ROOT: Path = Path(os.getenv("WORKSPACE_ROOT", "/root/pentest_workspace"))
    STAMP_STORAGE_PATH: Path = Path(os.getenv("STAMP_STORAGE_PATH", "/root/pentest_workspace/.stamps"))
    TOOLBOX_PATH: Path = Path(os.getenv("TOOLBOX_PATH", "/root/mcp-agent/toolbox"))
    TODO_FILE: Path = Path(os.getenv("TODO_FILE", "/root/mcp-agent/todo.json"))
    
    # === 执行配置 ===
    COMMAND_TIMEOUT: int = int(os.getenv("COMMAND_TIMEOUT", "120"))
    MAX_OUTPUT_LENGTH: int = int(os.getenv("MAX_OUTPUT_LENGTH", "2000"))
    MAX_SCRIPT_SIZE: int = int(os.getenv("MAX_SCRIPT_SIZE", "102400"))
    
    # === 安全配置 ===
    COMMAND_WHITELIST: List[str] = [
        r"^ls\b",
        r"^cat\b",
        r"^head\b",
        r"^tail\b",
        r"^grep\b",
        r"^find\b",
        r"^wc\b",
        r"^pwd\b",
        r"^whoami\b",
        r"^id\b",
        r"^ps\b",
        r"^netstat\b",
        r"^ss\b",
        r"^ip\b",
        r"^ping\b",
        r"^nmap\b",
        r"^curl\b",
        r"^wget\b",
        r"^python\b",
        r"^python3\b",
    ]
    
    DANGEROUS_CHARS: List[str] = [
        "&&",
        "||",
        ";",
        "`",
        "$(",
        "|",
        ">",
        "<",
        "\n",
    ]
    
    DANGEROUS_PATTERNS: List[str] = [
        "rm -rf /",
        "mkfs",
        "dd if=",
        "> /dev/",
        "chmod 777",
        ":(){ :|:& };:",
    ]
    
    ALLOWED_PATHS: List[str] = [
        "/root/pentest_workspace",
        "/root/mcp-agent",
        "/tmp",
    ]
    
    ALLOWED_SCRIPT_PATHS: List[str] = [
        "/root/pentest_workspace",
        "/root/mcp-agent",
        "/tmp",
    ]
    
    @classmethod
    def ensure_directories(cls):
        """确保必要目录存在"""
        cls.WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        cls.STAMP_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        cls.MCP_AGENT_PATH.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_stamp_workspace(cls, stamp: str) -> Path:
        """获取任务戳的工作空间路径"""
        return cls.WORKSPACE_ROOT / stamp
    
    @classmethod
    def print_config(cls):
        """打印当前配置"""
        print("=" * 60)
        print("  Pentest MCP Server")
        print("=" * 60)
        print(f"  Host: {cls.HOST}:{cls.PORT}")
        print(f"  API Key: {'*' * len(cls.API_KEY)}")
        print("-" * 60)
        print(f"  MCP Agent Path: {cls.MCP_AGENT_PATH}")
        print(f"  Workspace Root: {cls.WORKSPACE_ROOT}")
        print(f"  Toolbox Path: {cls.TOOLBOX_PATH}")
        print("-" * 60)
        print(f"  Command Timeout: {cls.COMMAND_TIMEOUT}s")
        print(f"  Max Output: {cls.MAX_OUTPUT_LENGTH} chars")
        print("=" * 60)
    
    @classmethod
    def is_command_safe(cls, command: str) -> tuple:
        """检查命令是否安全"""
        # 检查黑名单模式
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern in command:
                return False, f"命令匹配危险模式: {pattern}"
        
        # 检查白名单
        cmd_base = command.split()[0] if command else ""
        if cmd_base not in ["ls", "cat", "head", "tail", "grep", "find", "wc",
                           "pwd", "whoami", "id", "ps", "netstat", "ss", "ip",
                           "ping", "nmap", "curl", "wget", "python", "python3"]:
            return False, f"命令不在白名单中: {cmd_base}"
        
        return True, "OK"


# 初始化时确保目录存在
try:
    ServerConfig.ensure_directories()
except Exception as e:
    print(f"警告: 无法创建目录 - {e}")
