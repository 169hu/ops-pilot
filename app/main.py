"""OpsPilot FastAPI 应用：工单 Agent 的 REST API + 静态托管前端。

启动：
    .venv\\Scripts\\python -m uvicorn app.main:app --reload --port 8000
"""
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.store import get_store
from tool_gateway import definitions as defs

app = FastAPI(title="OpsPilot API", version="0.4.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ops-pilot"}


@app.get("/api/tools")
def tools():
    reg = defs.tool_registry()
    return [{"name": n, "label": t["label"], "returns": t["description"],
             "risk_level": t["risk_level"],
             "requires_approval": t["requires_approval"]}
            for n, t in reg.items()]


@app.get("/api/tickets")
def list_tickets(status: str | None = None, category: str | None = None,
                 q: str | None = None, limit: int = Query(60, le=200)):
    rows = get_store().list_tickets(status, category, q, limit)
    return {"total": len(rows), "items": rows}


@app.get("/api/tickets/{ticket_id}")
def ticket_detail(ticket_id: str):
    s = get_store()
    t = s.get_ticket(ticket_id)
    if not t:
        raise HTTPException(404, "工单不存在")
    out = dict(t)
    out["requester"] = s.requester(t)
    out["messages"] = s.messages_of(ticket_id)
    out["last_run"] = s.runs.get(ticket_id)
    return out


@app.post("/api/tickets/{ticket_id}/run")
def run(ticket_id: str, role: str = Query("it_staff")):
    s = get_store()
    try:
        return s.run(ticket_id, role)
    except KeyError:
        raise HTTPException(404, "工单不存在")


@app.get("/api/approvals")
def approvals():
    return {"items": get_store().list_approvals()}


@app.post("/api/approvals/{ticket_id}/approve")
def approve(ticket_id: str):
    try:
        return get_store().approve(ticket_id)
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.get("/api/audit")
def audit(ticket_id: str | None = None, limit: int = Query(200, le=1000)):
    rows = get_store().audit(ticket_id, limit)
    return {"total": len(rows), "items": rows}


@app.get("/api/eval")
def eval_report():
    return get_store().eval_report()


# 托管前端构建产物（ui/dist），生产由同一端口提供；SPA 路由回退到 index.html
_UI_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "dist")
if os.path.isdir(_UI_DIST):
    from fastapi.responses import FileResponse

    _INDEX = os.path.join(_UI_DIST, "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path and not full_path.strip("/"):
            full_path = ""
        p = os.path.abspath(os.path.join(_UI_DIST, full_path or ""))
        if full_path and os.path.isfile(p) and os.path.commonpath(
                [p, os.path.abspath(_UI_DIST)]) == os.path.abspath(_UI_DIST):
            return FileResponse(p)
        return FileResponse(_INDEX)