# HK Safety Report Assistant

Streamlit MVP for Hong Kong construction safety officers / safety consultants. It drafts and reviews safety documents, but every output is marked:

> AI-generated draft. To be reviewed and approved by Safety Officer / authorised person before use.

## Current MVP Features

- RA-focused interface
- Step 1: collect Method Statement status, activity, location, equipment/tools and confined space status
- Step 2: confirm user-provided or inferred construction steps
- Step 3: generate a structured RA report
- Word export for full RA report
- Excel export for cover, signatures, PPE, risk matrix and RA table
- NVIDIA NIM OpenAI-compatible backend using `z-ai/glm-5.2` by default, configurable for free endpoints such as `z-ai/glm-5.1`
- Redaction before AI calls
- Other modules are preserved in `hidden_pages/` and can be restored later

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Secrets

Create `.streamlit/secrets.toml` locally or configure secrets in Streamlit Community Cloud. Do not commit this file.

```toml
NVIDIA_API_KEY = "..."
NVIDIA_MODEL = "z-ai/glm-5.2" # or the free endpoint model ID shown on build.nvidia.com, e.g. "z-ai/glm-5.1"
NVIDIA_TEMPERATURE = 0.2
NVIDIA_TOP_P = 1
NVIDIA_MAX_TOKENS = 16384
NVIDIA_TIMEOUT_SECONDS = 30
NVIDIA_SEED = "" # optional
GOOGLE_SHEET_ID = "..."
GOOGLE_DRIVE_FOLDER_ID = "..."
GOOGLE_SERVICE_ACCOUNT_JSON = '''{"type":"service_account","project_id":"..."}'''
```

For NVIDIA Build Free Endpoint:

1. Log in to NVIDIA Build.
2. Open the model page, for example GLM.
3. Create or copy your API key.
4. Put the key in `NVIDIA_API_KEY`.
5. Put the exact model ID shown by NVIDIA in `NVIDIA_MODEL`.

The API key is never displayed in the UI and is never committed to GitHub.

For safety reports, keep `NVIDIA_TEMPERATURE` low, such as `0.2`, so the output is more stable and less creative.

After setting secrets, open the Settings page and click `Test NVIDIA backend connection`. The test runs server-side and never displays the API key.

## Google Sheets Worksheets

Create worksheets using these names:

- `projects`
- `ra_records`
- `ra_items`
- `inspection_findings`
- `incident_reports`
- `follow_up_actions`
- `hazard_library`
- `legal_reference_library`
- `ai_generation_log`
- `audit_log`

The expected columns are defined in `services/google_sheets.py`.

## Google Drive Folders

Recommended folder layout:

- `Safety_Report_Assistant/RA_Reports`
- `Safety_Report_Assistant/Inspection_Reports`
- `Safety_Report_Assistant/Incident_Reports`
- `Safety_Report_Assistant/Uploaded_Photos`
- `Safety_Report_Assistant/Uploaded_MS_RA`
- `Safety_Report_Assistant/Generated_DOCX`
- `Safety_Report_Assistant/Generated_PDF`

Set `GOOGLE_DRIVE_FOLDER_ID` to the parent or generated-report folder used by the app.

## Deployment Notes

This app is suitable for GitHub + Streamlit Community Cloud deployment. Keep secrets in Streamlit Secrets only. Never print, log, display, or commit API keys or Google credentials.

See `SECURITY.md` for NVIDIA API key handling rules. The key is used server-side only and is never rendered in the browser.

## Official References

- [Labour Department Occupational Safety publications](https://www.labour.gov.hk/tc/public/content2_8.htm)
- [Labour Department public forms](https://www.labour.gov.hk/tc/form/public_forms.htm)
- [NVIDIA GLM-5.2](https://build.nvidia.com/z-ai/glm-5.2)
- [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud)
- [Streamlit Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Google Sheets API limits](https://developers.google.com/workspace/sheets/api/limits)
- [Google Drive API limits](https://developers.google.com/workspace/drive/api/guides/limits)

## Next Build Steps

- Persist generated DOCX files to Google Drive and write file URLs back to Sheets
- Add PDF export
- Add role-based approval workflow
- Add audit log events for create / update / approval actions
- Expand controlled hazard and legal reference libraries
