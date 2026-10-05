import os
import base64

from outlook_auth import get_access_token
from outlook_mail import get_messages, is_job_related
from outlook_attachments import get_attachments


DOWNLOAD_FOLDER = "email_resumes"

ALLOWED_EXTENSIONS = [
    ".pdf",
    ".docx"
]


def download_resumes(on_device_code=None):

    os.makedirs(
        DOWNLOAD_FOLDER,
        exist_ok=True
    )

    messages = get_messages(
        on_device_code=on_device_code
    )

    downloaded_files = []

    for message in messages:

        if not is_job_related(message):
            continue

        subject = message.get(
            "subject",
            ""
        )

        print("\nChecking:", subject)

        message_id = message["id"]

        attachments = get_attachments(
            message_id,
            on_device_code=on_device_code
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

            content_bytes = attachment.get(
                "contentBytes"
            )

            if not content_bytes:
                print(
                    "No content available:",
                    file_name
                )
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

            downloaded_files.append(
                file_path
            )

            print(
                "Downloaded:",
                file_name
            )

    return downloaded_files


if __name__ == "__main__":

    print(
        "\nDownloading resume attachments...\n"
    )

    files = download_resumes()

    print("\n==============================")

    if files:

        print("Downloaded resumes:")

        for file in files:
            print(file)

    else:

        print(
            "No PDF or DOCX resumes found."
        )