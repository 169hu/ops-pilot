"""数据存取层：读取生成的仿真数据 + 缓存工单运行结果/审批态。

保持无第三方 DB 依赖（阶段5 可切换 Postgres/pgvector）。
进程内单例加载，前端各接口共享同一份内存态。
"""
import json
import os
import threading

from agents.graph import run_ticket

_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "generated")
_REPORTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")

_lock = threading.Lock()


def _load(*parts):
    with open(os.path.join(_BASE, *parts), encoding="utf-8") as f:
        return json.load(f)


class Store:
    def __init__(self):
        self.employees = _load("employees.json")
        self.systems = _load("systems.json")
        self.tickets = _load("tickets.json")
        self.messages = _load("ticket_messages.json")
        self.history = _load("history.json")
        self.tools = _load("tools.json") if os.path.exists(
            os.path.join(_BASE, "tools.json")) else []

        # 运行缓存：ticket_id -> 最近一次 run_ticket 结果（含 trace）
        self.runs: dict[str, dict] = {}
        # 审批队列：ticket_id -> 待审批的授权对象明细
        self.approvals: dict[str, dict] = {}
        self._by_id = {t["ticket_id"]: t for t in self.tickets}
        self._emp_by_id = {e["user_id"]: e for e in self.employees}
        self._msg_by_ticket: dict[str, list] = {}
        for m in self.messages:
            self._msg_by_ticket.setdefault(m["ticket_id"], []).append(m)

    # ---- 关联映射 ----
    def requester(self, ticket) -> dict | None:
        return self._emp_by_id.get(ticket.get("requester_id"))

    def messages_of(self, ticket_id) -> list:
        return self._msg_by_ticket.get(ticket_id, [])

    # ---- 工单 ----
    def get_ticket(self, ticket_id: str) -> dict | None:
        return self._by_id.get(ticket_id)

    def list_tickets(self, status=None, category=None, q=None, limit=200):
        rows = []
        for t in self.tickets:
            if status and t.get("status") != status:
                continue
            if category and t.get("category") != category:
                continue
            if q and q not in (t.get("description", "") or ""):
                continue
            t = dict(t)
            t["requester"] = self.requester(t)
            t["last_run"] = self.runs.get(t["ticket_id"])
            rows.append(t)
        return rows

    # ---- 运行 ----
    def run(self, ticket_id: str, requester_role: str = "it_staff") -> dict:
        t = self.get_ticket(ticket_id)
        if not t:
            raise KeyError(ticket_id)
        requester = {"user_id": t.get("requester_id"),
                     "role": requester_role}
        result = run_ticket({
            "ticket_id": t["ticket_id"],
            "title": t["description"][:2] + "…" if False else t["title"],
            "description": t["description"],
            "requester": requester,
        })
        with _lock:
            self.runs[ticket_id] = result
            self._sync_approval(ticket_id, result)
        return self._decorate(ticket_id, result)

    def approve(self, ticket_id: str) -> dict:
        """模拟审批通过：以已批准身份重放图，授权经 Tool Gateway 落地执行。"""
        old = self.runs.get(ticket_id)
        if not old:
            raise KeyError(f"{ticket_id} 尚未运行，无法审批")
        t = self.get_ticket(ticket_id)
        requester = {
            "user_id": t.get("requester_id"), "role": "it_staff",
            # 被授权人：工单描述中除申请人之外的员工，作为 grant 的对象
            "subject_user_id": self._resolve_subject(t) or t.get("requester_id"),
        }
        result = run_ticket({
            "ticket_id": t["ticket_id"],
            "title": t["title"],
            "description": t["description"],
            "requester": requester,
        }, approved=True)
        with _lock:
            self.runs[ticket_id] = result
            self.approvals.pop(ticket_id, None)
        return self._decorate(ticket_id, result)

    def _resolve_subject(self, t: dict) -> str | None:
        """从工单描述中找被授权人（非申请人）的 user_id"""
        desc = t.get("description", "") or ""
        me = t.get("requester_id")
        for uid, e in self._emp_by_id.items():
            name = e.get("name", "")
            if name and uid != me and name in desc:
                return uid
        return None

    def _sync_approval(self, ticket_id: str, result: dict):
        if result.get("next_action") == "WAITING_APPROVAL":
            self.approvals[ticket_id] = {
                "ticket_id": ticket_id,
                "title": self.get_ticket(ticket_id)["title"],
                "description": self.get_ticket(ticket_id)["description"],
                "intent": result.get("intent"),
                "risk_level": result.get("risk_level"),
                "pending_tools": result.get("pending_tools", []),
            }
        else:
            self.approvals.pop(ticket_id, None)

    def list_approvals(self) -> list:
        return list(self.approvals.values())

    def _decorate(self, ticket_id: str, result: dict) -> dict:
        out = dict(result)
        out["ticket"] = self.get_ticket(ticket_id)
        out["approvals"] = list(self.approvals.values())
        return out

    # ---- 审计 / 评测 ----
    def audit(self, ticket_id=None, limit=200):
        path = os.path.join(os.path.dirname(
            os.path.dirname(__file__)), "results", "tool_invocations.json")
        try:
            with open(path, encoding="utf-8") as f:
                rows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rows = []
        if ticket_id:
            rows = [r for r in rows if r.get("ticket_id") == ticket_id]
        return rows

    def eval_report(self) -> dict:
        path = os.path.join(_REPORTS, "eval.json")
        if not os.path.exists(path):
            return {"driver": "none", "metrics": {}, "gates": {}}
        with open(path, encoding="utf-8") as f:
            return json.load(f)


_instance = None
_lock_inst = threading.Lock()


def get_store() -> Store:
    global _instance
    if _instance is None:
        with _lock_inst:
            if _instance is None:
                _instance = Store()
    return _instance