"""Demonstration appointment slots for passport applications. Not a DFA booking system."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app import db
from app.models.notification import Notification
from app.models.passport_appointment import PassportAppointment
from app.services.application_service import read_details, write_details

DEMO_NOTICE = (
    "OneGov PH is an independent portfolio demonstration. This platform is not affiliated with or "
    "authorized by the Department of Foreign Affairs (DFA). All appointment schedules, payments, "
    "confirmations, and tracking records are simulated."
)

LOCATIONS = (
    {
        "code": "dfa_aseana",
        "region": "METRO MANILA (NCR)",
        "label": "DFA Aseana",
        "address": "Aseana Business Park, Bradco Avenue corner Macapagal Boulevard, Parañaque City, Metro Manila.",
        "latitude": 14.5325,
        "longitude": 120.9800,
    },
    {
        "code": "dfa_ncr_north_novaliches",
        "region": "METRO MANILA (NCR)",
        "label": "DFA NCR North – Robinsons Novaliches",
        "address": "3rd Floor, Lingkod Pinoy Center, Robinsons Novaliches, Quirino Highway, Brgy. Pasong Putik, Quezon City.",
        "latitude": 14.7210,
        "longitude": 121.0380,
    },
    {
        "code": "dfa_ncr_northeast_ali_mall",
        "region": "METRO MANILA (NCR)",
        "label": "DFA NCR Northeast – Ali Mall",
        "address": "Level 2, Government Center, Ali Mall, Araneta Center, Cubao, Quezon City.",
        "latitude": 14.6205,
        "longitude": 121.0610,
    },
    {
        "code": "dfa_ncr_east_megamall",
        "region": "METRO MANILA (NCR)",
        "label": "DFA NCR East – SM Megamall",
        "address": "7th Floor, Building C, SM Megamall, EDSA corner Julia Vargas Avenue, Mandaluyong City.",
        "latitude": 14.5850,
        "longitude": 121.0610,
    },
    {
        "code": "dfa_ncr_central_galleria",
        "region": "METRO MANILA (NCR)",
        "label": "DFA NCR Central – Robinsons Galleria",
        "address": "1st Floor, Lingkod Pinoy Center, Robinsons Galleria, EDSA corner Ortigas Avenue, Quezon City.",
        "latitude": 14.5840,
        "longitude": 121.0650,
    },
    {
        "code": "dfa_ncr_west_smcity_manila",
        "region": "METRO MANILA (NCR)",
        "label": "DFA NCR West – SM City Manila",
        "address": "5th Floor, SM City Manila, Natividad Almeda Lopez Street, Ermita, Manila.",
        "latitude": 14.5900,
        "longitude": 120.9800,
    },
    {
        "code": "dfa_ncr_south_festival_mall",
        "region": "METRO MANILA (NCR)",
        "label": "DFA NCR South – Festival Mall",
        "address": "3rd Level, West Wing, Festival Mall, Alabang, Muntinlupa City.",
        "latitude": 14.4230,
        "longitude": 121.0470,
    },
    {
        "code": "dfa_angeles_clark",
        "region": "CENTRAL LUZON",
        "label": "DFA Angeles – SM City Clark",
        "address": "Ground Floor, Tech Hub 2, SM City Clark, Malabanias, Angeles City, Pampanga.",
        "latitude": 15.1720,
        "longitude": 120.5600,
    },
    {
        "code": "dfa_pampanga_starmills",
        "region": "CENTRAL LUZON",
        "label": "DFA Pampanga – Robinsons Starmills",
        "address": "2nd Floor, Robinsons Starmills, City of San Fernando, Pampanga.",
        "latitude": 15.0300,
        "longitude": 120.6800,
    },
    {
        "code": "dfa_olongapo_central",
        "region": "CENTRAL LUZON",
        "label": "DFA Olongapo – SM City Olongapo Central",
        "address": "3rd Level, SM City Olongapo Central, Rizal Avenue East, Brgy. East Tapinac, Olongapo City.",
        "latitude": 14.8300,
        "longitude": 120.2900,
    },
    {
        "code": "dfa_paniqui_waltermart",
        "region": "CENTRAL LUZON",
        "label": "DFA Paniqui – WalterMart",
        "address": "WalterMart, MacArthur Highway, Brgy. Estacion, Paniqui, Tarlac.",
        "latitude": 15.6700,
        "longitude": 120.5500,
    },
    {
        "code": "dfa_malolos",
        "region": "CENTRAL LUZON",
        "label": "DFA Malolos",
        "address": "3rd Floor, Malolos City Central Transport Terminal, Brgy. Bulihan, Malolos City, Bulacan.",
        "latitude": 14.8400,
        "longitude": 120.8200,
    },
    {
        "code": "dfa_balanga",
        "region": "CENTRAL LUZON",
        "label": "DFA Balanga",
        "address": "The Bunker, Provincial Capitol Compound, Balanga City, Bataan.",
        "latitude": 14.6700,
        "longitude": 120.5400,
    },
    {
        "code": "dfa_baguio",
        "region": "NORTH LUZON",
        "label": "DFA Baguio",
        "address": "SM City Baguio, Upper Basement, Luneta Hill, Baguio City.",
        "latitude": 16.4020,
        "longitude": 120.6000,
    },
    {
        "code": "dfa_tuguegarao",
        "region": "NORTH LUZON",
        "label": "DFA Tuguegarao",
        "address": "City Hall Annex Building, Regional Government Center, Carig Sur, Tuguegarao City, Cagayan.",
        "latitude": 17.6100,
        "longitude": 121.7300,
    },
    {
        "code": "dfa_santiago",
        "region": "NORTH LUZON",
        "label": "DFA Santiago",
        "address": "3rd Floor, Robinsons Place Santiago, Maharlika Highway, Mabini, Santiago City, Isabela.",
        "latitude": 16.6900,
        "longitude": 122.1500,
    },
    {
        "code": "dfa_la_union",
        "region": "NORTH LUZON",
        "label": "DFA La Union",
        "address": "DFA Regional Consular Office, San Fernando City, La Union.",
        "latitude": 16.6200,
        "longitude": 120.3200,
    },
    {
        "code": "dfa_lipa",
        "region": "SOUTH LUZON",
        "label": "DFA Lipa",
        "address": "2nd Floor, Robinsons Place Lipa, J.P. Laurel Highway, Mataas na Lupa, Lipa City, Batangas.",
        "latitude": 13.9400,
        "longitude": 121.1600,
    },
    {
        "code": "dfa_san_pablo",
        "region": "SOUTH LUZON",
        "label": "DFA San Pablo",
        "address": "SM City San Pablo, San Pablo City, Laguna.",
        "latitude": 14.0700,
        "longitude": 121.3200,
    },
    {
        "code": "dfa_antipolo_sm_cherry",
        "region": "SOUTH LUZON",
        "label": "DFA Antipolo – SM Cherry",
        "address": "3rd Floor, SM Cherry, Marikina-Infanta Highway, Mayamot, Antipolo City, Rizal.",
        "latitude": 14.6200,
        "longitude": 121.1800,
    },
    {
        "code": "dfa_dasmarinas",
        "region": "SOUTH LUZON",
        "label": "DFA Dasmariñas",
        "address": "SM City Dasmariñas, Dasmariñas City, Cavite.",
        "latitude": 14.3300,
        "longitude": 120.9400,
    },
    {
        "code": "dfa_lucena",
        "region": "SOUTH LUZON",
        "label": "DFA Lucena",
        "address": "DFA Regional Consular Office, Lucena City, Quezon.",
        "latitude": 13.9300,
        "longitude": 121.6200,
    },
    {
        "code": "dfa_legazpi",
        "region": "SOUTH LUZON",
        "label": "DFA Legazpi",
        "address": "Pacific Mall-Legazpi, Legazpi City, Albay.",
        "latitude": 13.1400,
        "longitude": 123.4900,
    },
    {
        "code": "mm_consular_a",
        "label": "Metro Manila Consular Office A (Demonstration)",
        "address": "Demonstration site · Quezon City",
        "latitude": 14.6392,
        "longitude": 121.0437,
        "legacy": True,
    },
    {
        "code": "mm_consular_b",
        "label": "Metro Manila Consular Office B (Demonstration)",
        "address": "Demonstration site · Makati City",
        "latitude": 14.5547,
        "longitude": 121.0244,
        "legacy": True,
    },
)

TIME_SLOTS = ("08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00")
VISIBLE_MONTHS = 4  # current month plus the next 3 months

DEFAULT_DEMO_FEE = Decimal("1150.00")
DEMO_FEES = {
    "New": DEFAULT_DEMO_FEE,
    "Renewal": DEFAULT_DEMO_FEE,
}


def _now():
    return datetime.now().replace(microsecond=0)


def location_by_code(code):
    return next((item for item in LOCATIONS if item["code"] == code), None)


def demo_fee(application_type):
    cleaned = str(application_type or "").strip()
    return DEMO_FEES.get(cleaned, DEFAULT_DEMO_FEE)


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
    """Current month through the next 3 months. Past months are not bookable."""
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


def booked_slots(location_code=None):
    query = db.select(
        PassportAppointment.location_code,
        PassportAppointment.appointment_date,
        PassportAppointment.appointment_time,
    )
    if location_code:
        query = query.where(PassportAppointment.location_code == location_code)
    return {
        (row.location_code, row.appointment_date.isoformat(), row.appointment_time)
        for row in db.session.execute(query)
    }


def available_calendar(location_code, exclude_application_id=None):
    """Return weekday dates with open and taken slots for one demonstration location."""
    location = location_by_code(location_code)
    if location is None:
        return []
    taken = booked_slots(location_code)
    if exclude_application_id:
        own = db.session.scalar(
            db.select(PassportAppointment).where(
                PassportAppointment.application_id == exclude_application_id
            )
        )
        if own is not None:
            taken.discard((own.location_code, own.appointment_date.isoformat(), own.appointment_time))
    days = []
    for day in _weekdays():
        open_slots = []
        closed_slots = []
        for slot in TIME_SLOTS:
            key = (location_code, day.isoformat(), slot)
            if key in taken:
                closed_slots.append(slot)
            else:
                open_slots.append(slot)
        days.append(
            {
                "date": day.isoformat(),
                "label": day.strftime("%a, %d %b %Y"),
                "weekday": day.strftime("%a"),
                "day_number": day.day,
                "month_label": day.strftime("%b %Y"),
                "open_slots": open_slots,
                "closed_slots": closed_slots,
                "has_open": bool(open_slots),
            }
        )
    return days


def available_month_calendars(location_code, exclude_application_id=None):
    """Build current month plus the next 3 months. Past months are omitted."""
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
    row = db.session.scalar(
        db.select(PassportAppointment).where(
            PassportAppointment.application_id == application.application_id
        )
    )
    if row is not None:
        return {
            "location_code": row.location_code,
            "location_label": row.location_label,
            "appointment_date": row.appointment_date.isoformat(),
            "appointment_time": row.appointment_time,
            "label": "Demonstration Appointment – Not an Official DFA Appointment",
        }
    details = read_details(application)
    return details.get("appointment")


def save_appointment(application, user, location_code, appointment_date, appointment_time):
    """Book one demonstration slot. Stays draft until payment is completed."""
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
        "location_code": location["code"],
        "location_label": location["label"],
        "appointment_date": day.isoformat(),
        "appointment_time": slot,
        "label": "Demonstration Appointment – Not an Official DFA Appointment",
        "address": location["address"],
    }
    existing = db.session.scalar(
        db.select(PassportAppointment).where(
            PassportAppointment.application_id == application.application_id
        )
    )
    now = _now()
    if existing is None:
        existing = PassportAppointment(
            application_id=application.application_id,
            location_code=location["code"],
            location_label=location["label"],
            appointment_date=day,
            appointment_time=slot,
            created_at=now,
        )
        db.session.add(existing)
    else:
        existing.location_code = location["code"]
        existing.location_label = location["label"]
        existing.appointment_date = day
        existing.appointment_time = slot
        existing.created_at = now
    details = read_details(application)
    details["appointment"] = payload
    write_details(application, details, commit=False)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return "That demonstration slot was just taken. Choose another date or time."
    db.session.add(
        Notification(
            user_id=user.user_id,
            notification_title="Demonstration appointment saved",
            notification_message=(
                f"Your passport demonstration appointment for {payload['appointment_date']} "
                f"at {payload['appointment_time']} was saved. This is not an official DFA appointment."
            ),
            notification_type="appointment",
            read_status="unread",
            created_date=now,
        )
    )
    db.session.commit()
    return None
