# -*- coding: utf-8 -*-
"""
Main Agent Node
主代理节点 - Shadow Commander

修复：
1. 添加步数感知，临近上限时提示生成报告
2. 消息裁剪，防止上下文过长导致 API 错误
3. 主代理也使用独立递归限制
"""

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from core.state import PentestState
from core.config_loader import load_prompt
from agents.base_agent import create_model, clean_messages
from tools import MAIN_AGENT_TOOLS
from tools.local_tools import MAIN_AGENT_LOCAL_TOOLS


# 主代理单次调用的递归限制
MAIN_AGENT_RECURSION_LIMIT = 30

# 传入主代理的历史消息最大条数
MAX_HISTORY_MESSAGES = 20

# 步数警告阈值（超过此值开始提示收尾）
STEP_WARNING_THRESHOLD = 60


# ============================================================
# 主代理创建
# ============================================================

def _create_main_agent():
    """创建主代理 ReAct Agent"""
    system_prompt = load_prompt("main_agent")
    model = create_model()
    tools = MAIN_AGENT_TOOLS + MAIN_AGENT_LOCAL_TOOLS

    return create_react_agent(
        model=model,
        tools=tools,
        prompt=system_prompt
    )


_main_agent = None


def get_main_agent():
    """获取主代理单例"""
    global _main_agent
    if _main_agent is None:
        _main_agent = _create_main_agent()
    return _main_agent


def _trim_history(messages: list, max_count: int = MAX_HISTORY_MESSAGES) -> list:
    """
    裁剪消息历史

    策略：保留最近 max_count 条消息，
    确保 HumanMessage 和 AIMessage 配对完整
    """
    if len(messages) <= max_count:
        return messages

    # 只保留最近的消息
    trimmed = messages[-max_count:]

    # 确保第一条不是 ToolMessage（会导致 API 错误）
    while trimmed and isinstance(trimmed[0], (type(None),)):
        trimmed = trimmed[1:]

    # 如果第一条是 ToolMessage，在前面加一个说明
    from langchain_core.messages import ToolMessage as TM
    if trimmed and isinstance(trimmed[0], TM):
        trimmed = [AIMessage(content="（前序消息已省略）")] + trimmed

    return trimmed


def main_agent_node(state: PentestState) -> dict:
    """
    主代理节点

    职责：
    1. 分析当前状态
    2. 决定下一步行动（委派哪个子代理）
    3. 更新任务账本
    """
    agent = get_main_agent()
    step_count = state.get("step_count", 0)

    print(f"[main_agent] 第 {step_count} 步决策")

    # 构造上下文消息
    context = _build_context_message(state)

    # 准备输入并清理消息
    input_messages = list(state.get("messages", []))

    # 裁剪历史消息，防止上下文过长
    input_messages = _trim_history(input_messages)

    if context:
        input_messages = [HumanMessage(content=context)] + input_messages

    # 清理消息，避免 API 错误
    input_messages = clean_messages(input_messages)

    # ============================================================
    # 关键修复：主代理也使用独立递归限制
    # ============================================================
    try:
        result = agent.invoke(
            {"messages": input_messages},
            {"recursion_limit": MAIN_AGENT_RECURSION_LIMIT}
        )
    except Exception as e:
        error_str = str(e)
        if "recursion" in error_str.lower() or "more steps" in error_str.lower():
            print(f"[main_agent] ⚠️ 主代理达到递归限制，强制生成报告")
            return {
                "messages": [AIMessage(content="主代理工具调用次数已达上限，生成报告。\n[NEXT: report]")],
                "next_agent": "report"
            }
        raise

    # 解析主代理的决策
    next_agent = _parse_decision(result, state)

    return {
        "messages": result["messages"],
        "next_agent": next_agent
    }


def _build_context_message(state: PentestState) -> str:
    """构建上下文信息"""
    parts = []
    step_count = state.get("step_count", 0)

    # 基本信息
    parts.append(f"## 当前状态")
    parts.append(f"- 任务戳: {state.get('stamp', '未生成')}")
    parts.append(f"- 目标: {state.get('target', '未指定')}")
    parts.append(f"- 阶段: {state.get('current_phase', 'init')}")
    parts.append(f"- 当前步数: {step_count}")

    # 步数警告
    if step_count >= STEP_WARNING_THRESHOLD:
        remaining = 80 - step_count  # MAX_TOTAL_STEPS from graph.py
        parts.append(f"\n## ⚠️ 步数警告")
        parts.append(f"已执行 {step_count} 步，剩余约 {remaining} 步。")
        parts.append(f"**请尽快完成测试并生成报告！建议 [NEXT: report]**")

    # 侦察结果（截断过长内容）
    if state.get("recon_results"):
        recon_str = str(state['recon_results'])
        if len(recon_str) > 1000:
            recon_str = recon_str[:1000] + "\n... (截断)"
        parts.append(f"\n## 侦察结果")
        parts.append(recon_str)

    # 已发现的漏洞
    if state.get("findings"):
        parts.append(f"\n## 已发现漏洞: {len(state['findings'])} 个")
        for f in state["findings"][:5]:  # 最多显示5个
            parts.append(f"- [{f['severity']}] {f['vuln_type']}: {f['description'][:80]}...")

    # 任务历史（只显示最近3个）
    if state.get("task_history"):
        parts.append(f"\n## 最近任务")
        for t in state["task_history"][-3:]:
            parts.append(f"- {t['task_id']}: {t['status']}")

    parts.append("\n## 请决定下一步行动")
    parts.append("在回复末尾，用 [NEXT: xxx] 格式指定：")
    parts.append("- [NEXT: recon] - 侦察专家")
    parts.append("- [NEXT: input_vuln] - 输入漏洞专家")
    parts.append("- [NEXT: access_logic] - 访问控制专家")
    parts.append("- [NEXT: report] - 生成报告")
    parts.append("- [NEXT: end] - 结束")

    return "\n".join(parts)


def _parse_decision(result: dict, state: PentestState) -> str:
    """解析主代理的决策"""
    messages = result.get("messages", [])

    # 检查是否已经发现 flag
    import re
    for msg in messages:
        if isinstance(msg, AIMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            flag_patterns = [
                r'flag\{[^}]+\}',
                r'FLAG\{[^}]+\}',
                r'ctf\{[^}]+\}',
                r'CTF\{[^}]+\}',
            ]
            for pattern in flag_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return "report"

    # 检查 <END_MISSION_REASON> 标记
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if '<END_MISSION_REASON>' in content:
                return "report"
            break

    # 从最后一条 AI 消息中提取 [NEXT: xxx]
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)

            match = re.search(r'\[NEXT:\s*(\w+)\]', content, re.IGNORECASE)
            if match:
                decision = match.group(1).lower()
                valid_decisions = ["recon", "input_vuln", "access_logic", "knowledge", "report", "end"]
                if decision in valid_decisions:
                    return decision
            break

    # 默认逻辑
    phase = state.get("current_phase", "init")
    if phase == "init":
        return "recon"
    elif phase == "recon":
        return "input_vuln"
    elif phase == "vuln_test":
        return "access_logic"
    elif phase == "access_test":
        return "report"
    else:
        return "end"
