"""
QuantumGreen - Report Generator
Generates downloadable executive CSV and PDF reports containing
energy audits, baseline vs optimized metrics, and equipment schedules.
"""

import io
import csv
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from database import get_connection
import classical_optimizer
import energy_engine

def generate_csv_report(building_id):
    """
    Produces a comprehensive CSV string detailing facility energy analysis,
    equipment schedules, and 24-hour load optimization profiles.
    """
    building = energy_engine.get_building_by_id(building_id)
    summary = energy_engine.get_dashboard_summary(building_id)
    opt_res = classical_optimizer.run_classical_optimization(building_id)

    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Facility Header
    writer.writerow(["QUANTUMGREEN ENERGY AUDIT & OPTIMIZATION REPORT"])
    writer.writerow(["Facility Name", building["name"]])
    writer.writerow(["Facility Type", building["building_type"]])
    writer.writerow(["Date Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow(["Grid Emission Factor (kg CO2e/kWh)", building["emission_factor"]])
    writer.writerow(["Base Tariff", f"{building['currency']} {building['base_tariff']}/kWh"])
    writer.writerow(["Peak Tariff", f"{building['currency']} {building['peak_tariff']}/kWh"])
    writer.writerow([])

    # 2. Executive KPI Summary
    m = opt_res["metrics"]
    writer.writerow(["EXECUTIVE SAVINGS & ENVIRONMENTAL METRICS"])
    writer.writerow(["Metric", "Baseline (Unmanaged)", "Optimized (QuantumGreen)", "Net Savings / Impact", "Unit"])
    writer.writerow(["Daily Electricity Cost", m["baseline_cost"], m["optimized_cost"], f"-{m['cost_saved']} (-{m['cost_reduction_percent']}%)", building["currency"]])
    writer.writerow(["Estimated Monthly Cost", round(m["baseline_cost"] * 30, 2), round(m["optimized_cost"] * 30, 2), f"-{m['monthly_cost_saved']}", building["currency"]])
    writer.writerow(["Daily Carbon Emissions", m["baseline_emissions_kg"], m["optimized_emissions_kg"], f"-{m['emissions_saved_kg']} (-{m['emissions_reduction_percent']}%)", "kg CO2e"])
    writer.writerow(["Estimated Monthly Emissions", round(m["baseline_emissions_kg"] * 30, 2), round(m["optimized_emissions_kg"] * 30, 2), f"-{m['monthly_emissions_saved_kg']}", "kg CO2e"])
    writer.writerow(["Peak Grid Demand", m["baseline_peak_kw"], m["optimized_peak_kw"], f"-{m['peak_shaved_kw']} (-{m['peak_shaved_percent']}%)", "kW"])
    writer.writerow(["Equivalent Trees Offset", "-", "-", round(m['monthly_emissions_saved_kg'] * 12 / 21.77, 1), "Trees/year"])
    writer.writerow([])

    # 3. Equipment Operational Schedule
    writer.writerow(["EQUIPMENT OPERATIONAL SCHEDULE OPTIMIZATION"])
    writer.writerow(["Equipment Name", "Category", "Power (W)", "Run Hours", "Priority", "Baseline Schedule", "Recommended Schedule", "Shifted?"])
    for eq in opt_res["equipment_schedules"]:
        writer.writerow([
            eq["name"],
            eq["category"],
            eq["power_watts"],
            eq["operating_hours"],
            eq["priority"],
            eq["baseline_hours_display"],
            eq["optimized_hours_display"],
            "YES" if eq["is_shifted"] else "NO"
        ])
    writer.writerow([])

    # 4. Hourly 24-Hour Load Curve
    writer.writerow(["24-HOUR HOURLY LOAD DISTRIBUTION & TARIFF"])
    writer.writerow(["Hour", "Time Window", "Tariff Rate", "Is Peak Window", "Baseline Load (kW)", "Optimized Load (kW)", "Delta (kW)"])
    for h in opt_res["hourly_comparison"]:
        delta = round(h["optimized_kw"] - h["baseline_kw"], 2)
        writer.writerow([
            h["hour"],
            h["label"],
            h["tariff"],
            "YES" if h["is_peak"] else "NO",
            h["baseline_kw"],
            h["optimized_kw"],
            f"{delta:+}"
        ])

    return output.getvalue()

def generate_pdf_report(building_id):
    """
    Generates a professionally styled PDF document using ReportLab.
    """
    building = energy_engine.get_building_by_id(building_id)
    summary = energy_engine.get_dashboard_summary(building_id)
    opt_res = classical_optimizer.run_classical_optimization(building_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    # Custom styles
    primary_color = colors.HexColor("#0B2545") # Dark blue
    accent_green = colors.HexColor("#10B981") # Emerald green
    text_dark = colors.HexColor("#1F2937")
    bg_light = colors.HexColor("#F3F4F6")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=primary_color
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#4B5563")
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceAfter=6,
        spaceBefore=12
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=text_dark
    )
    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#065F46")
    )

    story = []

    # Title & Header
    story.append(Paragraph("QUANTUMGREEN - ENERGY AUDIT & OPTIMIZATION REPORT", title_style))
    story.append(Paragraph(
        f"Facility: <b>{building['name']}</b> ({building['building_type']}) | "
        f"Generated: {datetime.now().strftime('%B %d, %Y - %H:%M')}",
        subtitle_style
    ))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2, color=accent_green, spaceAfter=14))

    # Executive Summary Card
    m = opt_res["metrics"]
    curr = building["currency"]
    summary_data = [
        [
            Paragraph("<b>Total Monthly Cost Savings:</b>", body_style),
            Paragraph(f"<font color='#059669'><b>{curr} {m['monthly_cost_saved']:,.2f}</b> ({m['cost_reduction_percent']}%)</font>", body_style),
            Paragraph("<b>Peak Demand Shaved:</b>", body_style),
            Paragraph(f"<b>{m['peak_shaved_kw']} kW</b> ({m['peak_shaved_percent']}%)", body_style)
        ],
        [
            Paragraph("<b>Monthly Carbon Reduction:</b>", body_style),
            Paragraph(f"<font color='#059669'><b>{m['monthly_emissions_saved_kg']} kg CO₂e</b></font>", body_style),
            Paragraph("<b>Annual Tree Offset Equiv:</b>", body_style),
            Paragraph(f"<b>{round(m['monthly_emissions_saved_kg'] * 12 / 21.77, 1)} mature trees</b>", body_style)
        ]
    ]
    summary_table = Table(summary_data, colWidths=[140, 120, 140, 130])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ECFDF5")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#A7F3D0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1FAE5")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # Key Performance Indicators Table
    story.append(Paragraph("1. Performance Metrics Comparison", section_heading))
    kpi_data = [
        ["Metric Dimension", "Baseline", "Optimized", "Impact Delta", "Status"],
        ["Daily Energy Cost", f"{curr} {m['baseline_cost']:.2f}", f"{curr} {m['optimized_cost']:.2f}", f"-{curr} {m['cost_saved']:.2f}", f"-{m['cost_reduction_percent']}%"],
        ["Monthly Projected Cost", f"{curr} {m['baseline_cost']*30:.2f}", f"{curr} {m['optimized_cost']*30:.2f}", f"-{curr} {m['monthly_cost_saved']:.2f}", "Optimized"],
        ["Daily Carbon Emissions", f"{m['baseline_emissions_kg']} kg", f"{m['optimized_emissions_kg']} kg", f"-{m['emissions_saved_kg']} kg", f"-{m['emissions_reduction_percent']}%"],
        ["Monthly Projected CO2e", f"{m['baseline_emissions_kg']*30:.1f} kg", f"{m['optimized_emissions_kg']*30:.1f} kg", f"-{m['monthly_emissions_saved_kg']} kg", "Decarbonized"],
        ["Peak Grid Demand", f"{m['baseline_peak_kw']} kW", f"{m['optimized_peak_kw']} kW", f"-{m['peak_shaved_kw']} kW", f"-{m['peak_shaved_percent']}%"]
    ]
    kpi_table = Table(kpi_data, colWidths=[150, 95, 95, 100, 90])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # Equipment Schedule Table
    story.append(Paragraph("2. Optimized Equipment Schedule (Time-of-Use Shift)", section_heading))
    eq_data = [["Equipment", "Watts", "Priority", "Original Hours", "Optimized Hours", "Action"]]
    for eq in opt_res["equipment_schedules"][:7]: # Top 7 equipment
        action_tag = "SHIFTED" if eq["is_shifted"] else "FIXED"
        eq_data.append([
            Paragraph(f"<b>{eq['name'][:24]}</b>", body_style),
            f"{eq['power_watts']:,} W",
            eq["priority"],
            Paragraph(eq["baseline_hours_display"], body_style),
            Paragraph(eq["optimized_hours_display"], body_style),
            action_tag
        ])
    eq_table = Table(eq_data, colWidths=[130, 60, 55, 120, 120, 45])
    eq_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))
    story.append(eq_table)
    story.append(Spacer(1, 14))

    # Methodology & Environmental Statement
    story.append(Paragraph("3. Optimization Methodology & Climate Significance", section_heading))
    methodology_text = (
        "<b>Algorithmic Formulation:</b> This optimization leverages Time-of-Use tariff arbitrage coupled with "
        "quadratic peak-demand penalties. Deferrable high-load appliances are intelligently mapped outside regional "
        f"peak stress hours ({building['peak_start_hour']}:00 - {building['peak_end_hour']}:00), eliminating reliance "
        "on high-carbon peaker plants. QuantumGreen additionally provides an experimental Qiskit QAOA Hamiltonian formulation "
        "to showcase how future fault-tolerant quantum processors will solve large-scale microgrid combinatorial dispatch.<br/><br/>"
        f"<b>Carbon Accounting:</b> Calculations apply a local grid emissions factor of <b>{building['emission_factor']} kg CO₂e/kWh</b>. "
        "Real-world decarbonization depends on the regional dispatch stack, generation mix, and transmission efficiency."
    )
    story.append(Paragraph(methodology_text, body_style))
    story.append(Spacer(1, 12))

    # Footer note
    footer_text = (
        "<i>QuantumGreen Hackathon Platform — AI-Powered Smart Energy Optimization for a Sustainable Future. "
        "Official submission for Quantum Applications for Climate Change & Sustainability.</i>"
    )
    story.append(Paragraph(footer_text, ParagraphStyle("Footer", parent=body_style, fontSize=7, textColor=colors.HexColor("#9CA3AF"))))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
