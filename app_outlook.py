import streamlit as st
import pandas as pd

from match_candidates import match_candidates
from outlook_sync import sync_outlook_resumes


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

            # Save returned report
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


        if not matches:

            st.info(
                "No candidates are currently available. "
                "Sync Outlook first."
            )


        else:

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
