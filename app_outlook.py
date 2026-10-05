import streamlit as st
import pandas as pd
import os
import io
import zipfile

from match_candidates import match_candidates
from outlook_sync import sync_outlook_resumes
from database.db import get_connection
from folder_sync import scan_resume_folder


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Resume Matcher",
    page_icon="📄",
    layout="wide"
)


# ============================================================
# SESSION STATE
# ============================================================

if "outlook_sync_report" not in st.session_state:
    st.session_state.outlook_sync_report = None

if "outlook_sync_error" not in st.session_state:
    st.session_state.outlook_sync_error = None

if "candidate_matches" not in st.session_state:
    st.session_state.candidate_matches = None

if "candidate_matches_job" not in st.session_state:
    st.session_state.candidate_matches_job = None


# ============================================================
# RESUME FILE FUNCTIONS
# ============================================================

def get_resume_file_path(candidate_id):
    """
    Get the stored resume file path for a candidate
    from the database.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT resume_file
        FROM candidates
        WHERE id = ?
        """,
        (candidate_id,)
    )

    row = cursor.fetchone()

    connection.close()

    if not row:
        return None

    resume_file = row["resume_file"]

    if not resume_file:
        return None

    # If database already contains a full path
    if os.path.isabs(resume_file):
        file_path = resume_file

    # If database contains only filename
    else:
        file_path = os.path.join(
            "email_resumes",
            os.path.basename(resume_file)
        )

    if os.path.exists(file_path):
        return file_path

    return None


# ============================================================
# GET INDIVIDUAL RESUME
# ============================================================

def get_resume_bytes(candidate_id):

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
        mime_type
    )


# ============================================================
# CREATE ZIP OF MATCHED RESUMES
# ============================================================

