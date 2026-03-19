# -*- coding: utf-8 -*-
"""
Subagent Nodes
子代理节点

关键修复：
1. 子代理使用独立的 recursion_limit，不与外层图共享计数器
2. 添加重试和超时保护
3. 消息裁剪，避免上下文过长
"""

import re
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from core.state import PentestState
from core.config_loader import load_prompt
from agents.base_agent import create_model, clean_messages
from tools import SUBAGENT_TOOLS, RECON_TOOLS
from tools.local_tools import read_local_file
from tools.mission_control import end_mission, MISSION_CONTROL_TOOLS


# 子代理内部递归限制（独立于外层图）
# 每次工具调用 ≈ 2 次递归（LLM决策 + 工具执行）
# 40 次 ≈ 允许 ~18 个工具调用
SUBAGENT_RECURSION_LIMIT = 40

# 传入子代理的历史消息最大条数（防止上下文爆炸）
MAX_CONTEXT_MESSAGES = 10


# ============================================================
# 子代理创建
# ============================================================

_agents_cache = {}


def _get_or_create_agent(agent_name: str, tools: list):
    """获取或创建子代理"""
    cache_key = f"{agent_name}_{len(tools)}"
    if cache_key not in _agents_cache:
        system_prompt = load_prompt(agent_name)
        model = create_model()
        _agents_cache[cache_key] = create_react_agent(
            model=model,
            tools=tools,
            prompt=system_prompt
        )
    return _agents_cache[cache_key]


def _check_end_mission(messages: list) -> tuple:
    """
    检查消息中是否有 end_mission 工具调用

    Returns:
        (mission_complete, reason)
    """
    for msg in messages:
        # 检查 ToolMessage
        if isinstance(msg, ToolMessage):
            if hasattr(msg, 'name') and msg.name == 'end_mission':
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                if "原因:" in content:
                    reason = content.split("原因:")[-1].strip()
                    return True, reason
                return True, "子代理请求结束任务"

        # 检查 AIMessage 的 tool_calls
        if isinstance(msg, AIMessage):
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None)
                    if tool_name == 'end_mission':
                        args = tc.get('args', {}) if isinstance(tc, dict) else getattr(tc, 'args', {})
                        reason = args.get('reason', '子代理请求结束任务')
                        return True, reason

    return False, ""


def _check_end_mission_marker(messages: list) -> tuple:
    """
    检查消息中是否有 <END_MISSION_REASON> 文本标记（兜底机制）

    Returns:
        (mission_complete, reason)
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            match = re.search(r'<END_MISSION_REASON>(.*?)</END_MISSION_REASON>', content, re.DOTALL)
            if match:
                return True, match.group(1).strip()
    return False, ""


def _trim_messages(messages: list, max_count: int = MAX_CONTEXT_MESSAGES) -> list:
    """
    裁剪消息列表，只保留最近的 N 条

    保留策略：
    - 始终保留第一条消息（任务指令）
    - 保留最近的 max_count 条消息
    """
    if len(messages) <= max_count + 1:
        return messages

    # 保留第一条 + 最近 N 条
    return [messages[0]] + messages[-(max_count):]


def _invoke_subagent(agent_name: str, tools: list, state: PentestState, task_prompt: str) -> dict:
    """
    调用子代理的通用逻辑

    关键改进：
    1. 子代理 .invoke() 使用独立的 recursion_limit，
       不消耗外层图的递归计数
    2. 捕获 GraphRecursionError 并优雅降级
    3. 消息裁剪防止上下文溢出

    Args:
        agent_name: 代理名称
        tools: 工具列表
        state: 当前状态
        task_prompt: 任务提示

    Returns:
        状态更新
    """
    # 添加 end_mission 工具到工具列表
    all_tools = tools + MISSION_CONTROL_TOOLS

    agent = _get_or_create_agent(agent_name, all_tools)

    # 构造任务消息
    task_message = HumanMessage(content=f"""
## 任务指令

