import streamlit as st
import pandas as pd
import os
import io
import zipfile
import re

from match_candidates import match_candidates
from outlook_sync import sync_outlook_resumes
from database.db import get_connection


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Resume Matcher",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "outlook_sync_report": None,
    "outlook_sync_error": None,
    "candidate_matches": None,
    "candidate_matches_job": None,
    "candidate_matches_job_title": None,
    "job_title_input": "",
    "job_form_open": False,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_job_opening():
    st.session_state.job_title_input = ""
    st.session_state.job_description_input = ""
    st.session_state.candidate_matches = None
    st.session_state.candidate_matches_job = None
    st.session_state.candidate_matches_job_title = None
    st.session_state.job_form_open = True


def edit_job_opening():
    st.session_state.job_form_open = True


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

    :root {
        --bg: #f4f0f7;
        --panel: rgba(248, 245, 251, 0.78);
        --panel-strong: #f8f5fb;
        --ink: #252238;
        --muted: #706b83;
        --line: rgba(91, 77, 117, 0.14);
        --brand-1: #7662aa;
        --brand-2: #6f9c98;
        --brand-3: #d99a78;
        --success: #427c68;
        --warning: #bd8751;
        --shadow: 0 18px 44px rgba(45, 37, 61, 0.08);
    }

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background:
            radial-gradient(ellipse at 12% 0%, rgba(196, 177, 220, 0.24), transparent 32%),
            radial-gradient(ellipse at 92% 18%, rgba(170, 207, 196, 0.18), transparent 28%),
            linear-gradient(180deg, #f6f3f8 0%, #eeeaf3 100%);
        color: var(--ink);
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.1rem;
        padding-left: 3rem;
        padding-right: 3rem;
        padding-bottom: 4rem;
    }

    header[data-testid="stHeader"] {
        background: rgba(246, 243, 248, 0.76);
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #302a40 0%, #242235 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    section[data-testid="stSidebar"] * {
        color: #edf2ff;
    }

    section[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #8875b8 0%, #67958f 100%);
        border: none;
        color: #fff;
        box-shadow: 0 12px 24px rgba(31, 25, 45, 0.22);
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        filter: brightness(1.04);
    }

    .stTabs [role="tablist"] {
        gap: 0.6rem;
        background: rgba(248, 245, 251, 0.55);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 0.4rem;
        margin-bottom: 1rem;
    }

    .stTabs [role="tab"] {
        border-radius: 12px;
        padding: 0.65rem 1rem;
        font-weight: 700;
        color: var(--muted);
        transition: all 0.2s ease;
    }

    .stTabs [role="tab"][aria-selected="true"] {
        background: rgba(118, 98, 170, 0.10);
        color: var(--ink);
        border: 1px solid rgba(118, 98, 170, 0.10);
        box-shadow: 0 6px 16px rgba(53, 43, 74, 0.07);
    }

    h1, h2, h3, h4 {
        letter-spacing: -0.04em;
        font-family: 'Space Grotesk', 'Inter', sans-serif;
    }

    .creative-hero {
        position: relative;
        padding: 3.2rem 1rem 2.6rem;
        margin: 0 auto 0.8rem;
    }

    .hero-row {
        display: flex;
        justify-content: center;
        text-align: center;
    }

    .hero-kicker {
        display: inline-block;
        margin-bottom: 1rem;
        color: #7662aa;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.18em;
        text-transform: uppercase;
    }

    .creative-hero h1 {
        color: #292438;
        margin: 0;
        font-family: Georgia, 'Times New Roman', serif;
        font-size: clamp(2.5rem, 5.2vw, 4.25rem);
        line-height: 1.08;
        letter-spacing: -0.045em;
        max-width: 900px;
        margin-inline: auto;
    }

    .hero-accent {
        color: #79669d;
        font-style: italic;
    }

    .hero-flow {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.65rem;
        margin-top: 1.8rem;
    }

    .hero-flow-item {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.48rem 0.8rem 0.48rem 0.48rem;
        border-radius: 999px;
        background: rgba(248, 245, 251, 0.62);
        color: #615a72;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.015em;
    }

    .job-openings-heading {
        padding: 0.5rem 0 0.75rem;
        color: #5f596d;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.16em;
    }

    .st-key-sticky-workflow-panel {
        position: sticky;
        top: 1rem;
        align-self: flex-start;
        z-index: 5;
        max-height: calc(100vh - 2rem);
        overflow-y: auto;
    }

    .st-key-results-scroll-panel {
        max-height: calc(100vh - 2rem);
        overflow-y: auto;
        overscroll-behavior: contain;
        padding-right: 0.4rem;
        scrollbar-width: thin;
        scrollbar-color: rgba(91, 77, 117, 0.3) transparent;
    }

    .st-key-job-openings-panel > [data-testid="stVerticalBlock"] {
        gap: 0.55rem;
    }

    .flow-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.45rem;
        height: 1.45rem;
        border-radius: 50%;
        background: #e7e0ef;
        color: #6e5c95;
        font-size: 0.68rem;
        font-weight: 800;
    }

    .creative-hero p {
        color: #716b7e;
        margin: 1.1rem auto 0;
        font-size: 1.02rem;
        line-height: 1.65;
        max-width: 780px;
    }

    h1, h2, h3, h4 {
        color: #292438;
    }

    div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stExpander"],
    div[data-testid="stDataFrame"] {
        border-radius: 22px;
        border: 1px solid rgba(91, 77, 117, 0.12);
        box-shadow: 0 12px 32px rgba(45, 37, 61, 0.055);
        overflow: hidden;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(248, 245, 251, 0.36);
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(250,248,252,0.78), rgba(232,226,240,0.52));
        border: 1px solid rgba(91, 77, 117, 0.10);
        border-radius: 17px;
        padding: 0.85rem 1rem;
        box-shadow: none;
    }

    div[data-testid="stMetricLabel"] {
        color: #777186;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    div[data-testid="stMetricValue"] {
        color: #302a40;
        font-family: 'Space Grotesk', 'Inter', sans-serif;
        font-weight: 700;
    }

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 13px;
        font-weight: 700;
        min-height: 44px;
        box-shadow: 0 7px 18px rgba(45, 37, 61, 0.07);
        transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 22px rgba(45, 37, 61, 0.12);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(120deg, #7662aa 0%, #648d88 100%);
        border: none;
        color: white;
    }

    [class*="st-key-new_job_button"] button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #17684d !important;
        padding-left: 0.35rem;
        padding-right: 0.35rem;
    }

    [class*="st-key-new_job_button"] button:hover {
        background: rgba(23, 104, 77, 0.08) !important;
        box-shadow: none !important;
    }

    [class*="st-key-save_job_button"] button {
        background: #17684d !important;
        border: 1px solid #17684d !important;
        color: #fff !important;
        box-shadow: none !important;
    }

    [class*="st-key-save_job_button"] button:hover {
        background: #11583f !important;
        border-color: #11583f !important;
    }

    [class*="st-key-sync_outlook_button"] button {
        background: rgba(248, 245, 251, 0.62) !important;
        border: 1px solid #17684d !important;
        color: #17684d !important;
        box-shadow: none !important;
    }

    [class*="st-key-sync_outlook_button"] button:hover {
        background: rgba(23, 104, 77, 0.08) !important;
        border-color: #11583f !important;
        color: #11583f !important;
    }

    textarea, input, select {
        border-radius: 15px !important;
        border: 1px solid rgba(91, 77, 117, 0.18) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
    }

    textarea:focus, input:focus, select:focus {
        border-color: rgba(118, 98, 170, 0.46) !important;
        box-shadow: 0 0 0 0.16rem rgba(118, 98, 170, 0.12) !important;
    }

    .stDataFrame {
        border-radius: 16px;
        overflow: hidden;
    }

    div[data-testid="stAlert"] {
        border-radius: 15px;
        border: 1px solid rgba(91, 77, 117, 0.10);
    }

    hr {
        border-color: rgba(91, 77, 117, 0.14);
    }

    #MainMenu, footer {
        visibility: hidden;
    }

    @media (max-width: 900px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .st-key-sticky-workflow-panel {
            position: static;
            max-height: none;
            overflow: visible;
        }
        .st-key-results-scroll-panel {
            max-height: none;
            overflow: visible;
            padding-right: 0;
        }
        .creative-hero {
            padding: 2.4rem 0.4rem 1.7rem;
        }
        .creative-hero h1 {
            font-size: clamp(2.2rem, 10vw, 3.2rem);
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# RESUME FILE FUNCTIONS
# ============================================================

def get_resume_file_path(candidate_id):
    """
    Find the resume file belonging to a candidate.

    The database may contain:
        - absolute path
        - relative path
        - filename only

    We check:
        1. Absolute database path
        2. Database relative path
        3. email_resumes folder
        4. resumes folder
    """

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT resume_file
            FROM candidates
            WHERE id = ?
            """,
            (candidate_id,),
        )

        row = cursor.fetchone()

    finally:
        connection.close()

    if not row:
        return None

    try:
        resume_file = row["resume_file"]
    except Exception:
        resume_file = row[0]

    if not resume_file:
        return None

    resume_file = str(resume_file).strip()

    if not resume_file:
        return None

    possible_paths = []

    # Absolute database path
    if os.path.isabs(resume_file):
        possible_paths.append(resume_file)

    # Path exactly as stored
    possible_paths.append(resume_file)

    # Filename only
    filename = os.path.basename(resume_file)

    # Email resume folder
    possible_paths.append(
        os.path.join(
            "email_resumes",
            filename,
        )
    )

    # Regular resume folder
    possible_paths.append(
        os.path.join(
            "resumes",
            filename,
        )
    )

    for path in possible_paths:

        normalized_path = os.path.normpath(path)

        if os.path.exists(normalized_path):
            return normalized_path

    return None


# ============================================================
# GET RESUME BYTES
# ============================================================

def get_resume_bytes(candidate_id):
    """
    Return:
        file bytes
        filename
        MIME type
    """

    file_path = get_resume_file_path(candidate_id)

    if not file_path:
        return None, None, None

    try:

        with open(file_path, "rb") as file:
            file_bytes = file.read()

    except Exception:

        return None, None, None

    file_name = os.path.basename(file_path)

    extension = os.path.splitext(
        file_path
    )[1].lower()

    if extension == ".pdf":

        mime_type = "application/pdf"

    elif extension == ".docx":

        mime_type = (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )

    else:

        mime_type = "application/octet-stream"

    return (
        file_bytes,
        file_name,
        mime_type,
    )


# ============================================================
# CREATE ZIP
# ============================================================

def create_resume_zip(
    matches,
    extension_filter=None,
):
    """
    Create ZIP containing matched resumes.

    extension_filter:
        None    = PDF + DOCX
        .pdf    = PDF only
        .docx   = DOCX only
    """

    zip_buffer = io.BytesIO()

    added_files = set()

    with zipfile.ZipFile(
        zip_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as zip_file:

        for candidate in matches:

            candidate_id = candidate.get("id")

            if not candidate_id:
                continue

            file_path = get_resume_file_path(
                candidate_id
            )

            if not file_path:
                continue

            extension = os.path.splitext(
                file_path
            )[1].lower()

            if extension_filter:

                if extension != extension_filter:
                    continue

            real_path = os.path.abspath(
                file_path
            )

            if real_path in added_files:
                continue

            added_files.add(real_path)

            file_name = os.path.basename(
                file_path
            )

            zip_file.write(
                file_path,
                arcname=file_name,
            )

    zip_buffer.seek(0)

    return zip_buffer.getvalue()


# ============================================================
# COUNT AVAILABLE RESUMES
# ============================================================

def count_available_resumes(
    matches,
    extension_filter=None,
):

    count = 0

    checked_files = set()

    for candidate in matches:

        candidate_id = candidate.get("id")

        if not candidate_id:
            continue

        file_path = get_resume_file_path(
            candidate_id
        )

        if not file_path:
            continue

        extension = os.path.splitext(
            file_path
        )[1].lower()

        if extension_filter:

            if extension != extension_filter:
                continue

        real_path = os.path.abspath(
            file_path
        )

        if real_path in checked_files:
            continue

        checked_files.add(real_path)

        count += 1

    return count


# ============================================================
# SMALL HELPERS
# ============================================================

def display_skills(value):
    """
    Convert skills into safe plain text.

    No HTML is generated here.
    """

    if not value:
        return "None"

    if isinstance(
        value,
        (list, tuple, set),
    ):

        items = list(value)

    else:

        items = [
            item.strip()
            for item in str(value).split(",")
            if item.strip()
        ]

    if not items:
        return "None"

    return " • ".join(items[:12])


def _skill_list(value):
    """Convert matched/missing skill values into a normalized list."""
    if not value:
        return []

    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = re.split(r"[,;\\n•|]+", str(value))

    skills = []
    seen = set()

    for item in items:
        skill = str(item).strip()
        if not skill or skill.lower() in {
            "none", "not available", "n/a", "no matching skills detected"
        }:
            continue

        normalized = skill.casefold()
        if normalized not in seen:
            seen.add(normalized)
            skills.append(skill)

    return skills


def get_skill_match(candidate):
    """
    Return (percentage, matched_count, total_identified_skills).

    The percentage uses the matcher's matched_skills and missing_skills.
    """
    matched = _skill_list(candidate.get("matched_skills"))
    missing = _skill_list(candidate.get("missing_skills"))

    matched_keys = {skill.casefold() for skill in matched}
    missing_keys = {skill.casefold() for skill in missing}
    total = len(matched_keys | missing_keys)

    if total == 0:
        return 0, 0, 0

    matched_count = len(matched_keys)
    percentage = round(matched_count / total * 100)
    return percentage, matched_count, total


def clean_value(
    value,
    default="Not available",
):

    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    return value


# ============================================================
# SCORE HELPER
# ============================================================

def get_score(candidate):
    """
    Safely return candidate match score as float.
    """

    try:

        score = float(
            candidate.get(
                "score",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        score = 0.0

    return score


# ============================================================
# FILTER MATCHES ABOVE 50%
# ============================================================

def get_qualified_matches(matches):
    """
    Only candidates with match score > 50% are qualified.

    50% itself is NOT included.
    """

    if not matches:
        return []

    qualified_matches = []

    for candidate in matches:

        score = get_score(candidate)

        if score > 50:

            qualified_matches.append(
                candidate
            )

    # Highest match score first
    qualified_matches.sort(
        key=get_score,
        reverse=True,
    )

    return qualified_matches


def render_outlook_sync_report():
    report = st.session_state.outlook_sync_report

    if not report:
        return

    with st.expander("View Outlook sync report"):
        report_col1, report_col2, report_col3 = st.columns(3)

        with report_col1:
            st.metric("Emails scanned", report.get("emails_scanned", 0))
            st.metric("Downloaded", report.get("documents_downloaded", 0))

        with report_col2:
            st.metric(
                "Attachments checked",
                report.get("attachments_checked", 0),
            )
            st.metric("Already processed", report.get("already_processed", 0))

        with report_col3:
            st.metric("New resumes", report.get("resumes_saved", 0))
            st.metric("Non-resumes rejected", report.get("rejected_count", 0))


# ============================================================
# APP HEADER
# ============================================================

st.markdown(
    """
    <div class="creative-hero">
        <div class="hero-row">
            <div>
                <span class="hero-kicker">YOUR RECRUITING WORKSPACE</span>
                <h1>Find your next great hire, <span class="hero-accent">with clarity.</span></h1>
                <p>
                    Bring resumes and role requirements together. See your
                    strongest matches, understand the fit, and build a shortlist
                    with confidence.
                </p>
                <div class="hero-flow">
                    <span class="hero-flow-item"><span class="flow-number">01</span> Import resumes</span>
                    <span class="hero-flow-item"><span class="flow-number">02</span> Add the role</span>
                    <span class="hero-flow-item"><span class="flow-number">03</span> Review your shortlist</span>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()


# ============================================================
# WORKFLOW SECTIONS
# ============================================================

workflow_col, tab_results = st.columns([0.72, 1.83], gap="large")
sync_complete = st.session_state.outlook_sync_report is not None

with workflow_col.container(key="sticky-workflow-panel"):

    with st.container(key="job-openings-panel"):
        heading_col, new_col = st.columns([2, 1])

        with heading_col:
            st.markdown(
                '<div class="job-openings-heading">JOB OPENINGS</div>',
                unsafe_allow_html=True,
            )

        with new_col:
            st.button(
                "+ New",
                key="new_job_button",
                on_click=reset_job_opening,
                use_container_width=True,
            )

        if st.session_state.job_form_open:
            job_title = st.text_input(
                "Job title",
                placeholder="e.g. Senior Frontend Engineer",
                key="job_title_input",
            )

            job_description = st.text_area(
                "Job description",
                height=180,
                placeholder="Paste the job description...",
                key="job_description_input",
            )

            save_job_clicked = st.button(
                "Search",
                type="primary",
                use_container_width=True,
                key="save_job_button",
                disabled=not sync_complete,
            )

            if save_job_clicked:

                if not job_title.strip():
                    st.warning("Add a job title before saving this opening.")

                elif not job_description.strip():
                    st.warning("Paste the job description before saving this opening.")

                else:
                    with st.spinner("Saving the job and matching candidates..."):
                        try:
                            matches = match_candidates(job_description)
                            st.session_state.candidate_matches = matches
                            st.session_state.candidate_matches_job = job_description
                            st.session_state.candidate_matches_job_title = (
                                job_title.strip()
                            )
                            st.session_state.job_form_open = False

                            qualified_count = len(
                                get_qualified_matches(matches)
                            )

                            st.success(
                                f"Job saved — {qualified_count} candidate(s) "
                                f"above 50% match."
                            )

                        except Exception as error:
                            st.session_state.candidate_matches = None
                            st.session_state.candidate_matches_job = None
                            st.session_state.candidate_matches_job_title = None
                            st.error("Could not save the job and match candidates.")
                            st.code(str(error))

        elif st.session_state.candidate_matches_job_title:
            st.button(
                st.session_state.candidate_matches_job_title,
                key="saved_job_opening_button",
                on_click=edit_job_opening,
                use_container_width=True,
            )

    with st.container(border=True):
        st.markdown("#### Outlook sync")
        st.caption(
            "Connect Outlook to screen resumes from your “Resumes” folder."
        )

        sync_clicked = st.button(
            "Connect Outlook",
            type="secondary",
            use_container_width=True,
            key="sync_outlook_button",
        )

        if sync_clicked:

            def show_device_code(message):
                st.warning("Microsoft Outlook sign-in is required.")
                st.write("Complete Microsoft authentication:")
                st.code(message)

            with st.spinner("Checking Outlook for resumes..."):
                try:
                    report = sync_outlook_resumes(
                        on_device_code=show_device_code
                    )
                    st.session_state.outlook_sync_report = report
                    st.session_state.outlook_sync_error = None
                except Exception as error:
                    st.session_state.outlook_sync_report = None
                    st.session_state.outlook_sync_error = str(error)

        if st.session_state.outlook_sync_error:
            st.error("Outlook sync failed.")
            st.code(st.session_state.outlook_sync_error)
        elif sync_complete:
            st.success("Outlook sync completed.")
        else:
            st.caption("Sync resumes before saving a job to find candidates.")

    render_outlook_sync_report()


# ============================================================
# STEP 3 — RESULTS
# ============================================================

with tab_results.container(key="results-scroll-panel"):

    st.header("Results")

    matches = (
        st.session_state.candidate_matches
    )

    saved_job_description = (
        st.session_state.candidate_matches_job
    )

    current_job_description = (
        st.session_state.get(
            "job_description_input",
            "",
        )
    )
    current_job_title = st.session_state.get(
        "job_title_input",
        "",
    ).strip()

    # --------------------------------------------------------
    # NO RUN
    # --------------------------------------------------------

    if matches is None:

        st.info(
            "Create a job opening on the left and select **Search** "
            "to see matching candidates here."
        )

    # --------------------------------------------------------
    # JOB CHANGED
    # --------------------------------------------------------

    elif (
        saved_job_description
        != current_job_description
        or st.session_state.candidate_matches_job_title
        != current_job_title
    ):

        st.warning(
            "The job opening has changed. Select **Search** "
            "to refresh the candidate matches."
        )

    else:
        if current_job_title:
            st.caption(f"JOB OPENING  ·  {current_job_title}")

        # ====================================================
        # IMPORTANT:
        # ONLY SHOW CANDIDATES ABOVE 50%
        # ====================================================

        qualified_matches = get_qualified_matches(
            matches
        )

        # ----------------------------------------------------
        # NO QUALIFIED CANDIDATES
        # ----------------------------------------------------

        if not qualified_matches:

            st.info(
                "No candidates found with a match score "
                "above 50%."
            )

        else:

            # =================================================
            # SUMMARY METRICS
            # =================================================

            average_score = (
                sum(
                    get_score(candidate)
                    for candidate in qualified_matches
                )
                / len(qualified_matches)
            )

            top_score = get_score(
                qualified_matches[0]
            )

            result_col1, result_col2, result_col3 = (
                st.columns(3)
            )

            with result_col1:

                st.metric(
                    "Qualified candidates",
                    len(qualified_matches),
                )

            with result_col2:

                st.metric(
                    "Average match",
                    f"{average_score:.0f}%",
                )

            with result_col3:

                st.metric(
                    "Best match",
                    f"{top_score:.0f}%",
                )

            st.write("")

            # =================================================
            # RESULTS TABLE
            # =================================================

            st.subheader(
                "Candidate overview"
            )

            result_rows = []

            for candidate in qualified_matches:

                result_rows.append(
                    {
                        "Candidate": clean_value(
                            candidate.get("name"),
                            "Unnamed Candidate",
                        ),

                        "Email": clean_value(
                            candidate.get("email"),
                            "",
                        ),

                        "Experience": clean_value(
                            candidate.get("experience"),
                            "",
                        ),

                        "Match": (
                            f"{get_score(candidate):.0f}%"
                        ),

                        "Skill Match": (
                            f"{get_skill_match(candidate)[0]}%"
                            if get_skill_match(candidate)[2] > 0
                            else "N/A"
                        ),

                        "Matching Skills": display_skills(
                            candidate.get(
                                "matched_skills",
                                "",
                            )
                        ),

                        "Skills to Verify": display_skills(
                            candidate.get(
                                "missing_skills",
                                "",
                            )
                        ),
                    }
                )

            result_dataframe = pd.DataFrame(
                result_rows
            )

            st.dataframe(
                result_dataframe,
                hide_index=True,
                use_container_width=True,
                column_config={

                    "Candidate": st.column_config.TextColumn(
                        "Candidate",
                        width="medium",
                    ),

                    "Email": st.column_config.TextColumn(
                        "Email",
                        width="large",
                    ),

                    "Experience": st.column_config.TextColumn(
                        "Experience",
                        width="medium",
                    ),

                    "Match": st.column_config.TextColumn(
                        "Match",
                        width="small",
                    ),

                    "Skill Match": st.column_config.TextColumn(
                        "Skill Match",
                        help="Percentage of identified job skills matched.",
                        width="small",
                    ),

                    "Matching Skills": st.column_config.TextColumn(
                        "Matching Skills",
                        width="large",
                    ),

                    "Skills to Verify": st.column_config.TextColumn(
                        "Skills to Verify",
                        width="large",
                    ),
                },
            )

            st.write("")

            # =================================================
            # CANDIDATE DETAILS
            # =================================================

            st.subheader(
                "Candidate details"
            )

            st.caption(
                f"Showing {len(qualified_matches)} candidate(s) "
                f"with a match score above 50%."
            )

            # IMPORTANT:
            # We loop through qualified_matches,
            # NOT the original matches list.

            for index, candidate in enumerate(
                qualified_matches
            ):

                candidate_name = clean_value(
                    candidate.get("name"),
                    "Unnamed Candidate",
                )

                candidate_email = clean_value(
                    candidate.get("email"),
                    "Email not available",
                )

                score = get_score(
                    candidate
                )

                experience = clean_value(
                    candidate.get("experience"),
                    "Not available",
                )

                matched_skills = display_skills(
                    candidate.get(
                        "matched_skills",
                        "",
                    )
                )

                missing_skills = display_skills(
                    candidate.get(
                        "missing_skills",
                        "",
                    )
                )

                candidate_id = candidate.get(
                    "id"
                )

                # --------------------------------------------
                # GET RESUME
                # --------------------------------------------

                if candidate_id:

                    (
                        file_bytes,
                        file_name,
                        mime_type,
                    ) = get_resume_bytes(
                        candidate_id
                    )

                else:

                    file_bytes = None
                    file_name = None
                    mime_type = None

                # --------------------------------------------
                # CANDIDATE CARD
                # --------------------------------------------

                with st.container(
                    border=True
                ):

                    header_col1, header_col2, header_col3 = (
                        st.columns(
                            [4, 1, 1],
                            vertical_alignment="center",
                        )
                    )

                    with header_col1:

                        st.markdown(
                            f"### {candidate_name}"
                        )

                        st.caption(
                            candidate_email
                        )

                    with header_col2:

                        st.metric(
                            "Overall Match",
                            f"{score:.0f}%",
                        )

                    skill_percentage, matched_count, total_skills = (
                        get_skill_match(candidate)
                    )

                    with header_col3:

                        st.metric(
                            "Skill Match",
                            (
                                f"{skill_percentage}%"
                                if total_skills
                                else "N/A"
                            ),
                        )

                    if total_skills:
                        st.caption(
                            f"{matched_count} of {total_skills} "
                            f"identified skills matched"
                        )
                    else:
                        st.caption(
                            "Skill match percentage unavailable: "
                            "no matched/missing skill data was returned."
                        )

                    st.divider()

                    # ----------------------------------------
                    # EXPERIENCE
                    # ----------------------------------------

                    st.markdown(
                        "**Experience**"
                    )

                    st.write(
                        experience
                    )

                    skill_col1, skill_col2 = st.columns(2)

                    with skill_col1:
                        st.markdown("**Matching skills**")
                        if matched_skills == "None":
                            st.caption("No matching skills detected.")
                        else:
                            st.write(matched_skills)

                    with skill_col2:
                        st.markdown("**Skills to verify**")
                        if missing_skills == "None":
                            st.caption("No missing skills detected.")
                        else:
                            st.write(missing_skills)

                    st.divider()

                    # ----------------------------------------
                    # DOWNLOAD
                    # ----------------------------------------

                    if file_bytes:

                        st.download_button(
                            label=(
                                f"⬇️ Download "
                                f"{candidate_name}'s resume"
                            ),

                            data=file_bytes,

                            file_name=file_name,

                            mime=mime_type,

                            use_container_width=True,

                            key=(
                                f"individual_resume_"
                                f"{candidate_id}_"
                                f"{index}"
                            ),
                        )

                    else:

                        st.warning(
                            f"Resume file is not currently "
                            f"available for {candidate_name}."
                        )

            # =================================================
            # BULK DOWNLOADS
            # =================================================

            st.divider()

            st.subheader(
                "Download matched resumes"
            )

            st.caption(
                "Only resumes belonging to candidates above "
                "50% match are included."
            )

            all_count = count_available_resumes(
                qualified_matches
            )

            pdf_count = count_available_resumes(
                qualified_matches,
                extension_filter=".pdf",
            )

            docx_count = count_available_resumes(
                qualified_matches,
                extension_filter=".docx",
            )

            download_col1, download_col2, download_col3 = (
                st.columns(3)
            )

            # =================================================
            # ALL
            # =================================================

            with download_col1:

                if all_count > 0:

                    all_zip = create_resume_zip(
                        qualified_matches
                    )

                    st.download_button(
                        label=(
                            f"📦 All resumes "
                            f"({all_count})"
                        ),

                        data=all_zip,

                        file_name=(
                            "matched_resumes.zip"
                        ),

                        mime="application/zip",

                        type="primary",

                        use_container_width=True,

                        key="download_all_resumes",
                    )

                else:

                    st.button(
                        "📦 All resumes (0)",
                        disabled=True,
                        use_container_width=True,
                        key="download_all_disabled",
                    )

            # =================================================
            # PDF
            # =================================================

            with download_col2:

                if pdf_count > 0:

                    pdf_zip = create_resume_zip(
                        qualified_matches,
                        extension_filter=".pdf",
                    )

                    st.download_button(
                        label=(
                            f"📄 PDF resumes "
                            f"({pdf_count})"
                        ),

                        data=pdf_zip,

                        file_name=(
                            "matched_pdf_resumes.zip"
                        ),

                        mime="application/zip",

                        use_container_width=True,

                        key="download_pdf_resumes",
                    )

                else:

                    st.button(
                        "📄 PDF resumes (0)",
                        disabled=True,
                        use_container_width=True,
                        key="download_pdf_disabled",
                    )

            # =================================================
            # DOCX
            # =================================================

            with download_col3:

                if docx_count > 0:

                    docx_zip = create_resume_zip(
                        qualified_matches,
                        extension_filter=".docx",
                    )

                    st.download_button(
                        label=(
                            f"📝 DOCX resumes "
                            f"({docx_count})"
                        ),

                        data=docx_zip,

                        file_name=(
                            "matched_docx_resumes.zip"
                        ),

                        mime="application/zip",

                        use_container_width=True,

                        key="download_docx_resumes",
                    )

                else:

                    st.button(
                        "📝 DOCX resumes (0)",
                        disabled=True,
                        use_container_width=True,
                        key="download_docx_disabled",
                    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Resume Matcher · Outlook Import · Candidate Matching"
)