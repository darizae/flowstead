"""In-memory, bounded PDF Plant reports."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from io import BytesIO
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .infrastructure.persistence.records import ForecastRead, PlantRow, ReadingRow

MAX_REPORT_BYTES = 256_000
SYNTHETIC_SOURCE = "Synthetic source: Flowstead M1 dataset (fictional demonstration data)"


def _ascii(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value))
    without_marks = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return without_marks.encode("ascii", "replace").decode("ascii")


def _safe_text(value: object) -> str:
    return escape(_ascii(value))


def safe_report_filename(plant: PlantRow) -> str:
    """Return an ASCII-only attachment name with no path/control characters."""
    stem = _ascii(plant.name).lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-") or "plant"
    plant_id = re.sub(r"[^a-z0-9]+", "-", _ascii(plant.plant_id).lower()).strip("-") or "plant"
    return f"flowstead-{stem}-{plant_id}.pdf"


def _number(value: object) -> str:
    if value is None:
        return "No data"
    try:
        return f"{float(value):,.3f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return "No data"


def _date(value: datetime, timezone_name: str) -> str:
    return value.astimezone(ZoneInfo(timezone_name)).strftime("%Y-%m-%d")


def render_report(
    plant: PlantRow,
    reading: ReadingRow | None,
    forecast: ForecastRead | None,
    *,
    generated_at_utc: datetime | None = None,
    max_bytes: int = MAX_REPORT_BYTES,
) -> bytes:
    """Render one authorized Plant report without filesystem or database access."""
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    generated = generated_at_utc or datetime.now(UTC)
    if generated.tzinfo is None or generated.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    generated = generated.astimezone(UTC)
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#123b36"),
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    subtitle = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#49625e"),
        spaceAfter=14,
    )
    section = ParagraphStyle(
        "ReportSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#123b36"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#243a37"),
    )
    small = ParagraphStyle(
        "ReportSmall",
        parent=body,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#49625e"),
    )
    head = ParagraphStyle("ReportTableHead", parent=small, textColor=colors.white)
    right = ParagraphStyle("ReportRight", parent=body, alignment=TA_RIGHT)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Flowstead Plant report - {_ascii(plant.name)}",
        author="Flowstead",
        subject="Synthetic Plant report",
    )
    story: list[object] = []
    name = _safe_text(plant.name)
    story.append(Paragraph("Flowstead Plant report", title))
    story.append(
        Paragraph(
            f"{name}<br/>{_safe_text(plant.city)}, {_safe_text(plant.state_code)} | {_safe_text(plant.timezone)}",
            subtitle,
        )
    )
    identity = [
        [Paragraph("Plant ID", small), Paragraph(_safe_text(plant.plant_id), body)],
        [
            Paragraph("Generated (UTC)", small),
            Paragraph(generated.strftime("%Y-%m-%d %H:%M UTC"), body),
        ],
        [Paragraph("Plant-local date", small), Paragraph(_date(generated, plant.timezone), body)],
    ]
    table = Table(identity, colWidths=[1.35 * inch, 5.85 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f2ee")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfd8ce")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d6e6df")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([table, Spacer(1, 8), Paragraph("Latest readings", section)])
    channels = (
        ("Influent flow", "gal/h"),
        ("Rainfall", "in/h"),
        ("Dissolved oxygen", "mg/L"),
        ("Effluent pH", "unitless"),
    )
    rows = [
        [
            Paragraph("Measurement", head),
            Paragraph("Value", head),
            Paragraph("Quality", head),
            Paragraph("Units", head),
        ]
    ]
    values = reading.values if reading is not None else (None,) * 4
    qualities = reading.qualities if reading is not None else ("missing",) * 4
    for index, (label, units) in enumerate(channels):
        rows.append(
            [
                Paragraph(label, body),
                Paragraph(_number(values[index]), right),
                Paragraph(_safe_text(qualities[index]), body),
                Paragraph(units, body),
            ]
        )
    latest_table = Table(
        rows, colWidths=[2.35 * inch, 1.35 * inch, 1.25 * inch, 2.25 * inch], repeatRows=1
    )
    latest_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b36")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c8ddd4")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5faf7")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(latest_table)

    story.append(Paragraph("12-hour forecast", section))
    build = forecast.build if forecast is not None else None
    if build is None or not build.available or len(build.points) != 12:
        reason = _safe_text(
            build.unavailable_reason
            if build is not None and build.unavailable_reason
            else "unavailable"
        )
        story.append(Paragraph(f"Forecast unavailable: {reason}.", body))
    else:
        issued = (
            build.issued_at_utc.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
            if build.issued_at_utc
            else "Not issued"
        )
        story.append(
            Paragraph(f"Issued: {issued} | Model: {_safe_text(build.model_version)}", small)
        )
        forecast_rows = [
            [
                Paragraph("Target", head),
                Paragraph("Time (UTC)", head),
                Paragraph("Predicted flow", head),
                Paragraph("Units", head),
            ]
        ]
        for point in build.points:
            forecast_rows.append(
                [
                    Paragraph(str(point.hour_number), body),
                    Paragraph(
                        point.target_time_utc.astimezone(UTC).strftime("%Y-%m-%d %H:%M"), body
                    ),
                    Paragraph(_number(point.predicted_flow_gal_h), right),
                    Paragraph("gal/h", body),
                ]
            )
        forecast_table = Table(
            forecast_rows, colWidths=[0.7 * inch, 2.5 * inch, 2.0 * inch, 2.0 * inch], repeatRows=1
        )
        forecast_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b6f67")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c8ddd4")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f5faf7")],
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(forecast_table)
        if build.source_revision:
            story.append(Paragraph(f"Source revision: {_safe_text(build.source_revision)}", small))
    story.extend([Spacer(1, 12), Paragraph(SYNTHETIC_SOURCE, small)])
    doc.build(story)
    result = buffer.getvalue()
    if len(result) > max_bytes:
        raise ValueError(f"report exceeds {max_bytes} bytes")
    return result