任务戳: {state.get('stamp', '未知')}
目标: {state.get('target', '未知')}

{task_prompt}

## ⚠️ 重要提示

1. 如果你认为任务已完成（找到 flag、获取敏感数据、验证漏洞成功等），
   请调用 `end_mission(reason)` 工具结束任务。

2. 如果任务未完成，正常汇报你的发现，指挥官会决定下一步。

3. **效率提示**: 优先使用预装工具（run_tool），尽量减少工具调用次数。
   每次调用都有成本，请合理规划。

请执行任务。
""")

    # 清理消息
    messages = clean_messages([task_message])

    # ============================================================
    # 关键修复：子代理使用独立的 recursion_limit
    # ============================================================
    try:
        result = agent.invoke(
            {"messages": messages},
            {"recursion_limit": SUBAGENT_RECURSION_LIMIT}
        )
    except Exception as e:
        error_str = str(e)

        # 检查是否是递归限制错误
        if "recursion" in error_str.lower() or "more steps" in error_str.lower():
            print(f"[{agent_name}] ⚠️ 子代理达到递归限制 ({SUBAGENT_RECURSION_LIMIT})，优雅退出")
            return {
                "messages": [AIMessage(content=f"""
## ⚠️ {agent_name} 工具调用次数已达上限

子代理在当前回合中使用了过多工具调用，已自动停止。
这通常意味着需要更精确的测试策略。

请指挥官决定下一步：
- 重新委派该子代理（使用更精确的指令）
- 委派其他子代理
- 生成报告

[NEXT: report]
""")],
            }
        else:
            # 其他错误
            print(f"[{agent_name}] ❌ 子代理执行出错: {error_str}")
            return {
                "messages": [AIMessage(content=f"子代理 {agent_name} 执行出错: {error_str}")],
            }

    # 检查是否调用了 end_mission（工具调用方式）
    result_messages = result.get("messages", [])
    mission_complete, reason = _check_end_mission(result_messages)

    # 兜底：检查文本标记方式
    if not mission_complete:
        mission_complete, reason = _check_end_mission_marker(result_messages)

    # 构建状态更新
    # 只传递精简后的消息，避免状态膨胀
    trimmed_messages = _trim_messages(clean_messages(result_messages))

    update = {
        "messages": trimmed_messages
    }

    if mission_complete:
        update["mission_complete"] = True
        update["mission_end_reason"] = reason
        print(f"[{agent_name}] ✅ 任务完成: {reason}")

    return update


# ============================================================
# 侦察专家节点
# ============================================================

def recon_agent_node(state: PentestState) -> dict:
    """侦察专家节点"""
    step = state.get("step_count", 0)
    print(f"[recon] 开始执行（第 {step} 步）")

    task_prompt = """
### 侦察任务

请**高效**执行以下侦察工作（优先使用预装工具）：

1. **端口扫描**: 调用 `run_tool(stamp, "recon/port_scan", '{"target": "目标地址"}')`
2. **目录枚举**: 调用 `run_tool(stamp, "recon/dir_enum", '{"url": "http://目标地址"}')`
3. **首页分析**: 调用 `run_tool(stamp, "utils/http_request", '{"url": "http://目标地址"}')`

⚠️ 请直接使用 run_tool 而不是 deploy_and_run_task 写脚本！

完成后，总结发现。如果直接发现了 flag，调用 end_mission 结束。
"""

    result = _invoke_subagent("reconnaissance_agent", RECON_TOOLS, state, task_prompt)
    result["current_phase"] = "recon"
    return result


# ============================================================
# 输入漏洞专家节点
# ============================================================

def input_vuln_agent_node(state: PentestState) -> dict:
    """输入漏洞专家节点"""
    step = state.get("step_count", 0)
    print(f"[input_vuln] 开始执行（第 {step} 步）")

    recon = state.get("recon_results", {})

    task_prompt = f"""
### 输入漏洞测试任务

侦察结果摘要：
{recon}

