"""
app.py — Presentation & UI Controller Layer
============================================
Strictly the interface skin. Contains zero SQL, zero API client calls.
All computation is delegated to:
    - services/gemini_service.py  → sentiment analysis
    - database/db_manager.py      → persistence

Run with:
    streamlit run app.py
"""

import streamlit as st

from config import DB_NAME
from database.db_manager import (
    init_db,
    save_summary,
    get_summaries_by_category,
    get_summary_by_id,
)
from services.gemini_service import analyze_review_sentiment

# ---------------------------------------------------------------------------
# Bootstrap — ensure schema exists before any UI renders
# ---------------------------------------------------------------------------
init_db(DB_NAME)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Review Sentiment Analyser",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 Review Sentiment Analyser")
st.caption("Upload a review file or paste text — the model scores and stores it automatically.")

# ---------------------------------------------------------------------------
# Session state — tracks which tab is active and last saved record id
# ---------------------------------------------------------------------------
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Analyse"

if "last_saved_id" not in st.session_state:
    st.session_state.last_saved_id = None

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# ---------------------------------------------------------------------------
# Tab navigation
# ---------------------------------------------------------------------------
TAB_ANALYSE  = "Analyse"
TAB_HISTORY  = "History"
TAB_LOOKUP   = "Lookup by ID"

tab_analyse, tab_history, tab_lookup = st.tabs([TAB_ANALYSE, TAB_HISTORY, TAB_LOOKUP])


# ===========================================================================
# TAB 1 — Analyse
# ===========================================================================
with tab_analyse:
    st.subheader("Submit a Review")

    # --- Input grid: file upload (left) + text area (right) ----------------
    col_upload, col_text = st.columns([1, 2], gap="large")

    with col_upload:
        st.markdown("**Drag & drop a `.txt` file**")
        uploaded_file = st.file_uploader(
            label="Review file",
            type=["txt"],
            accept_multiple_files=False,
            label_visibility="collapsed",
        )
        if uploaded_file is not None:
            file_text = uploaded_file.read().decode("utf-8", errors="replace")
            st.success(f"Loaded `{uploaded_file.name}` ({len(file_text)} chars)")
        else:
            file_text = ""

    with col_text:
        st.markdown("**Or type / paste review text**")
        manual_text = st.text_area(
            label="Review content",
            placeholder="The product exceeded my expectations in every way...",
            height=180,
            label_visibility="collapsed",
        )

    # Resolve which input to use — file takes priority
    review_content = file_text if file_text.strip() else manual_text
    source_filename = uploaded_file.name if uploaded_file else "manual_entry.txt"

    st.divider()

    # --- Action row --------------------------------------------------------
    col_btn, col_status = st.columns([1, 3], gap="medium")

    with col_btn:
        run_analysis = st.button(
            "🔍 Analyse",
            type="primary",
            use_container_width=True,
            disabled=not review_content.strip(),
        )

    # --- Execute & persist -------------------------------------------------
    if run_analysis:
        with st.spinner("Querying model…"):
            try:
                result = analyze_review_sentiment(review_content)
                record_id = save_summary(
                    DB_NAME,
                    filename=source_filename,
                    summary=result["raw"],
                    rating=result["rating"],
                    category=result["category"],
                )
                st.session_state.analysis_result = result
                st.session_state.last_saved_id   = record_id
            except ValueError as e:
                st.error(f"Parse error: {e}")
                st.stop()
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()

    # --- Result display ----------------------------------------------------
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result

        st.subheader("Result")
        col_rating, col_category, col_id = st.columns(3, gap="medium")

        CATEGORY_COLOUR = {"Good": "🟢", "Average": "🟡", "Bad": "🔴"}
        icon = CATEGORY_COLOUR.get(result["category"], "⚪")

        with col_rating:
            st.metric("Rating", f"{result['rating']} / 5")

        with col_category:
            st.metric("Category", f"{icon} {result['category']}")

        with col_id:
            st.metric("Saved as record #", st.session_state.last_saved_id or "—")

        with st.expander("Full model response"):
            st.text(result["raw"])


# ===========================================================================
# TAB 2 — History (filter by category)
# ===========================================================================
with tab_history:
    st.subheader("Historical Records by Category")

    col_filter, col_spacer = st.columns([1, 3], gap="medium")

    with col_filter:
        category_choice = st.selectbox(
            "Filter by category",
            options=["Good", "Average", "Bad"],
            index=0,
        )

    rows = get_summaries_by_category(DB_NAME, category_choice)

    if not rows:
        st.info(f"No records found for category **{category_choice}** yet.")
    else:
        st.caption(f"{len(rows)} record(s) found")

        for row in rows:
            with st.expander(
                f"#{row['id']} — {row['filename']}  |  "
                f"Rating {row['rating']}  |  {row['created_at']}"
            ):
                col_meta, col_summary = st.columns([1, 3], gap="medium")

                with col_meta:
                    st.markdown(f"**ID:** {row['id']}")
                    st.markdown(f"**File:** {row['filename']}")
                    st.markdown(f"**Rating:** {row['rating']} / 5")
                    st.markdown(f"**Category:** {row['category']}")
                    st.markdown(f"**Saved:** {row['created_at']}")

                with col_summary:
                    st.markdown("**Model response:**")
                    st.text(row["summary"])


# ===========================================================================
# TAB 3 — Lookup by ID
# ===========================================================================
with tab_lookup:
    st.subheader("Fetch a Single Record by ID")

    col_input, col_go = st.columns([2, 1], gap="medium")

    with col_input:
        lookup_id = st.number_input(
            "Record ID",
            min_value=1,
            step=1,
            value=st.session_state.last_saved_id or 1,
            label_visibility="visible",
        )

    with col_go:
        st.write("")  # vertical alignment spacer
        do_lookup = st.button("🔎 Fetch", use_container_width=True)

    if do_lookup:
        row = get_summary_by_id(DB_NAME, int(lookup_id))

        if row is None:
            st.warning(f"No record found with ID **{int(lookup_id)}**.")
        else:
            st.success("Record found")

            col_a, col_b, col_c = st.columns(3, gap="medium")

            with col_a:
                st.metric("Rating", f"{row['rating']} / 5")
            with col_b:
                st.metric("Category", row["category"])
            with col_c:
                st.metric("Record ID", row["id"])

            st.markdown(f"**File:** `{row['filename']}`")
            st.markdown(f"**Saved:** {row['created_at']}")

            with st.expander("Full model response"):
                st.text(row["summary"])