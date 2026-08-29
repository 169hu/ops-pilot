"""LangGraph 状态图编排（对齐方案 mermaid 流转图）。

flowchart:
  START -> triage_agent -> (信息不足?) ask_clarification --补充--> triage_agent
                          -> retrieval_agent -> action_agent
                          -> risk_router -> LOW:auto / MEDIUM:approval / HIGH:escalate(reject)
                          -> tool_executor -> final_response -> END
"""
from langgraph.graph import END, START, StateGraph

from agents import nodes
from agents.state import GraphState


def build_graph():
    g = StateGraph(GraphState)

    g.add_node("triage_agent", nodes.triage_agent)
    g.add_node("ask_clarification", nodes.ask_clarification)
    g.add_node("retrieval_agent", nodes.retrieval_agent)
    g.add_node("action_agent", nodes.action_agent)
    g.add_node("risk_router", nodes.risk_router)
    g.add_node("tool_executor", nodes.tool_executor)
    g.add_node("final_response", nodes.final_response)

    g.add_edge(START, "triage_agent")

    # 信息不足 -> 澄清(终点；真实环境为异步"补充后重入"，进程内自动运行到此结束)
    g.add_conditional_edges(
        "triage_agent",
        lambda s: ("ask_clarification" if s.get("missing_fields")
                   else "retrieval_agent"),
        {"ask_clarification": "ask_clarification", "retrieval_agent": "retrieval_agent"})
    g.add_edge("ask_clarification", END)

    g.add_edge("retrieval_agent", "action_agent")
    g.add_edge("action_agent", "risk_router")

    # 风险路由：LOW/AUTO -> 执行；APPROVE(审批) -> 待审批终点；REJECT -> 拒绝终点
    g.add_conditional_edges(
        "risk_router",
        lambda s: _route(s),
        {"execute": "tool_executor", "wait": "final_response", "reject": "final_response"})

    g.add_edge("tool_executor", "final_response")
    # final_response 是汇合点，等待所有入边后执行
    g.add_edge("final_response", END)
    return g.compile()


def _route(state):
    decision = state.get("risk_decision", "AUTO")
    if decision in ("REJECT", "APPROVE_ESCALATE") or state.get("risk_level") == "HIGH":
        return "reject"
    if state.get("approved"):
        return "execute"   # 已批准：跳过审批等待，直接落地执行
    if decision == "APPROVE" or state.get("approval_required"):
        return "wait"      # 进入待审批终态（approval_required=True）
    return "execute"


build = build_graph


def run_ticket(ticket: dict, approved: bool = False) -> dict:
    """外部入口：把一条工单投进图，返回平台契约 dict + trace。

    ticket 需含 ticket_id / title / description / requester(无需完整，含 user_id/role)。
    approved: 审批通过后重放，注入审批态，令 grant 类工具跳过等待、落地执行。
    """
    graph, request_state = build(), None
    init = {
        "ticket_id": ticket["ticket_id"],
        "ticket_text": (ticket.get("title", "") + "，" + ticket.get("description", "")
                        ).strip("，"),
        "requester": ticket.get("requester", {"user_id": "U001", "role": "employee"}),
        "approved": approved,
        "trace_steps": [],
    }
    result = graph.invoke(init)
    decision = result.get("risk_decision", "AUTO")
    approval = bool(result.get("approval_required")) and not result.get("approved")
    if decision in ("REJECT", "APPROVE_ESCALATE") or result.get("risk_level") == "HIGH":
        next_action = "REJECTED" if not approval else "WAITING_APPROVAL"
    else:
        next_action = "WAITING_APPROVAL" if approval else "EXECUTED"
    return {
        "ticket_id": result.get("ticket_id"),
        "intent": result.get("intent"), "category": result.get("category"),
        "risk_level": result.get("risk_level"),
        "summary": _summary(result),
        "retrieved_docs": result.get("retrieved_docs", []),
        "tool_plan": result.get("tool_plan", []),
        "approval_required": approval,
        "pending_tools": ([t["tool"] for t in result.get("tool_plan", [])
                           if t["tool"] == "grant_permission"] if approval else []),
        "next_action": next_action,
        "final_answer": result.get("final_answer"),
        "execution_results": result.get("execution_results", []),
        "trace_id": result.get("trace_id"),
        "trace_steps": result.get("trace_steps", []),
    }


def _summary(result):
    if result.get("final_answer"):
        return result["final_answer"].splitlines()[1] if len(
            result["final_answer"].splitlines()) > 1 else result["final_answer"]
    return f"已分诊为 {result.get('category')}"