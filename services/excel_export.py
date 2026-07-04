from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from services.ai_prompts import DISCLAIMER


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

        pd.DataFrame(ra_rows).to_excel(writer, sheet_name="RA Table", index=False)
    buffer.seek(0)
    return buffer
