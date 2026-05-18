import streamlit as st
import pdfplumber
import re
import os
import json
from collections import Counter
from google import genai

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Resume Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap');

:root {
    --bg:        #0d0f14;
    --surface:   #141720;
    --border:    #252933;
    --accent:    #c8f542;
    --accent2:   #42b4f5;
    --muted:     #5a6174;
    --text:      #e8eaf0;
    --text-dim:  #9aa0b4;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1100px; }

.hero {
    border-bottom: 1px solid var(--border);
    padding-bottom: 2rem;
    margin-bottom: 2.5rem;
}
.hero-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 0.5rem;
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2.2rem, 5vw, 3.6rem);
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -0.02em;
    margin: 0 0 0.75rem;
}
.hero-title span { color: var(--accent); }
.hero-sub {
    font-size: 1rem;
    color: var(--text-dim);
    font-weight: 300;
    max-width: 560px;
    line-height: 1.6;
}

.section-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.6rem;
}

[data-testid="stFileUploader"] {
    background: var(--surface) !important;
    border: 1.5px dashed var(--border) !important;
    border-radius: 12px !important;
    padding: 1.5rem !important;
    transition: border-color 0.2s;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
}

textarea {
    background: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.92rem !important;
    resize: vertical !important;
    transition: border-color 0.2s !important;
}
textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(200,245,66,0.12) !important;
}

.stButton > button {
    background: var(--accent) !important;
    color: #0d0f14 !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.06em !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.7rem 2.2rem !important;
    transition: opacity 0.15s, transform 0.1s !important;
    cursor: pointer !important;
}
.stButton > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

.score-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 2rem 2.2rem;
    display: flex;
    align-items: center;
    gap: 2rem;
    margin-bottom: 2rem;
}
.score-ring {
    width: 90px; height: 90px; flex-shrink: 0;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem; font-weight: 800;
}
.score-ring.high  { background: rgba(200,245,66,0.12); color: var(--accent);  border: 2.5px solid var(--accent); }
.score-ring.mid   { background: rgba(66,180,245,0.10); color: var(--accent2); border: 2.5px solid var(--accent2); }
.score-ring.low   { background: rgba(255,100,100,0.10); color: #ff6464;       border: 2.5px solid #ff6464; }
.score-label { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 700; }
.score-desc  { font-size: 0.88rem; color: var(--text-dim); margin-top: 0.3rem; }

.pill-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.6rem; }
.pill {
    font-size: 0.78rem; font-weight: 500;
    border-radius: 6px; padding: 0.3rem 0.75rem;
}
.pill.match   { background: rgba(200,245,66,0.12); color: var(--accent);  border: 1px solid rgba(200,245,66,0.3); }
.pill.missing { background: rgba(255,100,100,0.10); color: #ff8080;        border: 1px solid rgba(255,100,100,0.25); }

.info-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
}
.info-box h4 {
    font-family: 'Syne', sans-serif;
    font-size: 0.82rem; font-weight: 700;
    letter-spacing: 0.12em; text-transform: uppercase;
    color: var(--muted); margin: 0 0 0.8rem;
}
.info-box p { margin: 0 0 0.4rem; font-size: 0.93rem; line-height: 1.65; color: var(--text-dim); }

hr { border-color: var(--border) !important; margin: 2rem 0 !important; }
.stSpinner > div { border-top-color: var(--accent) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Helper: Load GEMINI_API_KEY
# Works both locally (.env / os.environ) and
# on Streamlit Cloud (st.secrets)
# ─────────────────────────────────────────────
def get_gemini_key() -> str | None:
    # Streamlit Cloud secrets take priority
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    # Fall back to environment variable (local .env via python-dotenv)
    return os.getenv("GEMINI_API_KEY")


# ─────────────────────────────────────────────
# Helper: Extract text from uploaded PDF
# ─────────────────────────────────────────────
def extract_pdf_text(uploaded_file) -> str:
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


# ─────────────────────────────────────────────
# Helper: Keyword extraction (stopword filter)
# ─────────────────────────────────────────────
STOPWORDS = {
    "and","the","to","of","in","a","an","is","are","for","with","on","at",
    "by","from","that","this","as","be","have","has","will","we","you",
    "your","our","their","it","or","not","but","can","do","all","any",
    "more","also","such","both","each","other","about","into","through",
    "experience","work","working","team","strong","ability","skills","skill",
    "using","use","used","including","based","required","preferred","must",
    "good","great","excellent","years","year","within","across",
}

def extract_keywords(text: str, top_n: int = 30) -> list[str]:
    words = re.findall(r'\b[a-zA-Z][a-zA-Z+#\-\.]{1,}\b', text.lower())
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 2]
    freq = Counter(filtered)
    return [word for word, _ in freq.most_common(top_n)]


