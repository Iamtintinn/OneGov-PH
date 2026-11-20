"""Demonstration appointment slots for MySSS Card new application assistance."""

from datetime import date, datetime, timedelta

from app.models.notification import Notification
from app.services.application_service import read_details, write_details


def _location(code, label, region, address):
    return {
        "code": code,
        "label": label,
        "region": region,
        "address": address,
    }


LOCATIONS = (
    _location("sss_aub_paso_de_blas", "AUB Paso de Blas", "NCR", "Puregold Mall, Paso de Blas, Valenzuela City"),
    _location("sss_aub_las_pinas", "AUB Las Piñas", "NCR", "303 Real Street, Pamplona 3, Las Piñas City"),
    _location("sss_aub_binondo", "AUB Binondo", "NCR", "564 Quintin Paredes Street, Binondo, Manila"),
    _location("sss_aub_pioneer", "AUB Pioneer", "NCR", "8007 Pioneer Street, Pasig City"),
    _location("sss_diliman", "SSS Diliman", "NCR", "SSS Livelihood Building, East Avenue, Quezon City"),
    _location("sss_alabang", "SSS Alabang", "NCR", "22 Norfil Building, Putatan, Muntinlupa City"),
    _location("sss_binondo", "SSS Binondo", "NCR", "Ground Floor, 232 Juan Luna Street, Binondo, Manila"),
    _location("sss_pioneer", "SSS Pioneer", "NCR", "8007 Pioneer Street, Kapitolyo, Pasig City"),
    _location("sss_aub_malolos", "AUB Malolos", "Region III", "Km. 44–45 MacArthur Highway, Longos, Malolos, Bulacan"),
    _location("sss_aub_clark", "AUB Clark", "Region III", "Pavilion 12, Berthaphil Clark Center, Clark Freeport Zone, Pampanga"),
    _location("sss_aub_cabanatuan", "AUB Cabanatuan", "Region III", "Ground Floor, JRS Building, Maharlika Highway, Cabanatuan City"),
    _location("sss_malolos", "SSS Malolos", "Region III", "VIB Building, Km. 44–45 MacArthur Highway, Longos, Malolos, Bulacan"),
    _location("sss_tarlac", "SSS Tarlac", "Region III", "SSS Building, Macabulos Drive, San Vicente, Tarlac City"),
    _location("sss_aub_dagupan", "AUB Dagupan", "Region I", "One Pacific Place, Arellano Street, Dagupan City"),
    _location("sss_baguio", "SSS Baguio", "CAR", "SSS Building, Harrison Road, Baguio City"),
    _location("sss_aub_imus", "AUB Imus", "Region IV-A", "Km. 21 General Aguinaldo Highway, Bayan Luma, Imus, Cavite"),
    _location("sss_aub_taytay", "AUB Taytay", "Region IV-A", "DIVI Plaza, Market Road, Barangay San Juan, Taytay, Rizal"),
    _location("sss_calamba", "SSS Calamba", "Region IV-A", "SSS Building, National Highway, Parian, Calamba City, Laguna"),
    _location("sss_lipa", "SSS Lipa", "Region IV-A", "The Only Place Business Center, Marauoy, Lipa City, Batangas"),
    _location("sss_aub_naga", "AUB Naga", "Region V", "Nagaland Hotel, Elias Angeles Street, Naga City"),
    _location("sss_legazpi", "SSS Legazpi", "Region V", "Morante Building, Imperial Court Subdivision Phase II, Legazpi City"),
    _location("sss_tuguegarao", "SSS Tuguegarao", "Region II", "Robinsons Place, Level 2, Barangay Tanza, Tuguegarao City"),
)

TIME_SLOTS = ("08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00")
VISIBLE_MONTHS = 4


def _now():
    return datetime.now().replace(microsecond=0)


def location_by_code(code):
    return next((item for item in LOCATIONS if item["code"] == code), None)


def _add_months(value, months):
    month = value.month + months
    year = value.year
    while month > 12:
        month -= 12
        year += 1
    while month < 1:
        month += 12
        year -= 1
    return date(year, month, 1)


def _month_end(value):
    return _add_months(value, 1) - timedelta(days=1)


