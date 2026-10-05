import os
import base64

from outlook_auth import get_access_token
from outlook_mail import get_messages, get_attachments
from candidate_parser import parse_candidate, is_likely_resume
from database.db import get_connection, create_table


RESUME_FOLDER = "email_resumes"

ALLOWED_EXTENSIONS = [".pdf", ".docx"]


def save_candidate(candidate, file_path):
    connection = get_connection()
    cursor = connection.cursor()

    skills = ", ".join(candidate.get("skills", []))
    education = ", ".join(candidate.get("education", []))

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
            resume_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            candidate.get("name", ""),
            candidate.get("email", ""),
            candidate.get("phone", ""),
            skills,
            candidate.get("experience", ""),
            education,
            os.path.basename(file_path),
            candidate.get("resume_text", "")
        )
    )

    connection.commit()
    connection.close()


def already_processed(file_name):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM candidates
        WHERE resume_file = ?
        """,
        (file_name,)
    )

    count = cursor.fetchone()[0]

    connection.close()

    return count > 0


def sync_outlook_resumes(on_device_code=None):

    os.makedirs(RESUME_FOLDER, exist_ok=True)

    create_table()

    print("\nStarting Outlook resume sync...\n")

    # Microsoft authentication
    token = get_access_token(
        on_device_code=on_device_code
    )

    messages = get_messages(token)

    print(f"Emails found: {len(messages)}")

    attachments_checked = 0
    documents_downloaded = 0
    already_processed_count = 0
    resumes_saved = 0
    rejected_count = 0

    for message in messages:

        if not message.get("hasAttachments"):
            continue

        attachments = get_attachments(
            token,
            message["id"]
        )

        for attachment in attachments:

            file_name = attachment.get("name", "")

            extension = os.path.splitext(
                file_name
            )[1].lower()

            if extension not in ALLOWED_EXTENSIONS:
                continue

            attachments_checked += 1

            # Avoid duplicate database records
            if already_processed(file_name):

                print(
                    f"Already processed: {file_name}"
                )

                already_processed_count += 1

                continue

            content_bytes = attachment.get(
                "contentBytes"
            )

            if not content_bytes:

                print(
                    f"No content found: {file_name}"
                )

                continue

            file_path = os.path.join(
                RESUME_FOLDER,
                file_name
            )

            with open(file_path, "wb") as file:

                file.write(
                    base64.b64decode(
                        content_bytes
                    )
                )

            documents_downloaded += 1

            print("\n" + "=" * 60)
            print(
                f"Processing: {file_name}"
            )
            print("=" * 60)

            try:

                candidate = parse_candidate(
                    file_path
                )

                print("\nExtracted information:")

                print(
                    "Name       :",
                    candidate.get("name")
                )

                print(
                    "Email      :",
                    candidate.get("email")
                )

                print(
                    "Phone      :",
                    candidate.get("phone")
                )

                print(
                    "Skills     :",
                    candidate.get("skills")
                )

                print(
                    "Experience :",
                    candidate.get("experience")
                )

                print(
                    "Education  :",
                    candidate.get("education")
                )

                resume_text = candidate.get(
                    "resume_text",
                    ""
                )

                print(
                    "Text length:",
                    len(resume_text)
                )

                is_resume = is_likely_resume(
                    candidate
                )

                print(
                    "Resume check:",
                    "RESUME"
                    if is_resume
                    else "NOT A RESUME"
                )

                if is_resume:

                    save_candidate(
                        candidate,
                        file_path
                    )

                    resumes_saved += 1

                    print(
                        "Saved to database: YES"
                    )

                else:

                    rejected_count += 1

                    print(
                        "Saved to database: NO"
                    )

                    print(
                        "Keeping file for inspection:",
                        file_path
                    )

            except Exception as error:

                print(
                    f"Error processing {file_name}: "
                    f"{error}"
                )

    print("\n" + "=" * 60)
    print("SYNC SUMMARY")
    print("=" * 60)

    print(
        "PDF/DOCX attachments:",
        attachments_checked
    )

    print(
        "Documents downloaded:",
        documents_downloaded
    )

    print(
        "Already processed:",
        already_processed_count
    )

    print(
        "Resumes saved:",
        resumes_saved
    )

    print(
        "Non-resumes rejected:",
        rejected_count
    )

    print("\nSync finished.")

    # Return results to Streamlit
    return {
        "emails_scanned": len(messages),
        "attachments_checked": attachments_checked,
        "documents_downloaded": documents_downloaded,
        "already_processed": already_processed_count,
        "resumes_saved": resumes_saved,
        "rejected_count": rejected_count
    }


if __name__ == "__main__":
    sync_outlook_resumes()