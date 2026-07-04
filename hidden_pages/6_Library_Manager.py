import json
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Library Manager", layout="wide")
st.title("Library Manager")
st.caption("Controlled libraries. Legal clause numbers must be verified by Safety Officer.")

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
files = {
    "Hazard library": CONFIG_DIR / "hazard_library.json",
    "Legal / CoP reference library": CONFIG_DIR / "legal_reference_library.json",
    "Risk matrix": CONFIG_DIR / "risk_matrix.json",
    "Report templates": CONFIG_DIR / "report_templates.json",
}

name = st.selectbox("Library", list(files))
path = files[name]
data = json.loads(path.read_text(encoding="utf-8"))
edited = st.text_area("JSON", json.dumps(data, indent=2, ensure_ascii=False), height=420)
if st.button("Validate JSON"):
    json.loads(edited)
    st.success("JSON is valid. Edit persistence is intentionally disabled in MVP; update config files through Git review.")

