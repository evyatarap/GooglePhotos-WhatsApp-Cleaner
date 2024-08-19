import os
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/photoslibrary']

def print_albums(albums):
    if not albums:
        print('No albums found.')
    else:
        print('Albums:')
        for album in albums:
            print(f'Album: {album["title"]}, id: {album["id"]}')

def create_album(service, album_title):
    album_body = {
        'album': {'title': album_title}
    }
    created_album = service.albums().create(body=album_body).execute()
    return created_album

def split_into_batches(media_items, batch_size):
    for i in range(0, len(media_items), batch_size):
        yield media_items[i:i + batch_size]

def add_media_items_to_album(service, album_id, media_item_ids):
    batch_size = 50
    for batch in split_into_batches(media_item_ids, batch_size):
        body = {
            'mediaItemIds': batch
        }
        response = service.albums().batchAddMediaItems(albumId=album_id, body=body).execute()
    return response

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
            "pageSize": 100,
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
    
    # Get a specific period of time
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=365*2)


    # Scan all media items between the start and end date and filter out WhatsApp media items
    whatsapp_media_items = []
    nextPageToken = None
    total_media_items = 0
    while True:
        [photos, nextPageToken] = get_photos_by_date(service, start_date, end_date, nextPageToken)
        total_media_items += len(photos)
        for photo in photos:
            if is_valid_whatsapp_photo_or_video_filename(photo['filename']):
                whatsapp_media_items.append(photo)
            #print('FileName: {0}'.format(photo['filename']))
        print("Scanned {0} photos, found {1} whatsApp.".format(total_media_items, len(whatsapp_media_items)))
        if not nextPageToken:
            break
    
    print('Found {0} WhatsApp photos from total {1} photos.'.format(len(whatsapp_media_items), total_media_items))

    # Create a new album
    album_title = "WhatsApp-Media-Items"
    wa_media_album = create_album(service, album_title)
    print(f"Created album: {wa_media_album['title']} (ID: {wa_media_album['id']})")

    # Add WhatsApp media items to the new album
    media_item_ids = [media_item['id'] for media_item in whatsapp_media_items]
    add_media_items_to_album(service, wa_media_album['id'], media_item_ids)
    



if __name__ == '__main__':
    main()