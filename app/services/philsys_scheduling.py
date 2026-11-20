"""Demonstration appointment slots for PhilSys registration assistance. Not an official PSA booking system."""

from datetime import date, datetime, timedelta

from app.models.notification import Notification
from app.services.application_service import read_details, write_details

def _location(code, label, city, region, address):
    return {
        "code": code,
        "label": label,
        "city": city,
        "region": region,
        "address": address,
    }


LOCATIONS = (
    _location("psa_manila", "J&T Building, Sta. Mesa", "Manila", "NCR - National Capital Region", "J&T Building, 3894 Ramon Magsaysay Boulevard, Sta. Mesa, Manila"),
    _location("psa_manila_lucky_chinatown", "Lucky Chinatown Mall, Binondo", "Manila", "NCR - National Capital Region", "Lucky Chinatown Mall, 3rd Floor, West Wing, Binondo, Manila"),
    _location("psa_quezon_city_jackman_plaza", "Jackman Plaza Muñoz", "Quezon City", "NCR - National Capital Region", "Jackman Plaza Muñoz, 3rd Floor, EDSA, Quezon City"),
    _location("psa_qc", "PSA Complex, East Avenue, Diliman", "Quezon City", "NCR - National Capital Region", "PSA Complex, East Avenue, Diliman, Quezon City"),
    _location("psa_quezon_city_robinsons_novaliches", "Robinsons Novaliches", "Quezon City", "NCR - National Capital Region", "Robinsons Novaliches, 2nd Floor, Quezon City"),
    _location("psa_marikina_bluewave", "BlueWave Mall", "Marikina", "NCR - National Capital Region", "BlueWave Mall, 2nd Floor, Marikina City"),
    _location("psa_mandaluyong_sm_megamall", "SM Megamall, Building A", "Mandaluyong", "NCR - National Capital Region", "SM Megamall, 5th Floor, Building A, Mandaluyong City"),
    _location("psa_mandaluyong_city_hall", "Mandaluyong City Hall", "Mandaluyong", "NCR - National Capital Region", "Mandaluyong City Hall, Mandaluyong City"),
    _location("psa_makati", "7464 Bagtikan Street, San Antonio", "Makati", "NCR - National Capital Region", "7464 Bagtikan Street, Barangay San Antonio, Makati City"),
    _location("psa_pasig_choice_market", "Choice Market, Ortigas Avenue Extension", "Pasig", "NCR - National Capital Region", "Choice Market, Ortigas Avenue Extension, Barangay Rosario, Pasig City"),
    _location("psa_taguig_city_hall", "Taguig City Hall, 2nd Floor Auditorium", "Taguig", "NCR - National Capital Region", "Taguig City Hall, 2nd Floor Auditorium, General Luna Street, Taguig City"),
    _location("psa_caloocan_grandz", "The Grandz Commercial Center", "Caloocan", "NCR - National Capital Region", "The Grandz Commercial Center, 4th Floor, MacArthur Highway, Caloocan City"),
    _location("psa_caloocan_sm_sangandaan", "SM Sangandaan", "Caloocan", "NCR - National Capital Region", "SM Sangandaan, 3rd Floor, Marcelo H. Del Pilar Street, Caloocan City"),
    _location("psa_valenzuela_one_mall", "One Mall, General T. De Leon", "Valenzuela", "NCR - National Capital Region", "One Mall, 2nd Floor, General T. De Leon, Valenzuela City"),
    _location("psa_pasay_mille", "Mille Building, Sen. Gil Puyat Avenue", "Pasay", "NCR - National Capital Region", "Mille Building, 3rd Floor, 335–337 Sen. Gil Puyat Avenue, Pasay City"),
    _location("psa_paranaque_ayala_manila_bay", "Ayala Malls Manila Bay", "Parañaque", "NCR - National Capital Region", "Ayala Malls Manila Bay, 5th Floor, Parañaque City"),
    _location("psa_las_pinas_city_hall", "Las Piñas City Hall", "Las Piñas", "NCR - National Capital Region", "Las Piñas City Hall, Las Piñas City"),
    _location("psa_muntinlupa_city_hall", "Muntinlupa City Hall", "Muntinlupa", "NCR - National Capital Region", "Muntinlupa City Hall, Muntinlupa City"),
    _location("psa_abra_bangued", "St. Arnold Janssen Communication Center Building", "Bangued", "CAR - Cordillera Administrative Region", "St. Arnold Janssen Communication Center Building, Bangued"),
    _location("psa_apayao_luna", "Precious Sarah Residence", "Luna, Apayao", "CAR - Cordillera Administrative Region", "Precious Sarah Residence, San Isidro Sur, Luna"),
    _location("psa_benguet_baguio_malipat", "Malipat Building, 106 Magsaysay Avenue", "Baguio City", "CAR - Cordillera Administrative Region", "Malipat Building, 106 Magsaysay Avenue, Baguio City"),
    _location("psa_benguet_baguio_ctll", "CTLL Building, 141 Abanao Extension Road", "Baguio City", "CAR - Cordillera Administrative Region", "CTLL Building, 141 Abanao Extension Road, Baguio City"),
    _location("psa_ifugao_lagawe", "New LMDC Building, J.P. Rizal Avenue", "Lagawe", "CAR - Cordillera Administrative Region", "New LMDC Building, J.P. Rizal Avenue, Lagawe"),
    _location("psa_kalinga_tabuk", "GLIMZ Building, Balinag Street, Bulanao", "Tabuk City", "CAR - Cordillera Administrative Region", "GLIMZ Building, Balinag Street, Bulanao, Tabuk City"),
    _location("psa_mountain_province_bontoc", "Bontoc Municipal Capitol", "Bontoc", "CAR - Cordillera Administrative Region", "Bontoc Municipal Capitol, Poblacion, Bontoc"),
    _location("psa_ilocos_norte_laoag", "Dap-Ayan Commercial Center, San Nicolas", "Laoag City", "Region I - Ilocos Region", "Dap-Ayan Commercial Center, San Nicolas, Laoag City"),
    _location("psa_ilocos_sur_vigan", "UNP Town Center, Quirino Boulevard", "Vigan City", "Region I - Ilocos Region", "UNP Town Center, Quirino Boulevard, Barangay Tamag, Vigan City"),
    _location("psa_la_union_san_fernando", "J&V Commercial Building, Sevilla", "San Fernando City", "Region I - Ilocos Region", "J&V Commercial Building, Purok 3, Sevilla, San Fernando City"),
    _location("psa_pangasinan_calasiao", "Manuel Lim Building Annex, De Venecia Highway", "Calasiao", "Region I - Ilocos Region", "Manuel Lim Building Annex, De Venecia Highway, Nalsian, Calasiao"),
    _location("psa_batanes_basco", "JPM Office Space Rental, National Road", "Basco", "Region II - Cagayan Valley", "JPM Office Space Rental, National Road, Ihubok I, Basco"),
    _location("psa_cagayan_tuguegarao", "Dallan na Pappabalo, Regional Government Center", "Tuguegarao City", "Region II - Cagayan Valley", "Dallan na Pappabalo, Regional Government Center, Carig Sur, Tuguegarao City"),
    _location("psa_isabela_ilagan", "LGU City of Ilagan Commercial Building", "Ilagan City", "Region II - Cagayan Valley", "LGU City of Ilagan Commercial Building, Gangan Avenue, San Vicente, Ilagan City"),
    _location("psa_nueva_vizcaya_bayombong", "BR Gajes Building, Maharlika Highway", "Bayombong", "Region II - Cagayan Valley", "BR Gajes Building, Maharlika Highway, District IV, Bayombong"),
    _location("psa_quirino_cabarroguis", "Aguas Building, San Marcos", "Cabarroguis", "Region II - Cagayan Valley", "Aguas Building, San Marcos, Cabarroguis"),
    _location("psa_aurora_baler", "JS Center, Barangay Pingit", "Baler", "Region III - Central Luzon", "JS Center, Barangay Pingit, Baler"),
    _location("psa_bataan_balanga", "The Bunker Building, Capitol Compound", "Balanga City", "Region III - Central Luzon", "The Bunker Building, Capitol Compound, Tenejero, Balanga City"),
    _location("psa_bulacan_plaridel", "SAVERS Building, Cagayan Valley Road", "Plaridel", "Region III - Central Luzon", "SAVERS Building, 9377 GP Cagayan Valley Road, Banga I, Plaridel"),
    _location("psa_nueva_ecija_cabanatuan", "Harrison Building, Barangay Dicarma", "Cabanatuan City", "Region III - Central Luzon", "Harrison Building, Barangay Dicarma, Cabanatuan City"),
    _location("psa_pampanga_san_fernando", "3 & 1 Building DAVSAN I, Sindalan", "San Fernando City", "Region III - Central Luzon", "3 & 1 Building DAVSAN I, MacArthur Highway, Sindalan, San Fernando City"),
    _location("psa_tarlac_city", "MM Tan Building, MacArthur Highway", "Tarlac City", "Region III - Central Luzon", "MM Tan Building, MacArthur Highway, Barangay Ligtasan, Tarlac City"),
    _location("psa_zambales_olongapo", "Livelihood Training Center, Upper Kalaklan", "Olongapo City", "Region III - Central Luzon", "Livelihood Training Center, Ohio Street, Upper Kalaklan, Olongapo City"),
    _location("psa_batangas_city", "Citimart Caedo Plaza", "Batangas City", "Region IV-A - CALABARZON", "Citimart Caedo Plaza, Barangay Calicanto, Batangas City"),
    _location("psa_batangas_lipa", "Fiesta Mall, Barangay Marawoy", "Lipa City", "Region IV-A - CALABARZON", "Fiesta Mall, Barangay Marawoy, Lipa City"),
    _location("psa_cavite_trece_martires", "Boochico Holding Inc. Building, Governor's Drive", "Trece Martires City", "Region IV-A - CALABARZON", "Boochico Holding Inc. Building, Governor's Drive, Barangay San Agustin, Trece Martires City"),
    _location("psa_laguna_san_pablo", "PRIMEA Building, San Roque", "San Pablo City", "Region IV-A - CALABARZON", "PRIMEA Building, Hilario Batralo Street, Barangay San Roque, San Pablo City"),
    _location("psa_quezon_lucena", "Pacific Mall, M.L. Tagarao Street", "Lucena City", "Region IV-A - CALABARZON", "Pacific Mall, 3rd Floor, M.L. Tagarao Street, Lucena City"),
    _location("psa_rizal_antipolo", "Budgetlane Shopping Center, San Jose", "Antipolo City", "Region IV-A - CALABARZON", "Budgetlane Shopping Center, Circumferential Road, Barangay San Jose, Antipolo City"),
    _location("psa_marinduque_boac", "JRT Building, Barangay Tampus", "Boac", "MIMAROPA", "JRT Building, Barangay Tampus, Boac"),
    _location("psa_occidental_mindoro_mamburao", "National Road, Barangay Payompon", "Mamburao", "MIMAROPA", "National Road, Barangay Payompon, Mamburao"),
    _location("psa_oriental_mindoro_calapan", "Nuciti Central, Barangay Camilmil", "Calapan City", "MIMAROPA", "Nuciti Central, Barangay Camilmil, Calapan City"),
    _location("psa_palawan_puerto_princesa", "Goldraz Properties, Malvar Street", "Puerto Princesa City", "MIMAROPA", "Goldraz Properties, Malvar Street, Barangay San Miguel, Puerto Princesa City"),
    _location("psa_romblon_odiongan", "Kadbayan MPC Commercial Complex, Dapawan", "Odiongan", "MIMAROPA", "Kadbayan MPC Commercial Complex, Barangay Dapawan, Odiongan"),
    _location("psa_romblon_romblon", "Navarrete Building, Barangay II-Poblacion", "Romblon", "MIMAROPA", "Navarrete Building, Barangay II-Poblacion, Romblon"),
    _location("psa_albay_legazpi_embarcadero", "Embarcadero, Port Area, Victory Village", "Legazpi City", "Region V - Bicol Region", "Embarcadero, Port Area, Victory Village, Legazpi City"),
    _location("psa_albay_legazpi_psa", "PSA Building, Regional Government Center", "Legazpi City", "Region V - Bicol Region", "PSA Building, Regional Government Center, Legazpi City"),
    _location("psa_camarines_norte_daet", "LJR Building, Barangay III", "Daet", "Region V - Bicol Region", "LJR Building, Barangay III, Daet"),
    _location("psa_camarines_sur_naga", "ALDP Plaza Mall, Roxas Avenue", "Naga City", "Region V - Bicol Region", "ALDP Plaza Mall, Roxas Avenue, Barangay Triangulo, Naga City"),
    _location("psa_catanduanes_virac", "Socito Building, Calatagan Proper", "Virac", "Region V - Bicol Region", "Socito Building, Calatagan Proper, Virac"),
    _location("psa_masbate_masbate_city", "Ten-7 Building, Mabini Street", "Masbate City", "Region V - Bicol Region", "Ten-7 Building, Mabini Street, Barangay Kalipay, Masbate City"),
    _location("psa_sorsogon_sorsogon_city", "Clemente Building, Jesalva Street, Talisay", "Sorsogon City", "Region V - Bicol Region", "Clemente Building, Jesalva Street, Talisay, Sorsogon City"),
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
    if appointment.get("service_kind") and appointment.get("service_kind") != "philsys":
        return None
    return appointment


def save_appointment(application, user, location_code, appointment_date, appointment_time):
    """Book one demonstration PhilSys registration slot. Stays draft until payment step is completed."""
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
        "service_kind": "philsys",
        "location_code": location["code"],
        "location_label": location["label"],
        "appointment_date": day.isoformat(),
        "appointment_time": slot,
        "label": "Demonstration Appointment – Not an Official PhilSys Registration Booking",
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
                f"Your PhilSys demonstration appointment for {payload['appointment_date']} "
                f"at {payload['appointment_time']} was saved. This is not an official PSA booking."
            ),
            notification_type="appointment",
            read_status="unread",
            created_date=now,
        )
    )
    db.session.commit()
    return None
