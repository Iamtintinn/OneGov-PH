"""Admin Audit Trail Module - read-only, role-scoped, exportable."""

import csv
import io
import json
from datetime import datetime, timedelta, timezone

from flask import Blueprint, Response, abort, jsonify, render_template, request
from flask_login import current_user
from sqlalchemy import func, or_

from app import db
from app.models.audit_log import AuditLog
from app.services.audit_service import ensure_audit_table, to_pht
from app.utils.access import is_department_admin, is_system_admin
from app.utils.decorators import admin_console_required

audit_bp = Blueprint("admin_audit", __name__, url_prefix="/admin/audit-trail")
PHT = timezone(timedelta(hours=8))

MODULES = ["Authentication", "Accounts", "Citizens", "Applications", "Payments", "Documents", "Delivery", "System", "Audit"]
STATUSES = ["Success", "Failed", "Denied"]
ROLES = ["Citizen", "Department staff", "Department administrator", "System administrator", "system"]


def _scope_query(query):
    if is_system_admin():
        return query
    if is_department_admin():
        dept_id = getattr(current_user, "department_id", None)
        conds = [AuditLog.user_id == current_user.user_id]
        if dept_id:
            conds.append(AuditLog.department_id == dept_id)
        # Department admin: only own actions or records tagged to their department.
        query = query.filter(or_(*conds)).filter(AuditLog.user_role != "System administrator")
        return query
    abort(403)


def _parse_dt(value, end=False):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M"):
        try:
            dt = datetime.strptime(value, fmt)
            if fmt == "%Y-%m-%d" and end:
                dt = dt + timedelta(days=1) - timedelta(seconds=1)
            # treat input as PHT, convert to UTC for DB compare
            dt = dt.replace(tzinfo=PHT).astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            pass
    return None


def _filters():
    args = request.args
    preset = (args.get("preset") or "").strip()
    now_pht = datetime.now(PHT)
    date_from = args.get("date_from")
    date_to = args.get("date_to")
    if preset == "today":
        date_from = now_pht.strftime("%Y-%m-%d")
        date_to = now_pht.strftime("%Y-%m-%d")
    elif preset == "yesterday":
        y = (now_pht - timedelta(days=1)).strftime("%Y-%m-%d")
        date_from = date_to = y
    elif preset == "7d":
        date_from = (now_pht - timedelta(days=6)).strftime("%Y-%m-%d")
        date_to = now_pht.strftime("%Y-%m-%d")
    elif preset == "30d":
        date_from = (now_pht - timedelta(days=29)).strftime("%Y-%m-%d")
        date_to = now_pht.strftime("%Y-%m-%d")

    return {
        "q_name": (args.get("q_name") or "").strip()[:120],
        "q_activity_id": (args.get("q_activity_id") or "").strip()[:40],
        "q_record_id": (args.get("q_record_id") or "").strip()[:120],
        "role": (args.get("role") or "").strip()[:60],
        "module": (args.get("module") or "").strip()[:80],
        "activity_type": (args.get("activity_type") or "").strip()[:120],
        "status": (args.get("status") or "").strip()[:20],
        "ip_address": (args.get("ip_address") or "").strip()[:64],
        "date_from": (date_from or "").strip()[:10],
        "date_to": (date_to or "").strip()[:10],
        "preset": preset,
    }


def _apply_filters(query, f):
    if f["q_name"]:
        query = query.filter(AuditLog.user_name_snapshot.ilike(f"%{f['q_name']}%"))
    if f["q_activity_id"]:
        query = query.filter(AuditLog.activity_id.ilike(f"%{f['q_activity_id']}%"))
    if f["q_record_id"]:
        query = query.filter(AuditLog.record_id.ilike(f"%{f['q_record_id']}%"))
    if f["role"]:
        query = query.filter(AuditLog.user_role == f["role"])
    if f["module"]:
        query = query.filter(AuditLog.module == f["module"])
    if f["activity_type"]:
        query = query.filter(AuditLog.activity_type.ilike(f"%{f['activity_type']}%"))
    if f["status"]:
        query = query.filter(AuditLog.activity_status == f["status"])
    if f["ip_address"]:
        query = query.filter(AuditLog.ip_address.ilike(f"%{f['ip_address']}%"))
    dt_from = _parse_dt(f["date_from"], end=False)
    dt_to = _parse_dt(f["date_to"], end=True)
    if dt_from:
        query = query.filter(AuditLog.created_at >= dt_from)
    if dt_to:
        query = query.filter(AuditLog.created_at <= dt_to)
    return query


