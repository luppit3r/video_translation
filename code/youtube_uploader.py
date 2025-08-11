#!/usr/bin/env python3
"""
YouTube Uploader - Moduł do automatycznego uploadu wideo na YouTube
Wymaga: google-api-python-client, google-auth-httplib2, google-auth-oauthlib
"""

import os
import pickle
import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.http import MediaUpload
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    print("⚠️ YouTube API nie jest dostępne. Zainstaluj: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

# Konfiguracja YouTube API
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/youtube'
]
CLIENT_SECRETS_FILE = Path(__file__).parent / "client_secrets.json"
TOKEN_FILE = Path(__file__).parent / "token.pickle"

# Mapowanie kategorii YouTube
YOUTUBE_CATEGORIES = {
    "Education": "27",
    "Science & Technology": "28", 
    "Howto & Style": "26",
    "Entertainment": "24",
    "People & Blogs": "22",
    "Gaming": "20",
    "Music": "10",
    "Film & Animation": "1",
    "News & Politics": "25",
    "Comedy": "23",
    "Sports": "17",
    "Travel & Events": "19",
    "Autos & Vehicles": "2",
    "Pets & Animals": "15"
}

class YouTubeUploader:
    """Klasa do obsługi uploadu wideo na YouTube"""
    
    def __init__(self, client_secrets_file: str = None):
        """
        Inicjalizuje YouTube Uploader
        
        Args:
            client_secrets_file: Ścieżka do pliku client_secrets.json
        """
        if not YOUTUBE_API_AVAILABLE:
            raise ImportError("YouTube API nie jest dostępne. Zainstaluj wymagane biblioteki.")
        
        self.client_secrets_file = client_secrets_file or str(CLIENT_SECRETS_FILE)
        self.youtube = None
        self.credentials = None
        
    def authenticate(self) -> bool:
        """
        Autoryzuje użytkownika przez OAuth2
        
        Returns:
            bool: True jeśli autoryzacja się powiodła
        """
        try:
            # Sprawdź czy istnieje zapisany token
            if TOKEN_FILE.exists():
                with open(TOKEN_FILE, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # Jeśli nie ma ważnych credentials, poproś o nowe
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    if not Path(self.client_secrets_file).exists():
                        raise FileNotFoundError(
                            f"Plik {self.client_secrets_file} nie istnieje. "
                            "Pobierz go z Google Cloud Console."
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.client_secrets_file, SCOPES)
                    self.credentials = flow.run_local_server(port=0)
                
                # Zapisz credentials do pliku
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(self.credentials, token)
            
            # Buduj YouTube API service
            self.youtube = build('youtube', 'v3', credentials=self.credentials)
            return True
            
        except Exception as e:
            print(f"❌ Błąd autoryzacji: {e}")
            return False
    
    def upload_video(self, 
                    video_path: str,
                    title: str,
                    description: str = "",
                    tags: List[str] = None,
                    category: str = "Education",
                    privacy: str = "private",
                    thumbnail_path: str = None,
                    publish_at_iso: Optional[str] = None,
                    progress_callback=None) -> Dict:
        """
        Uploaduje wideo na YouTube
        
        Args:
            video_path: Ścieżka do pliku wideo
            title: Tytuł wideo
            description: Opis wideo
            tags: Lista tagów
            category: Kategoria wideo
            privacy: Prywatność (private/unlisted/public)
            thumbnail_path: Ścieżka do miniaturki
            progress_callback: Funkcja callback do raportowania postępu
            
        Returns:
            Dict: Wynik uploadu z ID wideo i URL
        """
        if not self.youtube:
            if not self.authenticate():
                raise Exception("Nie udało się autoryzować z YouTube API")
        
        try:
            # Sprawdź czy plik wideo istnieje
            if not Path(video_path).exists():
                raise FileNotFoundError(f"Plik wideo nie istnieje: {video_path}")
            
            # Przygotuj body request
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags or [],
                    'categoryId': YOUTUBE_CATEGORIES.get(category, "27")  # Domyślnie Education
                },
                'status': {
                    'privacyStatus': privacy,
                    'selfDeclaredMadeForKids': False
                }
            }

            # Planowanie publikacji: jeśli podano publish_at_iso, YouTube wymaga privacyStatus="private"
            # oraz ustawienia pola status.publishAt (RFC3339). Film zostanie opublikowany automatycznie o tej dacie.
            if publish_at_iso:
                # Wymuś private dla harmonogramu (API tak oczekuje)
                body['status']['privacyStatus'] = 'private'
                body['status']['publishAt'] = publish_at_iso
            
            # Utwórz MediaFileUpload
            media = MediaFileUpload(
                video_path, 
                chunksize=1024*1024,  # 1MB chunks
                resumable=True
            )
            
            if progress_callback:
                progress_callback(0, "Rozpoczynam upload...")
            
            # Wykonaj upload
            request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Monitoruj postęp
            response = None
            error = None
            retry = 0
            
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        if progress_callback:
                            progress = int(status.progress() * 100)
                            progress_callback(progress, f"Upload w toku... {progress}%")
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        error = f"Błąd serwera: {e}"
                        retry += 1
                        if retry > 3:
                            break
                        time.sleep(2 ** retry)  # Exponential backoff
                    else:
                        error = f"Błąd HTTP: {e}"
                        break
            
            if error:
                raise Exception(error)
            
            if progress_callback:
                progress_callback(100, "Upload zakończony!")
            
            # Upload miniaturki jeśli podano
            if thumbnail_path and Path(thumbnail_path).exists():
                try:
                    self.youtube.thumbnails().set(
                        videoId=response['id'],
                        media_body=MediaFileUpload(thumbnail_path)
                    ).execute()
                    if progress_callback:
                        progress_callback(100, "Miniaturka dodana!")
                except Exception as e:
                    print(f"⚠️ Nie udało się dodać miniaturki: {e}")
            
            # Przygotuj wynik
            video_url = f"https://www.youtube.com/watch?v={response['id']}"
            
            return {
                'success': True,
                'video_id': response['id'],
                'video_url': video_url,
                'title': response['snippet']['title'],
                'privacy': response['status']['privacyStatus'],
                'publishAt': body['status'].get('publishAt')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_upload_status(self, video_id: str) -> Dict:
        """
        Sprawdza status uploadu wideo
        
        Args:
            video_id: ID wideo na YouTube
            
        Returns:
            Dict: Status wideo
        """
        if not self.youtube:
            if not self.authenticate():
                raise Exception("Nie udało się autoryzować z YouTube API")
        
        try:
            response = self.youtube.videos().list(
                part="status,processingDetails",
                id=video_id
            ).execute()
            
            if response['items']:
                video = response['items'][0]
                return {
                    'uploadStatus': video['status']['uploadStatus'],
                    'privacyStatus': video['status']['privacyStatus'],
                    'processingStatus': video.get('processingDetails', {}).get('processingStatus', 'unknown')
                }
            else:
                return {'error': 'Wideo nie znalezione'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def get_channel_videos(self, channel_id: str = None, max_results: int = 10) -> Dict:
        """
        Pobiera listę wideo z kanału
        
        Args:
            channel_id: ID kanału (jeśli None, używa własnego kanału)
            max_results: Maksymalna liczba wyników
            
        Returns:
            Dict: Lista wideo z metadanymi
        """
        if not self.youtube:
            if not self.authenticate():
                raise Exception("Nie udało się autoryzować z YouTube API")
        
        try:
            # Jeśli nie podano channel_id, pobierz własny kanał
            if not channel_id:
                channels_response = self.youtube.channels().list(
                    part="id",
                    mine=True
                ).execute()
                
                if not channels_response['items']:
                    return {'error': 'Nie znaleziono kanału'}
                
                channel_id = channels_response['items'][0]['id']
            
            # Pobierz wideo z kanału
            search_response = self.youtube.search().list(
                part="id,snippet",
                channelId=channel_id,
                order="date",  # Najnowsze pierwsze
                type="video",
                maxResults=max_results
            ).execute()
            
            videos = []
            for item in search_response['items']:
                video_id = item['id']['videoId']
                
                # Pobierz szczegółowe informacje o wideo
                video_response = self.youtube.videos().list(
                    part="snippet,statistics,contentDetails",
                    id=video_id
                ).execute()
                
                if video_response['items']:
                    video = video_response['items'][0]
                    snippet = video['snippet']
                    statistics = video.get('statistics', {})
                    content_details = video.get('contentDetails', {})
                    
                    videos.append({
                        'id': video_id,
                        'title': snippet['title'],
                        'description': snippet['description'],
                        'tags': snippet.get('tags', []),
                        'category': snippet.get('categoryId', ''),
                        'published_at': snippet['publishedAt'],
                        'thumbnail': snippet['thumbnails']['high']['url'],
                        'duration': content_details.get('duration', ''),
                        'view_count': statistics.get('viewCount', '0'),
                        'like_count': statistics.get('likeCount', '0'),
                        'comment_count': statistics.get('commentCount', '0'),
                        'privacy_status': video.get('status', {}).get('privacyStatus', 'unknown')
                    })
            
            return {
                'success': True,
                'channel_id': channel_id,
                'videos': videos,
                'total_count': len(videos)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_latest_video(self) -> Dict:
        """
        Pobiera informacje o najnowszym wideo na kanale
        
        Returns:
            Dict: Informacje o najnowszym wideo
        """
        result = self.get_channel_videos(max_results=1)
        
        if result.get('success') and result.get('videos'):
            return {
                'success': True,
                'latest_video': result['videos'][0]
            }
        else:
            return result
    
    def update_video_metadata(self, video_id: str, title: str = None, 
                            description: str = None, tags: List[str] = None,
                            category: str = None) -> Dict:
        """
        Aktualizuje metadane wideo
        
        Args:
            video_id: ID wideo
            title: Nowy tytuł
            description: Nowy opis
            tags: Nowe tagi
            category: Nowa kategoria
            
        Returns:
            Dict: Wynik aktualizacji
        """
        if not self.youtube:
            if not self.authenticate():
                raise Exception("Nie udało się autoryzować z YouTube API")
        
        try:
            # Pobierz aktualne metadane
            current_response = self.youtube.videos().list(
                part="snippet",
                id=video_id
            ).execute()
            
            if not current_response['items']:
                return {'error': 'Wideo nie znalezione'}
            
            current_snippet = current_response['items'][0]['snippet']
            
            # Przygotuj nowe metadane
            new_snippet = {
                'title': title or current_snippet['title'],
                'description': description or current_snippet['description'],
                'tags': tags or current_snippet.get('tags', []),
                'categoryId': YOUTUBE_CATEGORIES.get(category, current_snippet.get('categoryId', '27'))
            }
            
            # Aktualizuj wideo
            update_response = self.youtube.videos().update(
                part="snippet",
                body={
                    'id': video_id,
                    'snippet': new_snippet
                }
            ).execute()
            
            return {
                'success': True,
                'video_id': video_id,
                'updated_title': update_response['snippet']['title'],
                'updated_description': update_response['snippet']['description'],
                'updated_tags': update_response['snippet'].get('tags', [])
            }
            
        except Exception as e:
            return {'error': str(e)}

def test_youtube_api():
    """Funkcja testowa do sprawdzenia YouTube API"""
    try:
        uploader = YouTubeUploader()
        if uploader.authenticate():
            print("✅ Autoryzacja YouTube API udana!")
            
            # Test pobierania ostatniego wideo
            print("\n📊 Pobieranie informacji o ostatnim wideo...")
            latest_result = uploader.get_latest_video()
            
            if latest_result.get('success'):
                video = latest_result['latest_video']
                print(f"🎬 Ostatnie wideo:")
                print(f"   Tytuł: {video['title']}")
                print(f"   ID: {video['id']}")
                print(f"   Wyświetlenia: {video['view_count']}")
                print(f"   Polubienia: {video['like_count']}")
                print(f"   Data publikacji: {video['published_at']}")
                print(f"   Miniaturka: {video['thumbnail']}")
                print(f"   Prywatność: {video['privacy_status']}")
            else:
                print(f"❌ Błąd pobierania wideo: {latest_result.get('error')}")
            
            return True
        else:
            print("❌ Autoryzacja YouTube API nieudana!")
            return False
    except Exception as e:
        print(f"❌ Błąd testu YouTube API: {e}")
        return False

if __name__ == "__main__":
    test_youtube_api() 