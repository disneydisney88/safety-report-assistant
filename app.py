import streamlit as st

from services import nvidia_client
from services.i18n import LANG_OPTIONS, t

st.set_page_config(page_title="HK Safety Report Assistant", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
    .block-container { padding-top: 2.0rem; max-width: 1080px; }
    .home-hero {
        border: 1px solid rgba(120, 130, 150, 0.30);
        border-radius: 12px;
        padding: 30px 34px 26px 34px;
        margin-bottom: 18px;
        background: linear-gradient(135deg, rgba(23, 105, 170, 0.18), rgba(15, 118, 110, 0.10));
    }
    .home-kicker {
        color: #2f6f7a;
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.82rem;
        letter-spacing: 0.06em;
        margin-bottom: 8px;
    }
    .home-hero h1 { font-size: 34px; line-height: 1.15; margin: 0 0 10px 0; }
    .home-hero p { margin: 4px 0; font-size: 1.02rem; }
    .home-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
    .home-chip {
        border: 1px solid rgba(120, 130, 150, 0.35);
        border-radius: 999px;
        padding: 5px 12px;
        background: rgba(255, 255, 255, 0.55);
        font-size: 0.88rem;
        font-weight: 600;
        color: #1e3a5f;
    }
    .home-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 6px 0 18px 0; }
    .home-card {
        border: 1px solid rgba(120, 130, 150, 0.32);
        border-radius: 10px;
        padding: 16px 18px;
        background: rgba(255, 255, 255, 0.06);
    }
    .home-card strong { display: block; margin-bottom: 6px; font-size: 1.0rem; }
    .home-card span { color: #64748b; font-size: 0.92rem; }
    @media (max-width: 900px) { .home-grid { grid-template-columns: 1fr; } }
    .status-ok {
        display: inline-block; border-radius: 999px; padding: 4px 14px;
        background: #ecfdf5; color: #065f46; border: 1px solid #10b981; font-weight: 700;
    }
    .status-missing {
        display: inline-block; border-radius: 999px; padding: 4px 14px;
        background: #fef2f2; color: #991b1b; border: 1px solid #ef4444; font-weight: 700;
    }
    div[data-testid="stButton"] button {
        background: #1769aa; color: white; border: 1px solid #1769aa; font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    choice = st.selectbox(t("language"), list(LANG_OPTIONS.keys()), index=0)
    st.session_state["lang"] = LANG_OPTIONS[choice]
    st.caption(t("draft_warning"))

st.markdown(
    """
    <div class="home-hero">
      <div class="home-kicker">Hong Kong OSH Reporting Suite / 香港職安健報告工具</div>
      <h1>HK Safety Report Assistant</h1>
      <p><strong>Risk Assessment Report Generator / 風險評估報告生成器</strong></p>
      <p>Upload a Method Statement, confirm the real work steps, and export a contractor-style RA report in Word / Excel.</p>
      <p>上載施工方法書，確認真實工序，即可輸出承建商格式的風險評估報告（Word / Excel）。</p>
      <div class="home-chips">
        <span class="home-chip">HK OSH + IEC 31010</span>
        <span class="home-chip">A3 RA Table / A3 風險評估表</span>
        <span class="home-chip">Word &amp; Excel Export</span>
        <span class="home-chip">中英報告語言可選</span>
      </div>
    </div>
    <div class="home-grid">
      <div class="home-card"><strong>1. Upload / 上載</strong><span>Method Statement, PDF or TXT — the app extracts the true work steps.<br/>上載施工方法書，系統抽取真實工序。</span></div>
      <div class="home-card"><strong>2. Confirm / 確認</strong><span>Review and edit the extracted steps before generation.<br/>生成前檢查及修改已抽取的工序。</span></div>
      <div class="home-card"><strong>3. Export / 輸出</strong><span>Formatted hazard identification &amp; RA table with risk matrix and approval page.<br/>輸出危害識別及風險評估表、風險矩陣及批核頁。</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.page_link("pages/1_RA_Generator.py", label="Open RA Generator / 開啟風險評估生成器", icon="📄")

st.divider()

st.subheader(t("config_status"))
if nvidia_client.has_api_key():
    st.markdown('<span class="status-ok">NVIDIA AI backend: ready / 已連接</span>', unsafe_allow_html=True)
else:
    st.markdown('<span class="status-missing">NVIDIA AI backend: key missing / 未設定金鑰</span>', unsafe_allow_html=True)
    st.info(
        "Set the NVIDIA key in Streamlit Cloud Secrets as `NVIDIA_API_KEY`. "
        "Do not paste the key into GitHub code or public files."
    )

if st.button("Test NVIDIA backend connection / 測試 AI 後端連線"):
    ok, message = nvidia_client.test_connection()
    if ok:
        st.success(f"NVIDIA backend connection: {message}")
    else:
        st.error(f"NVIDIA backend connection failed: {message}")

st.caption(t("draft_warning"))
