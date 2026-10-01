import os
import base64
import requests

from outlook_auth import get_access_token
from outlook_mail import get_messages, is_job_related
from candidate_parser import parse_candidate
from database.db import get_connection, create_table


GRAPH_URL = "https://graph.microsoft.com/v1.0"
DOWNLOAD_FOLDER = "email_resumes"

ALLOWED_EXTENSIONS = [".pdf", ".docx"]


def get_attachments(message_id):
    token = get_access_token()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = f"{GRAPH_URL}/me/messages/{message_id}/attachments"

    response = requests.get(
        url,
        headers=headers
    )

    response.raise_for_status()

    return response.json()["value"]


def candidate_exists(resume_file):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM candidates
        WHERE resume_file = ?
        """,
        (resume_file,)
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None


def save_candidate(candidate, resume_file):

    connection = get_connection()
    cursor = connection.cursor()

    skills = ", ".join(candidate["skills"])
    education = ", ".join(candidate["education"])

    cursor.execute(
        """
        INSERT INTO candidates (
            name,
            email,
            phone,
            skills,
            experience,
            education,
            resume_file,
            resume_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            candidate["name"],
            candidate["email"],
            candidate["phone"],
            skills,
            candidate["experience"],
            education,
            resume_file,
            candidate["resume_text"]
        )
    )

    connection.commit()
    connection.close()


def sync_outlook():

    create_table()

    os.makedirs(
        DOWNLOAD_FOLDER,
        exist_ok=True
    )

    messages = get_messages()

    downloaded_count = 0
    skipped_count = 0
    saved_count = 0

    for message in messages:

        if not is_job_related(message):
            continue

        message_id = message["id"]

        subject = message.get(
            "subject",
            ""
        )

        print(
            f"\nChecking email: {subject}"
        )

        attachments = get_attachments(
            message_id
        )

        for attachment in attachments:

            file_name = attachment.get(
                "name",
                ""
            )

            extension = os.path.splitext(
                file_name
            )[1].lower()

            if extension not in ALLOWED_EXTENSIONS:
                continue

            if candidate_exists(file_name):

                print(
                    "Already processed:",
                    file_name
                )

                skipped_count += 1

                continue

            content_bytes = attachment.get(
                "contentBytes"
            )

            if not content_bytes:
                continue

            file_path = os.path.join(
                DOWNLOAD_FOLDER,
                file_name
            )

            with open(
                file_path,
                "wb"
            ) as file:

                file.write(
                    base64.b64decode(
                        content_bytes
                    )
                )

            downloaded_count += 1

            print(
                "Downloaded:",
                file_name
            )

            try:

                candidate = parse_candidate(
                    file_path
                )

                save_candidate(
                    candidate,
                    file_name
                )

                saved_count += 1

                print(
                    "Candidate saved:",
                    candidate["name"]
                )

            except Exception as error:

                print(
                    "Error parsing:",
                    file_name,
                    error
                )

    return {
        "downloaded": downloaded_count,
        "skipped": skipped_count,
        "saved": saved_count
    }


if __name__ == "__main__":

    print(
        "\nStarting Outlook sync...\n"
    )

    result = sync_outlook()

    print(
        "\n=============================="
    )

    print(
        "Outlook Sync Completed"
    )

    print(
        "Downloaded:",
        result["downloaded"]
    )

    print(
        "Already processed:",
        result["skipped"]
    )

    print(
        "Candidates saved:",
        result["saved"]
    )