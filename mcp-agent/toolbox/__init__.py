# -*- coding: utf-8 -*-
"""
Pentest Toolbox
渗透测试工具库

配置化、参数化的工具管理系统。

使用方式:
    from toolbox import list_tools, run_tool, get_tool_schema
    
    # 列出工具
    tools = list_tools()
    
    # 运行工具
    result = run_tool("recon/port_scan", {"target": "192.168.1.1"})
    
    # 获取工具 schema
    schema = get_tool_schema("sqli/detect")
"""

from .engine import (
    ToolLoader,
    ToolConfig,
    get_loader,
    ToolRunner,
    ToolResult,
    get_runner,
    run_tool,
)

from .api import (
    ToolboxAPI,
    get_api,
    mcp_list_tools,
    mcp_get_tool_schema,
    mcp_get_tools_summary,
    mcp_run_tool,
)


def list_tools(category: str = None, tag: str = None) -> dict:
    """列出可用工具"""
    return get_api().list_tools(category, tag)


def get_tool_schema(tool_id: str) -> dict:
    """获取工具 schema"""
    return get_api().get_tool_schema(tool_id)


def get_tools_summary() -> str:
    """获取工具摘要（Markdown）"""
    result = get_api().get_tools_summary()
    return result.get('summary', '')


__all__ = [
    # 核心函数
    "list_tools",
    "run_tool",
    "get_tool_schema",
    "get_tools_summary",
    # 引擎
    "ToolLoader",
    "ToolConfig",
    "get_loader",
    "ToolRunner",
    "ToolResult",
    "get_runner",
    # API
    "ToolboxAPI",
    "get_api",
    # MCP 接口
    "mcp_list_tools",
    "mcp_get_tool_schema",
    "mcp_get_tools_summary",
    "mcp_run_tool",
]
