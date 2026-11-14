"""Citizen Apply Now steps. These views are registered on the citizen blueprint."""

from flask import abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user
from sqlalchemy.orm import joinedload

from app import db
from app.models.application import Application
from app.models.department import Department
from app.models.service import Service
from app.models.user import User
from app.services.application_forms import specification_for
from app.services.tracking_service import cancel_application
from app.services.application_service import (
    TERMS_TEXT,
    absolute_upload,
    cancel_draft,
    clear_id_autofill,
    continue_target,
    document_rules,
    ensure_draft,
    field_map,
    find_draft,
    missing_documents,
    barangay_review_ready,
    barangay_type_ready,
    birth_review_ready,
    birth_type_ready,
    cenomar_review_ready,
    mark_barangay_reviewed,
    mark_birth_reviewed,
    mark_cenomar_reviewed,
    mark_nbi_reviewed,
    mark_passport_reviewed,
    mark_philsys_reviewed,
    mark_residency_reviewed,
    mark_senior_reviewed,
    mark_sss_reviewed,
    nbi_review_ready,
    nbi_type_ready,
    philsys_review_ready,
    owned_application,
    passport_details_ready,
    passport_review_ready,
    passport_type_ready,
    residency_review_ready,
    residency_type_ready,
    senior_review_ready,
    senior_type_ready,
    sss_review_ready,
    prefill_values,
    read_checklist,
    read_details,
    read_fields,
    remove_upload,
    requirement_for,
    save_barangay_application_type,
    save_barangay_id,
    save_birth_application_type,
    save_draft,
    save_nbi_application_type,
    save_passport_application_type,
    save_passport_id,
    save_residency_application_type,
    save_senior_application_type,
    save_philsys_document,
    save_philsys_reference,
    save_cenomar_tracking,
    save_sss_id,
    save_sss_tracking,
    save_upload,
    submit_application,
    validate_answers,
    write_details,
)
from app.utils.decorators import role_required
from app.routes.citizen import STATUS_LABELS


def _service_or_404(service_id):
    service = db.session.scalar(
        db.select(Service)
        .join(Service.department)
        .where(
            Service.service_id == service_id,
            Service.service_status == "active",
            Department.department_status == "active",
        )
    )
    if service is None or specification_for(service) is None:
        abort(404)
    return service


def _draft_or_404(application_id):
    application = db.session.scalars(
        db.select(Application)
        .options(
            joinedload(Application.service).joinedload(Service.department),
            joinedload(Application.department),
            joinedload(Application.requirements),
            joinedload(Application.payments),
        )
        .where(
            Application.application_id == application_id,
            Application.applicant_id == current_user.user_id,
        )
    ).unique().first()
    if application is None or specification_for(application.service) is None:
        abort(404)
    return application


def _common(application, step):
    service = application.service
    values = field_map(application)
    spec = specification_for(service, values)
    return {
        "application": application,
        "service": service,
        "spec": spec,
        "step": step,
        "documents": document_rules(spec, values),
        "status_labels": STATUS_LABELS,
        "step_labels": spec.get("step_labels"),
    }


@role_required(User.ROLE_CITIZEN)
def apply_type(service_id):
    """Step 1 for type-first services: choose the application type."""
    service = _service_or_404(service_id)
    draft = ensure_draft(current_user, service)
    values = prefill_values(draft)
    spec = specification_for(service, values)
    kind = spec.get("kind")
    if not (
        spec.get("type_first")
        and kind in {"passport", "barangay", "residency", "senior", "nbi", "birth"}
    ):
        return redirect(url_for("citizen.apply_details", service_id=service.service_id))

    if kind == "barangay":
        from app.services.barangay_requirements import BARANGAY_TYPE_OPTIONS as TYPE_OPTIONS

        save_type = save_barangay_application_type
        next_endpoint = "citizen.apply_details"
        next_kwargs = {"service_id": service.service_id}
        continue_label = "Continue to application details"
        type_heading = "Barangay clearance application types"
        type_intro = (
            "Choose the clearance purpose that matches your request. "
            "Required document uploads depend on this choice."
        )
    elif kind == "residency":
        from app.services.residency_requirements import RESIDENCY_TYPE_OPTIONS as TYPE_OPTIONS

        save_type = save_residency_application_type
        next_endpoint = "citizen.apply_details"
        next_kwargs = {"service_id": service.service_id}
        continue_label = "Continue to application details"
        type_heading = "Certificate of residency application types"
        type_intro = (
            "Choose the residency certificate purpose that matches your request. "
            "Required document uploads depend on this choice."
        )
    elif kind == "senior":
        from app.services.senior_requirements import SENIOR_TYPE_OPTIONS as TYPE_OPTIONS

        save_type = save_senior_application_type
        next_endpoint = "citizen.apply_details"
        next_kwargs = {"service_id": service.service_id}
        continue_label = "Continue to application details"
        type_heading = "Senior Citizen ID application types"
        type_intro = (
            "Choose the Senior Citizen ID path that matches your situation. "
            "Physical documents to bring to the OSCA office depend on this choice."
        )
    elif kind == "nbi":
        from app.services.nbi_requirements import NBI_TYPE_OPTIONS as TYPE_OPTIONS

        save_type = save_nbi_application_type
        next_endpoint = "citizen.apply_details"
        next_kwargs = {"service_id": service.service_id}
        continue_label = "Continue to application details"
        type_heading = "NBI clearance application types"
        type_intro = (
            "Choose the NBI clearance path that matches your situation. "
            "New applications schedule a visit; other types continue fully online."
        )
    elif kind == "birth":
        from app.services.birth_requirements import BIRTH_TYPE_OPTIONS as TYPE_OPTIONS

        save_type = save_birth_application_type
        next_endpoint = "citizen.apply_details"
        next_kwargs = {"service_id": service.service_id}
        continue_label = "Continue to application details"
        type_heading = "Birth certificate request types"
        type_intro = (
            "Choose the birth certificate request that matches your situation. "
            "Required document uploads depend on this choice."
        )
    else:
        from app.services.passport_requirements import PASSPORT_TYPE_OPTIONS as TYPE_OPTIONS

        save_type = save_passport_application_type
        next_endpoint = "citizen.apply_documents"
        next_kwargs = {"application_id": draft.application_id}
        continue_label = "Continue to documents"
        type_heading = "Philippine passport application types"
        type_intro = (
            "Choose the passport application that matches your situation. "
            "Required physical documents on appointment day depend on this choice."
        )

    error = None
    if request.method == "POST":
        error = save_type(draft, request.form.get("application_type", ""))
        if not error:
            return redirect(url_for(next_endpoint, **next_kwargs))
        flash(error, "warning")
    return render_template(
        "applications/apply_type.html",
        service=service,
        spec=spec,
        application=draft,
        values=values,
        type_options=TYPE_OPTIONS,
        selected_type=values.get("application_type") or "",
        step=1,
        step_labels=spec.get("step_labels"),
        error=error,
        continue_label=continue_label,
        type_heading=type_heading,
        type_intro=type_intro,
    )


