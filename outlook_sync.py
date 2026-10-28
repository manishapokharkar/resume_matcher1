import os
import requests
from urllib.parse import quote

from outlook_auth import get_access_token
from outlook_mail import get_email_attachments

from candidate_parser import (
    parse_candidate,
    is_likely_resume
)

from database.db import (
    create_table,
    get_connection,
    candidate_exists,
    insert_candidate
)


# ============================================================
# SETTINGS
# ============================================================

EMAIL_RESUME_FOLDER = "email_resumes"

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
}


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
OUTLOOK_RESUME_FOLDER_NAME = "Resumes"


def graph_get_all_pages(access_token, url):
    """Fetch every page returned by Microsoft Graph."""
    headers = {"Authorization": f"Bearer {access_token}"}
    results = []
    while url:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        payload = response.json()
        results.extend(payload.get("value", []))
        url = payload.get("@odata.nextLink")
    return results


def find_mail_folder(access_token, target_name=OUTLOOK_RESUME_FOLDER_NAME):
    """Find a mail folder by display name, including nested folders."""
    headers = {"Authorization": f"Bearer {access_token}"}
    queue = [f"{GRAPH_BASE_URL}/me/mailFolders?$top=100"]
    visited_urls = set()
    target = target_name.strip().casefold()

    while queue:
        url = queue.pop(0)
        if url in visited_urls:
            continue
        visited_urls.add(url)

        while url:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            payload = response.json()

            for folder in payload.get("value", []):
                if str(folder.get("displayName", "")).strip().casefold() == target:
                    return folder
                folder_id = folder.get("id")
                if folder_id:
                    queue.append(
                        f"{GRAPH_BASE_URL}/me/mailFolders/"
                        f"{quote(folder_id, safe='')}/childFolders?$top=100"
                    )
            url = payload.get("@odata.nextLink")
    return None


def get_resume_folder_emails(access_token):
    """Return messages with attachments from the Outlook 'Resumes' folder only."""
    folder = find_mail_folder(access_token)
    if not folder:
        raise RuntimeError(
            "Could not find an Outlook mail folder named "
            f"'{OUTLOOK_RESUME_FOLDER_NAME}'. Create or rename the folder "
            "in Outlook, then run the sync again."
        )

    folder_id = quote(folder["id"], safe="")
    url = (
        f"{GRAPH_BASE_URL}/me/mailFolders/{folder_id}/messages"
        "?$select=id,subject,hasAttachments,receivedDateTime"
        "&$top=100"
    )
    emails = graph_get_all_pages(access_token, url)
    return [email for email in emails if email.get("hasAttachments", False)]



# ============================================================
# CREATE EMAIL RESUME FOLDER
# ============================================================

def create_email_resume_folder():

    os.makedirs(
        EMAIL_RESUME_FOLDER,
        exist_ok=True
    )


# ============================================================
# NORMALIZE FILE PATH
# ============================================================

def normalize_resume_path(file_path):

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

    if not file_name:
        return ""

    return os.path.basename(
        str(file_name).strip()
    )


# ============================================================
# CHECK IF RESUME ALREADY EXISTS
# ============================================================

def already_processed(file_name):

    clean_name = get_file_name(
        file_name
    )

    if not clean_name:
        return False

    create_table()

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

        stored_path = row["resume_file"]

        if not stored_path:
            continue

        stored_path = str(
            stored_path
        ).strip()

        stored_name = os.path.basename(
            stored_path
        )

        if (
            stored_name.lower()
            ==
            clean_name.lower()
        ):

            return True

    return False


# ============================================================
# CONVERT VALUE TO DATABASE TEXT
# ============================================================

def value_to_text(value):

    if value is None:
        return ""

    if isinstance(
        value,
        (list, tuple, set)
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
    file_path
):
    """
    Save parsed candidate information into SQLite.
    """

    name = value_to_text(
        candidate.get("name")
    )

    email = value_to_text(
        candidate.get("email")
    )

    phone = value_to_text(
        candidate.get("phone")
    )

    skills = value_to_text(
        candidate.get("skills", [])
    )

    experience = value_to_text(
        candidate.get("experience", "")
    )

    education = value_to_text(
        candidate.get("education", [])
    )

    resume_text = value_to_text(
        candidate.get("resume_text", "")
    )

    stored_file_path = normalize_resume_path(
        file_path
    )

    # --------------------------------------------------------
    # Insert candidate
    # --------------------------------------------------------

    candidate_id = insert_candidate(

        name=name,

        email=email,

        phone=phone,

        skills=skills,

        experience=experience,

        education=education,

        resume_file=stored_file_path,

        resume_text=resume_text,

        source="email"
    )

    return candidate_id


# ============================================================
# DOWNLOAD ATTACHMENT
# ============================================================

def download_attachment(
    access_token,
    message_id,
    attachment_id,
    file_name
):

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
        timeout=60
    )

    response.raise_for_status()

    file_path = os.path.join(
        EMAIL_RESUME_FOLDER,
        clean_name
    )

    with open(
        file_path,
        "wb"
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

    # ========================================================
    # DATABASE
    # ========================================================

    create_table()

    # ========================================================
    # RESUME FOLDER
    # ========================================================

    create_email_resume_folder()

    # ========================================================
    # MICROSOFT LOGIN
    # ========================================================

    access_token = get_access_token(
        on_device_code=on_device_code
    )

    # ========================================================
    # GET EMAILS FROM THE OUTLOOK "Resumes" FOLDER ONLY
    # ========================================================

    emails = get_resume_folder_emails(
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
        f"Emails with attachments found in Outlook Resumes folder: "
        f"{emails_scanned}"
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

        # ====================================================
        # GET ATTACHMENTS
        # ====================================================

        try:

            attachments = get_email_attachments(
                access_token,
                message_id
            )

        except Exception as error:

            print(
                f"ERROR getting attachments: "
                f"{error}"
            )

            rejected_count += 1

            continue

        # ====================================================
        # PROCESS ATTACHMENTS
        # ====================================================

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
                    f"Already processed: "
                    f"{file_name}"
                )

                continue

            # ------------------------------------------------
            # DOWNLOAD
            # ------------------------------------------------

            file_path = None

            try:

                file_path = download_attachment(
                    access_token,
                    message_id,
                    attachment_id,
                    file_name
                )

                documents_downloaded += 1

                print(
                    f"Downloaded: "
                    f"{file_path}"
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

                try:

                    if (
                        file_path
                        and
                        os.path.exists(
                            file_path
                        )
                    ):

                        os.remove(
                            file_path
                        )

                except Exception:
                    pass

                continue

            # ------------------------------------------------
            # RESUME VALIDATION
            # ------------------------------------------------

            if not is_likely_resume(
                candidate
            ):

                print(
                    f"Rejected as non-resume: "
                    f"{file_name}"
                )

                rejected_count += 1

                try:

                    if (
                        file_path
                        and
                        os.path.exists(
                            file_path
                        )
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

                candidate_id = save_candidate(
                    candidate,
                    file_path
                )

                resumes_saved += 1

                print(
                    f"SUCCESS - Resume saved"
                    f" | Candidate ID: "
                    f"{candidate_id}"
                    f" | File: "
                    f"{file_path}"
                )

            except Exception as error:

                print(
                    f"ERROR saving "
                    f"{file_name}: {error}"
                )

                rejected_count += 1

                continue

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()
    print("=" * 60)

    print(
        "OUTLOOK SYNC COMPLETED"
    )

    print("=" * 60)

    print(
        f"Emails scanned from Outlook Resumes folder: "
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
            rejected_count,
    }