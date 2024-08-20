import logging
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

def is_valid_media_item_id(service, media_item_id):
    try:
        response = service.mediaItems().get(mediaItemId=media_item_id).execute()
        return True
    except Exception as e:
        logging.error(f"Invalid media item ID {media_item_id}: {e}")
        return False

def add_media_items_to_album(service, album_id, media_item_ids):
    batch_size = 50
   
    is_valid_media_item_id(service, media_item_ids[0])

    for batch in split_into_batches(media_item_ids, batch_size):
        body = {
            'mediaItemIds': [media_item_ids[23]]
        }
        response = service.albums().batchAddMediaItems(albumId=album_id, body=body).execute()
    return response

def is_valid_whatsapp_photo_or_video_filename(filename):
    pattern = r'^(IMG-\d{8}-WA\d{4}\.jpg|VID-\d{8}-WA\d{4}\.mp4)$'
    return re.match(pattern, filename) is not None

def find_album_by_title(albums, title):
    for album in albums:
        if 'title' in album and album['title'] == title:
            return album
    return None

def get_all_albums(service):
    albums = []
    nextPageToken = None
    while True:
        results = service.albums().list(
            pageSize=50, fields="nextPageToken,albums(id,title)", pageToken=nextPageToken).execute()
        albums += results.get('albums', [])
        nextPageToken = results.get('nextPageToken', None)
        if not nextPageToken:
            break
    return albums

def get_last_added_media_item_in_album(service, album):
    album_id = album['id']
    media_items = []
    nextPageToken = None

    # Retrieve all media items in the album
    while True:
        response = service.mediaItems().search(body={'albumId': album_id, 'pageToken': nextPageToken}).execute()
        media_items.extend(response.get('mediaItems', []))
        nextPageToken = response.get('nextPageToken')
        if not nextPageToken:
            break

    if not media_items:
        return None

    # Sort media items by creation time
    media_items.sort(key=lambda item: item['mediaMetadata']['creationTime'])

    # Get the last added media item
    last_added_media_item = media_items[-1]
    return last_added_media_item

def get_media_item_datetime(media_item):
    return datetime.strptime(media_item['mediaMetadata']['creationTime'], '%Y-%m-%dT%H:%M:%SZ')

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

    last_item_date_time = None    
    WA_MEDIA_ALBUM_TITLE = "WhatsApp-Media-Items"
    DEFAULT_PERIOD_IN_DAYS = 100
    
    existing_albums = get_all_albums(service)
    wa_media_album = find_album_by_title(existing_albums, WA_MEDIA_ALBUM_TITLE)
    if wa_media_album:
        # Get the date and time of the media item that was the last to upload to Google Photos from a specific album
        last_media_item = get_last_added_media_item_in_album(service, wa_media_album)
        if last_media_item:
            last_item_date_time = get_media_item_datetime(last_media_item)

    # Get a specific period of time
    end_date = datetime.now(timezone.utc)
    if last_item_date_time:
        start_date = last_item_date_time + timedelta(seconds=1)
    else:
        start_date = end_date - timedelta(days=DEFAULT_PERIOD_IN_DAYS)

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
        print("Scanned {0} photos, found {1} whatsApp.".format(total_media_items, len(whatsapp_media_items)))
        if not nextPageToken:
            break
    
    print('Found {0} WhatsApp photos from total {1} photos.'.format(len(whatsapp_media_items), total_media_items))
        

    # Create a new album for WhatsApp media items
    if(not wa_media_album):
        wa_media_album = create_album(service, WA_MEDIA_ALBUM_TITLE)
        print(f"Created album: {wa_media_album['title']} (ID: {wa_media_album['id']})")
    else:
        print(f"Album already exists: {wa_media_album['title']} (ID: {wa_media_album['id']})")

    # Add WhatsApp media items to the new album
    media_item_ids = [media_item['id'] for media_item in whatsapp_media_items]
    add_media_items_to_album(service, wa_media_album['id'], media_item_ids)
    print(f"Added {len(whatsapp_media_items)} WhatsApp media items to the album.")


if __name__ == '__main__':
    main()