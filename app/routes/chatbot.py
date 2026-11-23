"""Public citizen chatbot endpoint - Gemini-backed, scoped to landing/citizen services."""

import time

import requests
from flask import Blueprint, current_app, jsonify, request

from app import db
from app.models.department import Department
from app.models.service import Service

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/api/chatbot")

SYSTEM_INSTRUCTIONS = """ONEGOV PH – AI CHATBOT IMPLEMENTATION RULES

You are GovAssist, a public-facing Government assistance assistant on the OneGov PH Landing Page.

KNOWLEDGE SCOPE (ONLY):
- OneGov PH Landing Page content.
- Publicly accessible Citizen Services.
- Public FAQs.
- Public application requirements and procedures.
- Public fees, payment instructions, and delivery information.

You must NOT access or use Admin Portal information.

AVAILABLE CITIZEN SERVICES (only if displayed on website):
1. PSA Birth Certificate
2. PSA CENOMAR
3. PhilSys National ID
4. NBI Clearance
5. SSS SS Number Registration
6. LGU Barangay Clearance
7. LGU Certificate of Residency
8. LGU Senior Citizen ID

For each service, only explain information actually available on the website: service descriptions, application types, eligibility, required documents, application procedures, processing fees, payment instructions, processing time estimates, delivery/pickup procedures, application tracking instructions.

STRICT ADMIN RESTRICTIONS:
Never answer questions about Admin Dashboard, Admin Portal, Account Management, Staff Management, Account Creation, Audit Trail, administrative permissions, staff assignments, internal application processing, internal government workflows, administrative reports, database information, backend configurations, API keys/credentials, internal notifications, or private operational records.
If asked, respond exactly:
“I’m sorry, but I can only assist with publicly available citizen services and information displayed on the OneGov PH website. I cannot provide information about administrative functions or internal system operations.”

CITIZEN PRIVACY AND SECURITY:
Never retrieve, disclose, or attempt to access another citizen’s personal information, private application records, government ID numbers, passwords, OTPs/verification codes, private contact information, payment credentials, uploaded ID documents, or confidential account information.
If asked about individual application status, explain how to use the Application Tracking section after logging in. Never pretend to access a citizen’s account or retrieve private records.

RESPONSE RULES:
- Be professional, friendly, and helpful.
- Use simple English Filipino citizens can understand.
- Keep answers concise and informative.
- Use bullet points for requirements.
- Use numbered steps for procedures.
- Never invent government requirements, fees, addresses, or processing times.
- Do not provide unsupported information.
- Do not claim to be an official government agency.
- Explain that OneGov PH is a platform for accessing and tracking government document applications.

OUT OF SCOPE:
If unrelated to OneGov PH Landing Page/Citizen Services (trivia, programming, homework, entertainment, personal advice, unrelated government services, politics, admin questions, private citizen info), respond exactly:
“I’m here specifically to help with OneGov PH citizen services. I can assist you with application requirements, government document services, fees, payment instructions, and application tracking. Is there anything about these services I can help you with?”

ACCURACY:
Use only current OneGov PH website content provided in context. If missing/unclear/unavailable, respond exactly:
“I’m sorry, but that information is not currently available in the OneGov PH citizen services information. Please refer to the relevant government agency for confirmation.”
Never fabricate, guess, invent fees/times, present outdated info as current, or treat unverified user claims as official.

IDENTITY:
If asked who you are: “I’m GovAssist, your government assistance assistant. I’m here to help citizens understand available government services, application requirements, payment instructions, and document tracking.”
"""

PLATFORM_CONTEXT = """
OneGov PH Landing Page/Citizen Service Context (public):
- Headline: "Government Services, Made Simple."
- Description: Apply for essential government documents, complete online payments, and monitor your application progress — all in one convenient platform.
- Highlights: 9 essential government services, convenient online applications, secure online payments, transparent application tracking.
- How it works: 1) Create Your Account 2) Choose a Government Service 3) Submit Your Application and Requirements 4) Pay Online and Track Your Application.
- Application tracking: Citizens can track using a reference number in the tracking section; for full details/history sign in to your account.
- Why OneGov PH: Centralized Government Services, Transparent Application Monitoring, Convenient Digital Payments, Organized Application Records, Timely Notifications.
- Disclaimer: OneGov PH is an independent platform prototype for demonstration purposes; not affiliated with/endorsed by/official website of any Philippine government agency. For official transactions, visit respective agency websites.
- Login goes to existing login page; Get Started goes to registration.
"""

