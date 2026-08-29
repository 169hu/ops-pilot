"""OpsPilot 阶段0 · 数据集自检：校验生成数据的分布与关键不变量。

用法：python -m data_generation.validate [--data data/generated]
"""
import argparse
import json
import collections
import os


def _load(base, name):
    with open(os.path.join(base, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join("data", "generated"))
    args = ap.parse_args()
    errs = []

    def check(cond, msg):
        print(("  ✓ " if cond else "  ✗ ") + msg)
        if not cond:
            errs.append(msg)

    print("== OpsPilot 数据集自检 ==")
    emp = _load(args.data, "employees.json")
    sys_ = _load(args.data, "systems.json")
    docs = _load(args.data, "kb_documents.json")
    chunks = _load(args.data, "kb_chunks.json")
    tickets = _load(args.data, "tickets.json")
    msgs = _load(args.data, "ticket_messages.json")
    hist = _load(args.data, "history.json")
    golden = _load(args.data, "golden_tickets.json")
    att = _load(args.data, "attack_cases.json")

    print("\n-- 规模 --")
    check(len(emp) == 10, f"员工 10 名 (实际 {len(emp)})")
    check(len(sys_) == 5, f"系统 5 个 (实际 {len(sys_)})")
    check(len(docs) == 30, f"知识库文档 30 篇 (实际 {len(docs)})")
    check(len(chunks) > len(docs), f"切片 {len(chunks)} 条 (>文档数)")
    check(len(tickets) == 80, f"工单 80 条 (实际 {len(tickets)})")
    check(len(hist) == 20, f"历史记录 20 条 (实际 {len(hist)})")
    check(len(golden) == 30, f"golden 30 条 (实际 {len(golden)})")
    check(len(att) == 10, f"攻击 10 条 (实际 {len(att)})")

    print("\n-- 工单分布 --")
    print("   risk:", dict(collections.Counter(t["risk_level"] for t in tickets)))
    print("   status:", dict(collections.Counter(t["status"] for t in tickets)))
    print("   category:", dict(collections.Counter(t["category"] for t in tickets)))
    check(all(t["risk_level"] in ("LOW", "MEDIUM", "HIGH") for t in tickets),
          "工单风险等级合法")
    check(hist_t := [t for t in tickets if t["ticket_id"] in {h["ticket_id"] for h in hist}],
          "历史记录均对应已解决工单")
    check(all(t["status"] == "RESOLVED" for t in hist_t), "历史工单状态均为 RESOLVED")

    print("\n-- golden 分类 (应 8/8/4/5/5) --")
    gold_cat = collections.Counter(g["expected_intent"] for g in golden)
    print("   ", dict(gold_cat))
    target = {"permission_request": 8, "system_fault": 8,
              "general_query": 4, "high_risk_request": 5, "attack": 5}
    check(all(gold_cat.get(k, 0) == v for k, v in target.items()),
          "golden 五类数量与方案一致 {8/8/4/5/5}")

    print("\n-- 攻击红线 --")
    check(all(a["expected_risk"] == "HIGH" or a["attack_type"] == "missing_param"
              for a in att), "攻击样例风险等级合规(除参数缺失外均为HIGH)")
    check(all(("grant_permission" in (a["must_not_call"] or [])) or not (a["must_not_call"] or [])
              for a in att if a["expected_action"] != "require_info"),
          "攻击样例若含工具禁令则必含高危工具")

    print("\n-- 权限基线 --")
    risky = [e for e in emp if e["risk_level"] == "HIGH"]
    check(len(risky) == 2, f"高风险账号 2 个 (实际 {len(risky)})")
    check(all(e["can_approve"] == (e["role"] == "manager") for e in emp),
          "审批权归属 manager")

    print("\n-- 汇总：{} 项检查，{} 项失败 --".format(
        "全部通过" if not errs else "", len(errs)))
    for e in errs:
        print("   FAIL:", e)
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())