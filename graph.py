# -*- coding: utf-8 -*-
"""
Pentest Graph
渗透测试状态图 - 主入口

修复：递归限制问题
- 提高外层 recursion_limit
- 子代理使用独立编译图（隔离递归计数）
- 添加步数追踪和安全退出机制
"""

import os
from dotenv import load_dotenv

load_dotenv()

from typing import Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from core.state import PentestState
from core.config_loader import config_loader


# ============================================================
# 递归限制配置
# ============================================================

# 外层图的递归限制（节点跳转次数上限）
# 每次 main_agent → subagent → main_agent 大约消耗 3 次
# 支持约 50 轮交互
OUTER_GRAPH_RECURSION_LIMIT = 150

# 子代理内部的递归限制（每个子代理单次调用内的工具调用次数上限）
# 每次工具调用消耗约 2 次（LLM + tool_result）
# 允许子代理单次调用中使用约 15 个工具
SUBAGENT_RECURSION_LIMIT = 40

# 最大总步数（安全阀，防止无限循环）
MAX_TOTAL_STEPS = 80


# ============================================================
# 模式判断
# ============================================================

def is_knowledge_enabled() -> bool:
    """检查是否启用知识库"""
    mode = os.getenv("MODE", "ctf").lower()
    if mode == "ctf":
        return False
    knowledge_config = config_loader.system.get("knowledge", {})
    return str(knowledge_config.get("enabled", "false")).lower() == "true"


KNOWLEDGE_ENABLED = is_knowledge_enabled()


# ============================================================
# 节点函数
# ============================================================

def parse_target_from_messages(state: PentestState) -> PentestState:
    """从用户消息中解析目标"""
    messages = state.get("messages", [])
    target = state.get("target", "")
    mission_name = state.get("mission_name", "渗透测试任务")

    if not target and messages:
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage) or (hasattr(msg, 'type') and msg.type == 'human'):
                content = msg.content if hasattr(msg, 'content') else str(msg)

                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, str):
                            text_parts.append(part)
                        elif isinstance(part, dict) and 'text' in part:
                            text_parts.append(part['text'])
                    content = ' '.join(text_parts)

                target = content.strip() if isinstance(content, str) else str(content).strip()
                break

    return {
        "target": target,
        "mission_name": mission_name
    }


def should_continue_after_init(state: PentestState) -> Literal["main_agent", "end"]:
    """初始化后的路由"""
    if state.get("error"):
        return "end"
    return "main_agent"


def route_from_main_agent(state: PentestState) -> str:
    """
    主代理决策路由

    增加：步数检查，防止无限循环
    """
    # 0. 步数安全阀
    step_count = state.get("step_count", 0)
    if step_count >= MAX_TOTAL_STEPS:
        print(f"[Graph] 达到最大步数 {MAX_TOTAL_STEPS}，强制生成报告")
        return "report"

    # 1. 首先检查 mission_complete 标志
    if state.get("mission_complete"):
        return "report"

    # 2. 获取 main_agent 的决策
    next_agent = state.get("next_agent", "end")

    # CTF 模式不支持 knowledge
    if KNOWLEDGE_ENABLED:
        valid_routes = ["recon", "input_vuln", "access_logic", "knowledge", "report", "end"]
    else:
        valid_routes = ["recon", "input_vuln", "access_logic", "report", "end"]
        if next_agent == "knowledge":
            return "input_vuln"

    if next_agent not in valid_routes:
        return "end"

    return next_agent


def route_after_subagent(state: PentestState) -> str:
    """子代理完成后的路由"""
    if state.get("mission_complete"):
        return "report"
    return "main_agent"


def increment_step_counter(state: PentestState) -> dict:
    """步数计数器节点 - 在每次进入 main_agent 前递增"""
    current = state.get("step_count", 0)
    return {"step_count": current + 1}


# ============================================================
# 构建图
# ============================================================

