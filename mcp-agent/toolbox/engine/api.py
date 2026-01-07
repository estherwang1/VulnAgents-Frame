#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Toolbox API
MCP Server 工具库接口
"""

import json
from pathlib import Path
from typing import Optional

from engine import get_loader, get_runner, reload_tools


class ToolboxAPI:
    """工具库 API"""
    
    def __init__(self):
        self.loader = get_loader()
        self.runner = get_runner()
    
    def list_tools(self, category: str = None, tag: str = None) -> dict:
        """
        列出可用工具
        
        Args:
            category: 按分类过滤
            tag: 按标签过滤
        
        Returns:
            工具列表
        """
        all_tools = self.loader.list_tools()
        
        if category or tag:
            filtered = {}
            for tool_id, info in all_tools.items():
                if category and info['category'] != category:
                    continue
                if tag and tag not in info.get('tags', []):
                    continue
                filtered[tool_id] = info
            return {
                "success": True,
                "tools": filtered,
                "count": len(filtered)
            }
        
        return {
            "success": True,
            "tools": all_tools,
            "count": len(all_tools)
        }
    
    def get_tool_schema(self, tool_id: str) -> dict:
        """
        获取工具详细信息
        
        Args:
            tool_id: 工具 ID
        
        Returns:
            工具 schema
        """
        schema = self.loader.get_tool_schema(tool_id)
        if schema:
            return {
                "success": True,
                "schema": schema
            }
        return {
            "success": False,
            "error": f"工具不存在: {tool_id}"
        }
    
    def get_tools_summary(self) -> dict:
        """
        获取工具摘要（Markdown 格式，适合给 LLM）
        
        Returns:
            工具摘要
        """
        summary = self.loader.get_tools_summary()
        return {
            "success": True,
            "summary": summary
        }
    
    def run_tool(self, tool_id: str, params: dict, stamp: str = None) -> dict:
        """
        运行工具
        
        Args:
            tool_id: 工具 ID
            params: 参数
            stamp: 任务戳
        
        Returns:
            执行结果
        """
        result = self.runner.run(tool_id, params, stamp)
        return result.to_dict()
    
    def reload(self) -> dict:
        """
        重新加载所有工具
        
        Returns:
            重载结果
        """
        count = reload_tools()
        # 更新本地引用
        self.loader = get_loader()
        return {
            "success": True,
            "message": f"已重新加载 {count} 个工具",
            "count": count
        }


# 全局 API 实例
_api: Optional[ToolboxAPI] = None


def get_api() -> ToolboxAPI:
    """获取全局 API"""
    global _api
    if _api is None:
        _api = ToolboxAPI()
    return _api


# ============================================================
# MCP 接口函数（供 MCP Server 调用）
# ============================================================

def mcp_list_tools(category: str = None, tag: str = None) -> str:
    """MCP: 列出工具"""
    result = get_api().list_tools(category, tag)
    return json.dumps(result, ensure_ascii=False)


def mcp_get_tool_schema(tool_id: str) -> str:
    """MCP: 获取工具 schema"""
    result = get_api().get_tool_schema(tool_id)
    return json.dumps(result, ensure_ascii=False)


def mcp_get_tools_summary() -> str:
    """MCP: 获取工具摘要"""
    result = get_api().get_tools_summary()
    return json.dumps(result, ensure_ascii=False)


def mcp_run_tool(stamp: str, tool_id: str, params: dict) -> str:
    """MCP: 运行工具"""
    result = get_api().run_tool(tool_id, params, stamp)
    return json.dumps(result, ensure_ascii=False)


def mcp_reload_tools() -> str:
    """MCP: 重新加载工具"""
    result = get_api().reload()
    return json.dumps(result, ensure_ascii=False)


# ============================================================
# 命令行测试
# ============================================================

if __name__ == "__main__":
    import sys
    
    api = get_api()
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python api.py list                    # 列出工具")
        print("  python api.py list <category>         # 按分类列出")
        print("  python api.py schema <tool_id>        # 查看工具")
        print("  python api.py run <tool_id> <params>  # 运行工具")
        print("  python api.py reload                  # 重新加载工具")
        print()
        print("示例:")
        print("  python api.py list")
        print("  python api.py list recon")
        print("  python api.py schema recon/port_scan")
        print('  python api.py run recon/port_scan \'{"target": "127.0.0.1"}\'')
        print("  python api.py reload")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        category = sys.argv[2] if len(sys.argv) > 2 else None
        result = api.list_tools(category=category)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif cmd == "summary":
        result = api.get_tools_summary()
        print(result['summary'])
    
    elif cmd == "schema":
        if len(sys.argv) < 3:
            print("需要指定 tool_id")
            sys.exit(1)
        result = api.get_tool_schema(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif cmd == "run":
        if len(sys.argv) < 4:
            print("需要指定 tool_id 和 params")
            sys.exit(1)
        tool_id = sys.argv[2]
        params = json.loads(sys.argv[3])
        result = api.run_tool(tool_id, params)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif cmd == "reload":
        result = api.reload()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
