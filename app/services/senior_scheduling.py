"""Demonstration appointment slots for Senior Citizen ID / OSCA visits. Not an official OSCA booking system."""

from datetime import date, datetime, timedelta

from app.models.notification import Notification
from app.services.application_service import read_details, write_details

LOCATIONS = (
    {"code": "osca_caloocan", "region": "NCR", "city": "Caloocan City", "label": "Caloocan OSCA", "address": "Caloocan City · NCR · Demonstration OSCA appointment office", "latitude": 14.7560, "longitude": 120.9400},
    {"code": "osca_quezon_city", "region": "NCR", "city": "Quezon City", "label": "Quezon City OSCA", "address": "Quezon City · NCR · Demonstration OSCA appointment office", "latitude": 14.6760, "longitude": 121.0437},
    {"code": "osca_manila", "region": "NCR", "city": "Manila", "label": "Manila OSCA", "address": "Manila · NCR · Demonstration OSCA appointment office", "latitude": 14.5995, "longitude": 120.9842},
    {"code": "osca_pasig", "region": "NCR", "city": "Pasig City", "label": "Pasig OSCA", "address": "Pasig City · NCR · Demonstration OSCA appointment office", "latitude": 14.5764, "longitude": 121.0851},
    {"code": "osca_makati", "region": "NCR", "city": "Makati City", "label": "Makati OSCA", "address": "Makati City · NCR · Demonstration OSCA appointment office", "latitude": 14.5547, "longitude": 121.0244},
    {"code": "osca_malabon", "region": "NCR", "city": "Malabon City", "label": "Malabon OSCA", "address": "Malabon City · NCR · Demonstration OSCA appointment office", "latitude": 14.6640, "longitude": 120.9550},
    {"code": "osca_valenzuela", "region": "NCR", "city": "Valenzuela City", "label": "Valenzuela OSCA", "address": "Valenzuela City · NCR · Demonstration OSCA appointment office", "latitude": 14.6760, "longitude": 120.9870},
    {"code": "osca_pasay", "region": "NCR", "city": "Pasay City", "label": "Pasay OSCA", "address": "Pasay City · NCR · Demonstration OSCA appointment office", "latitude": 14.5540, "longitude": 120.9900},
    {"code": "osca_angeles", "region": "Region III", "city": "Angeles City, Pampanga", "label": "Angeles OSCA", "address": "Angeles City, Pampanga · Region III · Demonstration OSCA appointment office", "latitude": 15.1450, "longitude": 120.5889},
    {"code": "osca_san_fernando_pampanga", "region": "Region III", "city": "San Fernando, Pampanga", "label": "San Fernando OSCA", "address": "San Fernando, Pampanga · Region III · Demonstration OSCA appointment office", "latitude": 15.0300, "longitude": 120.6819},
    {"code": "osca_olongapo", "region": "Region III", "city": "Olongapo City, Zambales", "label": "Olongapo OSCA", "address": "Olongapo City, Zambales · Region III · Demonstration OSCA appointment office", "latitude": 14.8300, "longitude": 120.2860},
    {"code": "osca_malolos", "region": "Region III", "city": "Malolos City, Bulacan", "label": "Malolos OSCA", "address": "Malolos City, Bulacan · Region III · Demonstration OSCA appointment office", "latitude": 14.8430, "longitude": 120.8120},
    {"code": "osca_meycauayan", "region": "Region III", "city": "Meycauayan, Bulacan", "label": "Meycauayan OSCA", "address": "Meycauayan, Bulacan · Region III · Demonstration OSCA appointment office", "latitude": 14.7330, "longitude": 120.9500},
    {"code": "osca_balanga", "region": "Region III", "city": "Balanga City, Bataan", "label": "Balanga OSCA", "address": "Balanga City, Bataan · Region III · Demonstration OSCA appointment office", "latitude": 14.7000, "longitude": 120.5400},
    {"code": "osca_antipolo", "region": "Region IV-A", "city": "Antipolo City, Rizal", "label": "Antipolo OSCA", "address": "Antipolo City, Rizal · Region IV-A · Demonstration OSCA appointment office", "latitude": 14.6210, "longitude": 121.1720},
    {"code": "osca_bacoor", "region": "Region IV-A", "city": "Bacoor City, Cavite", "label": "Bacoor OSCA", "address": "Bacoor City, Cavite · Region IV-A · Demonstration OSCA appointment office", "latitude": 14.4780, "longitude": 120.9180},
    {"code": "osca_dasmarinas", "region": "Region IV-A", "city": "Dasmariñas City, Cavite", "label": "Dasmariñas OSCA", "address": "Dasmariñas City, Cavite · Region IV-A · Demonstration OSCA appointment office", "latitude": 14.3310, "longitude": 120.9400},
    {"code": "osca_imus", "region": "Region IV-A", "city": "Imus City, Cavite", "label": "Imus OSCA", "address": "Imus City, Cavite · Region IV-A · Demonstration OSCA appointment office", "latitude": 14.4300, "longitude": 120.9360},
    {"code": "osca_calamba", "region": "Region IV-A", "city": "Calamba City, Laguna", "label": "Calamba OSCA", "address": "Calamba City, Laguna · Region IV-A · Demonstration OSCA appointment office", "latitude": 14.2110, "longitude": 121.1630},
    {"code": "osca_santa_rosa", "region": "Region IV-A", "city": "Santa Rosa City, Laguna", "label": "Santa Rosa OSCA", "address": "Santa Rosa City, Laguna · Region IV-A · Demonstration OSCA appointment office", "latitude": 14.2360, "longitude": 121.0770},
    {"code": "osca_batangas", "region": "Region IV-A", "city": "Batangas City", "label": "Batangas OSCA", "address": "Batangas City · Region IV-A · Demonstration OSCA appointment office", "latitude": 13.7565, "longitude": 121.0583},
    {"code": "osca_lucena", "region": "Region IV-A", "city": "Lucena City, Quezon", "label": "Lucena OSCA", "address": "Lucena City, Quezon · Region IV-A · Demonstration OSCA appointment office", "latitude": 13.9460, "longitude": 121.6500},
    {"code": "osca_san_fernando_la_union", "region": "Region I", "city": "San Fernando City, La Union", "label": "San Fernando OSCA", "address": "San Fernando City, La Union · Region I · Demonstration OSCA appointment office", "latitude": 16.6170, "longitude": 120.3160},
    {"code": "osca_laoag", "region": "Region I", "city": "Laoag City, Ilocos Norte", "label": "Laoag OSCA", "address": "Laoag City, Ilocos Norte · Region I · Demonstration OSCA appointment office", "latitude": 18.1980, "longitude": 120.5940},
    {"code": "osca_dagupan", "region": "Region I", "city": "Dagupan City, Pangasinan", "label": "Dagupan OSCA", "address": "Dagupan City, Pangasinan · Region I · Demonstration OSCA appointment office", "latitude": 16.0430, "longitude": 120.3330},
    {"code": "osca_tuguegarao", "region": "Region II", "city": "Tuguegarao City, Cagayan", "label": "Tuguegarao OSCA", "address": "Tuguegarao City, Cagayan · Region II · Demonstration OSCA appointment office", "latitude": 17.6130, "longitude": 121.7260},
    {"code": "osca_legazpi", "region": "Region V", "city": "Legazpi City, Albay", "label": "Legazpi OSCA", "address": "Legazpi City, Albay · Region V · Demonstration OSCA appointment office", "latitude": 13.1390, "longitude": 123.7430},
    {"code": "osca_baguio", "region": "CAR", "city": "Baguio City", "label": "Baguio OSCA", "address": "Baguio City · CAR · Demonstration OSCA appointment office", "latitude": 16.4023, "longitude": 120.5960},
    {"code": "osca_main", "region": "Demonstration", "city": "Demonstration site", "label": "OSCA Main Office (Demonstration)", "address": "Demonstration site · City / municipal OSCA main window", "latitude": 14.5995, "longitude": 120.9842, "legacy": True},
    {"code": "osca_satellite", "region": "Demonstration", "city": "Demonstration site", "label": "OSCA Satellite Desk (Demonstration)", "address": "Demonstration site · OSCA satellite service desk", "latitude": 14.5995, "longitude": 120.9842, "legacy": True},
    {"code": "osca_community", "region": "Demonstration", "city": "Demonstration site", "label": "OSCA Community Center Window (Demonstration)", "address": "Demonstration site · Community center senior services window", "latitude": 14.5995, "longitude": 120.9842, "legacy": True},
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
    if appointment.get("service_kind") and appointment.get("service_kind") != "senior":
        return None
    return appointment


def save_appointment(application, user, location_code, appointment_date, appointment_time):
    """Book one demonstration OSCA slot. Stays draft until the free payment step is completed."""
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
        "service_kind": "senior",
        "location_code": location["code"],
        "location_label": location["label"],
        "appointment_date": day.isoformat(),
        "appointment_time": slot,
        "label": "Demonstration Appointment – Not an Official OSCA Booking",
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
                f"Your Senior Citizen ID demonstration appointment for {payload['appointment_date']} "
                f"at {payload['appointment_time']} was saved. This is not an official OSCA booking."
            ),
            notification_type="appointment",
            read_status="unread",
            created_date=now,
        )
    )
    db.session.commit()
    return None
