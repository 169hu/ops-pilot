"""GraphState：贯穿 LangGraph 全链路的共享状态（对齐方案定义）。

字段分三层：
- 输入：ticket_id / ticket_text / requester
- 中间：intent / category / priority / risk_level / missing_fields /
        retrieved_docs / tool_plan / risk_decision / approval_required / approved
- 输出：execution_results / final_answer / trace_id
- 追溯：trace_steps（每节点逐步记录，供 Trace 页面）
"""
from typing import Any, Optional
from langgraph.graph import MessagesState

from tool_gateway import definitions as defs  # noqa: F401  (风险常量复用)


class GraphState(MessagesState):
    ticket_id: str
    ticket_text: str
    requester: dict

    intent: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    risk_level: Optional[str] = None
    missing_fields: list = []

    retrieved_docs: list = []
    knowledge_hits: list = []

    tool_plan: list = []
    risk_decision: Optional[str] = None   # AUTO / APPROVE / REJECT / APPROVE_ESCALATE
    approval_required: bool = False
    approved: Optional[bool] = None
    escalated: bool = False

    execution_results: list = []
    final_answer: Optional[str] = None

    trace_id: Optional[str] = None
    trace_steps: list = []