# ─────────────────────────────────────────────
# Helper: Compute keyword match score
# ─────────────────────────────────────────────
def compute_match(resume_text: str, job_text: str):
    resume_kw = set(extract_keywords(resume_text, 60))
    job_kw    = set(extract_keywords(job_text,    40))
    matched   = sorted(job_kw & resume_kw)
    missing   = sorted(job_kw - resume_kw)
    score     = round(len(matched) / max(len(job_kw), 1) * 100)
    return score, matched, missing


# ─────────────────────────────────────────────
# Helper: AI qualitative feedback via Gemini
# ─────────────────────────────────────────────
def ai_analyze(resume_text: str, job_text: str, score: int,
               matched: list, missing: list) -> dict | None:
    api_key = get_gemini_key()
    if not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""You are an expert career coach and ATS specialist.

RESUME (truncated to 3000 chars):
{resume_text[:3000]}

JOB DESCRIPTION (truncated to 2000 chars):
{job_text[:2000]}

KEYWORD MATCH SCORE: {score}%
MATCHED KEYWORDS: {', '.join(matched[:20])}
MISSING KEYWORDS: {', '.join(missing[:20])}

Respond ONLY with a valid JSON object (no markdown fences, no extra text) with exactly these four keys:
- "summary": 2-sentence overall assessment
- "strengths": list of 3 strings (what the resume does well for this role)
- "gaps": list of 3 strings (key gaps or missing elements)
- "suggestions": list of 3 actionable strings (how to improve the resume)
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        raw = response.text.strip()
        # Strip any accidental markdown fences
        raw = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(raw)

    except Exception:
        return None


# ─────────────────────────────────────────────
# UI: Hero header
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-label">AI-Powered Tool &middot; Gemini 2.5 Flash</div>
  <h1 class="hero-title">Resume<br><span>Analyzer</span></h1>
  <p class="hero-sub">
    Upload your résumé and paste the job description.
    We'll score your keyword match, surface gaps, and give you
    actionable advice to land the interview.
  </p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# UI: Inputs — two-column layout
# ─────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<div class="section-label">01 — Upload Résumé (PDF)</div>', unsafe_allow_html=True)
    uploaded_pdf = st.file_uploader(
        label="Drop your PDF here",
        type=["pdf"],
        label_visibility="collapsed",
    )
    if uploaded_pdf:
        st.success(f"✓  {uploaded_pdf.name}  ({uploaded_pdf.size // 1024} KB)")

with col_right:
    st.markdown('<div class="section-label">02 — Target Job Description</div>', unsafe_allow_html=True)
    job_description = st.text_area(
        label="Paste the full job posting",
        height=220,
        placeholder="Paste the job description here — requirements, responsibilities, preferred qualifications…",
        label_visibility="collapsed",
    )

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# UI: Analyze button
# ─────────────────────────────────────────────
_, btn_col, _ = st.columns([2, 1, 2])
with btn_col:
    analyze_clicked = st.button("Analyze Resume →", use_container_width=True)


