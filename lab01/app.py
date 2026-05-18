import streamlit as st
import PyPDF2
import re
import os
from collections import Counter
from openai import OpenAI

# ── Load API key ──────────────────────────────
def get_openai_key():
    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        return os.getenv("OPENAI_API_KEY")

# ── Extract text from PDF ─────────────────────
def extract_pdf_text(uploaded_file):
    reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

# ── Extract keywords ──────────────────────────
STOPWORDS = {
    "and","the","to","of","in","a","an","is","are","for","with","on","at",
    "by","from","that","this","as","be","have","has","will","we","you",
    "your","our","their","it","or","not","but","can","do","all","any",
    "more","also","such","both","each","other","about","into","through",
    "experience","work","working","team","strong","ability","skills","skill",
    "using","use","used","including","based","required","preferred","must",
    "good","great","excellent","years","year","within","across",
}

def extract_keywords(text, top_n=30):
    words = re.findall(r'\b[a-zA-Z][a-zA-Z+#\-]{1,}\b', text.lower())
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return [word for word, _ in Counter(filtered).most_common(top_n)]

# ── Compute match score ───────────────────────
def compute_match(resume_text, job_text):
    resume_kw = set(extract_keywords(resume_text, 60))
    job_kw    = set(extract_keywords(job_text, 40))
    matched   = sorted(job_kw & resume_kw)
    missing   = sorted(job_kw - resume_kw)
    score     = round(len(matched) / max(len(job_kw), 1) * 100)
    return score, matched, missing

# ── AI feedback ───────────────────────────────
def ai_feedback(resume_text, job_text, score, matched, missing):
    api_key = get_openai_key()
    if not api_key:
        return None
    try:
        client = OpenAI(api_key=api_key)
        prompt = f"""You are a career coach. Given this resume and job description, give brief feedback.

Resume (first 2000 chars): {resume_text[:2000]}
Job Description (first 1000 chars): {job_text[:1000]}
Match Score: {score}%
Matched Keywords: {', '.join(matched[:15])}
Missing Keywords: {', '.join(missing[:15])}

Give 3 short bullet points on how to improve the resume for this role."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI feedback unavailable: {e}"

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
st.title("📄 Resume Analyzer")
st.write("Upload your resume and paste a job description to see how well they match.")

# File upload
uploaded_pdf = st.file_uploader("Upload your Resume (PDF)", type=["pdf"])

# Job description input
job_description = st.text_area("Paste the Job Description here", height=200)

# Analyze button
if st.button("Analyze Resume"):

    if not uploaded_pdf:
        st.error("Please upload a PDF resume.")
        st.stop()
    if not job_description.strip():
        st.error("Please paste a job description.")
        st.stop()

    # Extract and score
    with st.spinner("Analyzing..."):
        resume_text = extract_pdf_text(uploaded_pdf)

        if len(resume_text) < 50:
            st.warning("Could not extract much text from the PDF. It may be image-based.")

        score, matched, missing = compute_match(resume_text, job_description)

    # Results
    st.success(f"Match Score: {score}%")

    st.write("### ✅ Matched Keywords")
    st.write(", ".join(matched) if matched else "None found.")

    st.write("### ❌ Missing Keywords")
    st.write(", ".join(missing) if missing else "None — great coverage!")

    # AI feedback
    st.write("### 💡 AI Suggestions")
    with st.spinner("Getting AI feedback..."):
        feedback = ai_feedback(resume_text, job_description, score, matched, missing)

    if feedback:
        st.write(feedback)
    else:
        st.info("Add an OPENAI_API_KEY to enable AI suggestions.")