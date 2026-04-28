from google_auth_oauthlib.flow import InstalledAppFlow
import json

CLIENT_CONFIG = {
    "installed": {
        "client_id": "REDACTED_GMAIL_CLIENT_ID",
        "client_secret": "REDACTED_GMAIL_CLIENT_SECRET",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = InstalledAppFlow.from_client_config(
    CLIENT_CONFIG,
    scopes=["https://www.googleapis.com/auth/gmail.send"]
)

creds = flow.run_local_server(port=8080)
print("\n✅ Nouveau REFRESH_TOKEN :")
print(creds.refresh_token)