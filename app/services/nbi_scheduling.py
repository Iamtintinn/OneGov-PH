"""Demonstration appointment slots for NBI clearance monitoring. Not an official NBI booking system."""

from datetime import date, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app import db
from app.models.nbi_appointment import NbiAppointment
from app.models.notification import Notification
from app.services.application_service import read_details, write_details

def _location(code, branch_name, region, province, city, address, latitude, longitude):
    return {
        "code": code,
        "department": "NBI",
        "branch_name": branch_name,
        "label": branch_name,
        "region": region,
        "province": province,
        "city": city,
        "address": address,
        "complete_address": address,
        "latitude": latitude,
        "longitude": longitude,
    }


LOCATIONS = (
    _location("nbi_clearance_center", "NBI Clearance Center", "NCR - National Capital Region", "Metro Manila", "Manila", "U.N. Avenue, Ermita, Manila", 14.5826, 120.9846),
    _location("nbi_quezon_city_hall", "Quezon City Hall", "NCR - National Capital Region", "Metro Manila", "Quezon City", "Makatarungan Street, Diliman, Quezon City", 14.6507, 121.0494),
    _location("nbi_montalban_rizal", "Montalban Rizal", "NCR - National Capital Region", "Rizal", "Rodriguez", "Ground Floor Municipal Hall, Rodriguez, Rizal", 14.7314, 121.1390),
    _location("nbi_muntinlupa_city", "Muntinlupa City", "NCR - National Capital Region", "Metro Manila", "Muntinlupa", "2nd Floor Starmall, Alabang, Muntinlupa City", 14.4170, 121.0415),
    _location("nbi_mandaluyong_city", "Mandaluyong City", "NCR - National Capital Region", "Metro Manila", "Mandaluyong", "Shaw Central Mall, Mandaluyong City", 14.5815, 121.0470),
    _location("nbi_las_pinas_city", "Las Pinas City", "NCR - National Capital Region", "Metro Manila", "Las Pinas", "SM Centrepoint, Las Pinas City", 14.4453, 120.9820),
    _location("nbi_robinsons_place_manila", "Robinsons Place Manila", "NCR - National Capital Region", "Metro Manila", "Manila", "Basement 1, Robinsons Place, Ermita, Manila", 14.5764, 120.9825),
    _location("nbi_robinsons_otis", "Robinsons Otis", "NCR - National Capital Region", "Metro Manila", "Manila", "Level 2, Guanzon Street, Paco, Manila", 14.5830, 120.9920),
    _location("nbi_robinsons_galleria", "Robinsons Galleria", "NCR - National Capital Region", "Metro Manila", "Quezon City", "Basement 1, Ortigas Avenue, Quezon City", 14.5895, 121.0575),
    _location("nbi_robinsons_metro_east", "Robinsons Metro East", "NCR - National Capital Region", "Metro Manila", "Pasig", "Level 4, Marcos Highway, Pasig", 14.6255, 121.0995),
    _location("nbi_robinsons_cainta", "Robinsons Cainta", "NCR - National Capital Region", "Rizal", "Cainta", "Level 2, Junction, Cainta, Rizal", 14.5760, 121.1220),
    _location("nbi_robinsons_novaliches", "Robinsons Novaliches", "NCR - National Capital Region", "Metro Manila", "Quezon City", "Quirino Highway corner Maligaya, Novaliches, Quezon City", 14.7210, 121.0380),
    _location("nbi_duty_free_fiesta_mall", "Duty Free Fiesta Mall", "NCR - National Capital Region", "Metro Manila", "Paranaque", "Ninoy Aquino Avenue, Paranaque City", 14.5060, 120.9900),
    _location("nbi_berma_centre", "Berma Centre", "NCR - National Capital Region", "Metro Manila", "Paranaque", "Redemptorist Road, Baclaran, Paranaque City", 14.5340, 120.9910),
    _location("nbi_lrt_north_mall", "LRT North Mall", "NCR - National Capital Region", "Metro Manila", "Caloocan", "Rizal Avenue Extension, Caloocan City", 14.6570, 120.9840),
    _location("nbi_marikina_riverbanks", "Marikina Riverbanks", "NCR - National Capital Region", "Metro Manila", "Marikina", "84 A. Bonifacio Avenue, Marikina City", 14.6290, 121.0830),
    _location("nbi_ali_mall_center", "Ali Mall Center", "NCR - National Capital Region", "Metro Manila", "Quezon City", "Ali Mall, Araneta Center, Cubao, Quezon City", 14.6190, 121.0520),
    _location("nbi_valenzuela_town_center", "Valenzuela Town Center", "NCR - National Capital Region", "Metro Manila", "Valenzuela", "Valenzuela Town Center, Valenzuela City", 14.7000, 120.9850),
    _location("nbi_marilao_municipal_hall", "Marilao Municipal Hall", "NCR - National Capital Region", "Bulacan", "Marilao", "Sandico Street, Poblacion 1, Marilao, Bulacan", 14.7580, 120.9480),
    _location("nbi_philpost_manila", "PhilPost Manila", "NCR - National Capital Region", "Metro Manila", "Manila", "Post Office Building, Liwasang Bonifacio, Manila", 14.5930, 120.9790),
    _location("nbi_poea_mandaluyong", "POEA Mandaluyong", "NCR - National Capital Region", "Metro Manila", "Mandaluyong", "Blas F. Ople Building, EDSA corner Ortigas Avenue Extension, Mandaluyong", 14.5830, 121.0590),
    _location("nbi_choice_market_ortigas", "Choice Market Ortigas", "NCR - National Capital Region", "Metro Manila", "Pasig", "Ortigas Avenue Extension, Rosario, Pasig City", 14.5870, 121.0850),
    _location("nbi_ncc_makati", "NCC Makati", "NCR - National Capital Region", "Metro Manila", "Makati", "23 EDSA corner General Apolinario, Bangkal, Makati", 14.5450, 121.0070),
    _location("nbi_baguio_city", "Baguio City", "CAR - Cordillera Administrative Region", "Benguet", "Baguio", "Upper Session Road, Baguio City", 16.4120, 120.5930),
    _location("nbi_one_stop_shop_baguio", "One Stop Shop Baguio", "CAR - Cordillera Administrative Region", "Benguet", "Baguio", "POEA-CAR, 3 Q.M. Subdivision, Baguio City", 16.4080, 120.5950),
    _location("nbi_san_fernando_la_union", "San Fernando La Union", "Region I - Ilocos Region", "La Union", "San Fernando", "Aguila Road, Sevilla Norte, San Fernando City, La Union", 16.6150, 120.3160),
    _location("nbi_agoo", "Agoo", "Region I - Ilocos Region", "La Union", "Agoo", "Municipal Hall, Barangay Sta. Barbara, Agoo, La Union", 16.3230, 120.3640),
    _location("nbi_tagudin", "Tagudin", "Region I - Ilocos Region", "Ilocos Sur", "Tagudin", "Del Pilar, Tagudin, Ilocos Sur", 16.9330, 120.4440),
    _location("nbi_one_stop_shop_san_fernando", "One Stop Shop San Fernando", "Region I - Ilocos Region", "La Union", "San Fernando", "Manna Mall, San Fernando City, La Union", 16.6150, 120.3150),
    _location("nbi_dagupan_city", "Dagupan City", "Region I - Ilocos Region", "Pangasinan", "Dagupan", "A.B. Fernandez West, Dagupan City, Pangasinan", 16.0430, 120.3340),
    _location("nbi_cb_mall_urdaneta", "CB Mall Urdaneta", "Region I - Ilocos Region", "Pangasinan", "Urdaneta", "McArthur Highway, Nancayasan, Urdaneta City, Pangasinan", 15.9780, 120.5700),
    _location("nbi_magic_mall_urdaneta", "Magic Mall Urdaneta", "Region I - Ilocos Region", "Pangasinan", "Urdaneta", "Alexander Street, Urdaneta City, Pangasinan", 15.9770, 120.5710),
    _location("nbi_laoag_city", "Laoag City", "Region I - Ilocos Region", "Ilocos Norte", "Laoag", "P. Gomez Street, Barangay 10, Laoag City", 18.1970, 120.5930),
    _location("nbi_vigan_city", "Vigan City", "Region I - Ilocos Region", "Ilocos Sur", "Bantay", "Govantes Dike, Bantay, Ilocos Sur", 17.5810, 120.3890),
    _location("nbi_tuguegarao_city", "Tuguegarao City", "Region II - Cagayan Valley", "Cagayan", "Tuguegarao", "Government Center, Carig Sur, Tuguegarao City, Cagayan", 17.6150, 121.7260),
    _location("nbi_bayombong", "Bayombong", "Region II - Cagayan Valley", "Nueva Vizcaya", "Bayombong", "Capitol Compound, Bayombong, Nueva Vizcaya", 16.4830, 121.1500),
    _location("nbi_ilagan_city", "Ilagan City", "Region II - Cagayan Valley", "Isabela", "Ilagan", "National Highway, Barangay Osmena, Ilagan, Isabela", 17.1480, 121.8890),
    _location("nbi_santiago_city", "Santiago City", "Region II - Cagayan Valley", "Isabela", "Santiago", "78 National Highway, Santiago City, Isabela", 16.6880, 121.5490),
    _location("nbi_san_fernando_pampanga", "San Fernando Pampanga", "Region III - Central Luzon", "Pampanga", "San Fernando", "Capitol Compound, City of San Fernando, Pampanga", 15.0330, 120.6850),
    _location("nbi_angeles_city", "Angeles City", "Region III - Central Luzon", "Pampanga", "Angeles", "Robinsons Place, MacArthur Highway, Balibago, Angeles City", 15.1650, 120.5890),
    _location("nbi_clark_one_stop_shop", "Clark One Stop Shop", "Region III - Central Luzon", "Pampanga", "Mabalacat", "Clark Freeport Zone, Pampanga", 15.1850, 120.5600),
    _location("nbi_malolos_city", "Malolos City", "Region III - Central Luzon", "Bulacan", "Malolos", "Provincial Capitol Compound, Guinhawa, Malolos City, Bulacan", 14.8430, 120.8110),
    _location("nbi_san_rafael", "San Rafael", "Region III - Central Luzon", "Bulacan", "San Rafael", "Municipal Hall, Maharlika Highway, Sampaloc, San Rafael, Bulacan", 14.9530, 120.9670),
    _location("nbi_san_jose_del_monte", "San Jose del Monte", "Region III - Central Luzon", "Bulacan", "San Jose del Monte", "Starmall, Barangay Poblacion, San Jose del Monte, Bulacan", 14.8130, 121.0450),
    _location("nbi_cabanatuan_city", "Cabanatuan City", "Region III - Central Luzon", "Nueva Ecija", "Cabanatuan", "Llanera Street, Old Provincial Capitol Compound, Cabanatuan City", 15.4860, 120.9670),
    _location("nbi_palayan_city", "Palayan City", "Region III - Central Luzon", "Nueva Ecija", "Palayan", "Palayan Business Hub, Barangay Singalat, Palayan City", 15.5410, 121.0850),
    _location("nbi_olongapo_city", "Olongapo City", "Region III - Central Luzon", "Zambales", "Olongapo", "17 Kentucky Lane, Upper Kalaklan, Olongapo City", 14.8290, 120.2820),
    _location("nbi_iba_zambales", "Iba Zambales", "Region III - Central Luzon", "Zambales", "Iba", "Livelihood Building, Zone 4, Iba, Zambales", 15.3270, 119.9780),
    _location("nbi_balanga_city", "Balanga City", "Region III - Central Luzon", "Bataan", "Balanga", "Provincial Capitol Compound, Balanga, Bataan", 14.6760, 120.5360),
    _location("nbi_tarlac_city", "Tarlac City", "Region III - Central Luzon", "Tarlac", "Tarlac", "Macabulos Drive, San Roque, Tarlac City", 15.4860, 120.5910),
    _location("nbi_metrotown_tarlac", "Metrotown Tarlac", "Region III - Central Luzon", "Tarlac", "Tarlac", "McArthur Highway corner Juan Luna Street, Tarlac City", 15.4860, 120.5900),
    _location("nbi_batangas_city", "Batangas City", "Region IV-A - CALABARZON", "Batangas", "Batangas City", "Capitol Site, Capitol Hills, Batangas City", 13.7570, 121.0580),
    _location("nbi_lipa_city_hall", "Lipa City Hall", "Region IV-A - CALABARZON", "Batangas", "Lipa", "New City Hall Compound, Marawoy, Lipa City", 13.9410, 121.1620),
    _location("nbi_balayan", "Balayan", "Region IV-A - CALABARZON", "Batangas", "Balayan", "Plaza Rizal, Balayan, Batangas", 13.9380, 120.7320),
    _location("nbi_sto_tomas_batangas", "Sto Tomas Batangas", "Region IV-A - CALABARZON", "Batangas", "Santo Tomas", "Unit 10, 2nd Floor, Sierra Makiling Building, Km 61 Maharlika Highway, Sto. Tomas, Batangas", 14.1080, 121.1410),
    _location("nbi_tagaytay_city", "Tagaytay City", "Region IV-A - CALABARZON", "Cavite", "Tagaytay", "J.P. Rizal Street, Kaybagal South, Tagaytay City", 14.1150, 120.9620),
    _location("nbi_robinsons_dasmarinas", "Robinsons Dasmarinas", "Region IV-A - CALABARZON", "Cavite", "Dasmarinas", "Robinsons Pala-Pala, Dasmarinas, Cavite", 14.2990, 120.9580),
    _location("nbi_bacoor_government_center", "Bacoor Government Center", "Region IV-A - CALABARZON", "Cavite", "Bacoor", "Bacoor Government Center, Molino Boulevard, Bacoor, Cavite", 14.4460, 120.9390),
    _location("nbi_anabu_imus_citymall", "Anabu Imus CityMall", "Region IV-A - CALABARZON", "Cavite", "Imus", "Emilio Aguinaldo Highway, Anabu, Imus, Cavite", 14.4080, 120.9400),
    _location("nbi_robinsons_general_trias", "Robinsons General Trias", "Region IV-A - CALABARZON", "Cavite", "General Trias", "Robinsons Place, General Trias City, Cavite", 14.3860, 120.8820),
    _location("nbi_sm_bacoor", "SM Bacoor", "Region IV-A - CALABARZON", "Cavite", "Bacoor", "3rd Floor, SM City Bacoor, General Tirona Highway, Barangay Habay 2, Bacoor", 14.4590, 120.9640),
    _location("nbi_lucena_city", "Lucena City", "Region IV-A - CALABARZON", "Quezon", "Lucena", "Grand Central Terminal, Barangay Ilayang Dupay, Lucena City", 13.9410, 121.6170),
    _location("nbi_santa_rosa_laguna", "Santa Rosa Laguna", "Region IV-A - CALABARZON", "Laguna", "Santa Rosa", "Rizal Boulevard, Barangay Tagapo, Santa Rosa, Laguna", 14.3120, 121.1110),
    _location("nbi_san_pablo_city", "San Pablo City", "Region IV-A - CALABARZON", "Laguna", "San Pablo", "4th Floor, San Pablo Shopping Mall, San Pablo City, Laguna", 14.0680, 121.3260),
    _location("nbi_pagsanjan", "Pagsanjan", "Region IV-A - CALABARZON", "Laguna", "Pagsanjan", "CLA Mall, Barangay Binan, Pagsanjan, Laguna", 14.2720, 121.4560),
    _location("nbi_lianas_calamba", "Lianas Calamba", "Region IV-A - CALABARZON", "Laguna", "Calamba", "Lianas Supermarket, Parian, Calamba City, Laguna", 14.2110, 121.1660),
    _location("nbi_one_stop_shop_calamba", "One Stop Shop Calamba", "Region IV-A - CALABARZON", "Laguna", "Calamba", "POEA Building, Ground Floor, Barangay Parian, Calamba City", 14.2110, 121.1660),
    _location("nbi_taytay_rizal", "Taytay Rizal", "Region IV-A - CALABARZON", "Rizal", "Taytay", "1st Floor, Old Municipal Building, Kadalagahan Street, Barangay San Isidro, Taytay, Rizal", 14.5580, 121.1320),
    _location("nbi_calapan_city", "Calapan City", "Region IV-B - MIMAROPA", "Oriental Mindoro", "Calapan", "Sitio Cuadro Aguas, Barangay Sta. Isabel, Calapan City", 13.4110, 121.1800),
    _location("nbi_puerto_princesa", "Puerto Princesa", "Region IV-B - MIMAROPA", "Palawan", "Puerto Princesa", "Taft Street, Barangay Liwanag, Puerto Princesa City", 9.7400, 118.7350),
    _location("nbi_legazpi_city", "Legazpi City", "Region V - Bicol Region", "Albay", "Legazpi", "Quezon Avenue, Legazpi City, Albay", 13.1390, 123.7430),
    _location("nbi_masbate_city", "Masbate City", "Region V - Bicol Region", "Masbate", "Masbate", "Masbate City Hall, Masbate City", 12.3680, 123.6220),
    _location("nbi_one_stop_shop_legazpi", "One Stop Shop Legazpi", "Region V - Bicol Region", "Albay", "Legazpi", "PhilHealth Albay Office, 2nd Floor, Delos Santos Building, Business Landco Park, Legazpi City", 13.1450, 123.7510),
    _location("nbi_naga_city", "Naga City", "Region V - Bicol Region", "Camarines Sur", "Naga", "Maria Cristina Street, Naga City, Camarines Sur", 13.6200, 123.1940),
    _location("nbi_daet", "Daet", "Region V - Bicol Region", "Camarines Norte", "Daet", "J. Lucban Street, Provincial Capitol, Daet, Camarines Norte", 14.1120, 122.9550),
    dict(_location("nbi_unquezon", "NBI Clearance Center", "NCR - National Capital Region", "Metro Manila", "Manila", "U.N. Avenue, Ermita, Manila", 14.5826, 120.9846), legacy=True),
    dict(_location("nbi_qc", "Quezon City Hall", "NCR - National Capital Region", "Metro Manila", "Quezon City", "Makatarungan Street, Diliman, Quezon City", 14.6507, 121.0494), legacy=True),
    dict(_location("nbi_makati", "NCC Makati", "NCR - National Capital Region", "Metro Manila", "Makati", "23 EDSA corner General Apolinario, Bangkal, Makati", 14.5450, 121.0070), legacy=True),
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


def booked_slots(location_code=None):
    query = db.select(
        NbiAppointment.location_code,
        NbiAppointment.appointment_date,
        NbiAppointment.appointment_time,
    )
    if location_code:
        query = query.where(NbiAppointment.location_code == location_code)
    return {
        (row.location_code, row.appointment_date.isoformat(), row.appointment_time)
        for row in db.session.execute(query)
    }


def available_calendar(location_code, exclude_application_id=None):
    location = location_by_code(location_code)
    if location is None:
        return []
    taken = booked_slots(location_code)
    if exclude_application_id:
        own = db.session.scalar(
            db.select(NbiAppointment).where(NbiAppointment.application_id == exclude_application_id)
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
        db.select(NbiAppointment).where(NbiAppointment.application_id == application.application_id)
    )
    if row is not None:
        return {
            "location_code": row.location_code,
            "location_label": row.location_label,
            "appointment_date": row.appointment_date.isoformat(),
            "appointment_time": row.appointment_time,
            "label": "Demonstration Appointment – Not an Official NBI Appointment",
        }
    details = read_details(application)
    return details.get("appointment")


def save_appointment(application, user, location_code, appointment_date, appointment_time):
    """Book one demonstration NBI slot. Stays draft until payment is completed."""
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
        "label": "Demonstration Appointment – Not an Official NBI Appointment",
        "address": location["address"],
    }
    existing = db.session.scalar(
        db.select(NbiAppointment).where(NbiAppointment.application_id == application.application_id)
    )
    now = _now()
    if existing is None:
        existing = NbiAppointment(
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
                f"Your NBI demonstration appointment for {payload['appointment_date']} "
                f"at {payload['appointment_time']} was saved. This is not an official NBI appointment."
            ),
            notification_type="appointment",
            read_status="unread",
            created_date=now,
        )
    )
    db.session.commit()
    return None
