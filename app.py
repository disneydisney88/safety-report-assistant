import streamlit as st

st.set_page_config(page_title="HK Safety Report Assistant", layout="wide", initial_sidebar_state="collapsed")

# The app is a single-purpose tool, so skip a separate landing page and open
# directly on the RA Generator. The public marketing / WhatsApp link-preview
# landing lives at docs/index.html (GitHub Pages), independent of this app.
try:
    st.switch_page("pages/1_RA_Generator.py")
except Exception:
    # Older Streamlit without st.switch_page: show a direct link instead.
    st.title("HK Safety Report Assistant / 香港職安健風險評估")
    st.page_link("pages/1_RA_Generator.py", label="Open RA Generator / 開啟風險評估生成器", icon="📄")
