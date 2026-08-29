"""LangGraph 节点与控制流（对齐方案 mermaid 状态流转图）。

节点：
  triage_agent   -> 意图/类别/优先级/风险/缺失信息（LLM 或规则驱动）
  Ask Clarification -> 信息不足时要求补充（在图上体现为回环）
  retrieval_agent-> 知识库检索，整理证据（RAG 引用）
  action_agent   -> 生成工具计划 + 审批需求
  risk_router    -> 按风险决策 AUTO / APPROVE / REJECT
  tool_executor  -> 经 Tool Gateway 执行（已批准/自动）
  final_response -> 有据生成最终回复

设计要点：
- 每个 Agent 节点经统一 llm.chat_json 调用，驱动(deepseek/rule)可切换，代码不变。
- 工具执行一律走 Tool Gateway 的 invoke()，不裸调，保证审计与安全。
- 审计/轨迹记录统一收集到 trace_steps，供 Trace 展示。
"""
import time
import uuid

import agents.llm as llm
from agents.state import GraphState
from tool_gateway import adapters, definitions as defs
from tool_gateway.gateway import invoke


def _step(state, cls, name, data, dt_ms=0.0, tokens=0):
    return {"node": name, "cls": cls, "ts": time.strftime("%H:%M:%S"),
            "data": data, "latency_ms": round(dt_ms, 1), "tokens": tokens}


def triage_agent(state: GraphState) -> dict:
    """Triage：解析工单意图/类别/风险/优先级/缺失信息。"""
    trace_id = state.get("trace_id")
    if trace_id is None:
        trace_id = "TR-" + str(uuid.uuid4())[:8]
    t0 = time.monotonic()
    text = state["ticket_text"]
    data, dt, tk = llm.chat_json([
        {"role": "system",
         "content": "TRIAGE|你是工单分诊智能体，输出意图/类别/优先级/风险/缺失信息 JSON"},
        {"role": "user", "content": text}], temperature=0.0)
    return {
        "trace_id": trace_id,
        "intent": data.get("intent"), "category": data.get("category"),
        "priority": data.get("priority"), "risk_level": data.get("risk_level"),
        "missing_fields": data.get("missing_fields", []),
        "trace_steps": state["trace_steps"] + [
            _step(state, "agent", "triage_agent", data, dt, tk)],
    }


def retrieval_agent(state: GraphState) -> dict:
    """Retrieval：抽取检索词，查知识库（RAG），整理证据。"""
    text = state["ticket_text"]
    data, dt, tk = llm.chat_json([
        {"role": "system", "content": "RETRIEVAL|抽取检索查询用于知识库检索 JSON"},
        {"role": "user", "content": text}], temperature=0.0)
    q = data.get("query") or (text[:30] if text else "")
    kb = adapters.search_kb(q, top_k=3)
    hits = kb.get("hits", [])
    return {
        "retrieved_docs": [h.get("document_id") for h in hits],
        "knowledge_hits": hits,
        "trace_steps": state["trace_steps"] + [
            _step(state, "tool", "search_kb",
                  {"query": q, "hits": len(hits)}, dt, tk)],
    }


def action_agent(state: GraphState) -> dict:
    """Action：综合工单/证据/风险，生成工具计划与审批需求。"""
    t0 = time.monotonic()
    sysname = next((h.get("metadata", {}).get("system", "")
                    for h in state.get("knowledge_hits", [])
                    if h.get("metadata", {}).get("system")), "")
    user = "\n".join([
        state["ticket_text"],
        f"INTENT:{state.get('intent')}",
        f"CATEGORY:{state.get('category')}",
        f"RISK:{state.get('risk_level')}",
        f"SYSTEM:{sysname}",
    ])
    data, dt, tk = llm.chat_json([
        {"role": "system",
         "content": "ACTION|你是行动智能体，输出工具计划与审批判断 JSON"},
        {"role": "user", "content": user}], temperature=0.0)
    return {
        "tool_plan": data.get("tool_plan", []),
        "approval_required": bool(data.get("approval_required")),
        "risk_decision": data.get("risk_decision", "AUTO"),
        "trace_steps": state["trace_steps"] + [
            _step(state, "agent", "action_agent", data, dt, tk)],
    }


def ask_clarification(state: GraphState) -> dict:
    """信息不足：记录缺什么，触发人工补充后重入（图上回环）。"""
    return {
        "final_answer": (
            "需要补充信息后继续分析：" + ", ".join(state.get("missing_fields", [])) + "。"
            f"工单 {state['ticket_id']} 待补充。"),
        "trace_steps": state["trace_steps"] + [
            _step(state, "control", "ask_clarification",
                  {"missing": state.get("missing_fields")})],
    }


def risk_router(state: GraphState) -> dict:
    """控制节点：按风险决定走向 AUTO / APPROVE / REJECT。"""
    decision = state.get("risk_decision", "AUTO")
    return {
        "trace_steps": state["trace_steps"] + [
            _step(state, "control", "risk_router",
                  {"decision": decision, "risk": state.get("risk_level"),
                   "approval_required": state.get("approval_required")})],
    }


def tool_executor(state: GraphState) -> dict:
    """控制节点：把工具计划经 Tool Gateway 执行（自动或已批准）。"""
    plan = state.get("tool_plan", [])
    results = list(state.get("execution_results", []))
    steps = list(state.get("trace_steps", []))
    subject = state["requester"].get("user_id", "")
    caller = state["requester"].get("role", "employee")
    ctx = {
        "caller_role": caller, "caller_user_id": state["requester"].get("user_id"),
        "subject_user_id": subject, "ticket_id": state["ticket_id"],
        "ticket_text": state["ticket_text"], "intent": state.get("intent"),
        "category": state.get("category"), "approved": bool(state.get("approved")),
    }
    for item in plan:
        tool = item["tool"]
        args = dict(item.get("args", {}))
        if "{subject}" in args.get("user_id", ""):
            args["user_id"] = subject
        for k in list(args):
            if isinstance(args[k], str) and args[k].startswith("{") and args[k].endswith("}"):
                key = args[k][1:-1]
                args[k] = state["requester"].get(key)
        r = invoke(tool, args, ctx)
        results.append({"tool": tool, "args": args, "gateway": r})
        steps = steps + [_step(state, "tool", r["tool_name"], r, 0.0, 0)]
    return {"execution_results": results, "trace_steps": steps}


def final_response(state: GraphState) -> dict:
    """有据生成最终回复（结论 + 依据 + 下一步）。"""
    outcome = []
    for r in state.get("execution_results", []):
        s = r["gateway"]["status"]
        outcome.append(f"{r['tool']} -> {s}")
    full = "\n".join(outcome)
    state["final_answer"] = (
        f"工单 {state['ticket_id']} 处理完成。\n"
        f"意图={state.get('intent')} | 风险={state.get('risk_level')} | "
        f"状态={state.get('approval_required') and '待审批' or '已处理'}\n"
        f"执行摘要：\n{full or '（本次无工具执行，建议人工跟进）'}")
    return {}