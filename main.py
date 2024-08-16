import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

def main():
    """Shows basic usage of the Google Photos API."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES, redirect_uri='http://localhost:8080')
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f'Please go to this URL: {auth_url}')
            code = input('Enter the authorization code: ')
            flow.fetch_token(code=code)
            creds = flow.credentials
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('photoslibrary', 'v1', credentials=creds, static_discovery=False)

    # Call the Photos API
    results = service.albums().list(
        pageSize=10, fields="nextPageToken,albums(id,title)").execute()
    items = results.get('albums', [])

    if not items:
        print('No albums found.')
    else:
        print('Albums:')
        for item in items:
            print('{0} ({1})'.format(item['title'], item['id']))

if __name__ == '__main__':
    main()