# -*- coding: utf-8 -*-
"""
Tool Router
工具路由器 - 根据配置自动路由到处理函数
"""

import importlib
from typing import Dict, Any, Callable, Optional
from config.loader import get_config, ToolConfig


class ToolRouter:
    """工具路由器"""
    
    def __init__(self):
        self.config = get_config()
        self._handlers: Dict[str, Callable] = {}
        self._load_handlers()
    
    def _load_handlers(self):
        """加载所有处理函数"""
        for tool_name, tool_config in self.config.tools.items():
            handler_path = tool_config.handler
            if not handler_path:
                continue
            
            try:
                handler = self._resolve_handler(handler_path)
                if handler:
                    self._handlers[tool_name] = handler
            except Exception as e:
                print(f"加载处理函数失败 {tool_name}: {e}")
    
    def _resolve_handler(self, handler_path: str) -> Optional[Callable]:
        """
        解析处理函数路径
        
        格式: module.function 或 module.submodule.function
        例如: stamp.generate_stamp -> handlers.stamp.handle_generate_stamp
        """
        parts = handler_path.split('.')
        if len(parts) < 2:
            return None
        
        module_name = parts[0]
        func_name = parts[-1]
        
        # 尝试导入模块
        try:
            # 首先尝试从 handlers 包导入
            module = importlib.import_module(f"handlers.{module_name}")
            
            # 查找处理函数（支持多种命名方式）
            for name_pattern in [
                f"handle_{func_name}",
                func_name,
                f"handle_{module_name}_{func_name}"
            ]:
                if hasattr(module, name_pattern):
                    return getattr(module, name_pattern)
            
        except ImportError:
            pass
        
        return None
    
    def get_handler(self, tool_name: str) -> Optional[Callable]:
        """获取处理函数"""
        return self._handlers.get(tool_name)
    
    def has_tool(self, tool_name: str) -> bool:
        """检查工具是否存在"""
        return tool_name in self._handlers
    
    async def route(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        路由工具调用
        
        Args:
            tool_name: 工具名称
            args: 参数
            
        Returns:
            执行结果
        """
        # 1. 检查工具是否存在
        tool_config = self.config.get_tool(tool_name)
        if not tool_config:
            return {"success": False, "error": f"未知工具: {tool_name}"}
        
        # 2. 验证参数
        valid, error = self.config.validate_params(tool_name, args)
        if not valid:
            return {"success": False, "error": error}
        
        # 3. 填充默认值
        args = self.config.fill_defaults(tool_name, args)
        
        # 4. 安全检查（如果需要）
        if tool_config.security.get('require_whitelist'):
            command = args.get('command', '')
            is_safe, reason = self.config.is_command_safe(command)
            if not is_safe:
                return {"success": False, "error": f"安全拦截: {reason}"}
        
        # 5. 获取处理函数
        handler = self.get_handler(tool_name)
        if not handler:
            return {"success": False, "error": f"处理函数未实现: {tool_name}"}
        
        # 6. 调用处理函数
        try:
            result = await handler(**args)
            return result
        except TypeError as e:
            # 参数不匹配
            return {"success": False, "error": f"参数错误: {e}"}
        except Exception as e:
            return {"success": False, "error": f"执行错误: {e}"}


# 全局路由器
_router: Optional[ToolRouter] = None


def get_router() -> ToolRouter:
    """获取全局路由器"""
    global _router
    if _router is None:
        _router = ToolRouter()
    return _router
