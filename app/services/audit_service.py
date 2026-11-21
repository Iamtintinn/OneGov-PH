"""Reusable backend audit logging service."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import has_request_context, request
from flask_login import current_user

from app import db
from app.models.audit_log import AuditLog

PHT = timezone(timedelta(hours=8))
SENSITIVE_KEYS = {
    "password", "password_hash", "current_password", "new_password", "confirm_password",
    "otp", "otp_code", "code", "api_key", "secret", "token", "csrf_token",
    "maya_secret", "maya_key", "card", "cvv", "pin",
}


def _sanitize(value: Any, depth: int = 0):
    if depth > 4:
        return "[truncated]"
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            lk = str(k).lower()
            if any(s in lk for s in SENSITIVE_KEYS):
                out[k] = "[redacted]"
            else:
                out[k] = _sanitize(v, depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_sanitize(v, depth + 1) for v in value[:50]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str) and len(value) > 500:
            return value[:500] + "…"
        return value
    return str(value)


def _request_ip():
    if not has_request_context():
        return None
    fwd = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return (fwd or request.remote_addr or "")[:64] or None


def _request_ua():
    if not has_request_context():
        return None
    return (request.user_agent.string or "")[:500] or None


def _actor_snapshot(user=None):
    user = user or (current_user if getattr(current_user, "is_authenticated", False) else None)
    if not user:
        return None, None, "System", "system"
    name = getattr(user, "full_name", None) or getattr(user, "email", None) or f"User {getattr(user, 'user_id', '')}"
    role = getattr(user, "role_label", None) or getattr(user, "role", None) or "unknown"
    dept_id = getattr(user, "department_id", None)
    return getattr(user, "user_id", None), dept_id, str(name)[:200], str(role)[:60]


_audit_table_ready = False

def ensure_audit_table():
    global _audit_table_ready
    if _audit_table_ready:
        return
    try:
        from sqlalchemy import inspect, text
        insp = inspect(db.engine)
        if not insp.has_table("audit_logs"):
            AuditLog.__table__.create(bind=db.engine, checkfirst=True)
            _audit_table_ready = True
            return

        cols = {c["name"] for c in insp.get_columns("audit_logs")}
        # Migrate legacy schema (log_id/action_performed/recorded_at, no id)
        if "id" not in cols and "log_id" in cols:
            try:
                # add new columns first
                legacy_adds = [
                    ("activity_id", "ALTER TABLE audit_logs ADD COLUMN activity_id VARCHAR(40) NULL"),
                    ("department_id", "ALTER TABLE audit_logs ADD COLUMN department_id INT UNSIGNED NULL"),
                    ("user_name_snapshot", "ALTER TABLE audit_logs ADD COLUMN user_name_snapshot VARCHAR(200) NOT NULL DEFAULT ''"),
                    ("user_role", "ALTER TABLE audit_logs ADD COLUMN user_role VARCHAR(60) NOT NULL DEFAULT ''"),
                    ("activity_type", "ALTER TABLE audit_logs ADD COLUMN activity_type VARCHAR(120) NOT NULL DEFAULT ''"),
                    ("module", "ALTER TABLE audit_logs ADD COLUMN module VARCHAR(80) NOT NULL DEFAULT ''"),
                    ("record_id", "ALTER TABLE audit_logs ADD COLUMN record_id VARCHAR(120) NULL"),
                    ("previous_value", "ALTER TABLE audit_logs ADD COLUMN previous_value JSON NULL"),
                    ("new_value", "ALTER TABLE audit_logs ADD COLUMN new_value JSON NULL"),
                    ("ip_address", "ALTER TABLE audit_logs ADD COLUMN ip_address VARCHAR(64) NULL"),
                    ("user_agent", "ALTER TABLE audit_logs ADD COLUMN user_agent VARCHAR(500) NULL"),
                    ("activity_status", "ALTER TABLE audit_logs ADD COLUMN activity_status VARCHAR(20) NOT NULL DEFAULT 'Success'"),
                    ("created_at", "ALTER TABLE audit_logs ADD COLUMN created_at DATETIME NULL"),
                ]
                for col, stmt in legacy_adds:
                    if col not in cols:
                        try:
                            db.session.execute(text(stmt)); db.session.commit()
                        except Exception:
                            db.session.rollback()
                # copy legacy values where possible
                try:
                    db.session.execute(text("UPDATE audit_logs SET activity_type=COALESCE(NULLIF(activity_type,''), LEFT(COALESCE(action_performed,''),120), 'Legacy Activity') WHERE 1=1"))
                    db.session.commit()
                except Exception: db.session.rollback()
                try:
                    db.session.execute(text("UPDATE audit_logs SET module=CASE WHEN module='' OR module IS NULL THEN 'System' ELSE module END"))
                    db.session.commit()
                except Exception: db.session.rollback()
                try:
                    db.session.execute(text("UPDATE audit_logs SET created_at=COALESCE(created_at, recorded_at, CURRENT_TIMESTAMP)"))
                    db.session.commit()
                except Exception: db.session.rollback()
                try:
                    db.session.execute(text("UPDATE audit_logs SET description=COALESCE(description,'')"))
                    db.session.commit()
                except Exception: db.session.rollback()
                # replace PK log_id -> id
                try:
                    db.session.execute(text("ALTER TABLE audit_logs DROP PRIMARY KEY"))
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                try:
                    db.session.execute(text("ALTER TABLE audit_logs ADD COLUMN id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST"))
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                try:
                    db.session.execute(text("ALTER TABLE audit_logs MODIFY COLUMN log_id INT UNSIGNED NULL"))
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                try:
                    db.session.execute(text("UPDATE audit_logs SET activity_id=CONCAT('AUD-LEGACY-', LPAD(id,8,'0')) WHERE activity_id IS NULL OR activity_id=''"))
                    db.session.commit()
                except Exception: db.session.rollback()
                try:
                    db.session.execute(text("CREATE UNIQUE INDEX uq_audit_logs_activity_id ON audit_logs(activity_id)"))
                    db.session.commit()
                except Exception: db.session.rollback()
            except Exception:
                db.session.rollback()
            # refresh cols
            insp = inspect(db.engine)
            cols = {c["name"] for c in insp.get_columns("audit_logs")} if insp.has_table("audit_logs") else set()

        if "id" not in cols:
            # unknown schema; try non-destructive add without PK if possible
            try:
                db.session.execute(text("ALTER TABLE audit_logs ADD COLUMN id INT UNSIGNED NULL"))
                db.session.commit()
            except Exception:
                db.session.rollback()
            insp = inspect(db.engine)
            cols = {c["name"] for c in insp.get_columns("audit_logs")}

        stmts = []
        def add(col, ddl):
            if col not in cols: stmts.append((col, ddl))
        add("activity_id", "ALTER TABLE audit_logs ADD COLUMN activity_id VARCHAR(40) NULL")
        add("user_id", "ALTER TABLE audit_logs ADD COLUMN user_id INT UNSIGNED NULL")
        add("department_id", "ALTER TABLE audit_logs ADD COLUMN department_id INT UNSIGNED NULL")
        add("user_name_snapshot", "ALTER TABLE audit_logs ADD COLUMN user_name_snapshot VARCHAR(200) NOT NULL DEFAULT ''")
        add("user_role", "ALTER TABLE audit_logs ADD COLUMN user_role VARCHAR(60) NOT NULL DEFAULT ''")
        add("activity_type", "ALTER TABLE audit_logs ADD COLUMN activity_type VARCHAR(120) NOT NULL DEFAULT ''")
        add("module", "ALTER TABLE audit_logs ADD COLUMN module VARCHAR(80) NOT NULL DEFAULT ''")
        add("description", "ALTER TABLE audit_logs ADD COLUMN description VARCHAR(600) NOT NULL DEFAULT ''")
        add("record_id", "ALTER TABLE audit_logs ADD COLUMN record_id VARCHAR(120) NULL")
        add("previous_value", "ALTER TABLE audit_logs ADD COLUMN previous_value JSON NULL")
        add("new_value", "ALTER TABLE audit_logs ADD COLUMN new_value JSON NULL")
        add("ip_address", "ALTER TABLE audit_logs ADD COLUMN ip_address VARCHAR(64) NULL")
        add("user_agent", "ALTER TABLE audit_logs ADD COLUMN user_agent VARCHAR(500) NULL")
        add("activity_status", "ALTER TABLE audit_logs ADD COLUMN activity_status VARCHAR(20) NOT NULL DEFAULT 'Success'")
        add("created_at", "ALTER TABLE audit_logs ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
        for _, stmt in stmts:
            try:
                db.session.execute(text(stmt)); db.session.commit()
            except Exception:
                db.session.rollback()
        try:
            db.session.execute(text("UPDATE audit_logs SET activity_id=CONCAT('AUD-LEGACY-', COALESCE(id,0), '-', RAND()) WHERE activity_id IS NULL OR activity_id=''") )
            db.session.commit()
        except Exception:
            try:
                db.session.execute(text("UPDATE audit_logs SET activity_id=CONCAT('AUD-LEGACY-', id) WHERE (activity_id IS NULL OR activity_id='') AND id IS NOT NULL"))
                db.session.commit()
            except Exception:
                db.session.rollback()
        _audit_table_ready = "id" in {c["name"] for c in inspect(db.engine).get_columns("audit_logs")}
    except Exception:
        try: db.session.rollback()
        except Exception: pass


def log_activity(
    *,
    activity_type: str,
    module: str,
    description: str,
    record_id: Any = None,
    previous_value: Any = None,
    new_value: Any = None,
    status: str = "Success",
    user=None,
    department_id=None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = False,
):
    ensure_audit_table()
    user_id, actor_dept_id, user_name, user_role = _actor_snapshot(user)
    row = AuditLog(
        activity_id=AuditLog.make_activity_id(),
        user_id=user_id,
        department_id=department_id if department_id is not None else actor_dept_id,
        user_name_snapshot=user_name,
        user_role=user_role,
        activity_type=str(activity_type)[:120],
        module=str(module)[:80],
        description=str(description)[:600],
        record_id=str(record_id)[:120] if record_id is not None and str(record_id).strip() else None,
        previous_value=_sanitize(previous_value) if previous_value is not None else None,
        new_value=_sanitize(new_value) if new_value is not None else None,
        ip_address=(ip_address or _request_ip() or "")[:64] or None,
        user_agent=(user_agent or _request_ua() or "")[:500] or None,
        activity_status=status if status in {"Success", "Failed", "Denied"} else "Success",
        created_at=datetime.utcnow(),
    )
    try:
        db.session.add(row)
        if commit:
            db.session.commit()
    except Exception:
        try: db.session.rollback()
        except Exception: pass
        return None
    return row


def to_pht(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(PHT)