def build_graph() -> StateGraph:
    """
    构建渗透测试状态图

    关键改进：
    1. 子代理节点内部使用独立的 .invoke() 调用，隔离递归计数
    2. 添加 step_counter 节点追踪总步数
    3. 提高 recursion_limit 到 150
    """
    from nodes import (
        init_node,
        main_agent_node,
        recon_agent_node,
        input_vuln_agent_node,
        access_logic_agent_node,
        report_node,
    )

    workflow = StateGraph(PentestState)

    # ============================================================
    # 添加节点
    # ============================================================

    workflow.add_node("parse_input", parse_target_from_messages)
    workflow.add_node("init", init_node)
    workflow.add_node("step_counter", increment_step_counter)
    workflow.add_node("main_agent", main_agent_node)
    workflow.add_node("recon", recon_agent_node)
    workflow.add_node("input_vuln", input_vuln_agent_node)
    workflow.add_node("access_logic", access_logic_agent_node)
    workflow.add_node("report", report_node)

    if KNOWLEDGE_ENABLED:
        from nodes import knowledge_agent_node
        workflow.add_node("knowledge", knowledge_agent_node)

    # ============================================================
    # 设置入口
    # ============================================================

    workflow.set_entry_point("parse_input")

    # ============================================================
    # 添加边
    # ============================================================

    workflow.add_edge("parse_input", "init")

    workflow.add_conditional_edges(
        "init",
        should_continue_after_init,
        {
            "main_agent": "step_counter",
            "end": END
        }
    )

    # step_counter → main_agent（每次进入 main_agent 前计数）
    workflow.add_edge("step_counter", "main_agent")

    # main_agent 的路由
    if KNOWLEDGE_ENABLED:
        route_map = {
            "recon": "recon",
            "input_vuln": "input_vuln",
            "access_logic": "access_logic",
            "knowledge": "knowledge",
            "report": "report",
            "end": END
        }
    else:
        route_map = {
            "recon": "recon",
            "input_vuln": "input_vuln",
            "access_logic": "access_logic",
            "report": "report",
            "end": END
        }

    workflow.add_conditional_edges(
        "main_agent",
        route_from_main_agent,
        route_map
    )

    # 子代理完成后：经过 step_counter 回到 main_agent
    subagent_route_map = {
        "main_agent": "step_counter",  # 改为先经过 step_counter
        "report": "report"
    }

    workflow.add_conditional_edges("recon", route_after_subagent, subagent_route_map)
    workflow.add_conditional_edges("input_vuln", route_after_subagent, subagent_route_map)
    workflow.add_conditional_edges("access_logic", route_after_subagent, subagent_route_map)

    if KNOWLEDGE_ENABLED:
        workflow.add_conditional_edges("knowledge", route_after_subagent, subagent_route_map)

    workflow.add_edge("report", END)

    return workflow


def create_graph():
    """创建并编译图"""
    workflow = build_graph()
    return workflow.compile()


# 打印当前模式
_mode = os.getenv("MODE", "ctf")
print(f"[PentestAgent] 模式: {_mode.upper()}, 知识库: {'启用' if KNOWLEDGE_ENABLED else '禁用'}")
print(f"[PentestAgent] 递归限制: 外层={OUTER_GRAPH_RECURSION_LIMIT}, 子代理={SUBAGENT_RECURSION_LIMIT}, 最大步数={MAX_TOTAL_STEPS}")

# 导出编译后的图
graph = create_graph()


# ============================================================
# 便捷运行函数
# ============================================================

def run_pentest(target: str, mission_name: str = "渗透测试任务"):
    """运行渗透测试"""
    from core.state import create_initial_state

    initial_state = create_initial_state(target, mission_name)
    # 关键修复：大幅提高递归限制
    final_state = graph.invoke(
        initial_state,
        {"recursion_limit": OUTER_GRAPH_RECURSION_LIMIT}
    )

    return final_state


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python graph.py <目标地址>")
        sys.exit(1)

    target = sys.argv[1]
    print(f"开始渗透测试: {target}")

    result = run_pentest(target)

    print("\n" + "=" * 60)
    print("任务完成")
    print("=" * 60)
    print(f"任务戳: {result.get('stamp')}")
    print(f"发现漏洞: {len(result.get('findings', []))} 个")
