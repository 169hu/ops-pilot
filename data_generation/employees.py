"""10 虚拟员工：覆盖不同角色与权限基线。

数据设计覆盖（对齐 README）：
- 角色：employee(员工)/it_staff(IT)/manager(主管)，对应 Tool Gateway 的调用者角色校验。
- 权益基线：employee 无生产库/管理员权限，it_staff 可申请普通项目权限，manager 可审批。
- risk_level：标记"高风险账号"（历史上越权/被注入的用户，用于攻击样例）。
"""
import random

from .constants import ROLES


def _make(idx: int, name: str, email: str, department: str,
          role: str, risk_level: str) -> dict:
    return {
        "user_id": f"U{idx:03d}",
        "name": name,
        "email": email,
        "department": department,
        "role": role,                     # employee / it_staff / manager
        "risk_level": risk_level,         # LOW / MEDIUM / HIGH
        # 权益基线：能申请的权限边界，Tool Gateway 据此判越权
        "can_grant_targets": {
            "employee":  ["gitlab", "vpn"],
            "it_staff":  ["gitlab", "vpn", "crm", "mail"],
            "manager":   ["gitlab", "vpn", "crm", "mail", "prod_db"],
        }.get(role, []),
        "can_approve": role == "manager",
        "is_protected_account": risk_level == "HIGH",
        "created_at": "2024-03-01T09:00:00+08:00",
    }


_EMPLOYEE_SPECS = [
    # (姓名, 部门, 角色, 风险)
    ("张三", "研发", "employee", "LOW"),
    ("李四", "研发", "employee", "LOW"),
    ("王五", "研发", "it_staff", "LOW"),
    ("赵六", "运维", "it_staff", "LOW"),
    ("陈七", "销售", "employee", "LOW"),
    ("刘八", "财务", "employee", "LOW"),
    ("孙九", "运维", "manager", "LOW"),
    ("周十", "研发", "manager", "LOW"),
    ("吴小明", "研发", "it_staff", "HIGH"),   # 高风险账号：历史上越权
    ("郑大强", "财务", "it_staff", "HIGH"),   # 高风险账号：被注入过
]


def generate(seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    return [
        _make(i + 1, name, f"user{i+1}@{_domain(dep)}",
              dep, role, risk)
        for i, (name, dep, role, risk) in enumerate(_EMPLOYEE_SPECS)
    ]


def _domain(department: str) -> str:
    return {"研发": "rd", "运维": "ops", "销售": "sales",
            "财务": "fin"}.get(department, "corp") + ".ops.test"