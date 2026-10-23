"""
QuantumGreen - Main Flask Application Server
REST API & Web UI Controller for Smart Energy Optimization & Quantum Lab
"""

import os
import io
import csv
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, Response
from database import init_db, get_connection
import energy_engine
import ml_engine
import classical_optimizer
import quantum_optimizer
import report_generator

app = Flask(__name__)
app.config["SECRET_KEY"] = "quantumgreen-climate-hackathon-2026"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024 # 16 MB max upload

# Initialize database on startup
init_db()

@app.route("/")
def index():
    return render_template("index.html")

# ----------------- BUILDING ROUTES ----------------- #
@app.route("/api/buildings", methods=["GET"])
def get_buildings():
    buildings = energy_engine.get_all_buildings()
    return jsonify({"status": "success", "buildings": buildings})

@app.route("/api/buildings", methods=["POST"])
def create_building():
    data = request.json or {}
    name = data.get("name", "").strip()
    b_type = data.get("building_type", "College").strip()
    base_tariff = float(data.get("base_tariff", 8.0))
    peak_tariff = float(data.get("peak_tariff", 12.0))
    peak_start = int(data.get("peak_start_hour", 18))
    peak_end = int(data.get("peak_end_hour", 22))
    emission_factor = float(data.get("emission_factor", 0.82))
    currency = data.get("currency", "₹").strip()

    if not name:
        return jsonify({"status": "error", "message": "Building name is required"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO buildings (name, building_type, base_tariff, peak_tariff, peak_start_hour, peak_end_hour, emission_factor, currency)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, b_type, base_tariff, peak_tariff, peak_start, peak_end, emission_factor, currency))
    new_id = cursor.lastrowid

    # Seed baseline logs for newly created building so user has immediate charts
    from database import _generate_hourly_logs
    _generate_hourly_logs(cursor, new_id, base_load=35.0, peak_load=90.0)

    # Seed 2 starter equipment items
    cursor.execute("""
    INSERT INTO equipment (building_id, name, category, power_watts, operating_hours, priority, preferred_window)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (new_id, "Central Air Conditioning System", "HVAC", 24000, 9.0, "Medium", "Daytime"))
    cursor.execute("""
    INSERT INTO equipment (building_id, name, category, power_watts, operating_hours, priority, preferred_window)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (new_id, "Campus Water Circulation Pump", "Pumps", 12000, 4.0, "Flexible", "Off-Peak"))

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "building_id": new_id, "message": f"Building '{name}' created successfully!"})

