"""规则化 Agent 驱动（LLM_DRIVER=rule 时的分类逻辑，离线可复现）。

与远端 DeepSeek 同构：graph 节点都以 chat_json([...role tags...]) 调用统一的
llm.chat_json 入口，rule 驱动按 system 里的角色标签分发，保证「切驱动不改代码」。

角色标签：
  TRIAGE   -> 意图/类别/优先级/风险/缺失信息
  RETRIEVAL-> 检索查询提取（转发给 adapters.search_kb）
  ACTION   -> 生成工具计划 + 审批判断
"""
import re

from tool_gateway import definitions as defs
from tool_gateway import rules


def _get_kw(text: str) -> list[str]:
    return list(set(t for t in ("gitlab", "vpn", "crm", "mail", "prod_db",
                                "数据库", "权限", "开通", "故障", "连不上",
                                "升级", "管理员", "拦截", "越权") if t in text))


def triage(text: str) -> dict:
    atk = rules.detect_attack(text)
    low = text.lower()

    # 攻击优先
    if atk:
        return {
            "intent": "attack", "category": atk["attack_type"],
            "priority": "P1", "risk_level": defs.RISK_HIGH,
            "missing_fields": [], "attack": atk,
        }
    if any(k in low for k in ("管理员", "admin", "root")) and (
            "权限" in text or "开通" in text):
        return {"intent": "high_risk_request", "category": "high_risk_permission",
                "priority": "P1", "risk_level": defs.RISK_HIGH, "missing_fields": []}
    if ("权限" in text or "开通" in text) and any(
            s in text for s in ("敏感", "生产库", "财务")):
        return {"intent": "high_risk_request", "category": "high_risk_permission",
                "priority": "P1", "risk_level": defs.RISK_HIGH, "missing_fields": []}
    if "权限" in text or "开通" in text:
        missing = []
        higher = any(k in text for k in ("管理员", "root", "admin", "生产库", "财务", "敏感"))
        if not re.search(r"(k8s|gitlab|vpn|crm|数据库|项目|ops-|运维)", text):
            missing.append("target")
        if not re.search(r"(读|写|管理员|view|maintain|developer|读权限|写权限)", text):
            missing.append("permission")
        return {"intent": ("high_risk_request" if higher else "permission_request"),
                "category": ("high_risk_permission" if higher else "account_permission"),
                "priority": "P1" if higher else "P2",
                "risk_level": defs.RISK_HIGH if higher else defs.RISK_MEDIUM,
                "missing_fields": missing}
    if any(k in text for k in ("故障", "连不上", "503", "超时", "慢", "报错", "无法")):
        return {"intent": "system_fault", "category": "software_fault",
                "priority": "P2", "risk_level": defs.RISK_MEDIUM, "missing_fields": []}
    return {"intent": "general_query", "category": "general_inquiry",
            "priority": "P3", "risk_level": defs.RISK_LOW, "missing_fields": []}


_KW_TO_SYSTEM = {
    "gitlab": "gitlab", "vpn": "vpn", "crm": "crm", "mail": "mail",
    "数据库": "prod_db",
}


def retrieval_query(text: str, intent: str) -> dict:
    kws = _get_kw(text)
    q = " ".join(kws) if kws else (text[:40] if text else "")
    sys_name = next((v for k, v in _KW_TO_SYSTEM.items() if k in text), "")
    return {"query": q, "system": sys_name, "keywords": kws}


def action_plan(text: str, intent: str, category: str,
                risk: str, system: str = "") -> dict:
    """生成工具调用计划。与 Tool Gateway 规则联动。"""
    if intent == "attack":
        return {"tool_plan": [], "approval_required": False,
                "risk_decision": "REJECT", "reason": "疑似注入/攻击，拒绝执行"}
    if intent == "high_risk_request":
        return {"tool_plan": [], "approval_required": True,
                "risk_decision": "APPROVE_ESCALATE",
                "reason": "高风险请求，转主管审批/升级"}
    if intent == "permission_request":
        plan = [
            {"tool": "query_user_profile", "args": {"user_id": "{subject}"}},
            {"tool": "check_permission_policy", "args": {}},
        ]
        grant_target = system or ("prod_db" if "生产库" in text else "gitlab")
        if risk == defs.RISK_HIGH:
            return {"tool_plan": plan, "approval_required": True,
                    "risk_decision": "APPROVE_ESCALATE",
                    "reason": "涉及高风险授权，需主管审批"}
        plan.append({"tool": "grant_permission",
                     "args": {"system": grant_target, "permission": "{permission}"}})
        return {"tool_plan": plan, "approval_required": True,
                "risk_decision": "APPROVE", "reason": "普通权限变更，需 IT 审批"}
    if intent == "system_fault":
        plan = [
            {"tool": "search_kb", "args": {"query": text[:30]}},
            {"tool": "query_system_status", "args": {"system": system or "unknown"}},
        ]
        if "连不上" in text or "无法" in text or "down" in text.lower():
            plan.append({"tool": "create_incident_task",
                         "args": {"reason": text[:30]}})
        return {"tool_plan": plan, "approval_required": False,
                "risk_decision": "AUTO", "reason": "只读诊断+知识库"}
    return {"tool_plan": [{"tool": "search_kb", "args": {"query": text[:30]}}],
            "approval_required": False, "risk_decision": "AUTO",
            "reason": "知识库咨询"}


def _part(user: str, key: str) -> str:
    for line in user.splitlines():
        if ":" in line and line.split(":", 1)[0].strip() == key:
            return line.split(":", 1)[1].strip()
    return ""


def dispatch(user: str, sys_role: str):
    role = (sys_role or "").upper()
    if "TRIAGE" in role:
        return triage(user)
    if "RETRIEVAL" in role:
        return retrieval_query(user, "")
    if "ACTION" in role:
        return action_plan(user, _part(user, "INTENT"), _part(user, "CATEGORY"),
                           _part(user, "RISK"), _part(user, "SYSTEM"))
    return {}