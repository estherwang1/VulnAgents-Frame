# -*- coding: utf-8 -*-
"""
Process Runner
异步脚本执行器
"""

import asyncio
from typing import Dict, Any, Optional
from config import ServerConfig


async def run_command(
    command: str,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    异步执行命令
    
    Args:
        command: 要执行的命令
        cwd: 工作目录
        timeout: 超时时间（秒），默认使用配置值
        
    Returns:
        {
            "success": bool,
            "stdout": str,
            "stderr": str,
            "return_code": int,
            "error": str (如果失败)
        }
    """
    timeout = timeout or ServerConfig.COMMAND_TIMEOUT
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        
        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()
        
        # 截断过长输出
        if len(stdout_str) > ServerConfig.MAX_OUTPUT_LENGTH:
            stdout_str = stdout_str[:ServerConfig.MAX_OUTPUT_LENGTH] + "\n... [输出已截断]"
        if len(stderr_str) > ServerConfig.MAX_OUTPUT_LENGTH:
            stderr_str = stderr_str[:ServerConfig.MAX_OUTPUT_LENGTH] + "\n... [输出已截断]"
        
        return {
            "success": process.returncode == 0,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "return_code": process.returncode
        }
        
    except asyncio.TimeoutError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "error": f"命令执行超时（{timeout}秒）"
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "error": str(e)
        }


async def run_script_background(
    script_path: str,
    log_file: str,
    cwd: str
) -> Dict[str, Any]:
    """
    后台执行脚本（nohup）
    
    Args:
        script_path: 脚本完整路径
        log_file: 日志文件路径
        cwd: 工作目录
        
    Returns:
        {
            "success": bool,
            "pid": str,
            "error": str (如果失败)
        }
    """
    # 根据脚本类型选择解释器
    if script_path.endswith(".py"):
        interpreter = "python3"
    elif script_path.endswith(".sh"):
        interpreter = "bash"
    else:
        return {
            "success": False,
            "pid": "",
            "error": "不支持的脚本类型"
        }
    
    # 构造后台执行命令
    command = f"cd {cwd} && nohup {interpreter} {script_path} > {log_file} 2>&1 & echo $!"
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        pid = stdout.decode().strip()
        
        if pid.isdigit():
            return {
                "success": True,
                "pid": pid
            }
        else:
            return {
                "success": False,
                "pid": "",
                "error": f"获取 PID 失败: {stderr.decode()}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "pid": "",
            "error": str(e)
        }


async def check_pid_running(pid: str) -> bool:
    """检查进程是否仍在运行"""
    result = await run_command(f"ps -p {pid}", timeout=5)
    return result["return_code"] == 0