请**高效**进行以下测试（优先使用预装工具）：

1. **SQL 注入**: 调用 `run_tool(stamp, "sqli/detect", '{{"url": "...", "method": "POST", "data": "...", "inject_param": "..."}}')`
2. **HTTP 请求**: 调用 `run_tool(stamp, "utils/http_request", '{{"url": "...", "method": "POST", "data": "..."}}')`

⚠️ 优先使用 run_tool，仅在预装工具不足时才用 deploy_and_run_task。

发现漏洞后使用 add_finding 记录。
如果成功利用漏洞获取了 flag 或敏感数据，调用 end_mission 结束。
"""

    result = _invoke_subagent("input_vuln_expert", SUBAGENT_TOOLS, state, task_prompt)
    result["current_phase"] = "vuln_test"
    return result


# ============================================================
# 访问控制专家节点
# ============================================================

def access_logic_agent_node(state: PentestState) -> dict:
    """访问控制专家节点"""
    step = state.get("step_count", 0)
    print(f"[access_logic] 开始执行（第 {step} 步）")

    recon = state.get("recon_results", {})

    task_prompt = f"""
### 访问控制测试任务

侦察结果摘要：
{recon}

请进行以下测试：

1. **IDOR**: 测试资源 ID 是否可被篡改访问
2. **垂直越权**: 测试普通用户能否访问管理接口
3. **认证绕过**: 测试认证机制是否可被绕过

使用 `run_tool(stamp, "utils/http_request", ...)` 发送自定义请求。

发现漏洞后使用 add_finding 记录。
如果成功获取了未授权访问或敏感数据，调用 end_mission 结束。
"""

    result = _invoke_subagent("access_logic_expert", SUBAGENT_TOOLS, state, task_prompt)
    result["current_phase"] = "access_test"
    return result


# ============================================================
# 知识库专家节点
# ============================================================

def knowledge_agent_node(state: PentestState) -> dict:
    """知识库专家节点"""
    from tools.knowledge_tools import KNOWLEDGE_TOOLS

    recon = state.get("recon_results", {})
    findings = state.get("findings", [])

    task_prompt = f"""
### 知识库查询任务

侦察结果：{recon}
已发现漏洞：{findings}

请使用知识库工具查询相关漏洞和利用方案。
"""

    tools = SUBAGENT_TOOLS + KNOWLEDGE_TOOLS
    result = _invoke_subagent("knowledge_agent", tools, state, task_prompt)
    return result


# ============================================================
# 报告生成节点
# ============================================================

def report_node(state: PentestState) -> dict:
    """报告生成节点"""
    from tools.local_tools import update_mission_log

    end_reason = state.get("mission_end_reason", "任务正常完成")
    step_count = state.get("step_count", 0)

    report = f"""# 渗透测试报告

## 基本信息
- 任务戳: {state.get('stamp', 'N/A')}
- 目标: {state.get('target', 'N/A')}
- 任务名称: {state.get('mission_name', 'N/A')}
- 结束原因: {end_reason}
- 总步数: {step_count}

## 侦察结果
{state.get('recon_results', '无')}

## 漏洞发现 ({len(state.get('findings', []))} 个)
"""

    for i, f in enumerate(state.get("findings", []), 1):
        report += f"""
### {i}. [{f.get('severity', 'N/A').upper()}] {f.get('vuln_type', 'N/A')}
- 描述: {f.get('description', 'N/A')}
- 证据: {f.get('evidence', {})}
"""

    report += f"""
## 任务日志
"""
    for t in state.get("task_history", []):
        report += f"- {t.get('task_id', 'N/A')}: {t.get('status', 'N/A')}\n"

    report += "\n## 状态: 已完成"

    try:
        update_mission_log.invoke({"content": report, "append": False})
    except Exception as e:
        print(f"[report] 保存报告失败: {e}")

    return {
        "current_phase": "completed",
        "messages": [AIMessage(content=f"报告已生成并保存到任务账本。\n\n{report}")]
    }
