import os
import base64
import requests

from outlook_auth import get_access_token
from outlook_mail import get_messages, is_job_related


GRAPH_URL = "https://graph.microsoft.com/v1.0"

DOWNLOAD_FOLDER = "email_resumes"

ALLOWED_EXTENSIONS = [
    ".pdf",
    ".docx"
]


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


def download_resumes():

    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    messages = get_messages()

    downloaded_files = []

    for message in messages:

        if not is_job_related(message):
            continue

        message_id = message["id"]

        subject = message.get("subject", "")

        print("\nChecking:", subject)

        attachments = get_attachments(message_id)

        for attachment in attachments:

            file_name = attachment.get("name", "")

            extension = os.path.splitext(
                file_name
            )[1].lower()

            if extension not in ALLOWED_EXTENSIONS:
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

            with open(file_path, "wb") as file:

                file.write(
                    base64.b64decode(content_bytes)
                )

            downloaded_files.append(file_path)

            print(
                "Downloaded:",
                file_name
            )

    return downloaded_files


if __name__ == "__main__":

    print("\nChecking Outlook for resume attachments...\n")

    files = download_resumes()

    print("\n--------------------------------")

    if files:

        print("Downloaded resumes:")

        for file in files:
            print(file)

    else:

        print("No PDF or DOCX resumes found.")