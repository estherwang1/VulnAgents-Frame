# -*- coding: utf-8 -*-
"""
Toolbox Handlers
工具库处理函数
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# 添加 toolbox 路径
TOOLBOX_PATH = Path("/root/mcp-agent/toolbox")
if TOOLBOX_PATH.exists():
    sys.path.insert(0, str(TOOLBOX_PATH))


async def handle_list_tools(category: str = None, tag: str = None) -> Dict[str, Any]:
    """列出可用工具"""
    try:
        from toolbox import list_tools
        result = list_tools(category=category, tag=tag)
        return result
    except ImportError:
        return {
            "success": False,
            "error": "工具库未安装，请检查 /root/mcp-agent/toolbox"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_get_tool_schema(tool_id: str) -> Dict[str, Any]:
    """获取工具 schema"""
    try:
        from toolbox import get_tool_schema
        result = get_tool_schema(tool_id)
        return result
    except ImportError:
        return {"success": False, "error": "工具库未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_run_tool(stamp: str, tool_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """运行工具"""
    try:
        from toolbox import run_tool
        result = run_tool(tool_id, params, stamp)
        return result
    except ImportError:
        return {"success": False, "error": "工具库未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# 别名（兼容配置中的 handler 路径）
list_tools = handle_list_tools
get_tool_schema = handle_get_tool_schema
run_tool = handle_run_tool
