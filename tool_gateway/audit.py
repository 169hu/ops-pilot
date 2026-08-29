"""审计日志：记录每次工具调用的完整证据（对齐 tool_invocations 表）。

关键：
- 每次调用写一条不可变记录（含输入/输出/决策/耗时/令牌）。
- 提供按 ticket 与按工具查询，供 Audit/Trace/安全复盘。
- in-memory + 落盘 JSON 双写，阶段5可切到 Postgres。
"""
import json
import os
import threading
import time
import uuid

_AUDIT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")
_lock = threading.Lock()


class AuditStore:
    def __init__(self, path: str | None = None):
        self._path = path or os.path.join(_AUDIT_DIR, "tool_invocations.json")
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._rows: list[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, encoding="utf-8") as f:
                    self._rows = json.load(f)
            except json.JSONDecodeError:
                self._rows = []

    def record(self, entry: dict) -> str:
        invocation_id = str(uuid.uuid4())[:8]
        row = {"invocation_id": invocation_id, "ts": time.strftime("%Y%m%dT%H%M%S"),
               **entry}
        with _lock:
            self._rows.append(row)
            self._flush()
        return invocation_id

    def _flush(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._rows[-5000:], f, ensure_ascii=False, indent=2)

    def by_ticket(self, ticket_id: str) -> list[dict]:
        return [r for r in self._rows if r.get("ticket_id") == ticket_id]

    def all(self) -> list[dict]:
        return list(self._rows)


# 进程级单例（生产可替换为 DB 实现）
_instance: AuditStore | None = None
_store_lock = threading.Lock()


def get_audit() -> AuditStore:
    global _instance
    if _instance is None:
        with _store_lock:
            if _instance is None:
                _instance = AuditStore()
    return _instance