def create_resume_zip(
    matches,
    extension_filter=None
):
    """
    Create a ZIP file containing matched resumes.

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
        zipfile.ZIP_DEFLATED
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

            # Apply PDF/DOCX filter
            if extension_filter:

                if extension != extension_filter:
                    continue

            # Avoid duplicate physical files
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
                arcname=file_name
            )

    zip_buffer.seek(0)

    return zip_buffer.getvalue()


# ============================================================
# COUNT AVAILABLE RESUMES
# ============================================================

def count_available_resumes(
    matches,
    extension_filter=None
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
# HEADER
# ============================================================

st.title("📄 Resume Matcher")

st.caption(
    "Read job-related resume emails from Outlook, "
    "extract candidate information, and match candidates "
    "against a job description."
)


# ============================================================
# OUTLOOK SECTION
# ============================================================

st.subheader("📥 Outlook Resume Sync")

st.write(
    "The application checks emails received from yesterday "
    "onward and processes PDF/DOCX resume attachments."
)


# ============================================================
# SYNC BUTTON
# ============================================================

sync_clicked = st.button(
    "🔄 Sync Outlook",
    type="primary"
)


# ============================================================
# RUN SYNC
# ============================================================

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

            st.session_state.outlook_sync_report = report

            st.session_state.outlook_sync_error = None

        except Exception as error:

            st.session_state.outlook_sync_report = None

            st.session_state.outlook_sync_error = (
                str(error)
            )


# ============================================================
# ERROR
# ============================================================

if st.session_state.outlook_sync_error:

    st.error(
        "❌ Outlook sync failed:\n\n"
        + st.session_state.outlook_sync_error
    )


# ============================================================
# SYNC REPORT
# ============================================================

if st.session_state.outlook_sync_report:

    report = st.session_state.outlook_sync_report

    st.success(
        "✅ Outlook sync completed."
    )


    # --------------------------------------------------------
    # MAIN METRICS
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)


    col1.metric(
        "Emails Scanned",
        report.get(
            "emails_scanned",
            0
        )
    )


    col2.metric(
        "PDF/DOCX Attachments",
        report.get(
            "attachments_checked",
            0
        )
    )


    col3.metric(
        "Resumes Saved",
        report.get(
            "resumes_saved",
            0
        )
    )


    # --------------------------------------------------------
    # SECONDARY INFORMATION
    # --------------------------------------------------------

    st.subheader("📊 Sync Details")

    detail_col1, detail_col2, detail_col3 = st.columns(3)


    detail_col1.metric(
        "Documents Downloaded",
        report.get(
            "documents_downloaded",
            0
        )
    )


    detail_col2.metric(
        "Already Processed",
        report.get(
            "already_processed",
            0
        )
    )


    detail_col3.metric(
        "Non-Resumes Rejected",
        report.get(
            "rejected_count",
            0
        )
    )

# ============================================================
# LOCAL FOLDER RESUME SCAN
# ============================================================

st.subheader("📁 Scan Resume Folder")

st.write(
    "Select a folder containing PDF/DOCX resumes. "
    "The resumes will be parsed and added to the database."
)

folder_path = st.text_input(
    "Resume Folder Path",
    value=r"D:\Manisha\resume_matcher\resumes",
    help="Enter the full path of the folder containing resumes."
)

scan_folder_clicked = st.button(
    "📂 Scan Resume Folder",
    type="primary"
)


# ============================================================
# RUN FOLDER SCAN
# ============================================================

if scan_folder_clicked:

    if not folder_path.strip():

        st.warning(
            "⚠️ Please enter a folder path."
        )

    else:

        with st.spinner(
            "Scanning resumes..."
        ):

            try:

                folder_report = scan_resume_folder(
                    folder_path.strip()
                )

                st.success(
                    "✅ Folder scan completed."
                )

                col1, col2, col3, col4 = st.columns(4)

                col1.metric(
                    "Files Checked",
                    folder_report["files_checked"]
                )

                col2.metric(
                    "New Resumes",
                    folder_report["resumes_saved"]
                )

                col3.metric(
                    "Already Processed",
                    folder_report["already_processed"]
                )

                col4.metric(
                    "Rejected",
                    folder_report["rejected_count"]
                )

            except Exception as error:

                st.error(
                    "❌ Folder scan failed:\n\n"
                    + str(error)
                )

# ============================================================
# DIVIDER
# ============================================================

st.divider()


# ============================================================
# MATCHING
# ============================================================

st.subheader(
    "🎯 Match Candidates"
)

st.write(
    "Paste a job description and compare it "
    "against the resumes stored in the database."
)


# ============================================================
# JOB DESCRIPTION
# ============================================================

job_description = st.text_area(
    "Job Description",
    height=220,
    placeholder=(
        "Example:\n\n"
        "We are looking for a Frontend Developer "
        "with experience in React.js, JavaScript, "
        "HTML, CSS, Tailwind CSS and Git."
    )
)


# ============================================================
# MATCH BUTTON
# ============================================================

match_clicked = st.button(
    "🔎 Find Matching Candidates",
    type="primary"
)


# ============================================================
# MATCH CANDIDATES
# ============================================================

if match_clicked:

    if not job_description.strip():

        st.warning(
            "⚠️ Please paste a job description first."
        )

    else:

        with st.spinner(
            "Matching candidates..."
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

            except Exception as error:

                st.session_state.candidate_matches = None

                st.session_state.candidate_matches_job = None

                st.error(
                    "❌ Could not match candidates:\n\n"
                    + str(error)
                )


# ============================================================
# DISPLAY RESULTS
# ============================================================

if st.session_state.candidate_matches is not None:

    matches = (
        st.session_state.candidate_matches
    )

    saved_job_description = (
        st.session_state.candidate_matches_job
    )


    if (
        saved_job_description
        != job_description
    ):

        st.info(
            "ℹ️ The job description changed. "
            "Click 'Find Matching Candidates' "
            "to refresh the results."
        )


    else:

        st.markdown(
            "### 📊 Matching Results"
        )


        # ----------------------------------------------------
        # NO MATCHES
        # ----------------------------------------------------

        if not matches:

            st.info(
                "No candidates are currently available. "
                "Sync Outlook first."
            )


        # ----------------------------------------------------
        # MATCHES FOUND
        # ----------------------------------------------------

        else:

            # ------------------------------------------------
            # MATCH STATISTICS
            # ------------------------------------------------

            average_score = (
                sum(
                    candidate["score"]
                    for candidate in matches
                )
                / len(matches)
            )


            top_score = matches[0]["score"]


            result_col1, result_col2, result_col3 = (
                st.columns(3)
            )


            result_col1.metric(
                "Candidates",
                len(matches)
            )


            result_col2.metric(
                "Average Match",
                f"{average_score:.0f}%"
            )


            result_col3.metric(
                "Top Match",
                f"{top_score:.0f}%"
            )


            # ------------------------------------------------
            # RESULTS TABLE
            # ------------------------------------------------

            result_rows = []


            for candidate in matches:

                result_rows.append(
                    {
                        "Candidate": (
                            candidate.get(
                                "name"
                            )
                            or "Unnamed Candidate"
                        ),

                        "Email": (
                            candidate.get(
                                "email",
                                ""
                            )
                        ),

                        "Experience": (
                            candidate.get(
                                "experience",
                                ""
                            )
                        ),

                        "Match": (
                            f"{candidate['score']:.0f}%"
                        ),

                        "Matching Skills": (
                            candidate.get(
                                "matched_skills",
                                ""
                            )
                        ),

                        "Skills to Verify": (
                            candidate.get(
                                "missing_skills",
                                ""
                            )
                        )
                    }
                )


            result_dataframe = pd.DataFrame(
                result_rows
            )


            st.dataframe(
                result_dataframe,
                hide_index=True,
                use_container_width=True
            )


            # =================================================
            # DOWNLOAD SECTION
            # =================================================

            st.divider()

            st.markdown(
                "### 📥 Download Matched Resumes"
            )

            st.write(
                "Download the resumes of the candidates "
                "matching this job description."
            )


            # -------------------------------------------------
            # COUNT AVAILABLE FILES
            # -------------------------------------------------

            all_count = count_available_resumes(
                matches
            )

            pdf_count = count_available_resumes(
                matches,
                extension_filter=".pdf"
            )

            docx_count = count_available_resumes(
                matches,
                extension_filter=".docx"
            )


            # -------------------------------------------------
            # DOWNLOAD ALL
            # -------------------------------------------------

            if all_count > 0:

                all_zip = create_resume_zip(
                    matches
                )

                st.download_button(
                    label=(
                        f"📦 Download All Matched "
                        f"Resumes ({all_count})"
                    ),

                    data=all_zip,

                    file_name=(
                        "matched_resumes.zip"
                    ),

                    mime="application/zip",

                    type="primary",

                    use_container_width=True,

                    key="download_all_resumes"
                )

                st.caption(
                    "Contains all matched PDF and DOCX resumes."
                )

            else:

                st.warning(
                    "No resume files are available "
                    "for download."
                )


            # -------------------------------------------------
            # PDF / DOCX DOWNLOAD
            # -------------------------------------------------

            download_col1, download_col2 = (
                st.columns(2)
            )


            # -------------------------------------------------
            # PDF DOWNLOAD
            # -------------------------------------------------

            with download_col1:

                if pdf_count > 0:

                    pdf_zip = create_resume_zip(
                        matches,
                        extension_filter=".pdf"
                    )

                    st.download_button(
                        label=(
                            f"📄 Download PDF Resumes "
                            f"({pdf_count})"
                        ),

                        data=pdf_zip,

                        file_name=(
                            "matched_pdf_resumes.zip"
                        ),

                        mime="application/zip",

                        use_container_width=True,

                        key="download_pdf_resumes"
                    )

                else:

                    st.info(
                        "No PDF resumes found."
                    )


            # -------------------------------------------------
            # DOCX DOWNLOAD
            # -------------------------------------------------

            with download_col2:

                if docx_count > 0:

                    docx_zip = create_resume_zip(
                        matches,
                        extension_filter=".docx"
                    )

                    st.download_button(
                        label=(
                            f"📝 Download DOCX Resumes "
                            f"({docx_count})"
                        ),

                        data=docx_zip,

                        file_name=(
                            "matched_docx_resumes.zip"
                        ),

                        mime="application/zip",

                        use_container_width=True,

                        key="download_docx_resumes"
                    )

                else:

                    st.info(
                        "No DOCX resumes found."
                    )


            # =================================================
            # INDIVIDUAL RESUME DOWNLOAD
            # =================================================

            st.markdown(
                "### 📄 Individual Resumes"
            )

            st.caption(
                "Download a specific candidate's resume."
            )


            for index, candidate in enumerate(
                matches
            ):

                candidate_id = candidate.get(
                    "id"
                )

                candidate_name = (
                    candidate.get(
                        "name"
                    )
                    or "Unnamed Candidate"
                )


                file_bytes, file_name, mime_type = (
                    get_resume_bytes(
                        candidate_id
                    )
                )


                if file_bytes:

                    individual_col1, individual_col2, individual_col3 = (
                        st.columns([3, 4, 1])
                    )


                    with individual_col1:

                        st.write(
                            f"**{candidate_name}**"
                        )


                    with individual_col2:

                        st.caption(
                            file_name
                        )


                    with individual_col3:

                        st.download_button(
                            label="⬇️ Download",

                            data=file_bytes,

                            file_name=file_name,

                            mime=mime_type,

                            key=(
                                f"download_resume_"
                                f"{candidate_id}_"
                                f"{index}"
                            )
                        )

                else:

                    st.warning(
                        f"Resume file not found for "
                        f"{candidate_name}."
                    )