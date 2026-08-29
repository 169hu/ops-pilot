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


# 权限申请意图相关措辞（账号申请/开通/解锁/重置/授权）
# 注：刻意不含 账号/访问/入口 这类泛指词，避免把"登录失败/进不去/入口在哪"误判为权限申请
_PERM_VERBS = ("权限", "开通", "申请", "解锁", "重置", "授权", "委托代开",
               "新建账号", "开户", "开一个", "开个")
# 故障意图相关措辞（系统/服务异常）
_FAULT_KEYS = ("故障", "连不上", "503", "超时", "慢", "报错", "无法", "失败", "锁定",
               "扩容", "延迟", "同步", "过期", "异常", "不可用", "升级", "断",
               "收不到", "发不出去", "不了")
# 高风险权限措辞（命中即 high_risk/permission，须升级审批）
_HIGH_PERM = ("生产库", "production", "主库", "财务", "admin", "root", "管理员",
              "敏感", "备份恢复", "批量")
# 越权/攻击措辞（命中即 attack）
_ATTACK_KEYS = ("忽略", "绕过", "无视", "骗", "破解", "帮我导出", "导出主管", "导出他人",
                "别人", "主管", "同事的", "越权", "逃审批", "所有人", "全公司")


def triage(text: str) -> dict:
    atk = rules.detect_attack(text)
    low = text.lower()

    # ---- 攻击优先：任何 detect_attack reject 红线（注入/敏感系统）→ 拒绝 ----
    if atk and atk.get("action") == "reject":
        return {
            "intent": "attack", "category": atk["attack_type"],
            "priority": "P1", "risk_level": defs.RISK_HIGH,
            "missing_fields": [], "attack": atk,
        }
    if any(k in text for k in _ATTACK_KEYS):
        return {
            "intent": "attack", "category": atk["attack_type"] if atk else "unauthorized_access",
            "priority": "P1", "risk_level": defs.RISK_HIGH,
            "missing_fields": [], "attack": atk or {},
        }

    # ---- 管理员授予：把某人 添加/设为/提升/授予 为管理员 → 高风险权限申请 ----
    if re.search(r"(添加|设为|提升|授予|换成).{0,8}管理员", text):
        return {"intent": "high_risk_request", "category": "high_risk_permission",
                "priority": "P1", "risk_level": defs.RISK_HIGH, "missing_fields": []}

    # ---- 高风险权限申请：生产库/管理员/批量 + 权限语境 → 升级审批 ----
    perm_like = any(k in text for k in _PERM_VERBS)
    if perm_like and any(k in text for k in _HIGH_PERM):
        return {"intent": "high_risk_request", "category": "high_risk_permission",
                "priority": "P1", "risk_level": defs.RISK_HIGH, "missing_fields": []}

    # ---- 普通权限申请 ----
    if perm_like:
        missing = []
        if not re.search(r"(k8s|gitlab|vpn|crm|数据库|系统|项目|邮箱|ops-|运维|入口)", text):
            missing.append("target")
        if not re.search(r"(读|写|只读|管理员|view|maintain|developer|编辑|使用|账号)", text):
            missing.append("permission")
        # 仅当目标与权限都缺失（完全无受授予实体/权限）才走澄清；否则视为可计划的权限申请
        if len(missing) >= 2:
            missing = ["subject", "permission"]
        else:
            missing = []
        return {"intent": "permission_request", "category": "account_permission",
                "priority": "P2", "risk_level": defs.RISK_MEDIUM,
                "missing_fields": missing}

    # ---- 系统/服务故障（敏感/生产系统升级 MEDIUM，普通排障 LOW 自动执行）----
    if any(k in text for k in _FAULT_KEYS):
        sensitive = any(s in text for s in ("生产", "数据库", "主库", "财务", "敏感", "批量"))
        return {"intent": "system_fault", "category": "software_fault",
                "priority": "P2", "risk_level": defs.RISK_MEDIUM if sensitive else defs.RISK_LOW,
                "missing_fields": []}
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