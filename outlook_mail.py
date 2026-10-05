import requests

from datetime import datetime, timedelta, timezone

from outlook_auth import get_access_token


GRAPH_URL = "https://graph.microsoft.com/v1.0"


# ============================================================
# GET EMAILS
# ============================================================

def get_messages(token):
    """
    Get Outlook emails received from yesterday onward.
    """

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Current UTC time
    now_utc = datetime.now(timezone.utc)

    # Start of today
    today_start = now_utc.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    # Start of yesterday
    yesterday_start = today_start - timedelta(days=1)

    yesterday_start_iso = (
        yesterday_start
        .isoformat()
        .replace("+00:00", "Z")
    )

    url = f"{GRAPH_URL}/me/messages"

    params = {
        "$select": (
            "id,"
            "subject,"
            "from,"
            "receivedDateTime,"
            "hasAttachments,"
            "bodyPreview"
        ),
        "$filter": (
            f"receivedDateTime ge "
            f"{yesterday_start_iso}"
        ),
        "$orderby": "receivedDateTime desc",
        "$top": "50"
    }

    messages = []

    while url:

        response = requests.get(
            url,
            headers=headers,
            params=params
        )

        if response.status_code != 200:

            print(
                "Error getting emails:",
                response.status_code
            )

            print(response.text)

            return messages

        data = response.json()

        messages.extend(
            data.get("value", [])
        )

        # Get next page if available
        url = data.get(
            "@odata.nextLink"
        )

        # nextLink already contains parameters
        params = None

    return messages


# ============================================================
# GET ATTACHMENTS
# ============================================================

def get_attachments(token, message_id):
    """
    Get all attachments for one Outlook email.
    """

    url = (
        f"{GRAPH_URL}/me/messages/"
        f"{message_id}/attachments"
    )

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(
        url,
        headers=headers
    )

    if response.status_code != 200:

        print(
            "Error getting attachments:",
            response.status_code
        )

        print(response.text)

        return []

    data = response.json()

    return data.get(
        "value",
        []
    )


# ============================================================
# GET EMAIL TEXT
# ============================================================

def get_message_text(message):

    subject = message.get(
        "subject",
        ""
    )

    body_preview = message.get(
        "bodyPreview",
        ""
    )

    return (
        str(subject)
        + " "
        + str(body_preview)
    ).strip()


# ============================================================
# GET SENDER EMAIL
# ============================================================

def get_sender_email(message):

    try:

        return (
            message
            .get("from", {})
            .get("emailAddress", {})
            .get("address", "")
        )

    except Exception:

        return ""


# ============================================================
# GET SENDER NAME
# ============================================================

def get_sender_name(message):

    try:

        return (
            message
            .get("from", {})
            .get("emailAddress", {})
            .get("name", "")
        )

    except Exception:

        return ""


# ============================================================
# GET RECEIVED DATE
# ============================================================

def get_received_date(message):

    return message.get(
        "receivedDateTime",
        ""
    )


# ============================================================
# OPTIONAL JOB EMAIL CHECK
# ============================================================

def analyze_job_email(message):

    text = get_message_text(
        message
    ).lower()

    keywords = [
        "job",
        "career",
        "vacancy",
        "opening",
        "position",
        "hiring",
        "recruitment",
        "application",
        "interview",
        "candidate",
        "resume",
        "cv",
        "developer",
        "engineer",
        "analyst"
    ]

    matched_keywords = []

    for keyword in keywords:

        if keyword in text:

            matched_keywords.append(
                keyword
            )

    return {
        "is_job_related": len(
            matched_keywords
        ) > 0,

        "score": len(
            matched_keywords
        ),

        "matched_keywords": matched_keywords
    }


# ============================================================
# SIMPLE JOB CHECK
# ============================================================

def is_job_related(message):

    result = analyze_job_email(
        message
    )

    return result["is_job_related"]


# ============================================================
# ATTACHMENT CHECK
# ============================================================

def get_attachment_signal(attachments):

    pdf_docx = []

    other_files = []

    for attachment in attachments:

        name = attachment.get(
            "name",
            ""
        )

        name_lower = name.lower()

        if (
            name_lower.endswith(".pdf")
            or name_lower.endswith(".docx")
        ):

            pdf_docx.append(
                name
            )

        else:

            other_files.append(
                name
            )

    return {
        "resume_attachments": pdf_docx,
        "other_attachments": other_files
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("======================================")
    print("OUTLOOK MAIL TEST")
    print("======================================")

    print()
    print("Authenticating with Microsoft...")

    try:

        token = get_access_token()

        print(
            "Authentication successful."
        )

    except Exception as error:

        print(
            "Authentication failed:"
        )

        print(error)

        raise SystemExit


    print()
    print(
        "Fetching emails from yesterday onward..."
    )

    messages = get_messages(
        token
    )

    print()
    print(
        "Messages found:",
        len(messages)
    )


    print()
    print("======================================")
    print("EMAILS")
    print("======================================")


    attachment_messages = 0


    for index, message in enumerate(
        messages,
        start=1
    ):

        subject = message.get(
            "subject",
            "(No Subject)"
        )

        sender = get_sender_email(
            message
        )

        received = get_received_date(
            message
        )

        has_attachments = message.get(
            "hasAttachments",
            False
        )

        if has_attachments:

            attachment_messages += 1

        print()
        print(
            f"{index}. {subject}"
        )

        print(
            "   From:",
            sender
        )

        print(
            "   Received:",
            received
        )

        print(
            "   Has attachments:",
            has_attachments
        )


    print()
    print("======================================")
    print("SUMMARY")
    print("======================================")

    print(
        "Total messages:",
        len(messages)
    )

    print(
        "Messages with attachments:",
        attachment_messages
    )


    print()
    print("======================================")
    print("ATTACHMENT DETAILS")
    print("======================================")


    for message in messages:

        if not message.get(
            "hasAttachments",
            False
        ):

            continue

        subject = message.get(
            "subject",
            "(No Subject)"
        )

        print()
        print(
            "Email:",
            subject
        )

        attachments = get_attachments(
            token,
            message.get("id")
        )

        for attachment in attachments:

            name = attachment.get(
                "name",
                ""
            )

            content_type = attachment.get(
                "contentType",
                ""
            )

            size = attachment.get(
                "size",
                0
            )

            print(
                "   File:",
                name
            )

            print(
                "   Type:",
                content_type
            )

            print(
                "   Size:",
                size,
                "bytes"
            )


    print()
    print("======================================")
    print("TEST COMPLETE")
    print("======================================")
