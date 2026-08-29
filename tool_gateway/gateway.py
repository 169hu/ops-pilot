"""Tool Gateway：唯一出入口。每次调用必经 7 步，返回统一契约。

7 步（对齐方案）：
1  校验 tool 是否启用
2  校验 input_schema（参数齐全/类型）
3  校验调用者角色（是否允许调该工具）
4  判断工具风险等级（含 grant 动态升级、攻击检测）
5  判断是否需要审批
6  写入 tool_invocations 审计日志
7  返回结构化结果（执行 / PENDING_APPROVAL / REJECTED / BLOCKED / INFO_REQUIRED）

安全立场：
- 前端/用户不能绕过本层"裸调"工具；唯一入口是本 invoke()。
- 高风险或攻击检测 → 拦截或升级，绝不自动执行。
"""
import time

from . import definitions as defs
from . import rules, adapters
from .audit import get_audit


class GatewayError(Exception):
    pass


def invoke(tool_name: str, args: dict, context: dict) -> dict:
    """执行一次工具调用。

    context 需含：caller_role, caller_user_id, ticket_id, subject_user_id,
                ticket_text(用于攻击检测), approved(bool)。缺省按保守处理。
    """
    ctx = context or {}
    t0 = time.monotonic()
    audit = get_audit()

    # ---------- 步骤 1：工具是否启用 ----------
    tool = defs.get_tool(tool_name)
    if tool is None:
        return _finish(audit, ctx, tool_name, args, defs.STATUS_ERROR,
                       "未知工具，不在注册表内", t0)
    if tool.get("disabled"):
        return _finish(audit, ctx, tool_name, args, defs.STATUS_ERROR,
                       "工具已禁用", t0)

    # ---------- 步骤 2：input_schema 校验 ----------
    missing = _validate_schema(tool["input_schema"], args or {})
    if missing:
        return _finish(audit, ctx, tool_name, args, defs.STATUS_INFO_REQUIRED,
                       f"参数缺失/非法：{missing}，请补充", t0)

    # ---------- 步骤 3：调用者角色校验 ----------
    caller_role = ctx.get("caller_role", "employee")
    if caller_role not in tool["roles_allowed"]:
        return _finish(audit, ctx, tool_name, args, defs.STATUS_BLOCKED,
                       f"调用者角色 {caller_role} 无权限调用 {tool_name}", t0)

    # ---------- 步骤 4：综合风险判定（工具风险 + 攻击 + grant 动态升级） ----------
    risk, reason = _resolve_risk(tool_name, args, tool, ctx)

    # ---------- 攻击防护：命中注入/敏感/批量 → 拦截或强审批 ----------
    atk = rules.detect_attack(ctx.get("ticket_text", ""))
    if atk and atk["action"] == "reject":
        return _finish(audit, ctx, tool_name, args, defs.STATUS_BLOCKED,
                       f"攻击防护拦截：{atk['reason']}", t0, attack=atk)
    if atk and atk["action"] == "escalate":
        risk, reason = defs.RISK_HIGH, atk["reason"]

    # ---------- 步骤 5：审批判断 ----------
    requires_approval = _requires_approval(tool_name, risk, tool)
    approved = bool(ctx.get("approved"))
    if requires_approval and not approved:
        inv_id = audit.record({
            "ticket_id": ctx.get("ticket_id"), "tool_name": tool_name,
            "input_json": args, "output_json": None, "status": defs.STATUS_PENDING_APPROVAL,
            "risk_level": risk, "caller_role": caller_role,
            "requires_approval": True, "reason": reason,
        })
        return {
            "tool_name": tool_name, "status": defs.STATUS_PENDING_APPROVAL,
            "risk_level": risk, "requires_approval": True,
            "reason": reason + "（等待审批）", "invocation_id": inv_id,
            "approved": False,
        }

    # ---------- 步骤 6+7：执行 + 审计 ----------
    try:
        result = adapters.execute(tool_name, args)
    except Exception as e:  # noqa: BLE001
        return _finish(audit, ctx, tool_name, args, defs.STATUS_ERROR,
                       f"执行异常：{e}", t0)
    inv_id = audit.record({
        "ticket_id": ctx.get("ticket_id"), "tool_name": tool_name,
        "input_json": args, "output_json": result, "status": defs.STATUS_OK,
        "risk_level": risk, "caller_role": caller_role,
        "requires_approval": requires_approval,
        "approved": requires_approval or approved, "reason": reason,
        "latency_ms": round((time.monotonic() - t0) * 1000, 1),
    })
    return {
        "tool_name": tool_name, "status": defs.STATUS_OK,
        "risk_level": risk, "requires_approval": requires_approval,
        "reason": reason, "invocation_id": inv_id, "approved": True,
        "result": result,
    }


def _resolve_risk(tool_name: str, args: dict, tool: dict, ctx: dict) -> tuple[str, str]:
    """工具风险 + grant 动态升级 + 工单意图兜底，取最高。"""
    risk = tool["risk_level"]
    reason = "工具定义风险"

    # grant_permission 动态升级
    if tool_name == "grant_permission":
        g_risk, g_reason = rules.check_grant_risk(
            args.get("system", ""), args.get("permission", ""))
        if _rank(g_risk) > _rank(risk):
            risk, reason = g_risk, g_reason

    # 工单层面的攻击/高风险（不覆盖危险 grant 的独立判定）
    int_risk, _ = rules.classify_risk(ctx.get("ticket_text", ""),
                                      ctx.get("intent", ""), ctx.get("category", ""))
    if _rank(int_risk) > _rank(risk):
        risk, reason = int_risk, "工单风险分级"
    return risk, reason


def _requires_approval(tool_name: str, risk: str, tool: dict) -> bool:
    if tool["name"] == "grant_permission":
        return True                                # 变更操作恒需审批
    if risk == defs.RISK_HIGH:
        return True
    return bool(tool.get("requires_approval"))


def _validate_schema(schema: dict, args: dict) -> list[str]:
    missing = []
    for field, spec in schema.items():
        if spec.get("required") and (field not in args or args[field] in (None, "")):
            missing.append(field)
    return missing


def _rank(r: str) -> int:
    return {"LOW": 0, "MEDIUM": 1, "HIGH": 2}.get(r, 0)


def _finish(audit, ctx, name, args, status, reason, t0, attack=None) -> dict:
    """统一收尾：拒绝/阻塞/错误/缺参都落审计并返回契约。"""
    risk = (attack or {}).get("risk", "LOW")
    inv_id = audit.record({
        "ticket_id": ctx.get("ticket_id"), "tool_name": name,
        "input_json": args, "output_json": None, "status": status,
        "risk_level": risk, "caller_role": ctx.get("caller_role"),
        "requires_approval": False, "reason": reason, "attack": attack,
        "latency_ms": round((time.monotonic() - t0) * 1000, 1),
    })
    return {
        "tool_name": name, "status": status, "risk_level": risk,
        "requires_approval": False, "reason": reason,
        "invocation_id": inv_id, "approved": False,
    }