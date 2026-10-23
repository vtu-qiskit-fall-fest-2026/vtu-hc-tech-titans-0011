"""
QuantumGreen - Database Layer (SQLite)
Manages buildings, equipment profiles, hourly energy logs, and optimization results.
"""

import sqlite3
import os
import json
import math
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "quantumgreen.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Buildings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS buildings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        building_type TEXT NOT NULL,
        base_tariff REAL NOT NULL DEFAULT 8.0,
        peak_tariff REAL NOT NULL DEFAULT 12.0,
        peak_start_hour INTEGER NOT NULL DEFAULT 18,
        peak_end_hour INTEGER NOT NULL DEFAULT 22,
        emission_factor REAL NOT NULL DEFAULT 0.82,
        currency TEXT NOT NULL DEFAULT '₹',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Equipment table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        building_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        power_watts REAL NOT NULL,
        operating_hours REAL NOT NULL,
        priority TEXT NOT NULL, -- 'Critical', 'Medium', 'Flexible'
        preferred_window TEXT NOT NULL DEFAULT 'Flexible', -- 'Anytime', 'Off-Peak', 'Daytime', 'Night'
        is_active INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE
    )
    """)

    # Hourly energy consumption logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS energy_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        building_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        hour_of_day INTEGER NOT NULL,
        consumption_kwh REAL NOT NULL,
        temperature_c REAL DEFAULT 28.0,
        is_peak INTEGER DEFAULT 0,
        FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE
    )
    """)

    # Optimization history
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS optimization_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        building_id INTEGER NOT NULL,
        run_type TEXT NOT NULL, -- 'classical' or 'quantum'
        original_cost REAL NOT NULL,
        optimized_cost REAL NOT NULL,
        original_emissions REAL NOT NULL,
        optimized_emissions REAL NOT NULL,
        peak_demand_reduced_kw REAL NOT NULL,
        details_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

    # Seed data if empty
    seed_default_data_if_needed()

def seed_default_data_if_needed():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM buildings")
    count = cursor.fetchone()[0]

    if count == 0:
        print("[Database] Seeding realistic sample datasets for QuantumGreen...")

        # Preset 1: Greenwood College Academic Block
        cursor.execute("""
        INSERT INTO buildings (name, building_type, base_tariff, peak_tariff, peak_start_hour, peak_end_hour, emission_factor, currency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("Greenwood Engineering College", "College", 8.0, 13.5, 17, 22, 0.82, "₹"))
        college_id = cursor.lastrowid

        college_equipment = [
            ("Central Air Conditioning (Academic Block)", "HVAC", 45000, 8.0, "Medium", "Daytime"),
            ("Computer Labs (300 Workstations + Servers)", "Computing", 25000, 10.0, "Critical", "Daytime"),
            ("Campus Water Pumping & Borewell System", "Pumps", 15000, 4.0, "Flexible", "Off-Peak"),
            ("Corridor & Classroom LED Lighting", "Lighting", 12000, 12.0, "Critical", "Anytime"),
            ("Library Digital Archive & Climate Control", "HVAC", 8000, 14.0, "Medium", "Daytime"),
            ("Auditorium Projectors & Stage Sound Rig", "Entertainment", 6000, 3.0, "Flexible", "Daytime"),
            ("Heavy Workshop Lathes & CNC Machines", "Lab Equipment", 22000, 5.0, "Flexible", "Daytime"),
            ("Cafeteria Electric Dishwashers & Chillers", "Kitchen", 10000, 6.0, "Flexible", "Off-Peak")
        ]
        for eq in college_equipment:
            cursor.execute("""
            INSERT INTO equipment (building_id, name, category, power_watts, operating_hours, priority, preferred_window)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (college_id, eq[0], eq[1], eq[2], eq[3], eq[4], eq[5]))

        _generate_hourly_logs(cursor, college_id, base_load=45.0, peak_load=140.0)

        # Preset 2: TechHub Student Hostels
        cursor.execute("""
        INSERT INTO buildings (name, building_type, base_tariff, peak_tariff, peak_start_hour, peak_end_hour, emission_factor, currency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("TechHub Student Hostels & Mess", "Hostel", 7.5, 12.0, 18, 22, 0.82, "₹"))
        hostel_id = cursor.lastrowid

        hostel_equipment = [
            ("Central Water Geysers / Boilers (4 Blocks)", "Water Heating", 36000, 5.0, "Flexible", "Off-Peak"),
            ("Mess Dining Commercial Induction & Exhaust", "Kitchen", 28000, 7.0, "Critical", "Daytime"),
            ("Hostel Common Room Air Coolers & Fans", "Cooling", 15000, 10.0, "Medium", "Night"),
            ("Laundromat Heavy Washing Machines (12 units)", "Laundry", 18000, 6.0, "Flexible", "Off-Peak"),
            ("Corridor & Stairwell Perimeter Lighting", "Lighting", 9000, 11.0, "Critical", "Night"),
            ("Overhead Water Supply Lift Pumps", "Pumps", 12000, 4.0, "Flexible", "Off-Peak")
        ]
        for eq in hostel_equipment:
            cursor.execute("""
            INSERT INTO equipment (building_id, name, category, power_watts, operating_hours, priority, preferred_window)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (hostel_id, eq[0], eq[1], eq[2], eq[3], eq[4], eq[5]))

        _generate_hourly_logs(cursor, hostel_id, base_load=30.0, peak_load=95.0)

        # Preset 3: BioSci Advanced Research Laboratories
        cursor.execute("""
        INSERT INTO buildings (name, building_type, base_tariff, peak_tariff, peak_start_hour, peak_end_hour, emission_factor, currency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("BioSci Advanced Research Labs", "Laboratory", 9.0, 14.0, 17, 21, 0.82, "₹"))
        lab_id = cursor.lastrowid

        lab_equipment = [
            ("Ultra-Low Temperature Freezers (-80°C)", "Cryo", 16000, 24.0, "Critical", "Anytime"),
            ("Autoclaves & Steam Sterilizers", "Sterilization", 24000, 5.0, "Flexible", "Off-Peak"),
            ("Cleanroom Precision HVAC & HEPA Airflow", "HVAC", 42000, 24.0, "Critical", "Anytime"),
            ("High-Speed Floor Centrifuges", "Lab Equipment", 14000, 4.0, "Flexible", "Daytime"),
            ("Fume Hood Scrubbers & Exhaust Blowers", "Exhaust", 18000, 12.0, "Critical", "Daytime"),
            ("Spectrometry & Gene Sequencers", "Precision Instruments", 12000, 8.0, "Medium", "Daytime")
        ]
        for eq in lab_equipment:
            cursor.execute("""
            INSERT INTO equipment (building_id, name, category, power_watts, operating_hours, priority, preferred_window)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (lab_id, eq[0], eq[1], eq[2], eq[3], eq[4], eq[5]))

        _generate_hourly_logs(cursor, lab_id, base_load=65.0, peak_load=120.0)

        # Preset 4: Metro Central Public Office Complex
        cursor.execute("""
        INSERT INTO buildings (name, building_type, base_tariff, peak_tariff, peak_start_hour, peak_end_hour, emission_factor, currency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("Metro Central Public Office Complex", "Office", 8.5, 13.0, 18, 22, 0.78, "₹"))
        office_id = cursor.lastrowid

        office_equipment = [
            ("Central Variable Chiller Plant", "HVAC", 60000, 10.0, "Medium", "Daytime"),
            ("High-Rise Elevator Bank (4 Elevators)", "Elevators", 30000, 11.0, "Critical", "Daytime"),
            ("Data Center Server Cooling & UPS Systems", "IT Infrastructure", 35000, 24.0, "Critical", "Anytime"),
            ("Floor LED Panels & Task Lighting", "Lighting", 18000, 11.0, "Medium", "Daytime"),
            ("Basement Sump & Fire Reserve Pumps", "Pumps", 16000, 3.0, "Flexible", "Off-Peak"),
            ("Pantry Microwave & Water Dispensers", "Appliances", 12000, 8.0, "Flexible", "Daytime")
        ]
        for eq in office_equipment:
            cursor.execute("""
            INSERT INTO equipment (building_id, name, category, power_watts, operating_hours, priority, preferred_window)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (office_id, eq[0], eq[1], eq[2], eq[3], eq[4], eq[5]))

        _generate_hourly_logs(cursor, office_id, base_load=50.0, peak_load=165.0)

        conn.commit()

    conn.close()

