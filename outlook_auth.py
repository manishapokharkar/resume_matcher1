import os
import msal
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

SCOPES = [
    "User.Read",
    "Mail.Read"
]

_msal_app = None

def get_access_token(on_device_code=None):
    global _msal_app

    if not CLIENT_ID or not TENANT_ID:
        raise RuntimeError("Set CLIENT_ID and TENANT_ID in your .env file before connecting Outlook.")

    if _msal_app is None:
        _msal_app = msal.PublicClientApplication(
            CLIENT_ID,
            authority=AUTHORITY
        )

    app = _msal_app

    # Try to use an existing login first
    accounts = app.get_accounts()

    if accounts:
        result = app.acquire_token_silent(
            SCOPES,
            account=accounts[0]
        )

        if result and "access_token" in result:
            return result["access_token"]

    # If there is no existing login, use device code login
    flow = app.initiate_device_flow(
        scopes=SCOPES
    )

    if "user_code" not in flow:
        raise Exception(
            "Unable to start device authentication"
        )

    if on_device_code:
        on_device_code(flow["message"])
    else:
        print(flow["message"])

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise Exception(
            f"Authentication failed: {result}"
        )

    return result["access_token"]