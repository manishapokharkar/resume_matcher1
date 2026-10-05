import os
import requests

from outlook_auth import get_access_token
from outlook_mail import get_job_emails, get_email_attachments
from candidate_parser import parse_candidate
from database.db import get_connection, create_table


# ============================================================
# SETTINGS
# ============================================================

EMAIL_RESUME_FOLDER = "email_resumes"

ALLOWED_EXTENSIONS = [
    ".pdf",
    ".docx"
]


# ============================================================
# CREATE EMAIL RESUME FOLDER
# ============================================================

def create_email_resume_folder():

    if not os.path.exists(
        EMAIL_RESUME_FOLDER
    ):

        os.makedirs(
            EMAIL_RESUME_FOLDER
        )


# ============================================================
# CHECK IF RESUME ALREADY EXISTS
# ============================================================

def already_processed(
    file_name
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM candidates
        WHERE resume_file = ?
        AND source = 'email'
        """,
        (file_name,)
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None


# ============================================================
# SAVE CANDIDATE
# ============================================================

def save_candidate(
    candidate,
    file_name
):

    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # Skills
    # --------------------------------------------------------

    skills = candidate.get(
        "skills",
        []
    )

    if isinstance(
        skills,
        list
    ):

        skills = ", ".join(
            str(skill).strip()
            for skill in skills
            if skill
        )

    elif skills is None:

        skills = ""

    else:

        skills = str(
            skills
        )

    # --------------------------------------------------------
    # Education
    # --------------------------------------------------------

    education = candidate.get(
        "education",
        []
    )

    if isinstance(
        education,
        list
    ):

        education = ", ".join(
            str(item).strip()
            for item in education
            if item
        )

    elif education is None:

        education = ""

    else:

        education = str(
            education
        )

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    experience = candidate.get(
        "experience",
        ""
    )

    if isinstance(
        experience,
        list
    ):

        experience = ", ".join(
            str(item).strip()
            for item in experience
            if item
        )

    elif experience is None:

        experience = ""

    else:

        experience = str(
            experience
        )

    # --------------------------------------------------------
    # Resume text
    # --------------------------------------------------------

    resume_text = candidate.get(
        "resume_text",
        ""
    )

    if resume_text is None:

        resume_text = ""

    elif not isinstance(
        resume_text,
        str
    ):

        resume_text = str(
            resume_text
        )

    # --------------------------------------------------------
    # Insert into database
    # --------------------------------------------------------

    cursor.execute(
        """
        INSERT INTO candidates
        (
            name,
            email,
            phone,
            skills,
            experience,
            education,
            resume_file,
            resume_text,
            source
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            candidate.get("name"),
            candidate.get("email"),
            candidate.get("phone"),
            skills,
            experience,
            education,
            file_name,
            resume_text,
            "email"
        )
    )

    connection.commit()

    connection.close()


# ============================================================
# DOWNLOAD ATTACHMENT
# ============================================================

def download_attachment(
    access_token,
    message_id,
    attachment_id,
    file_name
):

    url = (
        "https://graph.microsoft.com/v1.0"
        f"/me/messages/{message_id}"
        f"/attachments/{attachment_id}/$value"
    )

    headers = {
        "Authorization":
            f"Bearer {access_token}"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=60
    )

    response.raise_for_status()

    file_path = os.path.join(
        EMAIL_RESUME_FOLDER,
        file_name
    )

    with open(
        file_path,
        "wb"
    ) as file:

        file.write(
            response.content
        )

    return file_path


# ============================================================
# SYNC OUTLOOK RESUMES
# ============================================================

