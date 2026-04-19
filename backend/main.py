"""
FastAPI application for the OmniCloud FinOps Agent.

Endpoints:
  POST /api/chat        → Agentic chat (Ollama + MCP tools + Firebase)
  GET  /api/sessions    → List chat sessions for a user
  GET  /api/sessions/{id} → Get full session history
  POST /api/reports     → Save a generated report
  GET  /api/reports     → List saved reports
  GET  /api/tools       → List available MCP tools
  GET  /api/health      → Health check
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend import db
from backend.agent import run_agent
from backend.mcp_tools import get_tool_schemas, _KNOWLEDGE_TOPICS, _get_focus_df, _get_ri_recs_df
from backend.config import TEMPLATES_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnicloud")


# ── Lifespan ───────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Firebase on startup."""
    logger.info("Initializing Firebase...")
    try:
        db.init_firebase()
        logger.info("Firebase initialized successfully")
    except Exception as e:
        logger.warning(f"Firebase init skipped (will retry on first request): {e}")
    yield


# ── App ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="OmniCloud FinOps Agent",
    description="Shift-Left Cloud Cost Intelligence — Multi-cloud agentic FinOps system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev
        "http://localhost:5174",   # Vite dev (fallback port)
        "http://localhost:3000",   # Fallback
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ──────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: str = "default-user"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls_made: list = []


class ReportRequest(BaseModel):
    user_id: str = "default-user"
    session_id: str
    title: str
    content: str


# ── Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "OmniCloud FinOps Agent"}


@app.get("/api/tools")
async def list_tools():
    """List all available MCP tools."""
    schemas = get_tool_schemas()
    return {
        "tools": [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "parameters": t["function"]["parameters"],
            }
            for t in schemas
        ]
    }


@app.get("/api/dashboard")
async def get_dashboard():
    """
    Return real KPI metrics computed from Azure billing CSV.
    Provides: total spend, top services, idle resources, anomalies, RI savings.
    """
    try:
        import pandas as pd

        df = _get_focus_df()

        total_spend = float(df["EffectiveCost"].sum())

        # Top services by spend
        svc_costs = (
            df.groupby("ServiceName")["EffectiveCost"]
            .sum()
            .sort_values(ascending=False)
            .head(8)
        )
        top_services = [
            {
                "service": svc,
                "spend": round(float(cost), 2),
                "pct": round(float(cost / total_spend * 100), 1) if total_spend > 0 else 0,
            }
            for svc, cost in svc_costs.items()
        ]

        # Idle resources (cost between 0 and 0.01)
        idle_resources = []
        if "ResourceName" in df.columns:
            resource_costs = (
                df.groupby(["ResourceName", "ServiceName", "SubAccountName"])["EffectiveCost"]
                .sum()
            )
            idle = resource_costs[
                (resource_costs >= 0) & (resource_costs <= 0.01) &
                (resource_costs.index.get_level_values(0).str.strip() != "")
            ].sort_values().head(20)

            for (res, svc, acct), cost in idle.items():
                res_str = str(res)
                if res_str and res_str != "nan" and res_str.strip():
                    idle_resources.append({
                        "id": res_str[:40],
                        "name": res_str[:40],
                        "type": svc,
                        "account": acct,
                        "cost": round(float(cost), 4),
                        "status": "Idle" if cost > 0 else "Unused",
                        "risk": "high" if cost == 0 else "medium",
                    })

        # Cost anomalies: services > 1.5x average
        avg_svc_cost = float(svc_costs.mean())
        anomaly_count = int((svc_costs > avg_svc_cost * 1.5).sum())

        # Top accounts
        acct_costs = (
            df.groupby("SubAccountName")["EffectiveCost"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
        )
        top_accounts = [
            {"account": acct, "spend": round(float(cost), 2)}
            for acct, cost in acct_costs.items()
        ]

        # RI potential savings
        ri_savings = 0.0
        try:
            ri_df = _get_ri_recs_df()
            if "NetSavings" in ri_df.columns:
                ri_savings = float(pd.to_numeric(ri_df["NetSavings"], errors="coerce").fillna(0).sum())
        except Exception:
            pass

        return {
            "total_spend": round(total_spend, 2),
            "idle_resource_count": len(idle_resources),
            "anomaly_count": anomaly_count,
            "ri_potential_savings": round(ri_savings, 2),
            "top_services": top_services,
            "idle_resources": idle_resources[:10],
            "top_accounts": top_accounts,
            "data_size": len(df),
        }

    except FileNotFoundError as e:
        logger.warning(f"Dashboard data not available: {e}")
        return {
            "total_spend": 0,
            "idle_resource_count": 0,
            "anomaly_count": 0,
            "ri_potential_savings": 0,
            "top_services": [],
            "idle_resources": [],
            "top_accounts": [],
            "data_size": 0,
            "error": "Billing data file not found. Please configure EA_FOCUS_CSV_PATH.",
        }
    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        return {"error": str(e), "total_spend": 0, "top_services": [], "idle_resources": []}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Main agentic chat endpoint.

    1. Create or resume a session
    2. Fetch history from Firebase
    3. Run the agentic loop (Ollama + MCP)
    4. Persist messages to Firebase
    5. Return the assistant response
    """
    try:
        # Create or reuse session
        if req.session_id:
            session = db.get_session(req.session_id)
            if session is None:
                raise HTTPException(status_code=404, detail="Session not found")
            session_id = req.session_id
        else:
            session_id = db.create_session(req.user_id)
            session = {"messages": []}

        # Get prior messages (strip timestamps for the LLM)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in session.get("messages", [])
        ]

        # Persist the user message
        db.append_message(session_id, "user", req.message)

        # Run the agentic loop
        result = await run_agent(
            messages=history,
            user_message=req.message,
            session_id=session_id,
        )

        # Persist the assistant message
        db.append_message(session_id, "assistant", result["response"])

        return ChatResponse(
            response=result["response"],
            session_id=session_id,
            tool_calls_made=result.get("tool_calls_made", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def list_sessions(user_id: str = "default-user"):
    """List chat sessions for a user."""
    try:
        sessions = db.list_sessions(user_id)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"List sessions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get full session history."""
    try:
        session = db.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports")
async def save_report(req: ReportRequest):
    """Save a generated cost report."""
    try:
        report_id = db.save_report(
            user_id=req.user_id,
            session_id=req.session_id,
            title=req.title,
            content=req.content,
        )
        return {"report_id": report_id, "status": "saved"}
    except Exception as e:
        logger.error(f"Save report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports")
async def list_reports(user_id: str = "default-user"):
    """List saved reports for a user."""
    try:
        reports = db.list_reports(user_id)
        return {"reports": reports}
    except Exception as e:
        logger.error(f"List reports error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge")
async def list_knowledge():
    """List available FinOps knowledge base topics."""
    topics = [
        {
            "key": key,
            "title": info["title"],
            "description": info["description"],
        }
        for key, info in _KNOWLEDGE_TOPICS.items()
    ]
    return {"topics": topics}


@app.get("/api/templates/{name}")
async def get_template(name: str):
    """Serve a report template as raw markdown."""
    template_file = TEMPLATES_DIR / f"{name}.md"
    if not template_file.exists():
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
    content = template_file.read_text(encoding="utf-8")
    return {"name": name, "content": content}
