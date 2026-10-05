import os
import msal

from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")

AUTHORITY = (
    f"https://login.microsoftonline.com/{TENANT_ID}"
)

SCOPES = [
    "User.Read",
    "Mail.Read"
]


def get_access_token(
    on_device_code=None
):

    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY
    )

    accounts = app.get_accounts()

    if accounts:

        result = app.acquire_token_silent(
            SCOPES,
            account=accounts[0]
        )

        if result and "access_token" in result:

            return result["access_token"]

    flow = app.initiate_device_flow(
        scopes=SCOPES
    )

    if "user_code" not in flow:

        raise Exception(
            f"Unable to start device authentication: {flow}"
        )

    message = flow["message"]

    if on_device_code:

        on_device_code(message)

    else:

        print(message)

    result = app.acquire_token_by_device_flow(
        flow
    )

    if "access_token" not in result:

        raise Exception(
            f"Authentication failed: {result}"
        )

    return result["access_token"]