def _generate_hourly_logs(cursor, building_id, base_load=40.0, peak_load=120.0, days=30):
    """
    Generates 30 days of realistic hourly consumption logs with peak curves,
    weekday/weekend variations, temperature effects, and realistic noise.
    """
    now = datetime.now()
    start_date = now - timedelta(days=days)

    records = []
    for day_offset in range(days):
        current_day = start_date + timedelta(days=day_offset)
        weekday = current_day.weekday() # 0-4 weekday, 5-6 weekend
        is_weekend = 1 if weekday >= 5 else 0
        day_factor = 0.55 if is_weekend else 1.0

        for hour in range(24):
            # Diurnal temperature cycle: coolest at 5am, warmest at 2pm
            temp_c = 24.0 + 8.0 * math.sin((hour - 8) * math.pi / 12) + (1.5 if is_weekend else 0.0)

            # Load curve pattern
            # Night (0-5): low base load
            # Morning ramp (6-9): rising
            # Daytime work (10-16): high active load + cooling
            # Evening peak (17-21): lighting + peak appliances
            # Night ramp down (22-23)
            if 0 <= hour <= 5:
                curve = 0.25 + 0.05 * math.sin(hour)
            elif 6 <= hour <= 9:
                curve = 0.35 + 0.45 * ((hour - 6) / 3.0)
            elif 10 <= hour <= 16:
                # Cooling adds more load with temp
                cooling_extra = max(0.0, (temp_c - 26.0) * 0.04)
                curve = 0.80 + 0.15 * math.sin((hour - 10) * math.pi / 6) + cooling_extra
            elif 17 <= hour <= 21:
                curve = 0.95 + 0.05 * math.cos(hour) # Peak time
            else:
                curve = 0.45 - 0.15 * ((hour - 22) / 2.0)

            consumption = base_load + (peak_load - base_load) * curve * day_factor
            # Add realistic random variation (+/- 6%)
            noise = (math.sin(day_offset * 7 + hour * 13) % 1.0 - 0.5) * 0.12 * consumption
            final_kwh = round(max(5.0, consumption + noise), 2)

            ts_str = (current_day.replace(hour=hour, minute=0, second=0)).strftime("%Y-%m-%d %H:%M:%S")
            is_peak = 1 if (17 <= hour <= 21) else 0

            records.append((building_id, ts_str, hour, final_kwh, round(temp_c, 1), is_peak))

    cursor.executemany("""
    INSERT INTO energy_logs (building_id, timestamp, hour_of_day, consumption_kwh, temperature_c, is_peak)
    VALUES (?, ?, ?, ?, ?, ?)
    """, records)

if __name__ == "__main__":
    init_db()
    print("Database initialization complete.")