def booking_window(today=None):
    today = today or date.today()
    start_month = date(today.year, today.month, 1)
    end_month = _add_months(start_month, VISIBLE_MONTHS - 1)
    return start_month, _month_end(end_month)


def _weekdays(start=None, end=None):
    today = date.today()
    window_start, window_end = booking_window(today)
    start = start or max(today + timedelta(days=1), window_start)
    end = end or window_end
    found = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current >= today + timedelta(days=1):
            found.append(current)
        current += timedelta(days=1)
    return found


def available_calendar(location_code, exclude_application_id=None):
    location = location_by_code(location_code)
    if location is None:
        return []
    days = []
    for day in _weekdays():
        days.append(
            {
                "date": day.isoformat(),
                "label": day.strftime("%a, %d %b %Y"),
                "weekday": day.strftime("%a"),
                "day_number": day.day,
                "month_label": day.strftime("%b %Y"),
                "open_slots": list(TIME_SLOTS),
                "closed_slots": [],
                "has_open": True,
            }
        )
    return days


def available_month_calendars(location_code, exclude_application_id=None):
    bookable = {
        day["date"]: day
        for day in available_calendar(location_code, exclude_application_id)
    }
    start_month, end_month = booking_window()
    months = []
    cursor = start_month

    while cursor <= end_month:
        next_month = _add_months(cursor, 1)
        month_end = next_month - timedelta(days=1)
        lead = (cursor.weekday() + 1) % 7
        grid_start = cursor - timedelta(days=lead)
        cells = []
        day = grid_start
        while True:
            in_month = day.month == cursor.month
            iso = day.isoformat()
            info = bookable.get(iso) if in_month else None
            selectable = bool(info and info["has_open"])
            cells.append(
                {
                    "date": iso if in_month else "",
                    "day_number": day.day if in_month else "",
                    "in_month": in_month,
                    "label": day.strftime("%A, %d %B %Y") if in_month else "",
                    "open_slots": info["open_slots"] if info else [],
                    "has_open": selectable,
                    "selectable": selectable,
                    "is_unavailable": in_month and not selectable,
                }
            )
            day += timedelta(days=1)
            if day > month_end and len(cells) % 7 == 0:
                break

        months.append(
            {
                "key": cursor.strftime("%Y-%m"),
                "title": cursor.strftime("%B %Y"),
                "weeks": [cells[index : index + 7] for index in range(0, len(cells), 7)],
            }
        )
        cursor = next_month

    return months


def appointment_for(application):
    details = read_details(application)
    appointment = details.get("appointment")
    if not appointment:
        return None
    if appointment.get("service_kind") and appointment.get("service_kind") != "sss":
        return None
    return appointment


def save_appointment(application, user, location_code, appointment_date, appointment_time):
    """Book one demonstration MySSS Card appointment slot."""
    location = location_by_code(location_code)
    if location is None:
        return "Select a demonstration appointment location."
    try:
        day = datetime.strptime(str(appointment_date or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return "Select an available demonstration date."
    slot = str(appointment_time or "").strip()
    if slot not in TIME_SLOTS:
        return "Select an available demonstration time."
    _, window_end = booking_window()
    if day < date.today() + timedelta(days=1) or day > window_end or day.weekday() >= 5:
        return "Select an available demonstration weekday."
    open_days = {item["date"]: item for item in available_calendar(location_code, application.application_id)}
    day_info = open_days.get(day.isoformat())
    if day_info is None or slot not in day_info["open_slots"]:
        return "That demonstration slot is no longer available. Choose another date or time."

    payload = {
        "service_kind": "sss",
        "location_code": location["code"],
        "location_label": location["label"],
        "appointment_date": day.isoformat(),
        "appointment_time": slot,
        "label": "Demonstration Appointment – Not an Official SSS Booking",
        "address": location["address"],
    }
    details = read_details(application)
    details["appointment"] = payload
    write_details(application, details, commit=False)
    now = _now()
    from app import db

    db.session.add(
        Notification(
            user_id=user.user_id,
            notification_title="Demonstration appointment saved",
            notification_message=(
                f"Your MySSS Card demonstration appointment for {payload['appointment_date']} "
                f"at {payload['appointment_time']} was saved. This is not an official SSS appointment."
            ),
            notification_type="appointment",
            read_status="unread",
            created_date=now,
        )
    )
    db.session.commit()
    return None
