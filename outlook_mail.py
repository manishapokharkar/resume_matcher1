import requests
from outlook_auth import get_access_token

GRAPH_URL = "https://graph.microsoft.com/v1.0"

JOB_KEYWORDS = [
    "job",
    "job application",
    "application",
    "resume",
    "cv",
    "curriculum vitae",
    "frontend developer",
    "react developer",
    "software developer",
    "web developer",
    "developer",
    "career",
    "interview",
    "candidate"
]


def get_messages():

    token = get_access_token()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = f"{GRAPH_URL}/me/mailFolders/inbox/messages"

    params = {
        "$top": 50,
        "$select": "id,subject,from,receivedDateTime,hasAttachments"
    }

    response = requests.get(
        url,
        headers=headers,
        params=params
    )

    response.raise_for_status()

    return response.json()["value"]


def is_job_related(message):

    subject = message.get("subject", "")

    subject_lower = subject.lower()

    for keyword in JOB_KEYWORDS:

        if keyword in subject_lower:
            return True

    return False


if __name__ == "__main__":

    messages = get_messages()

    print("\nJob-related emails:\n")

    found = 0

    for message in messages:

        if is_job_related(message):

            found += 1

            sender = message.get(
                "from",
                {}
            ).get(
                "emailAddress",
                {}
            )

            print("--------------------------------")
            print("Subject:", message.get("subject"))
            print("From:", sender.get("address"))
            print("Received:", message.get("receivedDateTime"))
            print(
                "Has attachment:",
                message.get("hasAttachments")
            )

    if found == 0:

        print("No job-related emails found.")