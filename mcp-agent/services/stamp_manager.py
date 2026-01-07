# -*- coding: utf-8 -*-
"""
Stamp Manager
任务戳生命周期管理
基于原 remote_task_stamp_manager.py 重构
"""

import json
import hashlib
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ServerConfig
from services.workspace_manager import workspace_manager


class StampManager:
    """任务戳管理器"""
    
    def __init__(self):
        self.storage_path = ServerConfig.STAMP_STORAGE_PATH
        self.active_stamps_file = self.storage_path / "active_stamps.json"
        self.history_file = self.storage_path / "history.jsonl"
        self._ensure_storage()
    
    def _ensure_storage(self):
        """确保存储目录存在"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        if not self.active_stamps_file.exists():
            self.active_stamps_file.write_text("{}")
    
    def _load_active_stamps(self) -> Dict[str, Any]:
        """加载活跃任务戳"""
        if not self.active_stamps_file.exists():
            return {}
        try:
            return json.loads(self.active_stamps_file.read_text())
        except json.JSONDecodeError:
            return {}
    
    def _save_active_stamps(self, stamps: Dict[str, Any]):
        """保存活跃任务戳"""
        self.active_stamps_file.write_text(
            json.dumps(stamps, indent=2, ensure_ascii=False)
        )
    
    def _append_to_history(self, event_data: Dict[str, Any]):
        """追加事件到历史记录"""
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_data, ensure_ascii=False) + "\n")
    
    def generate(
        self,
        mission_name: str,
        target: str,
        operator: str = "shadow_commander",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        生成新的任务戳
        
        格式: SHADOW-{YYYYMMDD}-{HHmmss}-{SHORT_HASH}
        
        Args:
            mission_name: 任务名称
            target: 目标系统/IP
            operator: 操作者名称
            tags: 任务标签
            
        Returns:
            {
                "success": True,
                "stamp": "SHADOW-...",
                "workspace": "/root/pentest_workspace/SHADOW-..."
            }
        """
        timestamp = datetime.now()
        date_str = timestamp.strftime("%Y%m%d")
        time_str = timestamp.strftime("%H%M%S")
        
        # 生成短哈希
        hash_input = f"{mission_name}:{target}:{timestamp.isoformat()}:{os.urandom(4).hex()}"
        short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:4].upper()
        
        stamp = f"SHADOW-{date_str}-{time_str}-{short_hash}"
        
        # 构建元数据
        stamp_data = {
            "stamp": stamp,
            "mission_name": mission_name,
            "target": target,
            "operator": operator,
            "tags": tags or [],
            "created_at": timestamp.isoformat(),
            "unix_timestamp": int(timestamp.timestamp()),
            "status": "active",
            "task_ids": [],
            "findings": [],
            "events": []
        }
        
        # 保存到活跃列表
        active_stamps = self._load_active_stamps()
        active_stamps[stamp] = stamp_data
        self._save_active_stamps(active_stamps)
        
        # 记录历史
        self._append_to_history({
            "event": "stamp_created",
            "timestamp": timestamp.isoformat(),
            **stamp_data
        })
        
        # 创建工作空间
        workspace = workspace_manager.create_workspace(stamp)
        
        return {
            "success": True,
            "stamp": stamp,
            "workspace": str(workspace),
            "message": f"任务戳 {stamp} 已创建"
        }
    
    def get_info(self, stamp: str) -> Dict[str, Any]:
        """获取任务戳信息"""
        active_stamps = self._load_active_stamps()
        
        if stamp not in active_stamps:
            return {
                "success": False,
                "error": f"任务戳 {stamp} 不存在"
            }
        
        return {
            "success": True,
            "data": active_stamps[stamp]
        }
    
    def list_active(self) -> Dict[str, Any]:
        """列出所有活跃任务戳"""
        active_stamps = self._load_active_stamps()
        return {
            "success": True,
            "count": len(active_stamps),
            "stamps": list(active_stamps.keys()),
            "data": active_stamps
        }
    
    def associate_task(self, stamp: str, task_id: str) -> Dict[str, Any]:
        """
        关联任务ID到任务戳
        
        Args:
            stamp: 任务戳
            task_id: 任务ID
        """
        active_stamps = self._load_active_stamps()
        
        if stamp not in active_stamps:
            return {
                "success": False,
                "error": f"任务戳 {stamp} 不存在"
            }
        
        if task_id not in active_stamps[stamp]["task_ids"]:
            active_stamps[stamp]["task_ids"].append(task_id)
            self._save_active_stamps(active_stamps)
        
        self._append_to_history({
            "event": "task_associated",
            "timestamp": datetime.now().isoformat(),
            "stamp": stamp,
            "task_id": task_id
        })
        
        return {
            "success": True,
            "message": f"任务 {task_id} 已关联到 {stamp}"
        }
    
    def add_finding(
        self,
        stamp: str,
        vuln_type: str,
        severity: str,
        description: str,
        evidence: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        记录漏洞发现
        
        Args:
            stamp: 任务戳
            vuln_type: 漏洞类型 (SQLi, XSS, IDOR, etc.)
            severity: 严重程度 (critical, high, medium, low, info)
            description: 描述
            evidence: 证据数据
        """
        active_stamps = self._load_active_stamps()
        
        if stamp not in active_stamps:
            return {
                "success": False,
                "error": f"任务戳 {stamp} 不存在"
            }
        
        finding = {
            "id": f"F{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "type": vuln_type,
            "severity": severity,
            "description": description,
            "evidence": evidence or {}
        }
        
        active_stamps[stamp]["findings"].append(finding)
        self._save_active_stamps(active_stamps)
        
        self._append_to_history({
            "event": "finding_added",
            "stamp": stamp,
            **finding
        })
        
        return {
            "success": True,
            "finding_id": finding["id"],
            "message": f"漏洞发现已记录到 {stamp}"
        }
    
    def add_event(
        self,
        stamp: str,
        event_type: str,
        message: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """添加任务事件"""
        active_stamps = self._load_active_stamps()
        
        if stamp not in active_stamps:
            return {
                "success": False,
                "error": f"任务戳 {stamp} 不存在"
            }
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "data": data or {}
        }
        
        active_stamps[stamp]["events"].append(event)
        self._save_active_stamps(active_stamps)
        
        return {
            "success": True,
            "message": "事件已记录"
        }
    
    def update_status(
        self,
        stamp: str,
        status: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新任务戳状态
        
        Args:
            stamp: 任务戳
            status: 状态 (active, completed, failed, paused)
            notes: 备注
        """
        active_stamps = self._load_active_stamps()
        
        if stamp not in active_stamps:
            return {
                "success": False,
                "error": f"任务戳 {stamp} 不存在"
            }
        
        active_stamps[stamp]["status"] = status
        active_stamps[stamp]["updated_at"] = datetime.now().isoformat()
        
        if notes:
            active_stamps[stamp]["status_notes"] = notes
        
        self._save_active_stamps(active_stamps)
        
        self._append_to_history({
            "event": "status_updated",
            "timestamp": datetime.now().isoformat(),
            "stamp": stamp,
            "status": status,
            "notes": notes
        })
        
        return {
            "success": True,
            "message": f"任务戳 {stamp} 状态已更新为 {status}"
        }
    
    def archive(self, stamp: str) -> Dict[str, Any]:
        """归档任务戳"""
        active_stamps = self._load_active_stamps()
        
        if stamp not in active_stamps:
            return {
                "success": False,
                "error": f"任务戳 {stamp} 不存在"
            }
        
        stamp_data = active_stamps.pop(stamp)
        stamp_data["archived_at"] = datetime.now().isoformat()
        
        self._save_active_stamps(active_stamps)
        
        self._append_to_history({
            "event": "stamp_archived",
            "timestamp": datetime.now().isoformat(),
            **stamp_data
        })
        
        return {
            "success": True,
            "message": f"任务戳 {stamp} 已归档"
        }
    
    def get_history(
        self,
        stamp: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """获取历史记录"""
        if not self.history_file.exists():
            return {"success": True, "history": []}
        
        history = []
        with open(self.history_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if stamp is None or record.get("stamp") == stamp:
                        history.append(record)
                except json.JSONDecodeError:
                    continue
        
        return {
            "success": True,
            "history": history[-limit:]
        }


# 全局实例
stamp_manager = StampManager()