@role_required(User.ROLE_CITIZEN)
def apply_details(service_id):
    service = _service_or_404(service_id)
    draft = find_draft(current_user.user_id, service.service_id)
    errors = {}
    values = prefill_values(draft)
    spec = specification_for(service, request.form if request.method == "POST" else values)
    if spec.get("kind") == "passport" or spec.get("documents_first"):
        draft = ensure_draft(current_user, service)
        values = prefill_values(draft)
        spec = specification_for(service, request.form if request.method == "POST" else values)
        if spec.get("kind") == "passport" and spec.get("type_first") and not passport_type_ready(draft):
            return redirect(url_for("citizen.apply_type", service_id=service.service_id))
        if missing_documents(draft, spec):
            return redirect(url_for("citizen.apply_documents", application_id=draft.application_id))
        if request.method == "POST":
            stored, errors = validate_answers(
                service,
                spec,
                request.form,
                extra={"application_type": values.get("application_type") or ""},
            )
            if not errors:
                draft = save_draft(current_user, service, stored, draft)
                if spec.get("kind") == "passport" or spec.get("review_before_schedule"):
                    return redirect(url_for("citizen.apply_review", application_id=draft.application_id))
                return redirect(url_for("citizen.apply_schedule", application_id=draft.application_id))
            values = {item["key"]: item["value"] for item in stored}
            next_label = "review" if (spec.get("kind") == "passport" or spec.get("review_before_schedule")) else "scheduling"
            flash(
                f"This application cannot continue to {next_label} yet. "
                "Fix the highlighted fields below, then try Continue again.",
                "warning",
            )
        autofill_keys = set(read_details(draft).get("id_autofill_keys") or [])
        autofilled_labels = [
            field["label"]
            for field in spec["fields"]
            if field["key"] in autofill_keys and values.get(field["key"])
        ]
        error_items = [
            {"key": field["key"], "label": field["label"], "message": errors[field["key"]]}
            for field in spec["fields"]
            if field["key"] in errors
        ]
        details_step = 3 if (spec.get("kind") == "passport" and spec.get("type_first")) else 2
        return render_template(
            "applications/apply_details.html",
            service=service,
            spec=spec,
            fields=spec["fields"],
            values=values,
            errors=errors,
            error_items=error_items,
            step=details_step,
            step_labels=spec.get("step_labels"),
            application=draft,
            autofilled_labels=autofilled_labels,
        )
    draft = ensure_draft(current_user, service)
    values = prefill_values(draft)
    spec = specification_for(service, request.form if request.method == "POST" else values)
    if spec.get("kind") == "barangay" and spec.get("type_first") and not barangay_type_ready(draft):
        return redirect(url_for("citizen.apply_type", service_id=service.service_id))
    if spec.get("kind") == "residency" and spec.get("type_first") and not residency_type_ready(draft):
        return redirect(url_for("citizen.apply_type", service_id=service.service_id))
    if spec.get("kind") == "senior" and spec.get("type_first") and not senior_type_ready(draft):
        return redirect(url_for("citizen.apply_type", service_id=service.service_id))
    if spec.get("kind") == "nbi" and spec.get("type_first") and not nbi_type_ready(draft):
        return redirect(url_for("citizen.apply_type", service_id=service.service_id))
    if spec.get("kind") == "birth" and spec.get("type_first") and not birth_type_ready(draft):
        return redirect(url_for("citizen.apply_type", service_id=service.service_id))
    if request.method == "POST":
        stored, errors = validate_answers(
            service,
            spec,
            request.form,
            extra={"application_type": values.get("application_type") or ""} if spec.get("type_first") else None,
        )
        if not errors:
            draft = save_draft(current_user, service, stored, draft)
            if spec.get("kind") == "cenomar":
                return redirect(url_for("citizen.apply_review", application_id=draft.application_id))
            return redirect(url_for("citizen.apply_documents", application_id=draft.application_id))
        values = {item["key"]: item["value"] for item in stored}
        if spec.get("kind") in {"barangay", "residency", "cenomar", "birth", "senior", "nbi", "sss"}:
            next_label = "review" if spec.get("kind") == "cenomar" else "documents"
            flash(
                f"This application cannot continue to {next_label} yet. "
                "Fix the highlighted fields below, then try Continue again.",
                "warning",
            )
    error_items = []
    if errors and spec.get("kind") in {"barangay", "residency", "cenomar", "birth", "senior", "nbi", "sss"}:
        error_items = [
            {"key": field["key"], "label": field["label"], "message": errors[field["key"]]}
            for field in spec["fields"]
            if field["key"] in errors
        ]
    details_step = (
        2
        if (
            spec.get("kind") in {"barangay", "residency", "senior", "nbi", "birth"}
            and spec.get("type_first")
        )
        else 1
    )
    return render_template(
        "applications/apply_details.html",
        service=service,
        spec=spec,
        fields=spec["fields"],
        values=values,
        errors=errors,
        error_items=error_items,
        step=details_step,
        step_labels=spec.get("step_labels"),
        application=draft,
    )


def validate_and_store(service, spec):
    return validate_answers(service, spec, request.form)


@role_required(User.ROLE_CITIZEN)
def apply_documents(application_id):
    application = _draft_or_404(application_id)
    if application.application_status != "draft":
        return redirect(url_for("citizen.apply_confirmation", application_id=application.application_id))
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") == "passport" and spec.get("type_first") and not passport_type_ready(application):
        return redirect(url_for("citizen.apply_type", service_id=application.service_id))
    if spec.get("kind") == "barangay" and spec.get("type_first") and not barangay_type_ready(application):
        return redirect(url_for("citizen.apply_type", service_id=application.service_id))
    if spec.get("kind") == "residency" and spec.get("type_first") and not residency_type_ready(application):
        return redirect(url_for("citizen.apply_type", service_id=application.service_id))
    if spec.get("kind") == "senior" and spec.get("type_first") and not senior_type_ready(application):
        return redirect(url_for("citizen.apply_type", service_id=application.service_id))
    if spec.get("kind") == "nbi" and spec.get("type_first") and not nbi_type_ready(application):
        return redirect(url_for("citizen.apply_type", service_id=application.service_id))
    if spec.get("kind") == "birth" and spec.get("type_first") and not birth_type_ready(application):
        return redirect(url_for("citizen.apply_type", service_id=application.service_id))
    if not (spec.get("kind") == "passport" or spec.get("documents_first")) and not read_fields(application):
        return redirect(url_for("citizen.apply_details", service_id=application.service_id))
    if spec.get("kind") == "cenomar":
        return redirect(url_for("citizen.apply_review", application_id=application.application_id))
    if spec.get("kind") == "passport" and spec.get("type_first"):
        document_step = 2
    elif (
        spec.get("kind") in {"barangay", "residency", "senior", "nbi", "birth"}
        and spec.get("type_first")
    ):
        document_step = 3
    elif spec.get("kind") == "passport" or spec.get("documents_first"):
        document_step = 1
    else:
        document_step = 2
    context = _common(application, document_step)
    if context["spec"].get("kind") == "philsys":
        from app.services.philsys_national_id import supporting_id_groups

        matched = next(
            (item for item in read_checklist(application) if item.get("key") == "supporting_id"),
            None,
        )
        context["groups"] = supporting_id_groups(field_map(application).get("citizenship"))
        context["matched"] = matched
        context["requirements"] = {item.requirement_name: item for item in application.requirements}
        context["missing"] = missing_documents(application, context["spec"])
        return render_template("applications/apply_philsys_documents.html", **context)
    if context["spec"].get("checklist"):
        from app.services.philsys_national_id import checklist_groups

        matched = next(
            (item for item in read_checklist(application) if item.get("value") == "matched"),
            None,
        )
        context["groups"] = checklist_groups(field_map(application).get("citizenship"))
        context["matched"] = matched
        context["uploaded"] = requirement_for(application, matched["key"]) if matched else None
        return render_template("applications/apply_philsys_documents.html", **context)
    context["requirements"] = {item.requirement_name: item for item in application.requirements}
    context["upload_error"] = {}
    context["missing"] = missing_documents(application, context["spec"])
    if context["spec"].get("kind") == "passport":
        from app.services.passport_ids import passport_id_groups

        answers = field_map(application)
        context["id_picker_groups"] = passport_id_groups(
            answers.get("application_type"),
            answers.get("date_of_birth"),
        )
        context["id_picker_match"] = next(
            (
                item
                for item in read_checklist(application)
                if item.get("key") == "valid_id" and item.get("value") == "matched"
            ),
            None,
        )
    elif context["spec"].get("kind") in {"barangay", "residency", "senior", "nbi", "birth"}:
        from app.services.barangay_ids import barangay_id_groups

        context["id_picker_groups"] = barangay_id_groups()
        context["id_picker_matches"] = {
            item.get("key"): item
            for item in read_checklist(application)
            if item.get("value") in {"selected", "matched"} and item.get("key")
        }
        context["id_picker_match"] = context["id_picker_matches"].get("valid_id")
    elif context["spec"].get("kind") == "sss":
        from app.services.sss_ids import sss_alternative_groups, sss_primary_groups

        context["id_picker_groups"] = sss_primary_groups()
        context["id_picker_alt_groups"] = sss_alternative_groups()
        context["id_picker_matches"] = {
            item.get("key"): item
            for item in read_checklist(application)
            if item.get("value") in {"selected", "matched"} and item.get("key")
        }
        context["id_picker_match"] = context["id_picker_matches"].get("valid_id")
    return render_template("applications/apply_documents.html", **context)