@app.route("/api/building/<int:building_id>", methods=["PUT"])
def update_building(building_id):
    data = request.json or {}
    name = data.get("name")
    b_type = data.get("building_type")
    base_tariff = data.get("base_tariff")
    peak_tariff = data.get("peak_tariff")
    peak_start = data.get("peak_start_hour")
    peak_end = data.get("peak_end_hour")
    emission_factor = data.get("emission_factor")
    currency = data.get("currency")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE buildings
    SET name = COALESCE(?, name),
        building_type = COALESCE(?, building_type),
        base_tariff = COALESCE(?, base_tariff),
        peak_tariff = COALESCE(?, peak_tariff),
        peak_start_hour = COALESCE(?, peak_start_hour),
        peak_end_hour = COALESCE(?, peak_end_hour),
        emission_factor = COALESCE(?, emission_factor),
        currency = COALESCE(?, currency)
    WHERE id = ?
    """, (name, b_type, base_tariff, peak_tariff, peak_start, peak_end, emission_factor, currency, building_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Building profile updated!"})

# ----------------- DASHBOARD & ENERGY SUMMARY ----------------- #
@app.route("/api/summary/<int:building_id>", methods=["GET"])
def get_summary(building_id):
    summary = energy_engine.get_dashboard_summary(building_id)
    if not summary:
        return jsonify({"status": "error", "message": "Building not found"}), 404

    chart_data = energy_engine.get_chart_data(building_id)
    recs = energy_engine.generate_smart_recommendations(building_id)

    return jsonify({
        "status": "success",
        "summary": summary,
        "charts": chart_data,
        "recommendations": recs[:3] # Top 3 for dashboard overview
    })

# ----------------- EQUIPMENT ROUTES ----------------- #
@app.route("/api/equipment/<int:building_id>", methods=["GET"])
def get_equipment(building_id):
    eq_list = energy_engine.get_equipment_list(building_id)
    return jsonify({"status": "success", "equipment": eq_list})

@app.route("/api/equipment", methods=["POST"])
def add_equipment():
    data = request.json or {}
    building_id = int(data.get("building_id", 1))
    name = data.get("name", "").strip()
    category = data.get("category", "General").strip()
    power_watts = float(data.get("power_watts", 1000))
    operating_hours = float(data.get("operating_hours", 4.0))
    priority = data.get("priority", "Medium").strip()
    preferred_window = data.get("preferred_window", "Flexible").strip()

    if not name:
        return jsonify({"status": "error", "message": "Equipment name is required"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO equipment (building_id, name, category, power_watts, operating_hours, priority, preferred_window)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (building_id, name, category, power_watts, operating_hours, priority, preferred_window))
    eq_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "equipment_id": eq_id, "message": f"Added '{name}' successfully!"})

@app.route("/api/equipment/<int:equipment_id>", methods=["DELETE"])
def delete_equipment(equipment_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Equipment removed"})

# ----------------- CSV UPLOAD & TEMPLATE ----------------- #
@app.route("/api/sample-csv", methods=["GET"])
def download_sample_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "hour_of_day", "consumption_kwh", "temperature_c", "is_peak"])
    now = datetime.now()
    for h in range(24):
        ts = (now.replace(hour=h, minute=0, second=0)).strftime("%Y-%m-%d %H:%M:%S")
        is_pk = 1 if (17 <= h <= 21) else 0
        temp = round(24.0 + 8.0 * ((h - 6) % 12) / 6.0, 1)
        kwh = round(40.0 + (50.0 if is_pk else 15.0), 2)
        writer.writerow([ts, h, kwh, temp, is_pk])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=quantumgreen_sample_energy_data.csv"}
    )

@app.route("/api/upload-csv/<int:building_id>", methods=["POST"])
def upload_csv(building_id):
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No file selected"}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)

        # Validate columns
        required_cols = {"timestamp", "hour_of_day", "consumption_kwh"}
        if not required_cols.issubset(set(csv_reader.fieldnames or [])):
            return jsonify({
                "status": "error",
                "message": f"Invalid CSV headers. Required: {', '.join(required_cols)}"
            }), 400

        records = []
        for row in csv_reader:
            ts = row.get("timestamp", "").strip()
            hr = int(row.get("hour_of_day", 0))
            kwh = float(row.get("consumption_kwh", 0.0))
            temp = float(row.get("temperature_c", 28.0))
            is_pk = int(row.get("is_peak", 1 if (17 <= hr <= 21) else 0))
            if kwh >= 0:
                records.append((building_id, ts, hr, kwh, temp, is_pk))

        if not records:
            return jsonify({"status": "error", "message": "No valid data rows found in CSV"}), 400

        conn = get_connection()
        cursor = conn.cursor()
        # Clear existing logs for this building
        cursor.execute("DELETE FROM energy_logs WHERE building_id = ?", (building_id,))
        cursor.executemany("""
        INSERT INTO energy_logs (building_id, timestamp, hour_of_day, consumption_kwh, temperature_c, is_peak)
        VALUES (?, ?, ?, ?, ?, ?)
        """, records)
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": f"Successfully parsed and ingested {len(records)} hourly energy logs!"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"CSV parse error: {str(e)}"}), 500

# ----------------- AI PREDICTION ----------------- #
@app.route("/api/predict/<int:building_id>", methods=["GET"])
def run_prediction(building_id):
    result = ml_engine.train_and_predict(building_id)
    return jsonify(result)

# ----------------- RECOMMENDATIONS ----------------- #
@app.route("/api/recommendations/<int:building_id>", methods=["GET"])
def get_recommendations(building_id):
    recs = energy_engine.generate_smart_recommendations(building_id)
    return jsonify({"status": "success", "recommendations": recs})

# ----------------- CLASSICAL OPTIMIZATION ----------------- #
@app.route("/api/optimize/<int:building_id>", methods=["GET"])
def run_classical_optimize(building_id):
    result = classical_optimizer.run_classical_optimization(building_id)
    return jsonify(result)

# ----------------- QUANTUM QAOA LAB ----------------- #
@app.route("/api/quantum-run", methods=["POST"])
def run_quantum():
    data = request.json or {}
    num_qubits = int(data.get("num_qubits", 4))
    qaoa_reps = int(data.get("qaoa_reps", 1))
    tariff_delta = float(data.get("tariff_delta", 5.0))

    result = quantum_optimizer.run_quantum_optimization(
        num_qubits=num_qubits,
        qaoa_reps=qaoa_reps,
        tariff_delta=tariff_delta
    )
    return jsonify(result)

# ----------------- REPORTS (CSV & PDF) ----------------- #
@app.route("/api/report/csv/<int:building_id>", methods=["GET"])
def download_csv_report(building_id):
    csv_content = report_generator.generate_csv_report(building_id)
    building = energy_engine.get_building_by_id(building_id)
    filename = f"QuantumGreen_Audit_{building['name'].replace(' ', '_')}.csv"
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route("/api/report/pdf/<int:building_id>", methods=["GET"])
def download_pdf_report(building_id):
    pdf_bytes = report_generator.generate_pdf_report(building_id)
    building = energy_engine.get_building_by_id(building_id)
    filename = f"QuantumGreen_Audit_{building['name'].replace(' ', '_')}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )

if __name__ == "__main__":
    print("QuantumGreen platform server starting on http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=False)
