# -*- coding: utf-8 -*-
"""
Workspace Manager
任务工作空间隔离管理
"""

import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ServerConfig


class WorkspaceManager:
    """工作空间管理器"""
    
    def __init__(self):
        self.root = ServerConfig.WORKSPACE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
    
    def create_workspace(self, stamp: str) -> Path:
        """
        创建任务戳专属工作空间
        
        Args:
            stamp: 任务戳 ID
            
        Returns:
            工作空间路径
        """
        workspace = self.root / stamp
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace
    
    def get_workspace(self, stamp: str) -> Optional[Path]:
        """
        获取任务戳工作空间
        
        Args:
            stamp: 任务戳 ID
            
        Returns:
            工作空间路径，不存在返回 None
        """
        workspace = self.root / stamp
        if workspace.exists():
            return workspace
        return None
    
    def workspace_exists(self, stamp: str) -> bool:
        """检查工作空间是否存在"""
        return (self.root / stamp).exists()
    
    def save_script(self, stamp: str, script_name: str, script_content: str) -> Path:
        """
        保存脚本到工作空间
        
        Args:
            stamp: 任务戳 ID
            script_name: 脚本文件名
            script_content: 脚本内容
            
        Returns:
            脚本完整路径
        """
        workspace = self.create_workspace(stamp)
        script_path = workspace / script_name
        script_path.write_text(script_content, encoding="utf-8")
        # 添加执行权限
        script_path.chmod(0o755)
        return script_path
    
    def get_script_path(self, stamp: str, script_name: str) -> Optional[Path]:
        """获取脚本路径"""
        workspace = self.get_workspace(stamp)
        if workspace:
            script_path = workspace / script_name
            if script_path.exists():
                return script_path
        return None
    
    def list_scripts(self, stamp: str) -> List[str]:
        """列出工作空间中的脚本"""
        workspace = self.get_workspace(stamp)
        if not workspace:
            return []
        
        scripts = []
        for f in workspace.iterdir():
            if f.is_file() and (f.suffix == ".py" or f.suffix == ".sh"):
                scripts.append(f.name)
        return scripts
    
    def list_files(self, stamp: str) -> List[Dict[str, Any]]:
        """列出工作空间中的所有文件"""
        workspace = self.get_workspace(stamp)
        if not workspace:
            return []
        
        files = []
        for f in workspace.iterdir():
            if f.is_file():
                stat = f.stat()
                files.append({
                    "name": f.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        return files
    
    def read_file(self, stamp: str, filename: str, max_lines: int = 100) -> Optional[str]:
        """
        读取工作空间中的文件
        
        Args:
            stamp: 任务戳 ID
            filename: 文件名
            max_lines: 最大读取行数
            
        Returns:
            文件内容
        """
        workspace = self.get_workspace(stamp)
        if not workspace:
            return None
        
        file_path = workspace / filename
        if not file_path.exists():
            return None
        
        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(lines) > max_lines:
                return "\n".join(lines[:max_lines]) + f"\n... [截断，共 {len(lines)} 行]"
            return "\n".join(lines)
        except Exception:
            return None
    
    def cleanup_workspace(self, stamp: str) -> bool:
        """
        清理工作空间
        
        Args:
            stamp: 任务戳 ID
            
        Returns:
            是否成功
        """
        workspace = self.get_workspace(stamp)
        if workspace:
            shutil.rmtree(workspace)
            return True
        return False
    
    def get_log_file_path(self, stamp: str, task_id: str) -> Path:
        """获取任务日志文件路径"""
        workspace = self.create_workspace(stamp)
        return workspace / f"{task_id}.log"


# 全局实例
workspace_manager = WorkspaceManager()
