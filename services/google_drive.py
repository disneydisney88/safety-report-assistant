from __future__ import annotations

import json
from io import BytesIO

import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def configured() -> bool:
    return bool(st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON", "") and st.secrets.get("GOOGLE_DRIVE_FOLDER_ID", ""))


def _service():
    info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def upload_bytes(filename: str, data: bytes | BytesIO, mime_type: str, folder_id: str | None = None) -> str | None:
    if not configured():
        return None
    body = {"name": filename, "parents": [folder_id or st.secrets["GOOGLE_DRIVE_FOLDER_ID"]]}
    if isinstance(data, BytesIO):
        data.seek(0)
        stream = data
    else:
        stream = BytesIO(data)
    media = MediaIoBaseUpload(stream, mimetype=mime_type, resumable=False)
    file = _service().files().create(body=body, media_body=media, fields="id, webViewLink").execute()
    return file.get("webViewLink")