def _stats(scoped_base):
    today_utc_start = datetime.now(PHT).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).replace(tzinfo=None)
    def count(extra=None):
        q = scoped_base
        if extra is not None:
            q = q.filter(extra)
        return db.session.scalar(db.select(func.count()).select_from(q.subquery())) or 0
    return {
        "total": count(),
        "today": count(AuditLog.created_at >= today_utc_start),
        "admin_actions": count(AuditLog.user_role.in_(["System administrator", "Department administrator"])),
        "staff_actions": count(AuditLog.user_role == "Department staff"),
        "failed": count(AuditLog.activity_status == "Failed"),
        "security": count(AuditLog.module.in_(["Authentication", "Accounts"])),
    }


@audit_bp.route("/")
@admin_console_required
def index():
    ensure_audit_table()
    f = _filters()
    base = _scope_query(db.select(AuditLog))
    stats = _stats(base)
    q = _apply_filters(base, f).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = 20
    pagination = db.paginate(q, page=page, per_page=per_page, error_out=False)
    types = [r[0] for r in db.session.execute(_scope_query(db.select(AuditLog.activity_type).distinct().order_by(AuditLog.activity_type))).all() if r[0]]
    return render_template("admin/audit_trail.html", logs=pagination.items, pagination=pagination, stats=stats, filters=f,
                           modules=MODULES, statuses=STATUSES, roles=ROLES, activity_types=types, to_pht=to_pht)


@audit_bp.route("/<int:log_id>")
@admin_console_required
def detail(log_id):
    ensure_audit_table()
    q = _scope_query(db.select(AuditLog).where(AuditLog.id == log_id))
    log = db.session.scalar(q)
    if not log:
        abort(404)
    return jsonify({
        "activity_id": log.activity_id,
        "user_name": log.user_name_snapshot,
        "account_id": log.user_id,
        "role": log.user_role,
        "activity_type": log.activity_type,
        "module": log.module,
        "record_id": log.record_id,
        "created_at": to_pht(log.created_at).strftime("%d %b %Y, %I:%M:%S %p PHT") if log.created_at else "",
        "ip_address": log.ip_address or "—",
        "user_agent": log.user_agent or "—",
        "description": log.description,
        "previous_value": log.previous_value,
        "new_value": log.new_value,
        "status": log.activity_status,
    })


def _export_rows():
    ensure_audit_table()
    f = _filters()
    q = _apply_filters(_scope_query(db.select(AuditLog)), f).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    return db.session.scalars(q.limit(5000)).all()


@audit_bp.route("/export.csv")
@admin_console_required
def export_csv():
    rows = _export_rows()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Date/Time (PHT)", "Activity ID", "User", "Role", "Activity Type", "Module", "Record ID", "IP Address", "Status", "Description"])
    for r in rows:
        ts = to_pht(r.created_at).strftime("%Y-%m-%d %H:%M:%S PHT") if r.created_at else ""
        w.writerow([ts, r.activity_id, r.user_name_snapshot, r.user_role, r.activity_type, r.module, r.record_id or "", r.ip_address or "", r.activity_status, r.description])
    return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=audit-trail.csv"})


@audit_bp.route("/export.pdf")
@admin_console_required
def export_pdf():
    rows = _export_rows()
    # Lightweight PDF via reportlab if available; fallback to printable HTML response as PDF-like download is risky.
    try:
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=18, rightMargin=18, topMargin=18, bottomMargin=18)
        styles = getSampleStyleSheet()
        elems = [Paragraph("OneGov PH Audit Trail Report", styles['Title']), Paragraph(f"Generated: {datetime.now(PHT).strftime('%Y-%m-%d %H:%M:%S PHT')}", styles['Normal']), Spacer(1, 12)]
        data = [["Date/Time (PHT)", "User", "Role", "Activity", "Module", "Record ID", "IP", "Status"]]
        for r in rows[:1000]:
            ts = to_pht(r.created_at).strftime("%Y-%m-%d %H:%M") if r.created_at else ""
            data.append([ts, r.user_name_snapshot[:24], r.user_role[:20], r.activity_type[:28], r.module, (r.record_id or "")[:18], (r.ip_address or "")[:15], r.activity_status])
        table = Table(data, repeatRows=1, colWidths=[95,90,85,120,65,75,70,55])
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#173B72')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTSIZE',(0,0),(-1,-1),7),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F5F7FB')]),('GRID',(0,0),(-1,-1),0.25,colors.HexColor('#DCE5F1'))]))
        elems.append(table)
        doc.build(elems)
        return Response(buf.getvalue(), mimetype="application/pdf", headers={"Content-Disposition": "attachment; filename=audit-trail.pdf"})
    except Exception:
        # fallback CSV-named? No, return simple HTML for print/save as PDF
        html = render_template("admin/audit_trail_export.html", rows=rows, to_pht=to_pht, generated=datetime.now(PHT))
        return Response(html, mimetype="text/html")
