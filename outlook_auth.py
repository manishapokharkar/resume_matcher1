
import os
from pathlib import Path

import msal
import streamlit as st

from dotenv import load_dotenv
from msal_extensions import (
    PersistedTokenCache,
    build_encrypted_persistence,
)


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# MICROSOFT / AZURE CONFIGURATION
# ============================================================

def get_config_value(key):
    """
    Get configuration from the local .env file
    or Streamlit Cloud Secrets.
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
        "Add it to your local .env file "
        "or Streamlit Cloud Secrets."
    )

if not TENANT_ID:
    raise ValueError(
        "TENANT_ID is not configured. "
        "Add it to your local .env file "
        "or Streamlit Cloud Secrets."
    )


# ============================================================
# MICROSOFT AUTHORITY AND PERMISSIONS
# ============================================================

AUTHORITY = (
    f"https://login.microsoftonline.com/{TENANT_ID}"
)

SCOPES = [
    "User.Read",
    "Mail.Read",
]


# ============================================================
# PERSISTENT TOKEN CACHE
# ============================================================

CACHE_DIRECTORY = Path.home() / ".resume_matcher"

CACHE_FILE = (
    CACHE_DIRECTORY / "msal_token_cache.bin"
)


def create_token_cache():
    """
    Create an encrypted token cache on this computer.

    The cache can survive application restarts.
    Windows protects the encrypted cache using
    the current Windows user's security context.
    """

    CACHE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    persistence = build_encrypted_persistence(
        str(CACHE_FILE)
    )

    return PersistedTokenCache(persistence)


# ============================================================
# GET ACCESS TOKEN
# ============================================================

def get_access_token(on_device_code=None):
    """
    Get a Microsoft Graph access token.

    1. Load the persistent token cache.
    2. Try silent authentication.
    3. Request device-code login only when necessary.
    4. Return the access token.
    """

    # Load the saved encrypted token cache.
    token_cache = create_token_cache()

    # Give MSAL the persistent cache.
    app = msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        token_cache=token_cache,
    )

    # Look for previously authenticated accounts.
    accounts = app.get_accounts()

    if accounts:
        result = app.acquire_token_silent(
            scopes=SCOPES,
            account=accounts[0],
        )

        if result and "access_token" in result:
            return result["access_token"]

    # No usable cached token: begin Microsoft login.
    flow = app.initiate_device_flow(
        scopes=SCOPES
    )

    if "user_code" not in flow:
        error_description = flow.get(
            "error_description",
            "Unknown Microsoft authentication error.",
        )

        raise Exception(
            "Unable to start Microsoft device authentication: "
            f"{error_description}"
        )

    message = flow.get(
        "message",
        "Open Microsoft's device login page and enter the code.",
    )

    if on_device_code:
        on_device_code(message)
    else:
        print(message)

    # Wait for the user to finish signing in.
    result = app.acquire_token_by_device_flow(flow)

    if not result:
        raise Exception(
            "Microsoft authentication returned no result."
        )

    if "access_token" not in result:
        error = result.get("error", "unknown_error")

        error_description = result.get(
            "error_description",
            "Microsoft authentication failed.",
        )

        raise Exception(
            "Microsoft authentication failed.\n"
            f"Error: {error}\n"
            f"Details: {error_description}"
        )

    # MSAL updates the persistent cache automatically.
    return result["access_token"]
