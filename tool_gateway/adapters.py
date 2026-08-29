"""adapter 层：仿真企业 API 执行。真实落地时仅替换本模块的函数实现，Gateway 无需改动。

每个 adapter 代表一个"真实系统"的模拟端点：
- search_kb          -> 基于简单关键词/标题匹配检索知识库切片（阶段2换 pgvector 语义检索）
- query_user_profile -> 读 employees.json
- query_system_status-> 读系统状态（仿真随机但 seed 固定）
- check_permission_policy -> 判定申请是否越权（对比员工 can_grant_targets + 敏感系统）
- grant_permission        -> 记录授权（入内存/审计，生产落库）
- create_incident_task    -> 创建一个升级任务
"""
import json
import os
import random

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         "data", "generated")


def _load(name):
    with open(os.path.join(_DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def _employees():
    return _load("employees.json")


def _chunks():
    return _load("kb_chunks.json")


# ---- 各 adapter 执行实现 ----

def search_kb(query: str, top_k: int = 5) -> dict:
    chunks = _chunks()
    q = (query or "").strip()
    scored = []
    for c in chunks:
        text = c["chunk_text"] or ""
        meta = c["metadata"] or {}
        score = 0.0
        for token in (q or "").split():
            if token in text:
                score += 1.0
        for tag in meta.get("tags", []):
            if tag and tag in q:
                score += 0.5
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    hits = scored[:top_k]
    return {
        "hits": [
            {"chunk_id": c["chunk_id"], "document_id": c["document_id"],
             "text": c["chunk_text"], "title": c["metadata"].get("title", ""),
             "topic": c["metadata"].get("topic", "")}
            for _, c in hits
        ],
        "total": len(hits),
    }


def query_user_profile(user_id: str) -> dict:
    emp = _employees()
    for e in emp:
        if e["user_id"] == user_id:
            return {"user": {
                "user_id": e["user_id"], "name": e["name"],
                "department": e["department"], "role": e["role"],
                "risk_level": e["risk_level"],
                "can_grant_targets": e["can_grant_targets"],
                "can_approve": e["can_approve"],
            }}
    return {"user": None, "error": f"未找到用户 {user_id}"}


def query_system_status(system: str) -> dict:
    # 固定 seed 下稳定，保证评测可复现
    rng = random.Random(hash(system) & 0xffff)
    states = ["OPERATIONAL", "OPERATIONAL", "OPERATIONAL", "DEGRADED", "DOWN"]
    return {
        "system": system,
        "status": states[rng.randrange(len(states))],
        "latency_ms": rng.randrange(80, 400),
    }


def check_permission_policy(subject: str, target: str, permission: str) -> dict:
    emp = _employees()
    user = next((e for e in emp if e["email"] == subject or e["user_id"] == subject), None)
    role_allowed = False
    if user:
        role_allowed = permission in user.get("can_grant_targets", []) or \
            _system_allows_target(user["role"], target)
    sensitive = target in {"prod_db", "crm_saas", "finance"}
    unprivileged = any(k in (permission or "").lower()
                       for k in ("admin", "root", "owner"))
    violates_min_privilege = unprivileged or (not role_allowed)
    return {
        "subject": subject, "target": target, "permission": permission,
        "anomalous": False,
        "policy_decision": {
            "allowed": bool(role_allowed) and not sensitive and not unprivileged,
            "needs_approval": sensitive or unprivileged or "admin" in permission.lower(),
            "reason": (
                "越权：角色无权该目标/权限" if not role_allowed
                else ("敏感系统" if sensitive
                      else ("管理员权限需强审批" if unprivileged else "符合最小权限"))
            ),
        },
    }


def _system_allows_target(role: str, target: str) -> bool:
    matrix = {
        "employee":  {"gitlab", "vpn"},
        "it_staff":  {"gitlab", "vpn", "crm", "mail"},
        "manager":   {"gitlab", "vpn", "crm", "mail", "prod_db"},
    }
    return target in matrix.get(role, set())


# 授权记录（内存；生产写 tool_invocations / 权限表）
_GRANTS = []


def grant_permission(user_id: str, system: str, permission: str) -> dict:
    _GRANTS.append({"user_id": user_id, "system": system,
                    "permission": permission})
    return {"granted": True, "user_id": user_id, "system": system,
            "permission": permission, "audit_ref": f"GR-{len(_GRANTS):04d}"}


def create_incident_task(ticket_id: str, reason: str) -> dict:
    return {"task_id": f"INC-{abs(hash(ticket_id)) % 100000:05d}",
            "ticket_id": ticket_id, "reason": reason, "status": "OPEN"}


_ADAPTERS = {
    "search_kb": lambda a: search_kb(a.get("query", ""), a.get("top_k", 5)),
    "query_user_profile": lambda a: query_user_profile(a.get("user_id", "")),
    "query_system_status": lambda a: query_system_status(a.get("system", "")),
    "check_permission_policy": lambda a: check_permission_policy(
        a.get("subject", ""), a.get("target", ""), a.get("permission", "")),
    "grant_permission": lambda a: grant_permission(
        a.get("user_id", ""), a.get("system", ""), a.get("permission", "")),
    "create_incident_task": lambda a: create_incident_task(
        a.get("ticket_id", ""), a.get("reason", "")),
}


def execute(name: str, args: dict) -> dict:
    """执行模拟 API。name 不存在抛 KeyError（由 Gateway 前置校验兜底）。"""
    return _ADAPTERS[name](args)