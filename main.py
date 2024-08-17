import os
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

def print_albums(albums):
    if not albums:
        print('No albums found.')
    else:
        print('Albums:')
        for album in albums:
            print(f'Album: {album["title"]}, id: {album["id"]}')

def is_valid_whatsapp_photo_or_video_filename(filename):
    pattern = r'^(IMG-\d{8}-WA\d{4}\.jpg|VID-\d{8}-WA\d{4}\.mp4)$'
    return re.match(pattern, filename) is not None

def get_albums(service):
    results = service.albums().list(
        pageSize=50, fields="nextPageToken,albums(id,title)").execute()
    items = results.get('albums', [])
    return items

def get_photos_by_date(service, start_date, end_date, nextPageToken=None):

    # Create the date range filter
    date_range_filter = {
        "dateFilter": {
            "ranges": [
                {
                    "startDate": {
                        "year": start_date.year,
                        "month": start_date.month,
                        "day": start_date.day
                    },
                    "endDate": {
                        "year": end_date.year,
                        "month": end_date.month,
                        "day": end_date.day
                    }
                }
            ]
        }
    }
    

    results = service.mediaItems().search(
        body={
            "filters": date_range_filter,
            "pageSize": 50,
            "pageToken": nextPageToken
        }
    ).execute()

    items = results.get('mediaItems', [])
    return [items, results.get('nextPageToken', None)]

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

    albums = get_albums(service)
    
    # Get photos from the last week
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=365)

    whatsapp_photos = []

    nextPageToken = None
    total_photos = 0
    while True:
        [photos, nextPageToken] = get_photos_by_date(service, start_date, end_date, nextPageToken)
        total_photos += len(photos)
        for photo in photos:
            if is_valid_whatsapp_photo_or_video_filename(photo['filename']):
                whatsapp_photos.append(photo)
            #print('FileName: {0}'.format(photo['filename']))
        print("Scanned {0} photos.".format(total_photos))
        if not nextPageToken:
            break

    print('Found {0} WhatsApp photos from total {1} photos.'.format(len(whatsapp_photos), total_photos))

if __name__ == '__main__':
    main()