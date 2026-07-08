import streamlit as st

from services import nvidia_client
from services.i18n import LANG_OPTIONS, t

st.set_page_config(page_title="HK Safety Report Assistant", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.6rem; max-width: 1080px; }

    /* ---------- Hero ---------- */
    .home-hero {
        position: relative;
        border-radius: 16px;
        padding: 42px 44px 34px 44px;
        margin-bottom: 20px;
        background:
            radial-gradient(1200px 380px at 85% -10%, rgba(45, 212, 191, 0.25), transparent 60%),
            linear-gradient(135deg, #0b2545 0%, #13315c 55%, #134e4a 100%);
        color: #f8fafc;
        overflow: hidden;
        box-shadow: 0 18px 40px rgba(11, 37, 69, 0.35);
    }
    .home-hero::after {
        content: "";
        position: absolute; inset: 0;
        background-image: repeating-linear-gradient(135deg, rgba(255,255,255,0.03) 0 2px, transparent 2px 14px);
        pointer-events: none;
    }
    .home-kicker {
        display: inline-block;
        color: #0b2545;
        background: #fbbf24;
        font-weight: 800;
        font-size: 0.74rem;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        padding: 4px 12px;
        border-radius: 999px;
        margin-bottom: 16px;
    }
    .home-hero h1 { font-size: 40px; line-height: 1.12; margin: 0 0 6px 0; color: #ffffff; letter-spacing: -0.01em; }
    .home-hero .subtitle { font-size: 1.12rem; font-weight: 700; color: #99f6e4; margin: 0 0 14px 0; }
    .home-hero p { margin: 3px 0; font-size: 1.0rem; color: rgba(248, 250, 252, 0.88); }
    .home-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
    .home-chip {
        border: 1px solid rgba(153, 246, 228, 0.35);
        border-radius: 999px;
        padding: 5px 14px;
        background: rgba(255, 255, 255, 0.08);
        font-size: 0.86rem;
        font-weight: 600;
        color: #ccfbf1;
        backdrop-filter: blur(4px);
    }

    /* ---------- Workflow steps ---------- */
    .home-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin: 4px 0 8px 0; }
    .home-card {
        position: relative;
        border: 1px solid rgba(120, 130, 150, 0.28);
        border-radius: 14px;
        padding: 20px 20px 18px 20px;
        background: rgba(148, 163, 184, 0.06);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .home-card:hover { transform: translateY(-3px); box-shadow: 0 12px 26px rgba(11, 37, 69, 0.18); }
    .step-no {
        display: inline-flex; align-items: center; justify-content: center;
        width: 30px; height: 30px; border-radius: 999px;
        background: linear-gradient(135deg, #1769aa, #134e4a);
        color: #ffffff; font-weight: 800; font-size: 0.9rem;
        margin-bottom: 10px;
    }
    .home-card strong { display: block; margin-bottom: 6px; font-size: 1.02rem; }
    .home-card span { color: #64748b; font-size: 0.9rem; line-height: 1.5; }

    /* ---------- Capability strip ---------- */
    .cap-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 14px 0 20px 0; }
    .cap-card {
        border: 1px solid rgba(120, 130, 150, 0.25);
        border-left: 4px solid #1769aa;
        border-radius: 10px;
        padding: 13px 15px;
        background: rgba(148, 163, 184, 0.05);
    }
    .cap-card b { display: block; font-size: 0.92rem; margin-bottom: 3px; }
    .cap-card span { color: #64748b; font-size: 0.82rem; line-height: 1.45; }

    @media (max-width: 900px) {
        .home-grid, .cap-grid { grid-template-columns: 1fr; }
        .home-hero { padding: 30px 26px; }
        .home-hero h1 { font-size: 30px; }
    }

    /* ---------- Status + CTA ---------- */
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
        border-radius: 8px;
    }
    div[data-testid="stButton"] button:hover { filter: brightness(1.12); }
    div[data-testid="stPageLink"] a {
        background: linear-gradient(135deg, #1769aa, #134e4a);
        color: #ffffff !important;
        font-weight: 800;
        border-radius: 10px;
        padding: 0.75rem 1.2rem;
        box-shadow: 0 8px 20px rgba(23, 105, 170, 0.35);
    }
    div[data-testid="stPageLink"] a:hover { filter: brightness(1.1); text-decoration: none; }
    div[data-testid="stPageLink"] a p { font-size: 1.05rem !important; }

    .home-footer { color: #94a3b8; font-size: 0.82rem; margin-top: 10px; }
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
      <div class="home-kicker">Hong Kong OSH Reporting Suite · 香港職安健報告工具</div>
      <h1>HK Safety Report Assistant</h1>
      <p class="subtitle">Risk Assessment Report Generator / 風險評估報告生成器</p>
      <p>Upload a Method Statement, confirm the real work steps, and export a contractor-style Risk Assessment report in Word / Excel.</p>
      <p>上載施工方法書，確認真實工序，即可輸出承建商格式的風險評估報告（Word / Excel）。</p>
      <div class="home-chips">
        <span class="home-chip">HK OSH · IEC 31010</span>
        <span class="home-chip">Cap. 59 / 59I / 59J / 59AC 法例對應</span>
        <span class="home-chip">A3 RA Table · 風險矩陣</span>
        <span class="home-chip">Word &amp; Excel 匯出</span>
        <span class="home-chip">中英雙語 Bilingual</span>
      </div>
    </div>
    <div class="home-grid">
      <div class="home-card"><span class="step-no">1</span><strong>Upload / 上載</strong><span>Method Statement (DOCX / PDF / TXT) — AI 抽取真實工序、機械、工種、許可證及環境資料。</span></div>
      <div class="home-card"><span class="step-no">2</span><strong>Confirm / 確認</strong><span>Pre-RA Data Sheet 核對高風險標記、許可證及工序；生成前可自由修改。</span></div>
      <div class="home-card"><span class="step-no">3</span><strong>Export / 輸出</strong><span>危害識別及風險評估表、風險矩陣、PPE / 許可證 / 應急 / 訓練 / 巡查章節及批核頁。</span></div>
    </div>
    <div class="cap-grid">
      <div class="cap-card"><b>🎯 逐工序危害配對</b><span>每個工序獨立危害、成因、後果、控制措施及法例對應。</span></div>
      <div class="cap-card"><b>⚖️ 風險評級 QA</b><span>致命後果 S5 規則、剩餘風險目標 LR，未達標自動紅字提示。</span></div>
      <div class="cap-card"><b>📋 法定文件對應</b><span>Form 5、SWP Form 1-3、LALG 證書、T4 檢查按工種自動觸發。</span></div>
      <div class="cap-card"><b>🛟 應急及救援</b><span>高處救援、吊籠被困、惡劣天氣停工準則，工地資料紅字待填。</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.page_link("pages/1_RA_Generator.py", label="Open RA Generator / 開啟風險評估生成器", icon="📄")

st.divider()

st.subheader(t("config_status"))
if nvidia_client.has_api_key():
    st.markdown('<span class="status-ok">AI backend: ready / 已連接</span>', unsafe_allow_html=True)
else:
    st.markdown('<span class="status-missing">AI backend: key missing / 未設定金鑰</span>', unsafe_allow_html=True)
    st.info(
        "Set the API key in Streamlit Cloud Secrets as `NVIDIA_API_KEY`. "
        "Do not paste the key into GitHub code or public files."
    )

if st.button("Test AI backend connection / 測試 AI 後端連線"):
    ok, message = nvidia_client.test_connection()
    if ok:
        st.success(f"AI backend connection: {message}")
    else:
        st.error(f"AI backend connection failed: {message}")

st.caption(t("draft_warning"))
st.markdown('<div class="home-footer">HK Safety Report Assistant · Draft for Safety Officer review · 草擬本，須由安全主任覆核</div>', unsafe_allow_html=True)