# ─────────────────────────────────────────────
# UI: Results
# ─────────────────────────────────────────────
if analyze_clicked:

    # — Validation —
    if not uploaded_pdf:
        st.error("Please upload a PDF résumé before analyzing.")
        st.stop()
    if not job_description.strip():
        st.error("Please paste a job description before analyzing.")
        st.stop()

    # — Extract text & score —
    with st.spinner("Extracting text and scoring your résumé…"):
        try:
            resume_text = extract_pdf_text(uploaded_pdf)
        except Exception as e:
            st.error(f"Could not read the PDF: {e}")
            st.stop()

        if len(resume_text) < 80:
            st.warning(
                "Very little text was extracted — the PDF may be image-based. "
                "Results may be limited."
            )

        score, matched, missing = compute_match(resume_text, job_description)

    st.markdown("---")

    # — Score card —
    ring_class = "high" if score >= 70 else ("mid" if score >= 40 else "low")
    verdict    = ("Strong match — well aligned with this role."  if score >= 70 else
                  "Moderate match — some gaps to address."        if score >= 40 else
                  "Low match — significant optimisation needed.")

    st.markdown(f"""
    <div class="score-card">
      <div class="score-ring {ring_class}">{score}%</div>
      <div>
        <div class="score-label">Keyword Match Score</div>
        <div class="score-desc">{verdict}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # — Keyword pills —
    kw_col1, kw_col2 = st.columns(2, gap="medium")

    with kw_col1:
        st.markdown('<div class="section-label">✓ Matched Keywords</div>', unsafe_allow_html=True)
        if matched:
            pills = " ".join(f'<span class="pill match">{k}</span>' for k in matched)
            st.markdown(f'<div class="pill-grid">{pills}</div>', unsafe_allow_html=True)
        else:
            st.caption("No keyword matches found.")

    with kw_col2:
        st.markdown('<div class="section-label">✗ Missing Keywords</div>', unsafe_allow_html=True)
        if missing:
            pills = " ".join(f'<span class="pill missing">{k}</span>' for k in missing[:20])
            st.markdown(f'<div class="pill-grid">{pills}</div>', unsafe_allow_html=True)
        else:
            st.caption("No missing keywords — great coverage!")

    # — AI Feedback —
    st.markdown("---")
    st.markdown('<div class="section-label">03 — AI Feedback (Gemini)</div>', unsafe_allow_html=True)

    with st.spinner("Generating AI-powered feedback via Gemini…"):
        ai_result = ai_analyze(resume_text, job_description, score, matched, missing)

    if ai_result:
        st.markdown(f"""
        <div class="info-box">
          <h4>Overall Assessment</h4>
          <p>{ai_result.get('summary', '—')}</p>
        </div>
        """, unsafe_allow_html=True)

        ai_col1, ai_col2, ai_col3 = st.columns(3, gap="medium")

        def render_bullets(items: list) -> str:
            return "".join(f"<p>• {item}</p>" for item in (items or [])) or "<p>—</p>"

        with ai_col1:
            st.markdown(f"""
            <div class="info-box">
              <h4>💪 Strengths</h4>
              {render_bullets(ai_result.get('strengths', []))}
            </div>""", unsafe_allow_html=True)

        with ai_col2:
            st.markdown(f"""
            <div class="info-box">
              <h4>🔍 Gaps</h4>
              {render_bullets(ai_result.get('gaps', []))}
            </div>""", unsafe_allow_html=True)

        with ai_col3:
            st.markdown(f"""
            <div class="info-box">
              <h4>🚀 Suggestions</h4>
              {render_bullets(ai_result.get('suggestions', []))}
            </div>""", unsafe_allow_html=True)

    else:
        st.info(
            "AI feedback is unavailable — `GEMINI_API_KEY` is not configured. "
            "Add it to Streamlit Cloud → Advanced Settings → Secrets, "
            "or to your local `.env` file. "
            "Keyword scoring above is still fully functional."
        )

    # — Raw résumé text preview —
    with st.expander("📄 View extracted résumé text"):
        st.text_area(
            "Extracted Text", value=resume_text, height=300,
            disabled=True, label_visibility="collapsed"
        )


# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.markdown("""
<hr>
<p style="text-align:center;font-size:0.75rem;color:#3d4257;margin-top:1rem;">
  Resume Analyzer &middot; Built with Streamlit &amp; Google Gemini
</p>
""", unsafe_allow_html=True)
