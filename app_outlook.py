import streamlit as st
import pandas as pd
import os
import io
import zipfile

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
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "outlook_sync_report": None,
    "outlook_sync_error": None,
    "candidate_matches": None,
    "candidate_matches_job": None,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ======================================================
       MAIN APPLICATION
       ====================================================== */

    .stApp {
        background-color: #f7f8fc;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }


    /* ======================================================
       SIDEBAR
       ====================================================== */

    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }

    section[data-testid="stSidebar"] * {
        color: #e5e7eb;
    }

    section[data-testid="stSidebar"] .stButton button {
        background-color: #1f2937;
        border: 1px solid #374151;
        color: #f9fafb;
    }


    /* ======================================================
       HEADINGS
       ====================================================== */

    h1 {
        letter-spacing: -0.8px;
    }

    h2 {
        letter-spacing: -0.4px;
    }

    h3 {
        letter-spacing: -0.2px;
    }


    /* ======================================================
       CONTAINERS
       ====================================================== */

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px;
    }


    /* ======================================================
       BUTTONS
       ====================================================== */

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 9px;
        font-weight: 650;
        min-height: 42px;
    }

    button[data-baseweb="tab"] {
        font-weight: 650;
    }


    /* ======================================================
       INPUTS
       ====================================================== */

    textarea,
    input {
        border-radius: 9px !important;
    }


    /* ======================================================
       DATAFRAME
       ====================================================== */

    div[data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }


    /* ======================================================
       METRICS
       ====================================================== */

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: 0 4px 16px rgba(17, 24, 39, 0.04);
    }

    div[data-testid="stMetricLabel"] {
        color: #6b7280;
    }

    div[data-testid="stMetricValue"] {
        color: #111827;
    }


    /* ======================================================
       TABS
       ====================================================== */

    button[data-baseweb="tab"] {
        padding-left: 16px;
        padding-right: 16px;
    }


    /* ======================================================
       HIDE STREAMLIT DEFAULT MENU / FOOTER
       ====================================================== */

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }


    /* ======================================================
       MOBILE
       ====================================================== */

    @media (max-width: 900px) {

        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
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


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## 📄 Resume Matcher"
    )

    st.caption(
        "A simple workspace for sourcing, matching "
        "and downloading candidates."
    )

    st.divider()

    st.markdown(
        "### Workflow"
    )

    st.markdown(
        """
        **01** 📥 Import resumes from Outlook

        **02** 🎯 Add job description

        **03** 📊 Compare candidates

        **04** ⬇️ Download resumes
        """
    )

    st.divider()

    st.info(
        "💡 Tip: Sync Outlook before matching candidates."
    )


# ============================================================
# HERO
# ============================================================

with st.container(border=True):

    st.caption(
        "🟠 AI-ASSISTED RECRUITING WORKSPACE"
    )

    st.title(
        "Find the right candidate faster."
    )

    st.write(
        "Import resumes from Outlook, paste a job description, "
        "and quickly identify candidates with the strongest "
        "skill match."
    )


# ============================================================
# MAIN TABS
# ============================================================

tab_import, tab_match, tab_results = st.tabs(
    [
        "📥 Resume Sources",
        "🎯 Match Candidates",
        "📊 Results",
    ]
)


# ============================================================
# TAB 1 — RESUME SOURCES
# ============================================================

with tab_import:

    st.header(
        "Resume Sources"
    )

    st.caption(
        "Bring candidates into your resume database from Outlook."
    )

    with st.container(border=True):

        st.subheader(
            "📥 Outlook Resume Sync"
        )

        st.write(
            "Check Outlook for job-related emails and process "
            "supported PDF/DOCX resume attachments."
        )

    st.write("")

    sync_clicked = st.button(
        "🔄 Sync Outlook",
        type="primary",
        use_container_width=True,
        key="sync_outlook_button",
    )

    if sync_clicked:

        def show_device_code(message):

            st.warning(
                "Microsoft Outlook sign-in is required."
            )

            st.write(
                "Complete Microsoft authentication:"
            )

            st.code(message)

        with st.spinner(
            "Checking Outlook for resumes..."
        ):

            try:

                report = sync_outlook_resumes(
                    on_device_code=show_device_code
                )

                st.session_state.outlook_sync_report = (
                    report
                )

                st.session_state.outlook_sync_error = (
                    None
                )

            except Exception as error:

                st.session_state.outlook_sync_report = (
                    None
                )

                st.session_state.outlook_sync_error = (
                    str(error)
                )

    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

    if st.session_state.outlook_sync_error:

        st.error(
            "Outlook sync failed."
        )

        st.code(
            st.session_state.outlook_sync_error
        )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    if st.session_state.outlook_sync_report:

        report = (
            st.session_state.outlook_sync_report
        )

        st.success(
            "Outlook sync completed successfully."
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Emails scanned",
                report.get(
                    "emails_scanned",
                    0,
                ),
            )

        with col2:

            st.metric(
                "Attachments checked",
                report.get(
                    "attachments_checked",
                    0,
                ),
            )

        with col3:

            st.metric(
                "New resumes",
                report.get(
                    "resumes_saved",
                    0,
                ),
            )

        st.write("")

        with st.expander(
            "View Outlook sync details"
        ):

            detail_col1, detail_col2, detail_col3 = (
                st.columns(3)
            )

            with detail_col1:

                st.metric(
                    "Downloaded",
                    report.get(
                        "documents_downloaded",
                        0,
                    ),
                )

            with detail_col2:

                st.metric(
                    "Already processed",
                    report.get(
                        "already_processed",
                        0,
                    ),
                )

            with detail_col3:

                st.metric(
                    "Non-resumes rejected",
                    report.get(
                        "rejected_count",
                        0,
                    ),
                )


