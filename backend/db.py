"""
Firestore CRUD helpers for the OmniCloud FinOps Agent.

Collections:
  - users/{userId}         → AWS profile, preferred regions
  - chat_sessions/{id}     → messages[], userId, createdAt
  - saved_reports/{id}     → title, content, userId, sessionId, createdAt

Falls back to in-memory storage if Firebase credentials are not available.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
import uuid
from pathlib import Path

from backend.config import FIREBASE_CREDENTIALS_PATH

logger = logging.getLogger("omnicloud.db")

_db = None
_use_memory = False

# In-memory fallback stores
_mem_sessions: dict = {}
_mem_reports: dict = {}


def init_firebase():
    """Initialize Firebase Admin SDK. Falls back to in-memory if credentials missing."""
    global _db, _use_memory

    if _db is not None:
        return _db

    cred_path = Path(FIREBASE_CREDENTIALS_PATH)
    if not cred_path.exists():
        logger.warning(
            f"Firebase credentials not found at {cred_path}. "
            "Using in-memory storage (data will not persist across restarts)."
        )
        _use_memory = True
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            cred = credentials.Certificate(str(cred_path))
            firebase_admin.initialize_app(cred)

        _db = firestore.client()
        logger.info("Firebase Firestore initialized successfully.")
        return _db
    except Exception as e:
        logger.warning(f"Firebase init failed: {e}. Using in-memory storage.")
        _use_memory = True
        return None


def get_db():
    """Get (or create) the Firestore client. Returns None if using memory."""
    global _db, _use_memory
    if _use_memory:
        return None
    if _db is None:
        return init_firebase()
    return _db


# ── Sessions ───────────────────────────────────────────────────────────

def create_session(user_id: str) -> str:
    """Create a new chat session. Returns the session ID."""
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    if _use_memory:
        _mem_sessions[session_id] = {
            "userId": user_id,
            "messages": [],
            "createdAt": now,
            "updatedAt": now,
        }
        return session_id

    db = get_db()
    db.collection("chat_sessions").document(session_id).set({
        "userId": user_id,
        "messages": [],
        "createdAt": now,
        "updatedAt": now,
    })
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """Retrieve a chat session by ID."""
    if _use_memory:
        session = _mem_sessions.get(session_id)
        if session:
            return {**session, "id": session_id}
        return None

    db = get_db()
    doc = db.collection("chat_sessions").document(session_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


def list_sessions(user_id: str, limit: int = 50) -> list[dict]:
    """List chat sessions for a user, newest first."""
    if _use_memory:
        results = []
        for sid, data in _mem_sessions.items():
            if data.get("userId") != user_id:
                continue
            messages = data.get("messages", [])
            preview = ""
            for msg in messages:
                if msg.get("role") == "user":
                    preview = msg.get("content", "")[:80]
                    break
            results.append({
                "id": sid,
                "preview": preview,
                "createdAt": data.get("createdAt"),
                "updatedAt": data.get("updatedAt"),
            })
        results.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return results[:limit]

    try:
        db = get_db()
        # Simple query without orderBy to avoid requiring composite index
        query = (
            db.collection("chat_sessions")
            .where("userId", "==", user_id)
            .limit(limit)
        )
        results = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            messages = data.get("messages", [])
            preview = ""
            for msg in messages:
                if msg.get("role") == "user":
                    preview = msg.get("content", "")[:80]
                    break
            results.append({
                "id": doc.id,
                "preview": preview,
                "createdAt": data.get("createdAt"),
                "updatedAt": data.get("updatedAt"),
            })
        # Sort in Python instead of Firestore to avoid index requirement
        results.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return results
    except Exception as e:
        logger.warning(f"Firestore list_sessions failed: {e}. Returning empty list.")
        return []


def append_message(session_id: str, role: str, content: str):
    """Append a message to a chat session."""
    now = datetime.now(timezone.utc).isoformat()

    if _use_memory:
        if session_id in _mem_sessions:
            _mem_sessions[session_id]["messages"].append({
                "role": role,
                "content": content,
                "timestamp": now,
            })
            _mem_sessions[session_id]["updatedAt"] = now
        return

    from firebase_admin import firestore
    db = get_db()
    db.collection("chat_sessions").document(session_id).update({
        "messages": firestore.ArrayUnion([{
            "role": role,
            "content": content,
            "timestamp": now,
        }]),
        "updatedAt": now,
    })


# ── Reports ────────────────────────────────────────────────────────────

def save_report(
    user_id: str,
    session_id: str,
    title: str,
    content: str,
) -> str:
    """Save a generated cost report. Returns the report ID."""
    report_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    if _use_memory:
        _mem_reports[report_id] = {
            "userId": user_id,
            "sessionId": session_id,
            "title": title,
            "content": content,
            "createdAt": now,
        }
        return report_id

    db = get_db()
    db.collection("saved_reports").document(report_id).set({
        "userId": user_id,
        "sessionId": session_id,
        "title": title,
        "content": content,
        "createdAt": now,
    })
    return report_id


def list_reports(user_id: str, limit: int = 50) -> list[dict]:
    """List saved reports for a user, newest first."""
    if _use_memory:
        results = []
        for rid, data in _mem_reports.items():
            if data.get("userId") != user_id:
                continue
            results.append({**data, "id": rid})
        results.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return results[:limit]

    try:
        db = get_db()
        # Simple query without orderBy to avoid index requirement
        query = (
            db.collection("saved_reports")
            .where("userId", "==", user_id)
            .limit(limit)
        )
        results = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            results.append(data)
        results.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return results
    except Exception as e:
        logger.warning(f"Firestore list_reports failed: {e}. Returning empty list.")
        return []
