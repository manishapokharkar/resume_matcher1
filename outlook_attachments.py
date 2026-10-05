import requests

import outlook_auth
from outlook_mail import get_messages, is_job_related


GRAPH_URL = "https://graph.microsoft.com/v1.0"


def get_attachments(message_id, on_device_code=None):

    token = outlook_auth.get_access_token(
        on_device_code=on_device_code
    )

    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = (
        f"{GRAPH_URL}"
        f"/me/messages/{message_id}/attachments"
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.json()["value"]


if __name__ == "__main__":

    print("\nChecking Outlook attachments...\n")

    messages = get_messages()

    for message in messages:

        if not is_job_related(message):
            continue

        subject = message.get(
            "subject",
            ""
        )

        print("--------------------------------")
        print("Email:", subject)

        message_id = message["id"]

        attachments = get_attachments(
            message_id
        )

        if not attachments:

            print("No attachments found.")

            continue

        for attachment in attachments:

            print(
                "Attachment:",
                attachment.get("name")
            )

            print(
                "Type:",
                attachment.get("@odata.type")
            )

            print(
                "Size:",
                attachment.get("size"),
                "bytes"
            )