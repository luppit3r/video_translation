import cv2
import numpy as np
import argparse
from pathlib import Path
from moviepy.editor import VideoFileClip, concatenate_videoclips
from tqdm import tqdm
import json
from datetime import datetime

class VideoIntroOutroAdder:
    def __init__(self, intro_path=None, outro_path=None):
        """
        Inicjalizacja narzędzia do dodawania intro i outro.
        
        Args:
            intro_path: Ścieżka do pliku intro (opcjonalnie)
            outro_path: Ścieżka do pliku outro (opcjonalnie)
        """
        self.intro_path = intro_path
        self.outro_path = outro_path
        
    def add_intro_outro(self, video_path, output_path, add_intro=True, add_outro=True):
        """
        Dodaj intro i/o outro do wideo.
        
        Args:
            video_path: Ścieżka do głównego pliku wideo
            output_path: Ścieżka do pliku wyjściowego
            add_intro: Czy dodać intro
            add_outro: Czy dodać outro
        """
        print(f"Przetwarzanie wideo: {video_path}")
        
        # Lista klipów do połączenia
        clips = []
        
        # Dodaj intro jeśli wymagane
        if add_intro and self.intro_path and Path(self.intro_path).exists():
            print(f"Dodawanie intro: {self.intro_path}")
            intro_clip = VideoFileClip(str(self.intro_path))
            clips.append(intro_clip)
            print(f"  Czas trwania intro: {intro_clip.duration:.2f}s")
        
        # Dodaj główne wideo
        print(f"Ładowanie głównego wideo: {video_path}")
        main_clip = VideoFileClip(str(video_path))
        clips.append(main_clip)
        print(f"  Czas trwania głównego wideo: {main_clip.duration:.2f}s")
        
        # Dodaj outro jeśli wymagane
        if add_outro and self.outro_path and Path(self.outro_path).exists():
            print(f"Dodawanie outro: {self.outro_path}")
            outro_clip = VideoFileClip(str(self.outro_path))
            clips.append(outro_clip)
            print(f"  Czas trwania outro: {outro_clip.duration:.2f}s")
        
        # Połącz wszystkie klipy
        print("Łączenie klipów...")
        final_clip = concatenate_videoclips(clips, method="compose")
        
        # Zapisz wynik z zoptymalizowanymi ustawieniami
        print(f"Zapisywanie do: {output_path}")
        final_clip.write_videofile(
            str(output_path),
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None,
            preset='veryfast',  # Szybsze kodowanie niż ultrafast (lepszy balans szybkość/jakość)
            threads=8,  # Więcej wątków dla lepszej wydajności
            ffmpeg_params=['-crf', '23', '-movflags', '+faststart']  # Optymalizacje ffmpeg
        )
        
        # Wyświetl podsumowanie
        total_duration = final_clip.duration
        print(f"\n[SUKCES] Wideo zostało pomyślnie utworzone!")
        print(f"Całkowity czas trwania: {total_duration:.2f}s ({total_duration/60:.1f} min)")
        
        # Zwolnij zasoby
        final_clip.close()
        for clip in clips:
            clip.close()
        
        return output_path
    
    def get_video_info(self, video_path):
        """Pobierz informacje o wideo."""
        try:
            clip = VideoFileClip(str(video_path))
            info = {
                'duration': clip.duration,
                'fps': clip.fps,
                'size': clip.size,
                'audio': clip.audio is not None
            }
            clip.close()
            return info
        except Exception as e:
            print(f"Błąd podczas pobierania informacji o wideo: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description="Dodaj intro i outro do wideo")
    parser.add_argument("video_path", help="Ścieżka do głównego pliku wideo")
    parser.add_argument("--intro", help="Ścieżka do pliku intro (domyślnie: intro_outro/Intro_EN.mp4)")
    parser.add_argument("--outro", help="Ścieżka do pliku outro (domyślnie: intro_outro/Outro_EN.mp4)")
    parser.add_argument("--output", help="Ścieżka do pliku wyjściowego")
    parser.add_argument("--no-intro", action="store_true", help="Nie dodawaj intro")
    parser.add_argument("--no-outro", action="store_true", help="Nie dodawaj outro")
    parser.add_argument("--info", action="store_true", help="Pokaż tylko informacje o wideo")
    
    args = parser.parse_args()
    
    # Sprawdź plik wideo
    video_path = Path(args.video_path)
    if not video_path.exists():
        print(f"Błąd: Plik wideo nie istnieje: {video_path}")
        return
    
    # Ustaw domyślne ścieżki intro/outro
    if not args.intro:
        args.intro = "../intro_outro/Intro_EN.mp4"
    if not args.outro:
        args.outro = "../intro_outro/Outro_EN.mp4"
    
    # Ustaw ścieżkę wyjściową
    if args.output:
        output_path = Path(args.output)
        # Dodaj rozszerzenie .mp4 jeśli nie ma rozszerzenia
        if not output_path.suffix:
            output_path = output_path.with_suffix('.mp4')
    else:
        output_path = video_path.with_stem(video_path.stem + "_with_intro_outro").with_suffix('.mp4')
    
    # Inicjalizuj narzędzie
    adder = VideoIntroOutroAdder(
        intro_path=args.intro,
        outro_path=args.outro
    )
    
    # Pokaż informacje o wideo jeśli wymagane
    if args.info:
        print("INFORMACJE O WIDEO:")
        print("=" * 30)
        
        # Główne wideo
        main_info = adder.get_video_info(video_path)
        if main_info:
            print(f"Główne wideo: {video_path.name}")
            print(f"  Czas trwania: {main_info['duration']:.2f}s ({main_info['duration']/60:.1f} min)")
            print(f"  Rozdzielczość: {main_info['size'][0]}x{main_info['size'][1]}")
            print(f"  FPS: {main_info['fps']}")
            print(f"  Audio: {'Tak' if main_info['audio'] else 'Nie'}")
        
        # Intro
        if Path(args.intro).exists():
            intro_info = adder.get_video_info(args.intro)
            if intro_info:
                print(f"\nIntro: {Path(args.intro).name}")
                print(f"  Czas trwania: {intro_info['duration']:.2f}s")
                print(f"  Rozdzielczość: {intro_info['size'][0]}x{intro_info['size'][1]}")
                print(f"  FPS: {intro_info['fps']}")
        
        # Outro
        if Path(args.outro).exists():
            outro_info = adder.get_video_info(args.outro)
            if outro_info:
                print(f"\nOutro: {Path(args.outro).name}")
                print(f"  Czas trwania: {outro_info['duration']:.2f}s")
                print(f"  Rozdzielczość: {outro_info['size'][0]}x{outro_info['size'][1]}")
                print(f"  FPS: {outro_info['fps']}")
        
        return
    
    try:
        # Dodaj intro i outro
        result_path = adder.add_intro_outro(
            video_path=video_path,
            output_path=output_path,
            add_intro=not args.no_intro,
            add_outro=not args.no_outro
        )
        
        print(f"\nPlik został zapisany: {result_path}")
        
    except Exception as e:
        print(f"Błąd podczas przetwarzania: {e}")
        return

if __name__ == "__main__":
    main() 