import os
import msal
import streamlit as st

from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

# Loads values from local .env file
# This is used when running the application on your computer.
load_dotenv()


# ============================================================
# MICROSOFT / AZURE CONFIGURATION
# ============================================================

def get_config_value(key):
    """
    Get configuration value from:

    1. Local environment / .env
    2. Streamlit Cloud Secrets

    This allows the same code to work both locally
    and on Streamlit Cloud.
    """

    value = os.getenv(key)

    if value:
        return value.strip()

    try:
        value = st.secrets.get(key, "")
    except Exception:
        value = ""

    if value:
        return str(value).strip()

    return ""


CLIENT_ID = get_config_value("CLIENT_ID")
TENANT_ID = get_config_value("TENANT_ID")


# ============================================================
# VALIDATE CONFIGURATION
# ============================================================

if not CLIENT_ID:
    raise ValueError(
        "CLIENT_ID is not configured. "
        "Add CLIENT_ID to your .env file locally "
        "or Streamlit Cloud Secrets."
    )


if not TENANT_ID:
    raise ValueError(
        "TENANT_ID is not configured. "
        "Add TENANT_ID to your .env file locally "
        "or Streamlit Cloud Secrets."
    )


# ============================================================
# MICROSOFT AUTHORITY
# ============================================================

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"


# ============================================================
# MICROSOFT GRAPH PERMISSIONS
# ============================================================

SCOPES = [
    "User.Read",
    "Mail.Read",
]


# ============================================================
# GET ACCESS TOKEN
# ============================================================

def get_access_token(on_device_code=None):
    """
    Authenticate the user with Microsoft.

    Authentication flow:

    1. Try existing cached Microsoft account.
    2. Try silent authentication.
    3. If silent authentication fails,
       start Microsoft Device Code authentication.
    4. Return Microsoft Graph access token.

    Parameters
    ----------
    on_device_code : callable, optional
        Callback function used by Streamlit to display
        the Microsoft device-login instructions.

    Returns
    -------
    str
        Microsoft Graph access token.
    """

    # --------------------------------------------------------
    # Create MSAL Public Client Application
    # --------------------------------------------------------

    app = msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
    )

    # --------------------------------------------------------
    # Check existing logged-in accounts
    # --------------------------------------------------------

    accounts = app.get_accounts()

    if accounts:

        result = app.acquire_token_silent(
            scopes=SCOPES,
            account=accounts[0],
        )

        if result and "access_token" in result:

            return result["access_token"]

    # --------------------------------------------------------
    # Start Device Code Authentication
    # --------------------------------------------------------

    flow = app.initiate_device_flow(
        scopes=SCOPES
    )

    # Microsoft should return a user_code.
    # If not, authentication could not be started.

    if "user_code" not in flow:

        error_description = flow.get(
            "error_description",
            "Unknown Microsoft authentication error."
        )

        raise Exception(
            f"Unable to start Microsoft device authentication: "
            f"{error_description}"
        )

    # --------------------------------------------------------
    # Microsoft Login Instructions
    # --------------------------------------------------------

    message = flow.get(
        "message",
        "Open the Microsoft device login page and enter the provided code."
    )

    # If the Streamlit application supplied a callback,
    # display the message through the UI.

    if on_device_code:

        on_device_code(message)

    else:

        print(message)

    # --------------------------------------------------------
    # Wait for User Authentication
    # --------------------------------------------------------

    result = app.acquire_token_by_device_flow(
        flow
    )

    # --------------------------------------------------------
    # Check Authentication Result
    # --------------------------------------------------------

    if not result:

        raise Exception(
            "Microsoft authentication returned no result."
        )

    if "access_token" not in result:

        error = result.get(
            "error",
            "unknown_error"
        )

        error_description = result.get(
            "error_description",
            "Microsoft authentication failed."
        )

        raise Exception(
            f"Microsoft authentication failed.\n"
            f"Error: {error}\n"
            f"Details: {error_description}"
        )

    # --------------------------------------------------------
    # Return Access Token
    # --------------------------------------------------------

    return result["access_token"]