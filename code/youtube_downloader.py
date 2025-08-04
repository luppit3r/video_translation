import yt_dlp
import os
import sys
from pathlib import Path
import argparse

def download_youtube_video(url, output_dir="./downloads", quality="best"):
    """
    Pobiera video z YouTube w najlepszej jakości.
    
    Args:
        url: URL do video YouTube
        output_dir: Katalog docelowy
        quality: Jakość video ('best', 'worst', '720p', '1080p', etc.)
    """
    
    # Utwórz katalog jeśli nie istnieje
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Konfiguracja yt-dlp
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',  # Najlepsze MP4
        'outtmpl': str(output_path / '%(title)s.%(ext)s'),  # Nazwa pliku
        'writeinfojson': False,  # Nie zapisuj metadanych
        'writesubtitles': False,  # Nie pobieraj napisów
        'writeautomaticsub': False,  # Nie pobieraj auto-napisów
        'ignoreerrors': False,  # Zatrzymaj przy błędach
    }
    
    # Opcje jakości
    if quality == "best":
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
    elif quality == "720p":
        ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
    elif quality == "1080p":
        ydl_opts['format'] = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
    elif quality == "4k":
        ydl_opts['format'] = 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Pobierz informacje o video
            print("Pobieranie informacji o video...")
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'Nieznany tytuł')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'Nieznany autor')
            
            print(f"Tytuł: {title}")
            print(f"Autor: {uploader}")
            print(f"Długość: {duration//60}:{duration%60:02d}")
            print()
            
            # Pobierz video
            print("Rozpoczynam pobieranie...")
            ydl.download([url])
            
            # Znajdź pobrany plik
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            expected_file = output_path / f"{safe_title}.mp4"
            
            # Znajdź rzeczywisty plik (może mieć nieco inną nazwę)
            downloaded_files = list(output_path.glob("*.mp4"))
            if downloaded_files:
                latest_file = max(downloaded_files, key=os.path.getctime)
                print(f"[SUKCES] Pobrano pomyślnie: {latest_file}")
                return str(latest_file)
            else:
                print("[BLAD] Nie znaleziono pobranego pliku")
                return None
                
    except Exception as e:
        print(f"[BLAD] Błąd podczas pobierania: {str(e)}")
        return None

def list_formats(url):
    """Wyświetla dostępne formaty dla danego URL."""
    ydl_opts = {
        'listformats': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"Błąd podczas pobierania listy formatów: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Pobierz video z YouTube w najlepszej jakości')
    parser.add_argument('url', help='URL do video YouTube')
    parser.add_argument('-o', '--output', default='./downloads', 
                       help='Katalog docelowy (domyślnie: ./downloads)')
    parser.add_argument('-q', '--quality', default='best',
                       choices=['best', '720p', '1080p', '4k'],
                       help='Jakość video (domyślnie: best)')
    parser.add_argument('-l', '--list-formats', action='store_true',
                       help='Wyświetl dostępne formaty i wyjdź')
    
    args = parser.parse_args()
    
    if args.list_formats:
        print("Dostępne formaty:")
        list_formats(args.url)
        return
    
    print(f"Pobieranie z: {args.url}")
    print(f"Katalog docelowy: {args.output}")
    print(f"Jakość: {args.quality}")
    print("-" * 50)
    
    result = download_youtube_video(args.url, args.output, args.quality)
    
    if result:
        print("\n[SUKCES] Pobieranie zakończone pomyślnie!")
        print(f"Plik: {result}")
    else:
        print("\n[BLAD] Pobieranie nie powiodło się!")
        sys.exit(1)

if __name__ == "__main__":
    main()