# Security Notes

## NVIDIA API Key Handling

- Store the NVIDIA API key only in Streamlit Secrets as `NVIDIA_API_KEY`.
- Never put a real key in `app.py`, page files, README examples, screenshots, logs, or Git commits.
- The app reads the key only inside `services/nvidia_client.py`.
- The browser receives only generated report text, never the API key.
- If a key is pasted into chat, email, GitHub, screenshots, or any shared place, revoke it in NVIDIA Build and create a new key.

## Local Files

- `.streamlit/secrets.toml` is ignored by git.
- `.streamlit/secrets.toml.example` is safe because it contains placeholders only.

## Deployment

For Streamlit Community Cloud, put these values in the app's Secrets settings:

```toml
NVIDIA_API_KEY = "new_key_here"
NVIDIA_MODEL = "z-ai/glm-5.2"
NVIDIA_TEMPERATURE = 0.2
NVIDIA_TOP_P = 1
NVIDIA_MAX_TOKENS = 16384
NVIDIA_SEED = ""
```

Do not add the real key to GitHub repository secrets unless a GitHub Action specifically needs it. This app does not need GitHub Actions to know the NVIDIA key.

