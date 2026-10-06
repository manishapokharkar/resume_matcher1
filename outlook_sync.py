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

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
}


# ============================================================
# CREATE EMAIL RESUME FOLDER
# ============================================================

def create_email_resume_folder():
    os.makedirs(
        EMAIL_RESUME_FOLDER,
        exist_ok=True,
    )


# ============================================================
# NORMALIZE FILE PATH
# ============================================================

def normalize_resume_path(file_path):
    """
    Store a portable relative path.

    Example:
        email_resumes/Maya_Rodriguez.pdf

    We do NOT store an absolute Windows path because
    Streamlit Cloud uses a different filesystem.
    """

    if not file_path:
        return ""

    normalized = os.path.normpath(
        str(file_path).strip()
    )

    return normalized


# ============================================================
# GET FILE NAME SAFELY
# ============================================================

def get_file_name(file_name):
    """
    Prevent accidental directory traversal and ensure that
    only the attachment filename is used.
    """

    if not file_name:
        return ""

    return os.path.basename(
        str(file_name).strip()
    )


# ============================================================
# CHECK IF RESUME ALREADY EXISTS
# ============================================================

def already_processed(file_name):
    """
    Backward-compatible duplicate detection.

    Older records may contain:

        resume.pdf

    Newer records contain:

        email_resumes/resume.pdf

    Therefore we compare both the full stored path and
    the filename.
    """

    clean_name = get_file_name(file_name)

    if not clean_name:
        return False

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT resume_file
            FROM candidates
            WHERE source = 'email'
            """
        )

        rows = cursor.fetchall()

    finally:
        connection.close()

    for row in rows:

        try:
            stored_path = row["resume_file"]
        except Exception:
            stored_path = row[0]

        if not stored_path:
            continue

        stored_path = str(
            stored_path
        ).strip()

        stored_name = os.path.basename(
            stored_path
        )

        if stored_name.lower() == clean_name.lower():
            return True

    return False


# ============================================================
# CONVERT VALUE TO DATABASE TEXT
# ============================================================

def value_to_text(value):
    """
    Convert parser output into SQLite-friendly text.
    """

    if value is None:
        return ""

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return ", ".join(
            str(item).strip()
            for item in value
            if item
        )

    return str(value).strip()


# ============================================================
# SAVE CANDIDATE
# ============================================================

def save_candidate(
    candidate,
    file_path,
):
    """
    Save candidate and the ACTUAL resume path.

    Important:
        We now store:

            email_resumes/example.pdf

        instead of only:

            example.pdf
    """

    connection = get_connection()
    cursor = connection.cursor()

    try:

        skills = value_to_text(
            candidate.get(
                "skills",
                [],
            )
        )

        education = value_to_text(
            candidate.get(
                "education",
                [],
            )
        )

        experience = value_to_text(
            candidate.get(
                "experience",
                "",
            )
        )

        resume_text = value_to_text(
            candidate.get(
                "resume_text",
                "",
            )
        )

        stored_file_path = normalize_resume_path(
            file_path
        )

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
                stored_file_path,
                resume_text,
                "email",
            ),
        )

        connection.commit()

    finally:
        connection.close()


# ============================================================
# DOWNLOAD ATTACHMENT
# ============================================================

def download_attachment(
    access_token,
    message_id,
    attachment_id,
    file_name,
):
    """
    Download an Outlook attachment into email_resumes.

    Returns:
        email_resumes/<actual_filename>
    """

    clean_name = get_file_name(
        file_name
    )

    if not clean_name:
        raise ValueError(
            "Attachment filename is empty."
        )

    url = (
        "https://graph.microsoft.com/v1.0"
        f"/me/messages/{message_id}"
        f"/attachments/{attachment_id}/$value"
    )

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=60,
    )

    response.raise_for_status()

    file_path = os.path.join(
        EMAIL_RESUME_FOLDER,
        clean_name,
    )

    with open(
        file_path,
        "wb",
    ) as file:

        file.write(
            response.content
        )

    return normalize_resume_path(
        file_path
    )


# ============================================================
# SYNC OUTLOOK RESUMES
# ============================================================

def sync_outlook_resumes(
    on_device_code=None,
):

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    create_table()

    # --------------------------------------------------------
    # RESUME FOLDER
    # --------------------------------------------------------

    create_email_resume_folder()

    # --------------------------------------------------------
    # MICROSOFT LOGIN
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
        f"Job emails found: {emails_scanned}"
    )

    # ========================================================
    # PROCESS EMAILS
    # ========================================================

    for email in emails:

        message_id = email.get(
            "id"
        )

        subject = email.get(
            "subject",
            "",
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

            attachments = get_email_attachments(
                access_token,
                message_id,
            )

        except Exception as error:

            print(
                f"ERROR getting attachments: {error}"
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
                "",
            )

            if not file_name:
                continue

            file_name = get_file_name(
                file_name
            )

            extension = os.path.splitext(
                file_name
            )[1].lower()

            # ------------------------------------------------
            # PDF / DOCX ONLY
            # ------------------------------------------------

            if extension not in ALLOWED_EXTENSIONS:

                print(
                    f"Skipped unsupported attachment: "
                    f"{file_name}"
                )

                continue

            # ------------------------------------------------
            # DUPLICATE CHECK
            # ------------------------------------------------

            if already_processed(
                file_name
            ):

                already_processed_count += 1

                print(
                    f"Already processed: {file_name}"
                )

                continue

            # ------------------------------------------------
            # DOWNLOAD
            # ------------------------------------------------

            try:

                file_path = download_attachment(
                    access_token,
                    message_id,
                    attachment_id,
                    file_name,
                )

                documents_downloaded += 1

                print(
                    f"Downloaded: {file_path}"
                )

            except Exception as error:

                print(
                    f"ERROR downloading "
                    f"{file_name}: {error}"
                )

                rejected_count += 1

                continue

            # ------------------------------------------------
            # PARSE RESUME
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

                # Remove broken downloaded file
                try:
                    if os.path.exists(
                        file_path
                    ):
                        os.remove(
                            file_path
                        )
                except Exception:
                    pass

                continue

            # ------------------------------------------------
            # SAVE CANDIDATE
            # ------------------------------------------------

            try:

                # IMPORTANT:
                # Store file_path, not file_name.
                save_candidate(
                    candidate,
                    file_path,
                )

                resumes_saved += 1

                print(
                    f"SUCCESS - Resume saved: "
                    f"{file_path}"
                )

            except Exception as error:

                print(
                    f"ERROR saving "
                    f"{file_name}: {error}"
                )

                rejected_count += 1

    # ========================================================
    # FINAL REPORT
    # ========================================================

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
        "emails_scanned": emails_scanned,
        "attachments_checked": attachments_checked,
        "documents_downloaded": documents_downloaded,
        "already_processed": already_processed_count,
        "resumes_saved": resumes_saved,
        "rejected_count": rejected_count,
    }