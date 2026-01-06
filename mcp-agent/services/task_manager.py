# -*- coding: utf-8 -*-
"""
Task Manager
任务生命周期管理
基于原 task_manager.py 重构
"""

import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ServerConfig
from services.workspace_manager import workspace_manager
from services.stamp_manager import stamp_manager
from utils.process_runner import run_script_background, check_pid_running


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.todo_file = ServerConfig.TODO_FILE
        self._ensure_todo_file()
    
    def _ensure_todo_file(self):
        """确保任务账本文件存在"""
        if not self.todo_file.exists():
            self.todo_file.parent.mkdir(parents=True, exist_ok=True)
            self.todo_file.write_text("[]")
    
    def _load_todos(self) -> List[Dict[str, Any]]:
        """加载任务列表"""
        try:
            return json.loads(self.todo_file.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_todos(self, todos: List[Dict[str, Any]]):
        """保存任务列表"""
        self.todo_file.write_text(json.dumps(todos, indent=2, ensure_ascii=False))
    
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        return f"T{int(time.time())}"
    
    async def deploy_and_run(
        self,
        stamp: str,
        script_name: str,
        script_content: str
    ) -> Dict[str, Any]:
        """
        部署脚本并执行
        
        这是核心方法：
        1. 验证任务戳存在
        2. 将脚本内容保存到工作空间
        3. 后台启动脚本
        4. 关联任务到任务戳
        
        Args:
            stamp: 任务戳 ID
            script_name: 脚本文件名
            script_content: 脚本内容
            
        Returns:
            {
                "success": bool,
                "task_id": str,
                "pid": str,
                "log_file": str,
                "error": str (如果失败)
            }
        """
        # 1. 验证任务戳
        if not workspace_manager.workspace_exists(stamp):
            return {
                "success": False,
                "error": f"任务戳 {stamp} 的工作空间不存在，请先生成任务戳"
            }
        
        # 2. 保存脚本
        try:
            script_path = workspace_manager.save_script(stamp, script_name, script_content)
        except Exception as e:
            return {
                "success": False,
                "error": f"保存脚本失败: {str(e)}"
            }
        
        # 3. 生成任务ID和日志路径
        task_id = self._generate_task_id()
        workspace = workspace_manager.get_workspace(stamp)
        log_file = workspace / f"{task_id}.log"
        
        # 4. 后台执行脚本
        result = await run_script_background(
            script_path=str(script_path),
            log_file=str(log_file),
            cwd=str(workspace)
        )
        
        if not result["success"]:
            return {
                "success": False,
                "error": f"启动脚本失败: {result.get('error', '未知错误')}"
            }
        
        pid = result["pid"]
        
        # 5. 记录到任务账本
        todos = self._load_todos()
        task_record = {
            "task_id": task_id,
            "stamp": stamp,
            "pid": pid,
            "script_name": script_name,
            "script_path": str(script_path),
            "status": "RUNNING",
            "start_time": datetime.now().isoformat(),
            "log_file": str(log_file)
        }
        todos.append(task_record)
        self._save_todos(todos)
        
        # 6. 关联到任务戳
        stamp_manager.associate_task(stamp, task_id)
        
        return {
            "success": True,
            "task_id": task_id,
            "pid": pid,
            "log_file": str(log_file),
            "message": f"任务 {task_id} 已在 {stamp} 下启动"
        }
    
    async def get_task_status(
        self,
        stamp: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            stamp: 可选，筛选特定任务戳的任务
            task_id: 可选，筛选特定任务
            
        Returns:
            任务状态列表
        """
        todos = self._load_todos()
        updated = False
        
        # 过滤
        filtered_tasks = []
        for task in todos:
            if stamp and task.get("stamp") != stamp:
                continue
            if task_id and task.get("task_id") != task_id:
                continue
            
            # 检查运行中任务的状态
            if task["status"] == "RUNNING":
                is_running = await check_pid_running(task["pid"])
                if not is_running:
                    task["status"] = "COMPLETED"
                    task["end_time"] = datetime.now().isoformat()
                    updated = True
            
            filtered_tasks.append(task)
        
        # 保存更新
        if updated:
            self._save_todos(todos)
        
        return {
            "success": True,
            "count": len(filtered_tasks),
            "tasks": filtered_tasks
        }
    
    async def get_task_result(
        self,
        stamp: str,
        task_id: str,
        tail_lines: int = 50
    ) -> Dict[str, Any]:
        """
        获取任务执行结果
        
        Args:
            stamp: 任务戳 ID
            task_id: 任务 ID
            tail_lines: 读取日志的最后N行
            
        Returns:
            任务结果（日志内容）
        """
        # 查找任务
        todos = self._load_todos()
        task = None
        for t in todos:
            if t.get("task_id") == task_id and t.get("stamp") == stamp:
                task = t
                break
        
        if not task:
            return {
                "success": False,
                "error": f"任务 {task_id} 不存在"
            }
        
        # 检查状态
        if task["status"] == "RUNNING":
            is_running = await check_pid_running(task["pid"])
            if not is_running:
                task["status"] = "COMPLETED"
                task["end_time"] = datetime.now().isoformat()
                self._save_todos(todos)
        
        # 读取日志
        log_content = workspace_manager.read_file(
            stamp,
            f"{task_id}.log",
            max_lines=tail_lines
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "status": task["status"],
            "log": log_content or "(日志为空或不存在)",
            "start_time": task.get("start_time"),
            "end_time": task.get("end_time")
        }
    
    async def cancel_task(self, stamp: str, task_id: str) -> Dict[str, Any]:
        """
        取消正在运行的任务
        
        Args:
            stamp: 任务戳 ID
            task_id: 任务 ID
        """
        todos = self._load_todos()
        
        for task in todos:
            if task.get("task_id") == task_id and task.get("stamp") == stamp:
                if task["status"] != "RUNNING":
                    return {
                        "success": False,
                        "error": f"任务 {task_id} 状态为 {task['status']}，无法取消"
                    }
                
                # 杀死进程
                import asyncio
                process = await asyncio.create_subprocess_shell(
                    f"kill -9 {task['pid']}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                task["status"] = "CANCELLED"
                task["end_time"] = datetime.now().isoformat()
                self._save_todos(todos)
                
                return {
                    "success": True,
                    "message": f"任务 {task_id} 已取消"
                }
        
        return {
            "success": False,
            "error": f"任务 {task_id} 不存在"
        }
    
    def list_all_tasks(self, limit: int = 20) -> Dict[str, Any]:
        """列出所有任务"""
        todos = self._load_todos()
        return {
            "success": True,
            "count": len(todos),
            "tasks": todos[-limit:]
        }


# 全局实例
task_manager = TaskManager()