@role_required(User.ROLE_CITIZEN)
def upload_document(application_id, document_key):
    application = _draft_or_404(application_id)
    if application.application_status != "draft":
        return redirect(url_for("citizen.apply_confirmation", application_id=application.application_id))
    values = field_map(application)
    spec = specification_for(application.service, values)
    allowed = {item["key"]: item for item in document_rules(spec, values)}
    document = allowed.get(document_key)
    if document is None:
        abort(404)
    upload = request.files.get("document")
    error = None
    if upload is None or not upload.filename:
        error = f"Choose a file for {document['label']}."
    elif spec.get("kind") == "philsys" and document_key == "supporting_id":
        from app.services.philsys_national_id import _BIRTH_RECORD_KEYS, document_by_key

        selected = document_by_key(values.get("citizenship"), request.form.get("document_type", ""))
        if selected is None or selected["key"] in _BIRTH_RECORD_KEYS:
            error = "Select the supporting identification document shown in the file."
        else:
            error = save_philsys_document(application, selected, upload)
            if not error:
                filled = read_details(application).get("id_autofill_keys") or []
                if filled:
                    flash(
                        "ID uploaded. Readable details were filled into the application form. "
                        "Blank fields still need your input.",
                        "success",
                    )
                else:
                    flash(
                        "ID uploaded. No personal details could be read from this file. "
                        "Enter them on the next step.",
                        "success",
                    )
                return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
    elif document.get("id_choices") == "dfa":
        from app.services.passport_ids import passport_id_by_key

        selected = passport_id_by_key(
            values.get("application_type"),
            values.get("date_of_birth"),
            request.form.get("id_type", ""),
        )
        if selected is None:
            error = "Select one valid government ID from the list."
        else:
            error = save_passport_id(application, selected, upload)
            if not error:
                filled = read_details(application).get("id_autofill_keys") or []
                if filled:
                    flash(
                        "ID uploaded. Readable details were filled into the application form. "
                        "Blank fields still need your input.",
                        "success",
                    )
                else:
                    flash(
                        "ID uploaded. No personal details could be read from this file. "
                        "Enter them on the next step.",
                        "success",
                    )
                return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
    elif document.get("id_choices") == "barangay":
        from app.services.barangay_ids import barangay_id_by_key

        selected = barangay_id_by_key(request.form.get("id_type", ""))
        if selected is None:
            error = "Select one valid government ID from the list."
        else:
            error = save_barangay_id(application, selected, upload, document_key=document_key)
            if not error:
                flash(f"{selected['label']} uploaded.", "success")
                return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
    elif document.get("id_choices") in {"sss", "sss_alt"}:
        from app.services.sss_ids import sss_id_by_key

        pool = "alternative" if document.get("id_choices") == "sss_alt" else "primary"
        selected = sss_id_by_key(request.form.get("id_type", ""), pool=pool)
        if selected is None:
            error = "Select one identification document from the list."
        else:
            error = save_sss_id(
                application,
                selected,
                upload,
                document_key=document_key,
                pool=pool,
            )
            if not error:
                flash(f"{selected['label']} uploaded.", "success")
                return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
    else:
        error = save_upload(
            application,
            document_key,
            upload,
            upload.filename,
            None,
        )
    if error:
        flash(error, "error")
    return redirect(url_for("citizen.apply_documents", application_id=application.application_id))


@role_required(User.ROLE_CITIZEN)
def remove_document(application_id, document_key):
    application = _draft_or_404(application_id)
    if application.application_status != "draft":
        return redirect(url_for("citizen.apply_confirmation", application_id=application.application_id))
    values = field_map(application)
    spec = specification_for(application.service, values)
    allowed = {item["key"]: item for item in document_rules(spec, values)}
    document = allowed.get(document_key)
    if document is None:
        abort(404)
    remove_upload(application, document_key)
    if (spec.get("kind") == "philsys" and document_key == "supporting_id") or (
        document.get("id_choices") in {"dfa", "barangay", "sss", "sss_alt"}
    ):
        details = read_details(application)
        details["checklist"] = [item for item in details["checklist"] if item.get("key") != document_key]
        if (document.get("id_choices") == "dfa" and document_key == "valid_id") or (
            spec.get("kind") == "philsys" and document_key == "supporting_id"
        ):
            write_details(application, details, commit=False)
            clear_id_autofill(application)
            db.session.commit()
        else:
            write_details(application, details)
    flash(f"{document['label']} removed.", "success")
    return redirect(url_for("citizen.apply_documents", application_id=application.application_id))


@role_required(User.ROLE_CITIZEN)
def continue_documents(application_id):
    application = _draft_or_404(application_id)
    if application.application_status != "draft":
        return redirect(url_for("citizen.apply_confirmation", application_id=application.application_id))
    spec = specification_for(application.service, field_map(application))
    if spec.get("checklist"):
        from app.services.philsys_national_id import document_by_key

        selected = document_by_key(
            field_map(application).get("citizenship"),
            request.form.get("document_key", ""),
        )
        if selected is None:
            flash("Select a document from the list.", "warning")
            return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
        upload = request.files.get("document")
        matched = next(
            (item for item in read_checklist(application) if item.get("value") == "matched"),
            None,
        )
        same_file = (
            matched is not None
            and matched["key"] == selected["key"]
            and requirement_for(application, selected["key"]) is not None
        )
        if (upload is None or not upload.filename) and same_file:
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        if upload is None or not upload.filename:
            flash("Upload a photo or PDF of the document you selected.", "warning")
            return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
        error = save_philsys_document(application, selected, upload)
        if error:
            flash(error, "error")
            return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
        return redirect(url_for("citizen.apply_review", application_id=application.application_id))
    missing = missing_documents(application, spec)
    if missing:
        flash(f"Still needed before you continue: {', '.join(missing)}.", "warning")
        return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
    if spec.get("kind") == "passport" or spec.get("documents_first"):
        return redirect(url_for("citizen.apply_details", service_id=application.service_id))
    return redirect(url_for("citizen.apply_review", application_id=application.application_id))


