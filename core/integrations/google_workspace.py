import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import datetime

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def get_google_creds():
    """Gets valid user credentials from storage."""
    creds = None
    # Assuming local desktop first - token.json
    # TODO: In production, store this securely per-user in Supabase or local_db
    token_path = os.path.join(os.path.dirname(__file__), 'google_token.json')
    creds_path = os.path.join(os.path.dirname(__file__), 'google_credentials.json')

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        
        if not creds and os.path.exists(creds_path):
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
    return creds

def read_emails(max_results=5):
    """Read recent emails from Gmail."""
    creds = get_google_creds()
    if not creds:
        return "Google Workspace not configured or not authorized. Please add google_credentials.json."
        
    try:
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().messages().list(userId='me', maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            return 'No new messages.'
            
        output = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='metadata').execute()
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            snippet = msg.get('snippet', '')
            output.append(f"From: {sender}\nSubject: {subject}\nSnippet: {snippet}\n---")
            
        return "\n".join(output)
    except Exception as e:
        return f"An error occurred reading emails: {e}"

def check_calendar(days=1):
    """Check Google Calendar for upcoming events."""
    creds = get_google_creds()
    if not creds:
        return "Google Workspace not configured or not authorized."
        
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=days)).isoformat() + 'Z'
        
        events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=time_max,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return f'No upcoming events found for the next {days} day(s).'

        output = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Busy')
            output.append(f"{start}: {summary}")
            
        return "\n".join(output)
    except Exception as e:
        return f"An error occurred reading calendar: {e}"
