import streamlit as st

from services import google_drive, google_sheets, nvidia_client
from services.i18n import t
from services.nvidia_client import BASE_URL

st.set_page_config(page_title="Settings", layout="wide")
st.title("Settings")
st.warning("Secrets are shown as loaded/missing only. Values are never displayed.")

st.table(
    [
        {"Setting": "NVIDIA_API_KEY", "Status": t("loaded") if nvidia_client.has_api_key() else t("missing")},
        {"Setting": "GOOGLE_SERVICE_ACCOUNT_JSON", "Status": t("loaded") if st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON", "") else t("missing")},
        {"Setting": "GOOGLE_SHEET_ID", "Status": t("loaded") if st.secrets.get("GOOGLE_SHEET_ID", "") else t("missing")},
        {"Setting": "GOOGLE_DRIVE_FOLDER_ID", "Status": t("loaded") if st.secrets.get("GOOGLE_DRIVE_FOLDER_ID", "") else t("missing")},
        {"Setting": "Google Sheets connected", "Status": "yes" if google_sheets.configured() else "no"},
        {"Setting": "Google Drive connected", "Status": "yes" if google_drive.configured() else "no"},
        {"Setting": "Model", "Status": nvidia_client.model_name()},
        {"Setting": "Base URL", "Status": BASE_URL},
    ]
)

st.info("NVIDIA API calls are made server-side only. The API key is read from Streamlit Secrets and is never rendered in the browser.")

if st.button("Test NVIDIA backend connection"):
    ok, message = nvidia_client.test_connection()
    if ok:
        st.success(f"NVIDIA backend connection: {message}")
    else:
        st.error(f"NVIDIA backend connection failed: {message}")
