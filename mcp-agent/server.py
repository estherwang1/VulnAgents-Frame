# -*- coding: utf-8 -*-
"""
MCP Server - Main Entry Point
配置化的 MCP 服务器
"""

import json
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import ServerConfig
from config.loader import get_config, reload_config
from router import get_router


# ============================================================
# 初始化
# ============================================================

config = get_config()
router = get_router()


# ============================================================
# FastAPI 应用
# ============================================================

app = FastAPI(
    title=config.server.get('name', 'MCP Server'),
    description="配置化的渗透测试 MCP 服务器",
    version=config.server.get('version', '2.0.0')
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MCP 端点
# ============================================================

@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    x_api_key: str = Header(None, alias="X-API-key")
):
    """
    MCP JSON-RPC 端点
    """
    # 1. 认证
    if x_api_key != ServerConfig.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    # 2. 解析请求
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    msg_id = body.get("id")
    method = body.get("method")
    
    # 3. 工具发现
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": config.get_mcp_definitions()
            }
        }
    
    # 4. 工具调用
    if method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        # 路由到处理函数
        result = await router.route(tool_name, args)
        
        # 格式化响应
        if isinstance(result, dict):
            text = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            text = str(result)
        
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [{"type": "text", "text": text}]
            }
        }
    
    # 5. 未知方法
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    }


# ============================================================
# 管理端点
# ============================================================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": config.server.get('version', '2.0.0'),
        "tools_count": len(config.tools)
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": config.server.get('name', 'MCP Server'),
        "version": config.server.get('version', '2.0.0'),
        "endpoints": {
            "mcp": "/mcp (POST)",
            "health": "/health (GET)",
            "tools": "/tools (GET)",
            "reload": "/reload (POST)"
        }
    }


@app.get("/tools")
async def list_tools():
    """列出所有工具（调试用）"""
    tools_by_group = {}
    
    for tool in config.tools.values():
        group = tool.group
        if group not in tools_by_group:
            group_info = config.groups.get(group, {})
            tools_by_group[group] = {
                "name": group_info.get('name', group),
                "description": group_info.get('description', ''),
                "tools": []
            }
        
        tools_by_group[group]["tools"].append({
            "name": tool.name,
            "description": tool.description,
            "handler": tool.handler
        })
    
    return {
        "groups": tools_by_group,
        "total": len(config.tools)
    }


@app.post("/reload")
async def reload_configuration(
    x_api_key: str = Header(None, alias="X-API-key")
):
    """重新加载配置"""
    if x_api_key != ServerConfig.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    global config, router
    config = reload_config()
    router = get_router()
    
    return {
        "success": True,
        "message": "配置已重新加载",
        "tools_count": len(config.tools)
    }


# ============================================================
# 启动
# ============================================================


if __name__ == "__main__":
    # 打印配置信息
    ServerConfig.print_config()
    print(f"  Tools: {len(config.tools)}")
    print("-" * 60)
    
    # 按分组显示工具
    for group_name, group_info in config.groups.items():
        tools = config.get_tools_by_group(group_name)
        if tools:
            print(f"  [{group_info.get('name', group_name)}]")
            for tool in tools:
                print(f"    - {tool.name}")
    
    print("=" * 60)
    
    uvicorn.run(
        app,
        host=ServerConfig.HOST,
        port=ServerConfig.PORT
    )
