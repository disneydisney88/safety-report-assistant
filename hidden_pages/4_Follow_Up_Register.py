import pandas as pd
import streamlit as st

from services.google_sheets import read_sheet
from services.i18n import t

st.set_page_config(page_title="Follow-up Register", layout="wide")
st.title("Follow-up Register")

df = read_sheet("follow_up_actions")
if df.empty:
    df = pd.DataFrame(
        [
            {
                "action_id": "DEMO-001",
                "source_type": "inspection",
                "project_id": "Demo Project",
                "action_description": "Rectify unsafe access arrangement",
                "responsible_party": "Contractor",
                "target_date": "2026-07-10",
                "status": "Open",
                "evidence_url": "",
                "remarks": "Demo row shown because Google Sheets has no data or is not configured.",
                "updated_at": "",
            }
        ]
    )

c1, c2, c3, c4 = st.columns(4)
project = c1.text_input(t("project"))
contractor = c2.text_input(t("contractor"))
status = c3.selectbox(t("status"), ["", "Open", "In progress", "Closed", "Overdue"])
risk = c4.selectbox(t("risk_level"), ["", "Low", "Medium", "High", "Critical"])

filtered = df.copy()
if project and "project_id" in filtered:
    filtered = filtered[filtered["project_id"].astype(str).str.contains(project, case=False, na=False)]
if contractor and "responsible_party" in filtered:
    filtered = filtered[filtered["responsible_party"].astype(str).str.contains(contractor, case=False, na=False)]
if status and "status" in filtered:
    filtered = filtered[filtered["status"].astype(str).eq(status)]
if risk and "risk_level" in filtered:
    filtered = filtered[filtered["risk_level"].astype(str).eq(risk)]

st.dataframe(filtered, use_container_width=True, hide_index=True)

