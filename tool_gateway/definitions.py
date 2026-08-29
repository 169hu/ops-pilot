"""6 工具注册表：名称、作用、风险、审批策略、出入参 schema、启用状态（对齐方案规则表）。

为什么在这里定义而非散落各处：
- 单点登记 = 可审计的"工具目录"，Tool Gateway 校验时统一读取，杜绝白名单外调用。
- adapter 只实现"执行"，规则（风险/审批/权限）全部收敛在 Gateway，职责分离。
"""

from enum import Enum

RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"


class ToolStatus(Enum):
    DISABLED = "DISABLED"
    ENABLED = "ENABLED"


# 调用最终状态
STATUS_OK = "OK"
STATUS_PENDING_APPROVAL = "PENDING_APPROVAL"
STATUS_REJECTED = "REJECTED"
STATUS_ESCALATED = "ESCALATED"
STATUS_BLOCKED = "BLOCKED"        # 攻击防护拦截
STATUS_ERROR = "ERROR"
STATUS_INFO_REQUIRED = "INFO_REQUIRED"


# 每工具：(注册名, 中文名, 作用, 风险, 是否需审批, 自动执行条件, 拒绝条件, input_schema)
_TOOLS = [
    {
        "name": "search_kb",
        "label": "检索知识库",
        "description": "检索运维知识库，返回匹配文档/切片",
        "risk_level": RISK_LOW,
        "requires_approval": False,
        "auto_condition": "任意工单可用",
        "deny_condition": "无",
        "roles_allowed": ["employee", "it_staff", "manager"],
        "input_schema": {
            "query": {"type": "string", "required": True, "desc": "检索关键词/问题"},
            "top_k": {"type": "integer", "required": False, "default": 5},
        },
    },
    {
        "name": "query_user_profile",
        "label": "查询员工信息",
        "description": "查询员工基本信息与权限基线",
        "risk_level": RISK_LOW,
        "requires_approval": False,
        "auto_condition": "IT/主管角色可用",
        "deny_condition": "查询非本工单相关用户（越权查人）",
        "roles_allowed": ["it_staff", "manager"],
        "input_schema": {
            "user_id": {"type": "string", "required": True, "desc": "被查用户 ID"},
        },
    },
    {
        "name": "query_system_status",
        "label": "查询系统状态",
        "description": "查询虚拟系统当前运行状态",
        "risk_level": RISK_LOW,
        "requires_approval": False,
        "auto_condition": "只读查询",
        "deny_condition": "无",
        "roles_allowed": ["employee", "it_staff", "manager"],
        "input_schema": {
            "system": {"type": "string", "required": True, "desc": "系统 code"},
        },
    },
    {
        "name": "check_permission_policy",
        "label": "检查权限策略",
        "description": "查询权限策略，判断某申请是否符合最小权限/越权要求",
        "risk_level": RISK_LOW,
        "requires_approval": False,
        "auto_condition": "权限类工单",
        "deny_condition": "无",
        "roles_allowed": ["it_staff", "manager"],
        "input_schema": {
            "subject": {"type": "string", "required": True, "desc": "申请权限的主体/用户"},
            "target": {"type": "string", "required": True, "desc": "目标系统/资源"},
            "permission": {"type": "string", "required": True, "desc": "拟授予权限"},
        },
    },
    {
        "name": "grant_permission",
        "label": "授予系统权限",
        "description": "授予系统权限（变更操作，中高风险）",
        "risk_level": RISK_MEDIUM,   # 默认 MEDIUM；若目标为生产/敏感则升级 HIGH
        "requires_approval": True,
        "auto_condition": "普通项目权限 + 已审批",
        "deny_condition": "生产库/admin/root/跨部门越权",
        "roles_allowed": ["it_staff", "manager"],
        "input_schema": {
            "user_id": {"type": "string", "required": True, "desc": "被授权用户 ID"},
            "system": {"type": "string", "required": True, "desc": "目标系统 code"},
            "permission": {"type": "string", "required": True, "desc": "权限级别"},
        },
    },
    {
        "name": "create_incident_task",
        "label": "创建升级任务",
        "description": "创建升级处理任务（解决失败/高风险升级）",
        "risk_level": RISK_MEDIUM,
        "requires_approval": False,    # 可选审批
        "auto_condition": "故障未解决或高风险升级",
        "deny_condition": "参数缺失",
        "roles_allowed": ["it_staff", "manager"],
        "input_schema": {
            "ticket_id": {"type": "string", "required": True, "desc": "工单号"},
            "reason": {"type": "string", "required": True, "desc": "升级原因"},
        },
    },
]

# 风险动态升级规则：grant_permission 命中以下目标强制 HIGH
GRANT_UPGRADE_SYSTEMS = {"prod_db"}
GRANT_UPGRADE_KEYWORDS = ("admin", "root")


def tool_registry() -> dict:
    """返回 {name: definition} 的注册表视图。"""
    return {t["name"]: dict(t) for t in _TOOLS}


def enabled_names() -> list[str]:
    return [t["name"] for t in _TOOLS]


def get_tool(name: str) -> dict | None:
    return {t["name"]: dict(t) for t in _TOOLS}.get(name)