import requests
from datetime import datetime, timedelta, timezone


GRAPH_BASE_URL = (
    "https://graph.microsoft.com/v1.0"
)


# ============================================================
# GET YESTERDAY'S JOB EMAILS
# ============================================================

def get_job_emails(
    access_token
):

    # --------------------------------------------------------
    # Yesterday 00:00 UTC
    # --------------------------------------------------------

    yesterday = (
        datetime.now(timezone.utc)
        - timedelta(days=1)
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    yesterday_string = (
        yesterday.isoformat()
        .replace(
            "+00:00",
            "Z"
        )
    )

    url = (
        f"{GRAPH_BASE_URL}"
        "/me/mailFolders/inbox/messages"
    )

    params = {

        "$top": 50,

        "$select":
            "id,subject,from,receivedDateTime,"
            "hasAttachments,bodyPreview,body",

        "$filter":
            f"receivedDateTime ge "
            f"{yesterday_string}"
    }

    headers = {

        "Authorization":
            f"Bearer {access_token}",

        "Content-Type":
            "application/json"
    }

    all_emails = []

    # --------------------------------------------------------
    # Pagination
    # --------------------------------------------------------

    while url:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        emails = data.get(
            "value",
            []
        )

        all_emails.extend(
            emails
        )

        # ----------------------------------------------------
        # Next page
        # ----------------------------------------------------

        url = data.get(
            "@odata.nextLink"
        )

        # Parameters are already included
        # inside nextLink.

        params = {}

    # --------------------------------------------------------
    # Filter job-related emails
    # --------------------------------------------------------

    job_keywords = [

        "resume",
        "cv",
        "job",
        "application",
        "applying",
        "candidate",
        "vacancy",
        "position",
        "opening",
        "career",
        "recruitment",
        "hiring",
        "interview",
        "developer",
        "engineer",
        "analyst",
        "software",
        "frontend",
        "backend",
        "python",
        "react",
        "data analyst"
    ]

    application_phrases = [

        "job application",
        "job opportunity",
        "application for",
        "applying for",
        "resume attached",
        "cv attached",
        "candidate application",
        "application received",
        "new application"
    ]

    job_emails = []

    for email in all_emails:

        subject = (
            email.get(
                "subject",
                ""
            )
            or ""
        )

        body_preview = (
            email.get(
                "bodyPreview",
                ""
            )
            or ""
        )

        body = (
            email.get(
                "body",
                {}
            )
            or {}
        )

        body_content = (
            body.get(
                "content",
                ""
            )
            or ""
        )

        combined_text = (
            subject
            + " "
            + body_preview
            + " "
            + body_content
        ).lower()

        score = 0

        # ----------------------------------------------------
        # Subject keyword
        # ----------------------------------------------------

        subject_lower = (
            subject.lower()
        )

        for keyword in job_keywords:

            if keyword in subject_lower:

                score += 2

                break

        # ----------------------------------------------------
        # Application phrase
        # ----------------------------------------------------

        for phrase in application_phrases:

            if phrase in combined_text:

                score += 3

                break

        # ----------------------------------------------------
        # Body job keywords
        # ----------------------------------------------------

        body_matches = 0

        for keyword in job_keywords:

            if keyword in combined_text:

                body_matches += 1

        if body_matches >= 3:

            score += 2

        # ----------------------------------------------------
        # Must have attachment
        # ----------------------------------------------------

        has_attachments = email.get(
            "hasAttachments",
            False
        )

        if not has_attachments:

            continue

        # ----------------------------------------------------
        # Final job email decision
        # ----------------------------------------------------

        if score >= 3:

            email["_job_score"] = score

            job_emails.append(
                email
            )

    return job_emails


# ============================================================
# GET EMAIL ATTACHMENTS
# ============================================================

def get_email_attachments(
    access_token,
    message_id
):

    url = (
        f"{GRAPH_BASE_URL}"
        f"/me/messages/{message_id}"
        "/attachments"
    )

    headers = {

        "Authorization":
            f"Bearer {access_token}",

        "Content-Type":
            "application/json"
    }

    all_attachments = []

    while url:

        response = requests.get(
            url,
            headers=headers,
            params={
                "$top": 50
            },
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        attachments = data.get(
            "value",
            []
        )

        all_attachments.extend(
            attachments
        )

        url = data.get(
            "@odata.nextLink"
        )

    # --------------------------------------------------------
    # Return only file attachments
    # --------------------------------------------------------

    file_attachments = []

    for attachment in all_attachments:

        attachment_type = (
            attachment.get(
                "@odata.type",
                ""
            )
        )

        file_name = (
            attachment.get(
                "name",
                ""
            )
            or ""
        )

        # Ignore inline images and other
        # non-file attachments.

        if (
            attachment_type
            == "#microsoft.graph.fileAttachment"
        ):

            attachment["name"] = file_name

            file_attachments.append(
                attachment
            )

    return file_attachments

