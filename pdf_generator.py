from datetime import datetime

from fpdf import FPDF

# Characters the built-in latin-1 fonts cannot render, mapped to safe equivalents
# so they don't come out as "?" in the finished document.
_SUBSTITUTIONS = {
    "—": "-",   # em dash
    "–": "-",   # en dash
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    "₹": "INR ",  # rupee sign
    "•": "-",
}


def _safe(text) -> str:
    """fpdf2's built-in fonts only support latin-1; substitute or strip the rest."""
    if text is None:
        return ""
    text = str(text)
    for char, replacement in _SUBSTITUTIONS.items():
        text = text.replace(char, replacement)
    return text.encode("latin-1", "replace").decode("latin-1")


def _fmt_datetime(value) -> str:
    """Render an ISO timestamp as a human-readable date, leaving other text as-is."""
    if not value:
        return "Not specified"
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%d %b %Y, %H:%M")
    except (ValueError, TypeError):
        return str(value)


def _fmt_amount(value) -> str:
    """Render a money amount without a trailing .0 for whole numbers."""
    if value is None:
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"INR {number:,.0f}" if number.is_integer() else f"INR {number:,.2f}"


def build_pdf(incident: dict) -> bytes:
    report = incident.get("generated_report") or {}

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, _safe("Aiges — Cyber Incident Report"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _safe(f"Tracking code: {incident.get('tracking_code')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _safe(f"Generated: {_fmt_datetime(report.get('generated_at'))}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _safe(f"Report type: {report.get('report_type_label', 'Standard Report')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    def body_text(text: str):
        """Render a wrapped paragraph and return the cursor to the left margin.

        multi_cell() leaves x at the right edge by default, which makes any
        following width-0 multi_cell have no room to render.
        """
        pdf.multi_cell(0, 6, _safe(text), new_x="LMARGIN", new_y="NEXT")

    def section(title: str, body: str):
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, _safe(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        body_text(body)
        pdf.ln(2)

    section("Incident Type", incident.get("incident_type") or "Not specified")
    section("Location / Platform", incident.get("location") or "Not specified")
    section("Date of Incident", _fmt_datetime(incident.get("occurred_at")))
    section("Executive Summary", report.get("summary", ""))

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe("Timeline"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for item in report.get("timeline", []):
        body_text(f"- {item.get('label')}: {_fmt_datetime(item.get('detail'))}")
    pdf.ln(2)

    tech = report.get("technical_details", {})
    section(
        "Technical Details",
        f"Incident type: {tech.get('incident_type')}\n"
        f"Location/platform: {tech.get('location_or_platform')}\n"
        f"Evidence files attached: {tech.get('evidence_files_count', 0)}",
    )

    impact = report.get("impact_assessment", {})
    section(
        "Impact Assessment",
        f"Financial loss: {impact.get('financial_loss')}\n"
        f"Amount lost: {_fmt_amount(impact.get('amount_lost'))}\n"
        f"Platform contacted: {impact.get('platform_contacted')}\n"
        f"Platform response: {impact.get('platform_response')}",
    )

    section("Evidence", report.get("evidence_summary", ""))

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe("Recommendations"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for rec in report.get("recommendations", []):
        body_text(f"- {rec}")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe("Next Steps"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for step in report.get("next_steps", []):
        body_text(f"- {step}")

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        0,
        5,
        _safe(
            "This report was generated automatically by Aiges based on information provided by the user. "
            "It may be shared with relevant authorities."
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )

    return bytes(pdf.output())