def sync_outlook_resumes(
    on_device_code=None
):

    create_table()

    create_email_resume_folder()

    # --------------------------------------------------------
    # GET MICROSOFT ACCESS TOKEN
    # --------------------------------------------------------

    access_token = get_access_token(
        on_device_code=on_device_code
    )

    # --------------------------------------------------------
    # GET JOB EMAILS
    # --------------------------------------------------------

    emails = get_job_emails(
        access_token
    )

    emails_scanned = len(
        emails
    )

    attachments_checked = 0
    documents_downloaded = 0
    already_processed_count = 0
    resumes_saved = 0
    rejected_count = 0

    print("=" * 60)
    print("OUTLOOK RESUME SYNC")
    print("=" * 60)

    print(
        f"Job emails found: "
        f"{emails_scanned}"
    )

    # --------------------------------------------------------
    # PROCESS EMAILS
    # --------------------------------------------------------

    for email in emails:

        message_id = email.get(
            "id"
        )

        subject = email.get(
            "subject",
            ""
        )

        print()
        print("-" * 60)

        print(
            f"Email: {subject}"
        )

        if not message_id:

            continue

        # ----------------------------------------------------
        # GET ATTACHMENTS
        # ----------------------------------------------------

        try:

            attachments = (
                get_email_attachments(
                    access_token,
                    message_id
                )
            )

        except Exception as error:

            print(
                f"ERROR getting attachments: "
                f"{error}"
            )

            rejected_count += 1

            continue

        # ----------------------------------------------------
        # PROCESS ATTACHMENTS
        # ----------------------------------------------------

        for attachment in attachments:

            attachments_checked += 1

            attachment_id = attachment.get(
                "id"
            )

            file_name = attachment.get(
                "name",
                ""
            )

            if not file_name:

                continue

            extension = os.path.splitext(
                file_name
            )[1].lower()

            # ------------------------------------------------
            # Only PDF / DOCX
            # ------------------------------------------------

            if extension not in ALLOWED_EXTENSIONS:

                print(
                    f"Skipped unsupported attachment: "
                    f"{file_name}"
                )

                continue

            # ------------------------------------------------
            # Duplicate check
            # ------------------------------------------------

            if already_processed(
                file_name
            ):

                already_processed_count += 1

                print(
                    f"Already processed: "
                    f"{file_name}"
                )

                continue

            # ------------------------------------------------
            # Download attachment
            # ------------------------------------------------

            try:

                file_path = (
                    download_attachment(
                        access_token,
                        message_id,
                        attachment_id,
                        file_name
                    )
                )

                documents_downloaded += 1

                print(
                    f"Downloaded: "
                    f"{file_name}"
                )

            except Exception as error:

                print(
                    f"ERROR downloading "
                    f"{file_name}: {error}"
                )

                rejected_count += 1

                continue

            # ------------------------------------------------
            # Parse resume
            # ------------------------------------------------

            try:

                candidate = parse_candidate(
                    file_path
                )

                print(
                    f"Parsed name: "
                    f"{candidate.get('name')}"
                )

                print(
                    f"Parsed email: "
                    f"{candidate.get('email')}"
                )

                print(
                    f"Skills: "
                    f"{candidate.get('skills', [])}"
                )

            except Exception as error:

                print(
                    f"ERROR parsing "
                    f"{file_name}: {error}"
                )

                rejected_count += 1

                continue

            # ------------------------------------------------
            # Save candidate
            # ------------------------------------------------

            try:

                save_candidate(
                    candidate,
                    file_name
                )

                resumes_saved += 1

                print(
                    f"SUCCESS - Resume saved: "
                    f"{file_name}"
                )

            except Exception as error:

                print(
                    f"ERROR saving "
                    f"{file_name}: {error}"
                )

                rejected_count += 1

    # --------------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("OUTLOOK SYNC COMPLETED")
    print("=" * 60)

    print(
        f"Emails scanned: "
        f"{emails_scanned}"
    )

    print(
        f"Attachments checked: "
        f"{attachments_checked}"
    )

    print(
        f"Documents downloaded: "
        f"{documents_downloaded}"
    )

    print(
        f"Already processed: "
        f"{already_processed_count}"
    )

    print(
        f"Resumes saved: "
        f"{resumes_saved}"
    )

    print(
        f"Rejected: "
        f"{rejected_count}"
    )

    print("=" * 60)

    return {

        "emails_scanned":
            emails_scanned,

        "attachments_checked":
            attachments_checked,

        "documents_downloaded":
            documents_downloaded,

        "already_processed":
            already_processed_count,

        "resumes_saved":
            resumes_saved,

        "rejected_count":
            rejected_count
    }