@role_required(User.ROLE_CITIZEN)
def apply_schedule(application_id):
    application = _draft_or_404(application_id)
    if application.application_status != "draft":
        return redirect(url_for("citizen.apply_confirmation", application_id=application.application_id))
    values = field_map(application)
    spec = specification_for(application.service, values)
    kind = spec.get("kind")
    if kind not in {"passport", "nbi", "philsys", "barangay", "residency", "senior"}:
        return redirect(url_for("citizen.apply_review", application_id=application.application_id))
    if missing_documents(application, spec):
        flash("Upload every required document before scheduling.", "warning")
        return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
    if kind == "passport":
        if not passport_details_ready(application, spec):
            flash("Complete the application details before scheduling.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not passport_review_ready(application):
            flash("Review your application before scheduling.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        from app.services.passport_scheduling import (
            LOCATIONS,
            appointment_for,
            available_month_calendars,
            location_by_code,
            save_appointment,
        )
    elif kind == "philsys":
        if not passport_details_ready(application, spec):
            flash("Complete the application details before scheduling.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not philsys_review_ready(application):
            flash("Review your application before scheduling.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        from app.services.philsys_scheduling import (
            LOCATIONS,
            appointment_for,
            available_month_calendars,
            location_by_code,
            save_appointment,
        )
    elif kind in {"barangay", "residency"}:
        type_ready = barangay_type_ready(application) if kind == "barangay" else residency_type_ready(application)
        reviewed = barangay_review_ready(application) if kind == "barangay" else residency_review_ready(application)
        if not type_ready:
            flash("Select an application type before scheduling.", "warning")
            return redirect(url_for("citizen.apply_type", service_id=application.service_id))
        if not read_fields(application):
            flash("Complete the application details before scheduling.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not reviewed:
            flash("Review your application before scheduling.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        from app.services.barangay_scheduling import (
            LOCATIONS,
            appointment_for,
            available_month_calendars,
            location_by_code,
            save_appointment,
        )
    elif kind == "senior":
        if not senior_type_ready(application):
            flash("Select an application type before scheduling.", "warning")
            return redirect(url_for("citizen.apply_type", service_id=application.service_id))
        if not read_fields(application):
            flash("Complete the application details before scheduling.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not senior_review_ready(application):
            flash("Review your application before scheduling.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        from app.services.senior_scheduling import (
            LOCATIONS,
            appointment_for,
            available_month_calendars,
            location_by_code,
            save_appointment,
        )
    else:
        if not nbi_type_ready(application):
            flash("Select an application type before scheduling.", "warning")
            return redirect(url_for("citizen.apply_type", service_id=application.service_id))
        if not spec.get("review_before_schedule"):
            flash("Scheduling is only required for New Application requests.", "warning")
            return redirect(url_for("citizen.apply_payment", application_id=application.application_id))
        if not read_fields(application):
            flash("Complete the application details before scheduling.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not nbi_review_ready(application):
            flash("Review your application before scheduling.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        from app.services.nbi_scheduling import (
            LOCATIONS,
            appointment_for,
            available_month_calendars,
            location_by_code,
            save_appointment,
        )

    selected_location = request.values.get("location_code") or (appointment_for(application) or {}).get(
        "location_code"
    ) or LOCATIONS[0]["code"]
    if location_by_code(selected_location) is None:
        selected_location = LOCATIONS[0]["code"]

    if request.method == "POST":
        error = save_appointment(
            application,
            current_user,
            request.form.get("location_code", ""),
            request.form.get("appointment_date", ""),
            request.form.get("appointment_time", ""),
        )
        if error:
            flash(error, "warning")
        else:
            return redirect(url_for("citizen.apply_payment", application_id=application.application_id))

    if kind in {"passport", "barangay", "residency", "senior", "nbi"} and spec.get("type_first"):
        schedule_step = 5
    else:
        schedule_step = 4
    context = _common(application, schedule_step)
    context["locations"] = LOCATIONS
    context["selected_location"] = selected_location
    context["calendar_months"] = available_month_calendars(selected_location, application.application_id)
    context["appointment"] = appointment_for(application)
    return render_template("applications/apply_schedule.html", **context)


@role_required(User.ROLE_CITIZEN)
def apply_payment(application_id):
    application = _draft_or_404(application_id)
    if application.application_status != "draft":
        return redirect(url_for("citizen.apply_confirmation", application_id=application.application_id))
    values = field_map(application)
    spec = specification_for(application.service, values)
    kind = spec.get("kind")
    if kind not in {"passport", "barangay", "residency", "senior", "nbi", "birth", "cenomar", "philsys", "sss"}:
        return redirect(url_for("citizen.apply_review", application_id=application.application_id))

    if missing_documents(application, spec):
        flash("Upload every required document before payment.", "warning")
        return redirect(url_for("citizen.apply_documents", application_id=application.application_id))

    if kind == "passport":
        from app.services.passport_payment import (
            ONLINE_METHODS,
            payment_summary,
            record_demo_payment,
            start_maya_checkout,
        )
        from app.services.passport_scheduling import appointment_for

        if not passport_details_ready(application, spec):
            flash("Complete the application details before payment.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not passport_review_ready(application):
            flash("Review your application before payment.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        if appointment_for(application) is None:
            flash("Select a demonstration appointment before payment.", "warning")
            return redirect(url_for("citizen.apply_schedule", application_id=application.application_id))
        payment_step = 6 if spec.get("type_first") else 5
        back_endpoint = "citizen.apply_schedule"
        free_payment = False
    elif kind == "senior":
        from app.services.senior_payment import confirm_free_application, payment_summary
        from app.services.senior_scheduling import appointment_for

        if not senior_type_ready(application):
            flash("Select an application type before payment.", "warning")
            return redirect(url_for("citizen.apply_type", service_id=application.service_id))
        if not read_fields(application):
            flash("Complete the application details before payment.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not senior_review_ready(application):
            flash("Review your application before payment.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        if appointment_for(application) is None:
            flash("Select a demonstration appointment before payment.", "warning")
            return redirect(url_for("citizen.apply_schedule", application_id=application.application_id))
        payment_step = 6 if spec.get("type_first") else 5
        back_endpoint = "citizen.apply_schedule"
        free_payment = True
        ONLINE_METHODS = ()
        record_demo_payment = None
        start_maya_checkout = None
    elif kind == "philsys":
        from app.services.philsys_payment import confirm_free_application, payment_summary
        from app.services.philsys_scheduling import appointment_for

        if not passport_details_ready(application, spec):
            flash("Complete the application details before payment.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not philsys_review_ready(application):
            flash("Review your application before payment.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        if appointment_for(application) is None:
            flash("Select a demonstration appointment before payment.", "warning")
            return redirect(url_for("citizen.apply_schedule", application_id=application.application_id))
        payment_step = 5
        back_endpoint = "citizen.apply_schedule"
        free_payment = True
        ONLINE_METHODS = ()
        record_demo_payment = None
        start_maya_checkout = None
    elif kind == "sss":
        from app.services.sss_payment import confirm_free_application, payment_summary

        if not read_fields(application):
            flash("Complete the application details before payment.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not sss_review_ready(application):
            flash("Review your application before payment.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        payment_step = 4
        back_endpoint = "citizen.apply_review"
        free_payment = True
        ONLINE_METHODS = ()
        record_demo_payment = None
        start_maya_checkout = None
    elif kind == "nbi":
        from app.services.nbi_payment import (
            payment_summary,
            record_demo_payment,
            start_maya_checkout,
        )
        from app.services.nbi_scheduling import appointment_for
        from app.services.passport_payment import ONLINE_METHODS

        if not nbi_type_ready(application):
            flash("Select an application type before payment.", "warning")
            return redirect(url_for("citizen.apply_type", service_id=application.service_id))
        if not read_fields(application):
            flash("Complete the application details before payment.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not nbi_review_ready(application):
            flash("Review your application before payment.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        if spec.get("review_before_schedule"):
            if appointment_for(application) is None:
                flash("Select a demonstration appointment before payment.", "warning")
                return redirect(url_for("citizen.apply_schedule", application_id=application.application_id))
            payment_step = 6 if spec.get("type_first") else 5
            back_endpoint = "citizen.apply_schedule"
        else:
            payment_step = 5 if spec.get("type_first") else 4
            back_endpoint = "citizen.apply_review"
        free_payment = False
    elif kind == "birth":
        from app.services.birth_payment import (
            payment_summary,
            record_demo_payment,
            start_maya_checkout,
        )
        from app.services.passport_payment import ONLINE_METHODS

        if not birth_type_ready(application):
            flash("Select a request type before payment.", "warning")
            return redirect(url_for("citizen.apply_type", service_id=application.service_id))
        if not read_fields(application):
            flash("Complete the application details before payment.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not birth_review_ready(application):
            flash("Review your application before payment.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        payment_step = 5 if spec.get("type_first") else 4
        back_endpoint = "citizen.apply_review"
        free_payment = False
    elif kind == "cenomar":
        from app.services.cenomar_payment import (
            payment_summary,
            record_demo_payment,
            start_maya_checkout,
        )
        from app.services.passport_payment import ONLINE_METHODS

        if not read_fields(application):
            flash("Complete the application details before payment.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not cenomar_review_ready(application):
            flash("Review your application before payment.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        payment_step = 3
        back_endpoint = "citizen.apply_review"
        free_payment = False
    else:
        from app.services.barangay_payment import (
            payment_summary,
            record_demo_payment,
            start_maya_checkout,
        )
        from app.services.passport_payment import ONLINE_METHODS

        if not read_fields(application):
            flash("Complete the application details before payment.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        reviewed = (
            barangay_review_ready(application)
            if kind == "barangay"
            else residency_review_ready(application)
        )
        if not reviewed:
            flash("Review your application before payment.", "warning")
            return redirect(url_for("citizen.apply_review", application_id=application.application_id))
        if kind in {"barangay", "residency"} and spec.get("review_before_schedule"):
            from app.services.barangay_scheduling import appointment_for

            if appointment_for(application) is None:
                flash("Select a demonstration appointment before payment.", "warning")
                return redirect(url_for("citizen.apply_schedule", application_id=application.application_id))
            payment_step = 6 if spec.get("type_first") else 5
            back_endpoint = "citizen.apply_schedule"
        else:
            payment_step = 4
            back_endpoint = "citizen.apply_review"
        free_payment = False

    if request.method == "POST":
        if free_payment:
            error = confirm_free_application(application, current_user)
            if error:
                flash(error, "warning")
            else:
                if kind == "philsys":
                    from app.services.philsys_confirmation_pdf import ensure_confirmation_pdf

                    ensure_confirmation_pdf(application)
                    flash(
                        "No payment was required. National ID registration remains free at PSA.",
                        "success",
                    )
                elif kind == "sss":
                    from app.services.sss_confirmation_pdf import ensure_confirmation_pdf

                    ensure_confirmation_pdf(application)
                    flash(
                        "No payment was required. Continue registration on the official SSS website.",
                        "success",
                    )
                else:
                    from app.services.senior_confirmation_pdf import ensure_confirmation_pdf

                    ensure_confirmation_pdf(application)
                    flash("No payment was required for this new Senior Citizen ID application.", "success")
                return redirect(
                    url_for("citizen.apply_confirmation", application_id=application.application_id)
                )
        else:
            choice = (request.form.get("payment_choice") or "").strip()
            online_method = (request.form.get("online_method") or "").strip()
            if choice == "online" and online_method == "maya":
                redirect_url, error = start_maya_checkout(application, current_user)
                if error:
                    flash(error, "warning")
                else:
                    return redirect(redirect_url)
            else:
                error = record_demo_payment(
                    application,
                    current_user,
                    choice,
                    online_method,
                )
                if error:
                    flash(error, "warning")
                else:
                    if kind == "passport":
                        from app.services.passport_confirmation_pdf import ensure_confirmation_pdf

                        ensure_confirmation_pdf(application)
                    elif kind in {"barangay", "residency"}:
                        from app.services.barangay_confirmation_pdf import ensure_confirmation_pdf

                        ensure_confirmation_pdf(application)
                    elif kind == "nbi":
                        from app.services.nbi_confirmation_pdf import ensure_confirmation_pdf

                        ensure_confirmation_pdf(application)
                    elif kind == "birth":
                        from app.services.birth_confirmation_pdf import ensure_confirmation_pdf

                        ensure_confirmation_pdf(application)
                    elif kind == "cenomar":
                        from app.services.cenomar_confirmation_pdf import ensure_confirmation_pdf

                        ensure_confirmation_pdf(application)
                    flash("Demonstration payment choice saved. No real payment was collected.", "success")
                    return redirect(
                        url_for("citizen.apply_confirmation", application_id=application.application_id)
                    )

    context = _common(application, payment_step)
    context["summary"] = payment_summary(application)
    context["online_methods"] = ONLINE_METHODS
    context["maya_sandbox"] = not free_payment
    context["payment_back_endpoint"] = back_endpoint
    context["free_payment"] = free_payment
    context["online_payment_only"] = bool(spec.get("online_payment_only")) or kind in {
        "barangay",
        "residency",
        "birth",
    }
    if not free_payment and not context["online_payment_only"]:
        from app.services.passport_payment import ONSITE_LOCATIONS

        context["onsite_locations"] = ONSITE_LOCATIONS
    else:
        context["onsite_locations"] = ()
    return render_template("applications/apply_payment.html", **context)


def _ensure_paid_confirmation_pdf(application, kind):
    if kind == "passport":
        from app.services.passport_confirmation_pdf import ensure_confirmation_pdf

        ensure_confirmation_pdf(application)
    elif kind in {"barangay", "residency"}:
        from app.services.barangay_confirmation_pdf import ensure_confirmation_pdf

        ensure_confirmation_pdf(application)
    elif kind == "nbi":
        from app.services.nbi_confirmation_pdf import ensure_confirmation_pdf

        ensure_confirmation_pdf(application)
    elif kind == "birth":
        from app.services.birth_confirmation_pdf import ensure_confirmation_pdf

        ensure_confirmation_pdf(application)
    elif kind == "cenomar":
        from app.services.cenomar_confirmation_pdf import ensure_confirmation_pdf

        ensure_confirmation_pdf(application)


def apply_maya_result(application_id):
    """
    Return URL after Maya hosted checkout (including QRPh).

    Maya wallet/QR returns can drop the login cookie on cross-site redirect.
    A signed ?token= lets this view verify payment without bouncing to /login first.
    Payment is never marked paid from the redirect alone — status is verified via Maya APIs.
    """
    from app.services.maya_checkout import verify_return_token
    from app.services.passport_payment import latest_payment, verify_maya_payment

    def _continue(endpoint):
        target = url_for(endpoint, application_id=application_id)
        if current_user.is_authenticated:
            return redirect(target)
        flash("Sign in to continue with this Maya payment result.", "warning")
        return redirect(url_for("auth.login", next=target))

    outcome = (request.args.get("outcome") or "").strip().lower()
    token_payload = verify_return_token((request.args.get("token") or "").strip())
    application = None
    if current_user.is_authenticated:
        application = owned_application(current_user.user_id, application_id)
    if application is None and token_payload and token_payload["application_id"] == application_id:
        application = db.session.get(Application, application_id)
    if application is None:
        # Keep the return URL so login can send the citizen back here with the token intact.
        return_path = request.full_path if request.query_string else request.path
        if return_path.endswith("?"):
            return_path = return_path[:-1]
        flash("Sign in again to finish verifying your Maya payment return.", "warning")
        return redirect(url_for("auth.login", next=return_path))

    values = field_map(application)
    spec = specification_for(application.service, values)
    if spec.get("kind") not in {"passport", "barangay", "residency", "nbi", "birth", "cenomar"}:
        abort(404)

    payment = latest_payment(application)
    if payment is None or payment.payment_method != "maya":
        flash("No Maya checkout was found for this application.", "warning")
        return _continue("citizen.apply_payment")
    if (
        token_payload
        and token_payload.get("payment_reference")
        and payment.payment_reference
        and token_payload["payment_reference"] != payment.payment_reference
    ):
        flash("This Maya return link does not match the current payment for this application.", "warning")
        return _continue("citizen.apply_payment")

    status, error = verify_maya_payment(application=application, payment=payment, source="redirect")
    if error:
        flash(
            f"Returned from Maya ({outcome or 'unknown'}), but verification needs a moment: {error}",
            "warning",
        )
        return _continue("citizen.apply_payment")

    db.session.refresh(application)
    payment = latest_payment(application)

    if status == "paid" or (payment and payment.payment_status == "paid"):
        _ensure_paid_confirmation_pdf(application, spec.get("kind"))
        flash("Maya sandbox payment verified as paid.", "success")
        return _continue("citizen.apply_confirmation")

    if status == "failed" or (payment and payment.payment_status == "failed"):
        flash("Maya sandbox payment failed. You can try Pay Now again.", "warning")
        return _continue("citizen.apply_payment")

    if status == "cancelled" or (payment and payment.payment_status == "cancelled"):
        flash("Maya sandbox checkout was cancelled or expired. You can try again.", "warning")
        return _continue("citizen.apply_payment")

    flash(
        "Maya payment is still processing. Refresh payment after a moment, or wait for the webhook.",
        "info",
    )
    return _continue("citizen.apply_payment")


@role_required(User.ROLE_CITIZEN)
def apply_review(application_id):
    application = _draft_or_404(application_id)
    if application.application_status != "draft":
        return redirect(url_for("citizen.apply_confirmation", application_id=application.application_id))
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") == "cenomar":
        from app.services.application_forms import cenomar_incomplete_step

        incomplete = cenomar_incomplete_step(field_map(application))
        if incomplete:
            flash("Complete the CENOMAR details before reviewing this request.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
    missing = missing_documents(application, spec)
    if spec.get("kind") in {"passport", "philsys"}:
        if missing:
            flash("Upload every required document before review.", "warning")
            return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
        if not passport_details_ready(application, spec):
            flash("Complete the application details before review.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
    elif not read_fields(application) or missing:
        flash("Complete the application details and required documents before review.", "warning")
        return redirect(url_for("citizen.application_continue", application_id=application.application_id))
    if spec.get("kind") == "passport" and spec.get("type_first"):
        review_step = 4
    elif spec.get("kind") in {"barangay", "residency", "senior", "nbi", "birth"} and spec.get(
        "type_first"
    ):
        review_step = 4
    elif spec.get("kind") in {"passport", "philsys"}:
        review_step = 3
    elif spec.get("kind") == "cenomar":
        review_step = 2
    else:
        review_step = 3
    context = _common(application, review_step)
    context["fields"] = read_fields(application)
    context["requirements"] = {item.requirement_name: item for item in application.requirements}
    context["checklist"] = read_checklist(application)
    context["terms"] = spec.get("terms") or TERMS_TEXT
    if spec.get("kind") == "philsys":
        from app.services.philsys_national_id import readiness_message

        context["checklist_warning"] = readiness_message(
            field_map(application).get("citizenship"),
            context["checklist"],
        )
    return render_template("applications/apply_review.html", **context)


@role_required(User.ROLE_CITIZEN)
def apply_submit(application_id):
    application = _draft_or_404(application_id)
    if request.form.get("accept_terms") != "yes":
        flash("Confirm the terms before continuing.", "warning")
        return redirect(url_for("citizen.apply_review", application_id=application.application_id))
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") == "passport":
        if missing_documents(application, spec):
            flash("Upload every required document before scheduling.", "warning")
            return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
        if not passport_details_ready(application, spec):
            flash("Complete the application details before scheduling.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        mark_passport_reviewed(application)
        return redirect(url_for("citizen.apply_schedule", application_id=application.application_id))
    if spec.get("kind") == "philsys":
        if missing_documents(application, spec):
            flash("Upload every required document before scheduling.", "warning")
            return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
        if not passport_details_ready(application, spec):
            flash("Complete the application details before scheduling.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        mark_philsys_reviewed(application)
        return redirect(url_for("citizen.apply_schedule", application_id=application.application_id))
    if spec.get("kind") == "nbi":
        if missing_documents(application, spec):
            flash("Upload every required document before continuing.", "warning")
            return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
        if not read_fields(application):
            flash("Complete the application details before continuing.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not nbi_type_ready(application):
            flash("Select an application type before continuing.", "warning")
            return redirect(url_for("citizen.apply_type", service_id=application.service_id))
        mark_nbi_reviewed(application)
        if spec.get("review_before_schedule"):
            return redirect(url_for("citizen.apply_schedule", application_id=application.application_id))
        return redirect(url_for("citizen.apply_payment", application_id=application.application_id))
    if spec.get("kind") in {"barangay", "residency"} and spec.get("review_before_schedule"):
        if missing_documents(application, spec):
            flash("Upload every required document before scheduling.", "warning")
            return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
        if not read_fields(application):
            flash("Complete the application details before scheduling.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        type_ready = (
            barangay_type_ready(application)
            if spec.get("kind") == "barangay"
            else residency_type_ready(application)
        )
        if not type_ready:
            flash("Select an application type before scheduling.", "warning")
            return redirect(url_for("citizen.apply_type", service_id=application.service_id))
        if spec.get("kind") == "residency":
            mark_residency_reviewed(application)
        else:
            mark_barangay_reviewed(application)
        return redirect(url_for("citizen.apply_schedule", application_id=application.application_id))
    if spec.get("kind") == "senior" and spec.get("review_before_schedule"):
        if missing_documents(application, spec):
            flash("Upload every required document before scheduling.", "warning")
            return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
        if not read_fields(application):
            flash("Complete the application details before scheduling.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if not senior_type_ready(application):
            flash("Select an application type before scheduling.", "warning")
            return redirect(url_for("citizen.apply_type", service_id=application.service_id))
        mark_senior_reviewed(application)
        return redirect(url_for("citizen.apply_schedule", application_id=application.application_id))
    if spec.get("kind") in {"barangay", "residency", "senior", "birth", "cenomar", "sss"} or spec.get(
        "payment_after_review"
    ):
        if missing_documents(application, spec):
            flash("Upload every required document before payment.", "warning")
            return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
        if not read_fields(application):
            flash("Complete the application details before payment.", "warning")
            return redirect(url_for("citizen.apply_details", service_id=application.service_id))
        if spec.get("kind") == "residency":
            mark_residency_reviewed(application)
        elif spec.get("kind") == "senior":
            mark_senior_reviewed(application)
        elif spec.get("kind") == "birth":
            mark_birth_reviewed(application)
        elif spec.get("kind") == "cenomar":
            mark_cenomar_reviewed(application)
        elif spec.get("kind") == "sss":
            mark_sss_reviewed(application)
        else:
            mark_barangay_reviewed(application)
        return redirect(url_for("citizen.apply_payment", application_id=application.application_id))
    error = submit_application(application, current_user)
    if error:
        flash(error, "warning")
        return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
    return redirect(url_for("citizen.apply_confirmation", application_id=application.application_id))


@role_required(User.ROLE_CITIZEN)
def record_sss_tracking(application_id):
    """Store an SS Number or transaction number the citizen already received from SSS."""
    application = _draft_or_404(application_id)
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") != "sss" or application.application_status == "draft":
        abort(404)
    error = save_sss_tracking(application, current_user, request.form, request.files)
    if error:
        flash(error, "warning")
    else:
        flash(
            "The SSS details were recorded. OneGov PH did not receive them from SSS, and this does not mean SSS issued or verified an SS Number.",
            "success",
        )
    return redirect(url_for("citizen.application_detail", application_id=application.application_id))


def record_cenomar_tracking(application_id):
    """Store a PSA reference the citizen already has. This does not submit the request to PSA."""
    application = _draft_or_404(application_id)
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") != "cenomar" or application.application_status == "draft":
        abort(404)
    error = save_cenomar_tracking(application, current_user, request.form)
    if error:
        flash(error, "warning")
    else:
        flash(
            "The PSA reference was recorded. OneGov PH did not receive it from PSA, and this does not mean PSA has approved or issued the CENOMAR.",
            "success",
        )
    return redirect(url_for("citizen.application_detail", application_id=application.application_id))


@role_required(User.ROLE_CITIZEN)
def record_philsys_reference(application_id):
    """Let the owner store a PSA reference later. This does not mark the person registered."""
    application = _draft_or_404(application_id)
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") != "philsys" or application.application_status == "draft":
        abort(404)
    error = save_philsys_reference(application, request.form.get("philsys_reference", ""))
    if error:
        flash(error, "warning")
    else:
        flash("The PhilSys transaction reference was saved. This does not register you with PhilSys.", "success")
    return redirect(url_for("citizen.application_detail", application_id=application.application_id))


@role_required(User.ROLE_CITIZEN)
def apply_cancel(application_id):
    application = owned_application(current_user.user_id, application_id)
    if application is None:
        abort(404)
    if application.application_status == "draft":
        cancel_draft(application)
        flash("The draft application was cancelled.", "success")
        return redirect(url_for("citizen.services"))
    error = cancel_application(application, current_user, request.form.get("cancellation_reason", ""))
    if error:
        flash(error, "warning")
    else:
        flash("The application was cancelled. OneGov PH has not withdrawn it from a government agency.", "success")
    return redirect(url_for("citizen.application_detail", application_id=application.application_id))


@role_required(User.ROLE_CITIZEN)
def apply_confirmation(application_id):
    application = _draft_or_404(application_id)
    if application.application_status == "draft":
        return redirect(url_for("citizen.application_continue", application_id=application.application_id))
    spec = specification_for(application.service, field_map(application))
    labels = dict(STATUS_LABELS)
    labels.update(spec.get("status_labels") or {})
    context = {
        "application": application,
        "service": application.service,
        "step": spec.get("confirmation_step") or 4,
        "step_labels": spec.get("step_labels"),
        "spec": spec,
        "fields": read_fields(application),
        "status_labels": labels,
    }
    if spec.get("kind") == "passport":
        from app.services.passport_confirmation_pdf import confirmation_id_for, ensure_confirmation_pdf
        from app.services.passport_payment import payment_summary
        from app.services.passport_requirements import bring_requirements_for
        from app.services.passport_scheduling import appointment_for

        ensure_confirmation_pdf(application)
        context["appointment"] = appointment_for(application)
        context["summary"] = payment_summary(application)
        context["confirmation_id"] = confirmation_id_for(application)
        context["bring_requirements"] = bring_requirements_for(field_map(application).get("application_type"))
    elif spec.get("kind") in {"barangay", "residency"}:
        from app.services.barangay_confirmation_pdf import confirmation_id_for, ensure_confirmation_pdf
        from app.services.barangay_payment import payment_summary
        from app.services.barangay_scheduling import appointment_for

        ensure_confirmation_pdf(application)
        context["summary"] = payment_summary(application)
        context["confirmation_id"] = confirmation_id_for(application)
        context["appointment"] = appointment_for(application)
    elif spec.get("kind") == "senior":
        from app.services.senior_confirmation_pdf import confirmation_id_for, ensure_confirmation_pdf
        from app.services.senior_payment import payment_summary
        from app.services.senior_requirements import bring_requirements_for
        from app.services.senior_scheduling import appointment_for

        answers = field_map(application)
        ensure_confirmation_pdf(application)
        context["summary"] = payment_summary(application)
        context["confirmation_id"] = confirmation_id_for(application)
        context["appointment"] = appointment_for(application)
        context["bring_requirements"] = bring_requirements_for(answers.get("application_type"))
        context["senior_answers"] = {
            "full_name": " ".join(
                part
                for part in (
                    answers.get("first_name"),
                    answers.get("middle_name"),
                    answers.get("last_name"),
                )
                if part
            ).strip(),
            "barangay": answers.get("barangay") or "",
            "city": answers.get("city") or "",
        }
    elif spec.get("kind") == "nbi":
        from app.services.nbi_confirmation_pdf import confirmation_id_for, ensure_confirmation_pdf
        from app.services.nbi_payment import payment_summary
        from app.services.nbi_requirements import bring_requirements_for, is_nbi_new_application

        answers = field_map(application)
        ensure_confirmation_pdf(application)
        context["summary"] = payment_summary(application)
        context["confirmation_id"] = confirmation_id_for(application)
        if is_nbi_new_application(answers.get("application_type")):
            context["bring_requirements"] = bring_requirements_for(answers.get("application_type"))
            context["appointment"] = (context["summary"] or {}).get("appointment")
    elif spec.get("kind") == "birth":
        from app.services.birth_confirmation_pdf import confirmation_id_for, ensure_confirmation_pdf
        from app.services.birth_payment import payment_summary

        ensure_confirmation_pdf(application)
        context["summary"] = payment_summary(application)
        context["confirmation_id"] = confirmation_id_for(application)
    elif spec.get("kind") == "cenomar":
        from app.services.cenomar_confirmation_pdf import confirmation_id_for, ensure_confirmation_pdf
        from app.services.cenomar_payment import payment_summary

        ensure_confirmation_pdf(application)
        context["summary"] = payment_summary(application)
        context["confirmation_id"] = confirmation_id_for(application)
    elif spec.get("kind") == "philsys":
        from app.services.philsys_confirmation_pdf import confirmation_id_for, ensure_confirmation_pdf
        from app.services.philsys_payment import payment_summary
        from app.services.philsys_scheduling import appointment_for

        ensure_confirmation_pdf(application)
        context["summary"] = payment_summary(application)
        context["confirmation_id"] = confirmation_id_for(application)
        context["appointment"] = appointment_for(application)
    elif spec.get("kind") == "sss":
        from app.services.sss_confirmation_pdf import confirmation_id_for, ensure_confirmation_pdf
        from app.services.sss_payment import payment_summary

        answers = field_map(application)
        ensure_confirmation_pdf(application)
        context["summary"] = payment_summary(application)
        context["confirmation_id"] = confirmation_id_for(application)
        context["sss_answers"] = {
            "full_name": " ".join(
                part
                for part in (
                    answers.get("first_name"),
                    answers.get("middle_name"),
                    answers.get("last_name"),
                )
                if part
            ).strip(),
            "barangay": answers.get("barangay") or "",
            "city": answers.get("city") or "",
            "has_primary_id": answers.get("has_primary_id") or "",
        }
    return render_template("applications/apply_confirmation.html", **context)


@role_required(User.ROLE_CITIZEN)
def passport_confirmation_pdf(application_id):
    application = _draft_or_404(application_id)
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") != "passport" or application.application_status == "draft":
        abort(404)
    from app.services.passport_confirmation_pdf import absolute_confirmation_pdf, ensure_confirmation_pdf

    ensure_confirmation_pdf(application)
    path = absolute_confirmation_pdf(application)
    if path is None:
        abort(404)
    return send_file(
        path,
        as_attachment=True,
        download_name=f"onegov-passport-demo-{application.tracking_number}.pdf",
    )


@role_required(User.ROLE_CITIZEN)
def barangay_confirmation_pdf(application_id):
    application = _draft_or_404(application_id)
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") not in {"barangay", "residency"} or application.application_status == "draft":
        abort(404)
    from app.services.barangay_confirmation_pdf import absolute_confirmation_pdf, ensure_confirmation_pdf

    ensure_confirmation_pdf(application)
    path = absolute_confirmation_pdf(application)
    if path is None:
        abort(404)
    slug = "residency" if spec.get("kind") == "residency" else "barangay"
    return send_file(
        path,
        as_attachment=True,
        download_name=f"onegov-{slug}-demo-{application.tracking_number}.pdf",
    )


@role_required(User.ROLE_CITIZEN)
def senior_confirmation_pdf(application_id):
    application = _draft_or_404(application_id)
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") != "senior" or application.application_status == "draft":
        abort(404)
    from app.services.senior_confirmation_pdf import absolute_confirmation_pdf, ensure_confirmation_pdf

    ensure_confirmation_pdf(application)
    path = absolute_confirmation_pdf(application)
    if path is None:
        abort(404)
    return send_file(
        path,
        as_attachment=True,
        download_name=f"onegov-senior-demo-{application.tracking_number}.pdf",
    )


@role_required(User.ROLE_CITIZEN)
def nbi_confirmation_pdf(application_id):
    application = _draft_or_404(application_id)
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") != "nbi" or application.application_status == "draft":
        abort(404)
    from app.services.nbi_confirmation_pdf import absolute_confirmation_pdf, ensure_confirmation_pdf

    ensure_confirmation_pdf(application)
    path = absolute_confirmation_pdf(application)
    if path is None:
        abort(404)
    return send_file(
        path,
        as_attachment=True,
        download_name=f"onegov-nbi-demo-{application.tracking_number}.pdf",
    )


@role_required(User.ROLE_CITIZEN)
def birth_confirmation_pdf(application_id):
    application = _draft_or_404(application_id)
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") != "birth" or application.application_status == "draft":
        abort(404)
    from app.services.birth_confirmation_pdf import absolute_confirmation_pdf, ensure_confirmation_pdf

    ensure_confirmation_pdf(application)
    path = absolute_confirmation_pdf(application)
    if path is None:
        abort(404)
    return send_file(
        path,
        as_attachment=True,
        download_name=f"onegov-birth-demo-{application.tracking_number}.pdf",
    )


@role_required(User.ROLE_CITIZEN)
def sss_confirmation_pdf(application_id):
    application = _draft_or_404(application_id)
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") != "sss" or application.application_status == "draft":
        abort(404)
    from app.services.sss_confirmation_pdf import absolute_confirmation_pdf, ensure_confirmation_pdf

    ensure_confirmation_pdf(application)
    path = absolute_confirmation_pdf(application)
    if path is None:
        abort(404)
    return send_file(
        path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"sss-confirmation-{application.tracking_number}.pdf",
    )


@role_required(User.ROLE_CITIZEN)
def philsys_confirmation_pdf(application_id):
    application = _draft_or_404(application_id)
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") != "philsys" or application.application_status == "draft":
        abort(404)
    from app.services.philsys_confirmation_pdf import absolute_confirmation_pdf, ensure_confirmation_pdf

    ensure_confirmation_pdf(application)
    path = absolute_confirmation_pdf(application)
    if path is None:
        abort(404)
    return send_file(
        path,
        as_attachment=True,
        download_name=f"onegov-philsys-demo-{application.tracking_number}.pdf",
    )


@role_required(User.ROLE_CITIZEN)
def cenomar_confirmation_pdf(application_id):
    application = _draft_or_404(application_id)
    spec = specification_for(application.service, field_map(application))
    if spec.get("kind") != "cenomar" or application.application_status == "draft":
        abort(404)
    from app.services.cenomar_confirmation_pdf import absolute_confirmation_pdf, ensure_confirmation_pdf

    ensure_confirmation_pdf(application)
    path = absolute_confirmation_pdf(application)
    if path is None:
        abort(404)
    return send_file(
        path,
        as_attachment=True,
        download_name=f"onegov-cenomar-demo-{application.tracking_number}.pdf",
    )


@role_required(User.ROLE_CITIZEN)
def application_document(application_id, requirement_id):
    application = _draft_or_404(application_id)
    row = next(
        (item for item in application.requirements if item.requirement_id == requirement_id),
        None,
    )
    path = absolute_upload(row.uploaded_file) if row is not None else None
    if path is None:
        abort(404)
    return send_file(path, as_attachment=False, download_name=row.remarks or path.name)


@role_required(User.ROLE_CITIZEN)
def application_continue(application_id):
    application = _draft_or_404(application_id)
    target = continue_target(application)
    if target == "type":
        return redirect(url_for("citizen.apply_type", service_id=application.service_id))
    if target == "details":
        return redirect(url_for("citizen.apply_details", service_id=application.service_id))
    if target == "documents":
        return redirect(url_for("citizen.apply_documents", application_id=application.application_id))
    if target == "schedule":
        return redirect(url_for("citizen.apply_schedule", application_id=application.application_id))
    if target == "payment":
        return redirect(url_for("citizen.apply_payment", application_id=application.application_id))
    if target == "review":
        return redirect(url_for("citizen.apply_review", application_id=application.application_id))
    return redirect(url_for("citizen.application_detail", application_id=application.application_id))


def register(blueprint):
    rules = (
        ("/citizen/services/<int:service_id>/apply", apply_details, ["GET", "POST"], "apply_details"),
        ("/citizen/services/<int:service_id>/apply/type", apply_type, ["GET", "POST"], "apply_type"),
        ("/citizen/applications/<int:application_id>/documents", apply_documents, ["GET"], "apply_documents"),
        (
            "/citizen/applications/<int:application_id>/documents/continue",
            continue_documents,
            ["POST"],
            "continue_documents",
        ),
        (
            "/citizen/applications/<int:application_id>/documents/<document_key>/remove",
            remove_document,
            ["POST"],
            "remove_document",
        ),
        (
            "/citizen/applications/<int:application_id>/documents/<document_key>",
            upload_document,
            ["POST"],
            "upload_document",
        ),
        (
            "/citizen/applications/<int:application_id>/schedule",
            apply_schedule,
            ["GET", "POST"],
            "apply_schedule",
        ),
        (
            "/citizen/applications/<int:application_id>/payment",
            apply_payment,
            ["GET", "POST"],
            "apply_payment",
        ),
        (
            "/citizen/applications/<int:application_id>/payment/maya/result",
            apply_maya_result,
            ["GET"],
            "apply_maya_result",
        ),
        (
            "/citizen/applications/<int:application_id>/passport-confirmation.pdf",
            passport_confirmation_pdf,
            ["GET"],
            "passport_confirmation_pdf",
        ),
        (
            "/citizen/applications/<int:application_id>/barangay-confirmation.pdf",
            barangay_confirmation_pdf,
            ["GET"],
            "barangay_confirmation_pdf",
        ),
        (
            "/citizen/applications/<int:application_id>/senior-confirmation.pdf",
            senior_confirmation_pdf,
            ["GET"],
            "senior_confirmation_pdf",
        ),
        (
            "/citizen/applications/<int:application_id>/nbi-confirmation.pdf",
            nbi_confirmation_pdf,
            ["GET"],
            "nbi_confirmation_pdf",
        ),
        (
            "/citizen/applications/<int:application_id>/birth-confirmation.pdf",
            birth_confirmation_pdf,
            ["GET"],
            "birth_confirmation_pdf",
        ),
        (
            "/citizen/applications/<int:application_id>/cenomar-confirmation.pdf",
            cenomar_confirmation_pdf,
            ["GET"],
            "cenomar_confirmation_pdf",
        ),
        (
            "/citizen/applications/<int:application_id>/philsys-confirmation.pdf",
            philsys_confirmation_pdf,
            ["GET"],
            "philsys_confirmation_pdf",
        ),
        (
            "/citizen/applications/<int:application_id>/sss-confirmation.pdf",
            sss_confirmation_pdf,
            ["GET"],
            "sss_confirmation_pdf",
        ),
        ("/citizen/applications/<int:application_id>/review", apply_review, ["GET"], "apply_review"),
        ("/citizen/applications/<int:application_id>/submit", apply_submit, ["POST"], "apply_submit"),
        (
            "/citizen/applications/<int:application_id>/philsys-reference",
            record_philsys_reference,
            ["POST"],
            "record_philsys_reference",
        ),
        (
            "/citizen/applications/<int:application_id>/cenomar-tracking",
            record_cenomar_tracking,
            ["POST"],
            "record_cenomar_tracking",
        ),
        (
            "/citizen/applications/<int:application_id>/sss-tracking",
            record_sss_tracking,
            ["POST"],
            "record_sss_tracking",
        ),
        ("/citizen/applications/<int:application_id>/cancel", apply_cancel, ["POST"], "apply_cancel"),
        (
            "/citizen/applications/<int:application_id>/confirmation",
            apply_confirmation,
            ["GET"],
            "apply_confirmation",
        ),
        (
            "/citizen/applications/<int:application_id>/files/<int:requirement_id>",
            application_document,
            ["GET"],
            "application_document",
        ),
        (
            "/citizen/applications/<int:application_id>/continue",
            application_continue,
            ["GET"],
            "application_continue",
        ),
    )
    for path, view, methods, endpoint in rules:
        blueprint.add_url_rule(path, endpoint=endpoint, view_func=view, methods=methods)
