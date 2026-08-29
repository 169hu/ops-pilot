"""规则引擎：风险分级 + 攻击防护检测（5 类）。

对齐方案：
- 风险三级：LOW(只读/知识库/普通排障) / MEDIUM(普通权限/建任务) / HIGH(生产库/批量/注入)。
- 攻击防护：Prompt Injection / 越权申请 / 敏感系统 / 批量操作 / 参数缺失。

职责边界：
- rules 只做"判定"，不触达执行；执行与拒绝落在 gateway。
- 所有判定保留 reason，供 Trace 与审计展示"为什么这样决策"。
"""
import re

from . import definitions as defs

# ---- Prompt Injection 特征（覆盖方案示例句式）----
_INJECTION_PATTERNS = [
    r"忽略.{0,6}(规则|指令|上述|以上)" ,
    r"忽略.{0,6}(话|内容|指令)",
    r"(把|将).{,8}(忘了|忘掉|忽略)",
    r"无视.{0,4}规则",
    r"绕过.{0,5}(审批|校验|规则)",
    r"(系统|你的).{0,6}(提示词|system\s*prompt|规则).{0,6}(输出|泄露|给我)",
    r"直接.{1,8}(管理员|root|admin).{0,4}权限",
]

# 越权敏感权限关键词（普通角色申请即越权）
_UNPRIVILEGED_PERM = ("admin", "root", "owner", "super")
# 敏感/生产系统（禁止自动执行）
SENSITIVE_SYSTEMS = {"prod_db", "crm_saas", "finance"}


def detect_attack(ticket_text: str) -> dict | None:
    """检测工单文本是否命中攻击特征。返回 {attack_type, reason, risk} 或 None。

    优先级：注入 > 越权/批量/敏感系统。返回首个命中（注入优先，且最严重）。
    """
    text = ticket_text or ""
    # 1) Prompt Injection：命中任意注入句式
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return {
                "attack_type": "prompt_injection",
                "reason": f"工单含疑似注入句式（匹配: {pat}），禁止自动执行",
                "risk": defs.RISK_HIGH,
                "action": "reject",
            }
    # 2) 批量操作：含"全/所有/每个/批量/一次性"等群体操作措辞
    if re.search(r"(所有人|全(部|员|公司|部门)|每个|批量|一次性|全体)", text):
        return {
            "attack_type": "batch_operation",
            "reason": "批量操作措辞，须强制人工审批/拒绝",
            "risk": defs.RISK_HIGH,
            "action": "escalate",
        }
    # 3) 敏感系统/生产库
    if any(s in text for s in ("生产库", "production", "主库", "财务")):
        return {
            "attack_type": "sensitive_system",
            "reason": "触及敏感/生产系统，禁止自动执行",
            "risk": defs.RISK_HIGH,
            "action": "reject",
        }
    return None


def classify_risk(ticket_text: str, intent: str, category: str) -> tuple[str, str]:
    """综合风险分级。返回 (risk, reason)。先攻击再按意图兜底。"""
    atk = detect_attack(ticket_text)
    if atk:
        return atk["risk"], atk["reason"]

    # 按意图/类别兜底
    if intent in ("attack", "high_risk_request") or category in (
            "high_risk_permission", "prompt_injection", "unauthorized_access"):
        return defs.RISK_HIGH, "高风险意图，须主管审批或拒绝"
    if intent == "permission_request" or category == "account_permission":
        return defs.RISK_MEDIUM, "普通权限申请，需 IT 审批"
    if intent == "system_fault" or category == "system_fault":
        return defs.RISK_MEDIUM, "系统故障处理（只读诊断，视工具而定）"
    return defs.RISK_LOW, "只读/知识库类，可自动执行"


def check_grant_risk(system: str, permission: str) -> tuple[str, str]:
    """grant_permission 动态风险：命中生产/敏感目标或 admin/root 关键词升级 HIGH。"""
    if (system in defs.GRANT_UPGRADE_SYSTEMS
            or any(k in (permission or "").lower() for k in defs.GRANT_UPGRADE_KEYWORDS)):
        return defs.RISK_HIGH, "授权目标为生产/敏感系统或管理员权限，升级高风险"
    return defs.RISK_MEDIUM, "普通项目权限"