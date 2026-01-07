#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Runner
工具运行器
"""

import json
import time
import traceback
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from .loader import get_loader, ToolConfig


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    tool_id: str
    data: Optional[Dict] = None
    error: Optional[str] = None
    flag: Optional[str] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ToolRunner:
    """工具运行器"""
    
    def __init__(self, workspace_root: str = "/root/pentest_workspace"):
        self.workspace_root = Path(workspace_root)
        self.loader = get_loader()
    
    def run(self, tool_id: str, params: dict, stamp: str = None) -> ToolResult:
        """
        运行工具
        
        Args:
            tool_id: 工具 ID（如 recon/port_scan）
            params: 参数字典
            stamp: 任务戳（用于记录日志）
        
        Returns:
            执行结果
        """
        start_time = time.time()
        
        # 获取工具配置
        tool = self.loader.get_tool(tool_id)
        if not tool:
            return ToolResult(
                success=False,
                tool_id=tool_id,
                error=f"工具不存在: {tool_id}"
            )
        
        # 验证参数
        validation_error = self._validate_params(tool, params)
        if validation_error:
            return ToolResult(
                success=False,
                tool_id=tool_id,
                error=validation_error
            )
        
        # 填充默认值
        full_params = self._fill_defaults(tool, params)
        
        # 加载模块并执行
        module = self.loader.load_tool_module(tool_id)
        if not module:
            return ToolResult(
                success=False,
                tool_id=tool_id,
                error=f"无法加载工具模块: {tool_id}"
            )
        
        if not hasattr(module, 'run'):
            return ToolResult(
                success=False,
                tool_id=tool_id,
                error=f"工具缺少 run 函数: {tool_id}"
            )
        
        try:
            # 执行工具
            result = module.run(**full_params)
            execution_time = time.time() - start_time
            
            # 提取 flag
            flag = None
            if isinstance(result, dict):
                flag = result.get('flag')
            
            # 记录日志
            if stamp:
                self._log_execution(stamp, tool_id, full_params, result, flag)
            
            return ToolResult(
                success=True,
                tool_id=tool_id,
                data=result,
                flag=flag,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            
            return ToolResult(
                success=False,
                tool_id=tool_id,
                error=str(e),
                execution_time=execution_time
            )
    
    def _validate_params(self, tool: ToolConfig, params: dict) -> Optional[str]:
        """验证参数"""
        for name, param_def in tool.params.items():
            if param_def.get('required', False) and name not in params:
                return f"缺少必要参数: {name}"
            
            if name in params:
                value = params[name]
                expected_type = param_def.get('type', 'string')
                
                # 类型检查
                if expected_type == 'integer' and not isinstance(value, int):
                    try:
                        int(value)
                    except:
                        return f"参数 {name} 应为整数"
                
                if expected_type == 'float' and not isinstance(value, (int, float)):
                    try:
                        float(value)
                    except:
                        return f"参数 {name} 应为数字"
                
                # 枚举检查
                if 'enum' in param_def and value not in param_def['enum']:
                    return f"参数 {name} 的值必须是 {param_def['enum']} 之一"
                
                # 范围检查
                if 'min' in param_def:
                    if isinstance(value, (int, float)) and value < param_def['min']:
                        return f"参数 {name} 不能小于 {param_def['min']}"
                
                if 'max' in param_def:
                    if isinstance(value, (int, float)) and value > param_def['max']:
                        return f"参数 {name} 不能大于 {param_def['max']}"
        
        return None
    
    def _fill_defaults(self, tool: ToolConfig, params: dict) -> dict:
        """填充默认值"""
        full_params = {}
        
        for name, param_def in tool.params.items():
            if name in params:
                value = params[name]
                # 类型转换
                expected_type = param_def.get('type', 'string')
                if expected_type == 'integer':
                    value = int(value)
                elif expected_type == 'float':
                    value = float(value)
                elif expected_type == 'boolean':
                    value = str(value).lower() in ('true', '1', 'yes')
                full_params[name] = value
            elif 'default' in param_def:
                full_params[name] = param_def['default']
        
        return full_params
    
    def _log_execution(self, stamp: str, tool_id: str, params: dict, result: dict, flag: str):
        """记录执行日志"""
        workspace = self.workspace_root / stamp
        workspace.mkdir(parents=True, exist_ok=True)
        
        log_file = workspace / "tool_logs.jsonl"
        
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tool_id": tool_id,
            "params": params,
            "success": True,
            "flag": flag
        }
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        # 如果发现 flag，单独记录
        if flag:
            flag_file = workspace / "FLAG_FOUND.txt"
            with open(flag_file, 'a', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {tool_id}: {flag}\n")


# 全局运行器
_runner: Optional[ToolRunner] = None


def get_runner() -> ToolRunner:
    """获取全局运行器"""
    global _runner
    if _runner is None:
        _runner = ToolRunner()
    return _runner


def run_tool(tool_id: str, params: dict, stamp: str = None) -> dict:
    """便捷函数：运行工具"""
    runner = get_runner()
    result = runner.run(tool_id, params, stamp)
    return result.to_dict()
