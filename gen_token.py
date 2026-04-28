from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id":     "REDACTED_GMAIL_CLIENT_ID",
            "client_secret": "REDACTED_GMAIL_CLIENT_SECRET",
            "redirect_uris": ["http://localhost"],
            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
            "token_uri":     "https://oauth2.googleapis.com/token",
        }
    },
    scopes=["https://www.googleapis.com/auth/gmail.send"],
)

creds = flow.run_local_server(port=0)
print(f"\nGMAIL_REFRESH_TOKEN={creds.refresh_token}")