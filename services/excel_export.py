from __future__ import annotations

import re
from io import BytesIO
from typing import Any

import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from services.ai_prompts import DISCLAIMER


INTERNAL_RA_COLUMNS = {
    "Source Step ID",
    "Source Step Original",
    "Source Step Translated",
    "Hazard ID",
    "Hazard Category",
}


def matrix_rows(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    if not matrix:
        return []
    bands = matrix.get("risk_bands", [])
    rows = []
    for likelihood in matrix.get("likelihood_scale", []):
        for severity in matrix.get("severity_scale", []):
            score = int(likelihood["score"]) * int(severity["score"])
            band = next((b for b in bands if int(b["min"]) <= score <= int(b["max"])), {})
            rows.append(
                {
                    "Likelihood": f"{likelihood['code']} {likelihood['label_en']}",
                    "Severity": f"{severity['code']} {severity['label_en']}",
                    "Score": score,
                    "Risk Level": band.get("level", ""),
                    "Action": band.get("action", ""),
                }
            )
    return rows


_HEADER_FILL = PatternFill("solid", fgColor="1F4D78")
_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
_BAND_FILL = PatternFill("solid", fgColor="F2F6FA")
_THIN = Side(style="thin", color="9AA7B4")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_RISK_FILLS = {
    "LR": PatternFill("solid", fgColor="C6EFCE"),
    "MR": PatternFill("solid", fgColor="FFEB9C"),
    "HR": PatternFill("solid", fgColor="FFC7CE"),
}
_ALERT_FONT = Font(bold=True, color="C00000")

# Column widths tuned per sheet; anything unlisted gets a sensible default.
_SHEET_WIDTHS = {
    "Cover": [26, 90],
    "MS Steps": [8, 110],
    "MS Extract": [24, 110],
    "Signatures": [30, 24, 24, 18],
    "PPE": [8, 40, 55],
    "Risk Matrix": [24, 24, 10, 12, 60],
}


def _risk_level_in(value: str) -> str:
    match = re.search(r"\b(LR|MR|HR)\b", str(value or ""))
    return match.group(1) if match else ""


def _style_workbook(book) -> None:
    """Format every sheet as a proper bordered, colour-coded table.

    Raw pandas dumps have no gridlines or fills, which reads as unfinished in
    a contractor deliverable. Header row gets the report blue, all cells get
    thin borders and wrapping, and risk-rating cells are colour-banded
    (green LR / amber MR / red HR) with residual MR/HR flagged in bold red.
    """
    for sheet in book.worksheets:
        if sheet.max_row < 1:
            continue
        headers = [str(cell.value or "") for cell in sheet[1]]
        risk_columns = {
            idx
            for idx, header in enumerate(headers, start=1)
            if any(token in header for token in ("Risk Level", "Initial Risk", "Residual Risk", "Score"))
        }
        residual_columns = {idx for idx, header in enumerate(headers, start=1) if "Residual" in header}
        for cell in sheet[1]:
            cell.fill = _HEADER_FILL
            cell.font = _HEADER_FONT
            cell.border = _BORDER
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                cell.border = _BORDER
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                if cell.row % 2 == 0:
                    cell.fill = _BAND_FILL
                if cell.column in risk_columns:
                    level = _risk_level_in(cell.value)
                    if level:
                        cell.fill = _RISK_FILLS[level]
                        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    if cell.column in residual_columns and level in {"MR", "HR"}:
                        cell.font = _ALERT_FONT
        widths = _SHEET_WIDTHS.get(sheet.title)
        for idx in range(1, sheet.max_column + 1):
            if widths and idx <= len(widths):
                width = widths[idx - 1]
            else:
                width = 28 if sheet.title == "RA Table" else 22
            sheet.column_dimensions[get_column_letter(idx)].width = width
        if sheet.title == "RA Table":
            # Narrow columns where long text is not expected.
            for idx, header in enumerate(headers, start=1):
                if header in {"Item", "P", "IC"}:
                    sheet.column_dimensions[get_column_letter(idx)].width = 8
                elif "Risk" in header:
                    sheet.column_dimensions[get_column_letter(idx)].width = 16
            sheet.freeze_panes = "C2"
        else:
            sheet.freeze_panes = "A2"


def build_ra_excel(report: dict[str, Any], ra_rows: list[dict[str, Any]], matrix: dict[str, Any] | None = None) -> BytesIO:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        cover_rows = [
            ["Report Title", report.get("title", "Risk Assessment Report")],
            ["Report Title", report.get("Project", "-")],
            ["Construction Activity", report.get("Construction Activity", "-")],
            ["Project Name", report.get("Task Location", "-")],
            ["Matrix Version", report.get("Assessment Standard", "-")],
            ["Jurisdiction Profile", report.get("Jurisdiction Profile", "-")],
            ["Risk Matrix", report.get("Risk Matrix", "-")],
            ["Report Language", report.get("Report Language", "-")],
            ["Assessment Date", report.get("Assessment Date", "-")],
            ["Version", report.get("Version", "-")],
            ["Next Review Date", report.get("Next Review Date", "-")],
        ]
        pd.DataFrame(cover_rows, columns=["Field", "Value"]).to_excel(writer, sheet_name="Cover", index=False)

        ms_text = str(report.get("Method Statement Extract", "") or "")
        confirmed_steps = report.get("Confirmed Steps", []) or []
        if ms_text or confirmed_steps:
            pd.DataFrame(
                [[idx + 1, step] for idx, step in enumerate(confirmed_steps)],
                columns=["Step", "Confirmed Work Sequence"],
            ).to_excel(writer, sheet_name="MS Steps", index=False)
            if ms_text:
                pd.DataFrame(
                    [["Method Statement Source", report.get("Method Statement Source", "-")], ["Extracted Text", ms_text[:30000]]],
                    columns=["Field", "Value"],
                ).to_excel(writer, sheet_name="MS Extract", index=False)

        pd.DataFrame(
            [
                ["Project Manager", "-", "-", "-"],
                ["Safety Officer / Consultant", "-", "-", "-"],
                ["Subcontractor Representative", "-", "-", "-"],
                ["Site Supervisor / Foreman", "-", "-", "-"],
            ],
            columns=["Position", "Name", "Signature", "Date"],
        ).to_excel(writer, sheet_name="Signatures", index=False)

        pd.DataFrame(
            [
                ["1", "Safety helmet with chin strap", "ANSI/ISEA Z89.1 / EN397 or project accepted equivalent"],
                ["2", "Safety footwear", "EN ISO 20345 or project accepted equivalent"],
                ["3", "Protective gloves", "BS EN 388 or task-specific equivalent"],
                ["4", "Eye protection", "BS EN 166 or task-specific equivalent"],
                ["5", "High visibility vest", "Project safety requirement"],
            ],
            columns=["Item", "PPE", "Relevant Standard"],
        ).to_excel(writer, sheet_name="PPE", index=False)

        matrix_data = matrix_rows(matrix or {})
        if matrix_data:
            pd.DataFrame(matrix_data).to_excel(writer, sheet_name="Risk Matrix", index=False)
        else:
            pd.DataFrame(
                [
                    ["HR", "High Risk", "HPA", "Immediate action required"],
                    ["MR", "Medium Risk", "MPA", "Control measures required"],
                    ["LR", "Low Risk", "LPA", "Regular monitoring required"],
                ],
                columns=["Risk Level", "Meaning", "Action Priority", "Treatment"],
            ).to_excel(writer, sheet_name="Risk Matrix", index=False)

        visible_ra_rows = [{key: value for key, value in row.items() if key not in INTERNAL_RA_COLUMNS} for row in ra_rows]
        pd.DataFrame(visible_ra_rows).to_excel(writer, sheet_name="RA Table", index=False)

        _style_workbook(writer.book)
    buffer.seek(0)
    return buffer
