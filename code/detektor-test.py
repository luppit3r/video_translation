import cv2
import pytesseract
from moviepy.editor import VideoFileClip
import re
import numpy as np
from collections import defaultdict
import argparse
import os
from difflib import SequenceMatcher

class VideoTextDetector:
    def __init__(self, tesseract_path=None, additional_phrases=None):
        """
        Inicjalizacja detektora tekstu.
        
        Args:
            tesseract_path: Ścieżka do Tesseract OCR
            additional_phrases: Lista dodatkowych fraz do wykrycia w formacie:
                              [(wzorzec_regex, tekst_normalizujący), ...]
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
        # Domyślne frazy do wykrycia
        self.key_phrases = [
            # Bardziej elastyczne dopasowanie pierwszej frazy
            (r'przykład.*?oblicz.*?(?:narysowa[ćc]|narys).*?(?:wykres|sił|wewnętrz)', 
             'przykład obliczyć i narysować wykresy sił wewnętrznych'),
            (r'równania?\s+równowagi\s+statyczn[aeyią]?', 'równania równowagi statycznej'),
            (r'\bsprawdzenie\b', 'sprawdzenie')
        ]
        
        if additional_phrases:
            self.key_phrases.extend(additional_phrases)

    def extract_key_phrases(self, text):
        """
        Wyodrębnia wszystkie sensowne polskie wyrazy i frazy z tekstu.
        """
        # Normalizacja tekstu
        text = text.lower()
        
        # Najpierw sprawdź predefiniowane frazy
        detected_phrases = []
        for pattern, replacement in self.key_phrases:
            if re.search(pattern, text, re.IGNORECASE):
                detected_phrases.append(replacement)
                # Usuń znalezioną frazę z tekstu, aby nie interferowała z dalszym przetwarzaniem
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Czyszczenie tekstu
        text = re.sub(r'www\.[^\s]+', '', text)  # usuń URL
        text = re.sub(r'\d+(?:\.\d+)?(?:kn|knm|m|cm|mm|n|nm)?/?(?:m|s|h)?²?', '', text)  # usuń liczby i jednostki
        text = re.sub(r'[+\-=×÷*/<>≤≥≠(){}[\]|"\'`]', ' ', text)  # usuń symbole matematyczne
        
        # Podziel tekst na słowa
        words = text.split()
        polish_words = []
        
        for word in words:
            # Usuń znaki specjalne z początku i końca wyrazu
            word = word.strip('.,!?:;«»""\'')
            
            # Pomijaj puste słowa i zbyt krótkie
            if not word or (len(word) < 3 and word.lower() not in ['i', 'w', 'z', 'we', 'ze']):
                continue
                
            # Sprawdź czy to polski wyraz
            is_polish = False
            
            # Sprawdź polskie znaki
            if re.search(r'[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', word):
                is_polish = True
            
            # Sprawdź typowe polskie końcówki i wzorce
            polish_patterns = [
                r'ość$', r'ać$', r'eć$', r'ić$', r'yć$', r'ąć$', r'ęć$',
                r'anie$', r'enie$', r'[aeiou]ł[aeiou]', 
                r'cz[yiae]', r'sz[yiae]', r'rz[yiae]',
                r'dzi[aeę]', r'ni[aeiou]',
                r'owy$', r'owa$', r'owe$',
                r'ski$', r'ska$', r'skie$',
                r'ny$', r'na$', r'ne$',
                r'ący$', r'ąca$', r'ące$'
            ]
            
            if any(re.search(pattern, word.lower()) for pattern in polish_patterns):
                is_polish = True
            
            # Sprawdź czy wyraz zawiera samogłoski
            if not re.search(r'[aeiouyąęó]', word):
                continue
            
            # Sprawdź czy nie ma zbyt wielu spółgłosek pod rząd
            if re.search(r'[bcćdfghjklłmnńprsśtwzźż]{4,}', word):
                continue
            
            # Sprawdź proporcję liter
            total_chars = len(word)
            letters = len(re.findall(r'[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', word))
            if letters / total_chars < 0.7:  # minimum 70% znaków to litery
                continue
            
            if is_polish:
                polish_words.append(word)
        
        # Połącz wszystkie znalezione wyrazy i frazy
        all_text = detected_phrases + polish_words
        
        return ' '.join(all_text).strip()

    def merge_text_segments(self, text_segments, max_gap=15.0):
        """
        Łączy segmenty tekstu z bardziej elastycznym podejściem.
        """
        if not text_segments:
            return []
            
        segments = sorted(text_segments, key=lambda x: x[0])
        merged = []
        current_start, current_end, current_text = segments[0]
        
        for start, end, text in segments[1:]:
            # Bardziej elastyczne łączenie segmentów
            gap = start - current_end
            
            # Jeśli przerwa jest wystarczająco mała lub teksty są podobne
            if gap <= max_gap or self.text_similarity(current_text, text) > 0.5:
                # Aktualizuj koniec segmentu
                current_end = end
                # Połącz teksty jeśli są różne
                if text != current_text:
                    # Zachowaj unikalną kolejność fraz
                    phrases = set(current_text.split() + text.split())
                    current_text = " ".join(phrases)
            else:
                # Dodaj poprzedni segment i zacznij nowy
                if current_text:
                    merged.append((current_start, current_end, current_text))
                current_start, current_end, current_text = start, end, text
        
        # Dodaj ostatni segment
        if current_text:
            merged.append((current_start, current_end, current_text))
        
        return merged
    
    def text_similarity(self, text1, text2):
        """
        Oblicza podobieństwo między tekstami.
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def detect_text_in_frame(self, frame):
        """
        Wykrywa tekst w pojedynczej klatce wideo.
        """
        # Konwersja do skali szarości
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Binaryzacja adaptacyjna
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Wykrywanie tekstu przy użyciu Tesseract
        custom_config = r'--oem 3 --psm 6 -l pol'
        text = pytesseract.image_to_string(binary, config=custom_config)
        
        # Wyodrębnienie kluczowych fraz
        return self.extract_key_phrases(text)

    def process_video(self, video_path, sampling_rate=1):
        """
        Przetwarza plik wideo i wykrywa polski tekst.
        """
        print(f"Rozpoczynam przetwarzanie pliku: {video_path}")
        video = VideoFileClip(video_path)
        duration = video.duration
        
        text_segments = []
        current_text = None
        start_time = None
        
        total_frames = int(duration * sampling_rate)
        for i, t in enumerate(np.arange(0, duration, 1/sampling_rate)):
            if i % 10 == 0:
                print(f"Postęp: {i}/{total_frames} klatek ({(i/total_frames*100):.1f}%)")
            
            frame = video.get_frame(t)
            detected_text = self.detect_text_in_frame(frame)
            
            if detected_text:
                if current_text != detected_text:
                    if current_text:
                        text_segments.append((start_time, t, current_text))
                    current_text = detected_text
                    start_time = t
            elif current_text:
                text_segments.append((start_time, t, current_text))
                current_text = None
                start_time = None
        
        if current_text:
            text_segments.append((start_time, duration, current_text))
        
        video.close()
        
        # Łączenie segmentów
        merged_segments = self.merge_text_segments(text_segments)
        
        # Filtrowanie krótkich segmentów
        filtered_segments = [(start, end, text) for start, end, text in merged_segments 
                           if end - start >= 2.0]
        
        return filtered_segments

    def format_time(self, seconds):
        """
        Formatuje czas w sekundach do formatu HH:MM:SS.
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def generate_report(self, text_segments, output_file=None):
        """
        Generuje raport z wykrytymi segmentami tekstu.
        """
        report = "Wykryte polskie wyrazy w wideo:\n\n"
        for start, end, text in text_segments:
            duration = int(end - start)
            report += f"Od: {self.format_time(start)} Do: {self.format_time(end)} (czas trwania: {duration} sekund)\n"
            report += f"Tekst: {text}\n\n"
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Raport zapisano do pliku: {output_file}")
        
        return report

def main():
    parser = argparse.ArgumentParser(description='Wykrywanie polskiego tekstu w pliku wideo')
    parser.add_argument('video_path', type=str, help='Ścieżka do pliku wideo')
    parser.add_argument('--tesseract', type=str, 
                       default='C:\\Program Files\\Tesseract-OCR\\tesseract.exe',
                       help='Ścieżka do Tesseract OCR (opcjonalne)')
    parser.add_argument('--sampling-rate', type=float, default=1,
                       help='Liczba klatek na sekundę do sprawdzenia (domyślnie: 1)')
    parser.add_argument('--output', type=str,
                       help='Ścieżka do pliku wyjściowego z raportem (opcjonalne)')
    parser.add_argument('--phrases', type=str, nargs='+',
                       help='Dodatkowe frazy do wykrycia (jako wyrażenia regularne)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video_path):
        print(f"Błąd: Plik {args.video_path} nie istnieje!")
        return
    
    # Przygotowanie dodatkowych fraz
    additional_phrases = []
    if args.phrases:
        for phrase in args.phrases:
            # Używamy tej samej frazy jako wzorca i tekstu normalizującego
            additional_phrases.append((phrase, phrase))
    
    try:
        detector = VideoTextDetector(args.tesseract, additional_phrases)
        text_segments = detector.process_video(args.video_path, args.sampling_rate)
        report = detector.generate_report(text_segments, args.output)
        
        print("\nPrzetwarzanie zakończone pomyślnie!")
        
    except Exception as e:
        print(f"Wystąpił błąd podczas przetwarzania: {str(e)}")

if __name__ == "__main__":
    main()