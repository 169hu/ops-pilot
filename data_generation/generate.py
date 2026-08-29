"""OpsPilot 阶段0 · 仿真数据集生成器主入口。

用法：
    python -m data_generation.generate [--out data/generated] [--seed 42]

生成文件（data/generated/）：
    employees.json / systems.json / kb_documents.json / kb_chunks.json
    tickets.json / ticket_messages.json / history.json
    golden_tickets.json / attack_cases.json

确定性：使用固定 seed，可复现。
"""
import argparse
import json
import os

from .constants import SYSTEMS
from .employees import generate as gen_employees
from .knowledge import generate as gen_knowledge
from .tickets import generate as gen_tickets
from .golden import generate as gen_golden
from .attacks import generate as gen_attacks
from . import constants


def _dump(dir_path: str, filename: str, data):
    with open(os.path.join(dir_path, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    n = len(data) if isinstance(data, list) else "-"
    print(f"  ✓ {filename}  ({n} 条)")


def main():
    ap = argparse.ArgumentParser(description="生成 OpsPilot 仿真数据集")
    ap.add_argument("--out", default=os.path.join("data", "generated"))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    print(f"[OpsPilot] 生成仿真数据集 (seed={args.seed})\n")

    # 系统（常量）
    systems = [
        {"system_id": f"SYS{i+1:02d}", "code": code, "name": info["name"],
         "kind": info["kind"], "protected": info["protected"]}
        for i, (code, info) in enumerate(SYSTEMS.items())
    ]
    _dump(args.out, "systems.json", systems)

    employees = gen_employees(args.seed)
    _dump(args.out, "employees.json", employees)

    docs, chunks = gen_knowledge(args.seed)
    _dump(args.out, "kb_documents.json", docs)
    _dump(args.out, "kb_chunks.json", chunks)

    tickets_pack = gen_tickets(employees, args.seed)
    _dump(args.out, "tickets.json", tickets_pack["tickets"])
    _dump(args.out, "ticket_messages.json", tickets_pack["ticket_messages"])
    _dump(args.out, "history.json", tickets_pack["history"])

    _dump(args.out, "golden_tickets.json", gen_golden(args.seed))
    _dump(args.out, "attack_cases.json", gen_attacks(args.seed))

    # 汇总
    summary = {
        "seed": args.seed,
        "units": {
            "employees": len(employees),
            "systems": len(systems),
            "kb_documents": len(docs),
            "kb_chunks": len(chunks),
            "tickets": len(tickets_pack["tickets"]),
            "ticket_messages": len(tickets_pack["ticket_messages"]),
            "history": len(tickets_pack["history"]),
            "golden_tickets": len(gen_golden(args.seed)),
            "attack_cases": len(gen_attacks(args.seed)),
        },
    }
    _dump(args.out, "summary.json", summary)
    print("\n[OpsPilot] 数据集生成完成 →", args.out)


if __name__ == "__main__":
    main()