# ============================================================
# TAB 2 — MATCH CANDIDATES
# ============================================================

with tab_match:

    st.header(
        "Match Candidates"
    )

    st.caption(
        "Paste the role requirements below to compare them "
        "against the resumes in your database."
    )

    job_description = st.text_area(
        "Job Description",
        height=260,
        placeholder=(
            "Example:\n\n"
            "We are looking for a Frontend Developer with "
            "experience in React.js, JavaScript, HTML, CSS, "
            "Tailwind CSS and Git.\n\n"
            "Add the important skills, tools, experience and "
            "responsibilities from the actual job description."
        ),
        key="job_description_input",
    )

    st.caption(
        "💡 Better job descriptions usually produce more useful "
        "skill matching."
    )

    match_clicked = st.button(
        "🔎 Find Matching Candidates",
        type="primary",
        use_container_width=True,
        key="match_candidates_button",
    )

    if match_clicked:

        if not job_description.strip():

            st.warning(
                "Please paste a job description first."
            )

        else:

            with st.spinner(
                "Comparing candidates with the job description..."
            ):

                try:

                    matches = match_candidates(
                        job_description
                    )

                    st.session_state.candidate_matches = (
                        matches
                    )

                    st.session_state.candidate_matches_job = (
                        job_description
                    )

                    # Count only qualified candidates
                    qualified_count = len(
                        get_qualified_matches(matches)
                    )

                    st.success(
                        f"Matching completed — "
                        f"{qualified_count} candidate(s) "
                        f"above 50% match."
                    )

                except Exception as error:

                    st.session_state.candidate_matches = (
                        None
                    )

                    st.session_state.candidate_matches_job = (
                        None
                    )

                    st.error(
                        "Could not match candidates."
                    )

                    st.code(
                        str(error)
                    )


# ============================================================
# TAB 3 — RESULTS
# ============================================================

with tab_results:

    st.header(
        "Matching Results"
    )

    st.caption(
        "Only candidates with a match score above 50% "
        "are displayed."
    )

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

    # --------------------------------------------------------
    # NO RUN
    # --------------------------------------------------------

    if matches is None:

        st.info(
            "No matching run yet. Go to **Match Candidates**, "
            "add a job description, and click "
            "**Find Matching Candidates**."
        )

    # --------------------------------------------------------
    # JOB CHANGED
    # --------------------------------------------------------

    elif (
        saved_job_description
        != current_job_description
    ):

        st.warning(
            "The job description has changed. Click "
            "**Find Matching Candidates** to refresh the results."
        )

    else:

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

                    header_col1, header_col2 = (
                        st.columns(
                            [5, 1],
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
                            "Match",
                            f"{score:.0f}%",
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

                    # ----------------------------------------
                    # SKILLS
                    # ----------------------------------------

                    skill_col1, skill_col2 = st.columns(2)

                    with skill_col1:

                        st.markdown(
                            "**Matching skills**"
                        )

                        if matched_skills == "None":

                            st.caption(
                                "No matching skills detected."
                            )

                        else:

                            st.write(
                                matched_skills
                            )

                    with skill_col2:

                        st.markdown(
                            "**Skills to verify**"
                        )

                        if missing_skills == "None":

                            st.caption(
                                "No missing skills detected."
                            )

                        else:

                            st.write(
                                missing_skills
                            )

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