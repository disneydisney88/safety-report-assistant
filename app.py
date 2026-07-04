import streamlit as st

from services import google_drive, google_sheets, nvidia_client
from services.i18n import LANG_OPTIONS, t

st.set_page_config(page_title="HK Safety Report Assistant", layout="wide")

with st.sidebar:
    choice = st.selectbox(t("language"), list(LANG_OPTIONS.keys()), index=0)
    st.session_state["lang"] = LANG_OPTIONS[choice]
    st.caption(t("draft_warning"))

st.title(t("app_title"))
st.warning(t("draft_warning"))

st.subheader("RA Report Generator MVP")
st.write(
    "Current version focuses on Risk Assessment only. Other modules are hidden for now. "
    "Use the RA Generator page to enter simple work steps, confirm them, then export Word / Excel."
)

st.subheader(t("config_status"))
col1, col2, col3 = st.columns(3)
col1.metric("NVIDIA API", t("loaded") if nvidia_client.has_api_key() else t("missing"))
col2.metric("Google Sheets", t("loaded") if google_sheets.configured() else t("missing"))
col3.metric("Google Drive", t("loaded") if google_drive.configured() else t("missing"))

if st.button("Test NVIDIA backend connection"):
    ok, message = nvidia_client.test_connection()
    if ok:
        st.success(f"NVIDIA backend connection: {message}")
    else:
        st.error(f"NVIDIA backend connection failed: {message}")

st.markdown(
    """
This MVP stores no secrets in code and uses backend Streamlit Secrets for NVIDIA.
"""
)