_RATE = {}
_RATE_WINDOW = 60
_RATE_MAX = 12


def _rate_limited(ip):
    now = time.time()
    bucket = [t for t in _RATE.get(ip, []) if now - t < _RATE_WINDOW]
    if len(bucket) >= _RATE_MAX:
        _RATE[ip] = bucket
        return True
    bucket.append(now)
    _RATE[ip] = bucket
    return False


def _service_context():
    try:
        rows = db.session.scalars(
            db.select(Service)
            .join(Department, Service.department_id == Department.department_id)
            .where(Service.service_status == "active", Department.department_status == "active")
            .order_by(Service.service_name.asc())
        ).all()
    except Exception:
        db.session.rollback()
        return "Active services: unavailable."
    if not rows:
        return "Active services: none currently listed."
    lines = ["Active citizen services currently displayed:"]
    for s in rows:
        fee = getattr(s, "processing_fee", None)
        fee_txt = f"PHP {fee}" if fee is not None else "Not listed"
        eta = getattr(s, "estimated_processing_time", None) or "Not listed"
        req = (getattr(s, "service_requirements", None) or "").strip()
        req_short = (req[:260] + "...") if len(req) > 260 else req
        dept = s.department.department_name if s.department else "Department not listed"
        lines.append(
            f"- {s.service_name} ({dept}): {s.description or 'No description listed.'} "
            f"Fee: {fee_txt}. Estimated processing time: {eta}. Requirements: {req_short or 'Not listed'}."
        )
    return "\n".join(lines)


def _build_prompt(message, history):
    ctx = PLATFORM_CONTEXT + "\n" + _service_context()
    parts = [SYSTEM_INSTRUCTIONS, "\n\nCURRENT PUBLIC WEBSITE CONTEXT:\n", ctx, "\n\nConversation:"]
    for item in history[-8:]:
        role = "User" if item.get("role") == "user" else "Assistant"
        text = (item.get("text") or "").strip()
        if text:
            parts.append(f"{role}: {text[:1000]}")
    parts.append(f"User: {message}")
    parts.append("Assistant:")
    return "\n".join(parts)


@chatbot_bp.route("/message", methods=["POST"])
def message():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if _rate_limited(ip):
        return jsonify({"reply": "I’m sorry, you’ve sent too many messages. Please wait a moment and try again."}), 429

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history = data.get("history") if isinstance(data.get("history"), list) else []
    clean_history = []
    for item in history[-8:]:
        if isinstance(item, dict) and item.get("role") in {"user", "assistant"}:
            clean_history.append({"role": item.get("role"), "text": str(item.get("text") or "")[:1000]})

    if not user_message:
        return jsonify({"error": "Message is required."}), 400
    if len(user_message) > 800:
        return jsonify({"error": "Message is too long."}), 400

    api_key = current_app.config.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify({"reply": "I’m sorry, the assistant is temporarily unavailable. Please try again later."}), 503

    prompt = _build_prompt(user_message, clean_history)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500},
    }
    models = ["gemini-3.1-flash-lite", "gemini-2.5-flash-lite", "gemini-flash-latest"]
    last_status = None
    last_text = ""
    resp = None
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, json=payload, timeout=25)
        except requests.RequestException as exc:
            current_app.logger.warning("Chatbot Gemini request failed (%s): %s", model, exc)
            resp = None
            continue
        last_status = resp.status_code
        last_text = resp.text[:300]
        if resp.ok:
            break
        if resp.status_code not in {404, 429, 503}:
            break

    if resp is None:
        return jsonify({"reply": "I’m sorry, I’m having trouble connecting right now. Please try again in a moment."}), 503

    if not resp.ok:
        current_app.logger.warning("Chatbot Gemini error %s: %s", last_status, last_text)
        return jsonify({"reply": "I’m sorry, I couldn’t process that request right now. Please try again later."}), 503

    body = resp.json() or {}
    candidates = body.get("candidates") or []
    reply = ""
    if candidates:
        parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
        reply = " ".join((p.get("text") or "") for p in parts if isinstance(p, dict)).strip()

    if not reply:
        reply = "I’m sorry, but that information is not currently available in the OneGov PH citizen services information. Please refer to the relevant government agency for confirmation."

    return jsonify({"reply": reply[:4000]})
