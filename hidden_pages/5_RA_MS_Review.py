import streamlit as st

from services.ai_prompts import RA_CHECKER_SYSTEM_PROMPT
from services.i18n import t
from services.nvidia_client import generate_json
from services.validators import CheckerDraft

st.set_page_config(page_title="RA / MS Review", layout="wide")
st.title("RA / MS Review")
st.warning(t("draft_warning"), icon="⚠️")

focus = st.multiselect(
    "Checking focus",
    ["missing hazards", "weak controls", "risk rating", "legal / CoP reference", "permit / competent person", "electrical safety", "lifting / transport", "confined space", "emergency arrangement"],
)
text = st.text_area("Paste existing RA / MS text", height=300)

if st.button("Review"):
    draft, flags, error = generate_json(RA_CHECKER_SYSTEM_PROMPT, {"focus": focus, "text": text}, CheckerDraft)
    if draft is None:
        draft = CheckerDraft(result="REVISE REQUIRED", comments=["AI unavailable or output invalid.", "Manual Safety Officer review required."], suggested_revised_wording=["To be verified by Safety Officer"])
        st.info(t("ai_unavailable") + f" ({error})")
    st.metric("Checker result", draft.result)
    st.write("**Comments**")
    st.write(draft.comments)
    st.write("**Suggested revised wording**")
    st.write(draft.suggested_revised_wording)
    if flags:
        st.caption("Redaction flags: " + ", ".join(flags))

