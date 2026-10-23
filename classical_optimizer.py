"""
QuantumGreen - Classical Energy Scheduling Optimizer
Formulates and solves a 24-hour constrained load-shifting and peak-shaving problem.
Optimizes operational time slots for each piece of equipment to minimize cost
under Time-of-Use tariffs while enforcing operational window and run-time constraints.
"""

from database import get_connection
import numpy as np

def run_classical_optimization(building_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM buildings WHERE id = ?", (building_id,))
    building = dict(cursor.fetchone())

    cursor.execute("""
    SELECT id, name, category, power_watts, operating_hours, priority, preferred_window
    FROM equipment
    WHERE building_id = ? AND is_active = 1
    """, (building_id,))
    equipment_list = [dict(r) for r in cursor.fetchall()]
    conn.close()

    base_tariff = building["base_tariff"]
    peak_tariff = building["peak_tariff"]
    peak_start = building["peak_start_hour"]
    peak_end = building["peak_end_hour"]
    emission_factor = building["emission_factor"]
    currency = building["currency"]

    # Hourly electricity price profile (24 hours)
    tariffs = []
    for h in range(24):
        if peak_start <= h <= peak_end:
            tariffs.append(peak_tariff)
        elif 0 <= h <= 5:
            # Off-peak night valley discount (10% rebate in many progressive tariffs)
            tariffs.append(round(base_tariff * 0.90, 2))
        else:
            tariffs.append(base_tariff)

    tariffs = np.array(tariffs)

    # 1. Construct Baseline Schedule
    # In unoptimized baseline:
    # Daytime/Flexible equipment runs primarily during convenient daytime/evening peak hours
    baseline_schedule = {}
    baseline_hourly_kw = np.zeros(24)

    for eq in equipment_list:
        eq_id = str(eq["id"])
        kw = eq["power_watts"] / 1000.0
        hrs_needed = int(round(eq["operating_hours"]))

        # Unoptimized default slots
        if eq["preferred_window"] == "Off-Peak":
            # Unmanaged: often runs in late afternoon / evening peak
            start_hr = 17
        elif eq["preferred_window"] == "Night":
            start_hr = 20
        elif eq["preferred_window"] == "Daytime":
            start_hr = 9
        else: # Flexible / Anytime
            start_hr = 14

        active_hours = []
        for i in range(hrs_needed):
            hr = (start_hr + i) % 24
            active_hours.append(hr)
            baseline_hourly_kw[hr] += kw

        baseline_schedule[eq_id] = {
            "name": eq["name"],
            "power_kw": kw,
            "category": eq["category"],
            "priority": eq["priority"],
            "hours": active_hours
        }

    # 2. Optimized Schedule via Constrained Greedy Load-Shifting Heuristic
    # Sort equipment: Critical first (fixed windows), then Medium, then Flexible (highest power first)
    priority_rank = {"Critical": 1, "Medium": 2, "Flexible": 3}
    sorted_equipment = sorted(
        equipment_list,
        key=lambda e: (priority_rank.get(e["priority"], 2), -e["power_watts"])
    )

    optimized_schedule = {}
    optimized_hourly_kw = np.zeros(24)
    # Background non-equipment building load (e.g., base infrastructure ~15 kW)
    base_infra_kw = 12.0
    optimized_hourly_kw += base_infra_kw
    baseline_hourly_kw += base_infra_kw

    for eq in sorted_equipment:
        eq_id = str(eq["id"])
        kw = eq["power_watts"] / 1000.0
        hrs_needed = int(round(eq["operating_hours"]))

        # Determine permissible time candidate hours
        if eq["priority"] == "Critical":
            # Must run within its required standard window
            if eq["preferred_window"] == "Daytime":
                candidate_pool = list(range(9, 19))
            elif eq["preferred_window"] == "Night":
                candidate_pool = list(range(20, 24)) + list(range(0, 6))
            else:
                candidate_pool = list(range(24))
        else:
            # Flexible or Medium:
            if eq["preferred_window"] == "Daytime":
                # Shift towards midday solar valley (10-15), avoid peak
                candidate_pool = [h for h in range(7, 18) if not (peak_start <= h <= peak_end)]
                if len(candidate_pool) < hrs_needed:
                    candidate_pool = list(range(6, 22))
            elif eq["preferred_window"] == "Off-Peak" or eq["priority"] == "Flexible":
                # Prefers midnight to early morning (00:00 - 06:00) or early afternoon (12:00 - 15:00)
                candidate_pool = [0, 1, 2, 3, 4, 5, 6, 12, 13, 14, 15, 23]
            elif eq["preferred_window"] == "Night":
                candidate_pool = [22, 23, 0, 1, 2, 3, 4, 5, 6]
            else:
                candidate_pool = [h for h in range(24) if not (peak_start <= h <= peak_end)]

        # Pick the optimal contiguous or distributed slots minimizing cost + peak spike
        # Evaluate each slot h in candidate_pool based on:
        # Score(h) = Tariff(h) + alpha * (current_hourly_kw[h] + kw)
        # alpha controls peak shaving penalty
        alpha = 0.15 # peak shaving weight
        slot_scores = []
        for h in candidate_pool:
            cost_term = tariffs[h] * kw
            peak_penalty = alpha * (optimized_hourly_kw[h] + kw)
            slot_scores.append((cost_term + peak_penalty, h))

        slot_scores.sort(key=lambda x: x[0])
        chosen_hours = [item[1] for item in slot_scores[:min(hrs_needed, len(slot_scores))]]
        # If needed hours exceed candidate pool, fill with cheapest remaining overall
        if len(chosen_hours) < hrs_needed:
            remaining_pool = [h for h in range(24) if h not in chosen_hours]
            remaining_pool.sort(key=lambda h: (tariffs[h], optimized_hourly_kw[h]))
            chosen_hours.extend(remaining_pool[:hrs_needed - len(chosen_hours)])

        chosen_hours.sort()

        for h in chosen_hours:
            optimized_hourly_kw[h] += kw

        optimized_schedule[eq_id] = {
            "name": eq["name"],
            "power_kw": kw,
            "category": eq["category"],
            "priority": eq["priority"],
            "hours": chosen_hours
        }

    # 3. Calculate Overall Financial & Carbon Metrics
    baseline_cost = float(np.sum(baseline_hourly_kw * tariffs))
    optimized_cost = float(np.sum(optimized_hourly_kw * tariffs))
    cost_saved = max(0.0, baseline_cost - optimized_cost)
    cost_reduction_percent = round((cost_saved / baseline_cost * 100), 1) if baseline_cost > 0 else 0

    baseline_total_kwh = float(np.sum(baseline_hourly_kw))
    optimized_total_kwh = float(np.sum(optimized_hourly_kw))

    # Marginal emission factor for peak peaker plants is higher (~0.95 kg/kWh) than base grid (0.75 kg/kWh)
    hourly_emission_factors = np.array([
        0.95 if (peak_start <= h <= peak_end) else 0.76
        for h in range(24)
    ])
    baseline_emissions = float(np.sum(baseline_hourly_kw * hourly_emission_factors))
    optimized_emissions = float(np.sum(optimized_hourly_kw * hourly_emission_factors))
    emissions_saved_kg = max(0.0, baseline_emissions - optimized_emissions)
    emissions_reduction_percent = round((emissions_saved_kg / baseline_emissions * 100), 1) if baseline_emissions > 0 else 0

    baseline_peak_kw = float(np.max(baseline_hourly_kw))
    optimized_peak_kw = float(np.max(optimized_hourly_kw))
    peak_shaved_kw = max(0.0, baseline_peak_kw - optimized_peak_kw)
    peak_shaved_percent = round((peak_shaved_kw / baseline_peak_kw * 100), 1) if baseline_peak_kw > 0 else 0

    # Format hourly comparison
    hourly_comparison = []
    for h in range(24):
        hourly_comparison.append({
            "hour": h,
            "label": f"{h:02d}:00",
            "baseline_kw": round(float(baseline_hourly_kw[h]), 2),
            "optimized_kw": round(float(optimized_hourly_kw[h]), 2),
            "tariff": float(tariffs[h]),
            "is_peak": bool(peak_start <= h <= peak_end)
        })

    # Equipment schedule comparison table
    equipment_schedules = []
    for eq in equipment_list:
        eq_id = str(eq["id"])
        base_hrs = baseline_schedule[eq_id]["hours"]
        opt_hrs = optimized_schedule[eq_id]["hours"]
        base_hrs_str = ", ".join([f"{h:02d}:00" for h in base_hrs])
        opt_hrs_str = ", ".join([f"{h:02d}:00" for h in opt_hrs])

        # Check if shifted
        is_shifted = (base_hrs != opt_hrs)

        equipment_schedules.append({
            "id": eq["id"],
            "name": eq["name"],
            "category": eq["category"],
            "power_watts": eq["power_watts"],
            "operating_hours": eq["operating_hours"],
            "priority": eq["priority"],
            "baseline_hours_display": base_hrs_str,
            "optimized_hours_display": opt_hrs_str,
            "baseline_hours": base_hrs,
            "optimized_hours": opt_hrs,
            "is_shifted": is_shifted
        })

    return {
        "status": "success",
        "algorithm": "Constrained Load-Shifting & Peak-Shaving Optimizer",
        "metrics": {
            "baseline_cost": round(baseline_cost, 2),
            "optimized_cost": round(optimized_cost, 2),
            "cost_saved": round(cost_saved, 2),
            "cost_reduction_percent": cost_reduction_percent,
            "monthly_cost_saved": round(cost_saved * 30, 2),
            "baseline_emissions_kg": round(baseline_emissions, 2),
            "optimized_emissions_kg": round(optimized_emissions, 2),
            "emissions_saved_kg": round(emissions_saved_kg, 2),
            "emissions_reduction_percent": emissions_reduction_percent,
            "monthly_emissions_saved_kg": round(emissions_saved_kg * 30, 2),
            "baseline_peak_kw": round(baseline_peak_kw, 2),
            "optimized_peak_kw": round(optimized_peak_kw, 2),
            "peak_shaved_kw": round(peak_shaved_kw, 2),
            "peak_shaved_percent": peak_shaved_percent,
            "total_kwh_daily": round(optimized_total_kwh, 2),
            "currency": currency
        },
        "hourly_comparison": hourly_comparison,
        "equipment_schedules": equipment_schedules
    }
