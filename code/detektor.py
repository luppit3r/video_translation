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
    def __init__(self, tesseract_path=None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def text_similarity(self, text1, text2):
        """
        Oblicza podobieństwo między dwoma tekstami.
        """
        return SequenceMatcher(None, text1, text2).ratio()
        
    def clean_and_filter_text(self, text):
        """
        Czyści i filtruje tekst, pozostawiając tylko sensowne polskie wyrazy.
        """
        # Ignorowanie adresów stron
        text = re.sub(r'www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)
        
        # Usuwanie liczb i jednostek
        text = re.sub(r'\d+(\.\d+)?(kN|kNm|m|cm|mm|N|Nm)?', '', text)
        
        # Usuwanie pojedynczych liter i symboli
        text = re.sub(r'\b[A-Za-z]\b', '', text)
        text = re.sub(r'[+\-=×÷*/<>≤≥≠(){}[\]|]', ' ', text)
        
        # Usuwanie linii z nadmiarem znaków specjalnych
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Pomijanie krótkich linii
            if len(line.strip()) < 5:
                continue
            
            # Pomijanie linii z nadmiarem znaków specjalnych
            special_chars = len(re.findall(r'[^a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ\s]', line))
            letters = len(re.findall(r'[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', line))
            if letters == 0 or special_chars / letters > 0.2:  # Zmniejszony próg tolerancji
                continue
                
            cleaned_lines.append(line)
        
        text = ' '.join(cleaned_lines)
        
        # Rozdzielenie wyrazów spacjami
        words = text.split()
        
        # Filtrowanie tylko sensownych polskich wyrazów
        polish_words = []
        for word in words:
            # Usuwanie znaków specjalnych z początku i końca wyrazu
            word = word.strip('.,!?:;«»""\'')
            
            # Pomijanie krótkich wyrazów, z wyjątkiem "i" oraz "w"
            if len(word) < 2 and word.lower() not in ['i', 'w']:
                continue
            
            # Pomijanie wyrazów z nadmiarem spółgłosek
            if re.search(r'[bcćdfghjklłmnńprsśtwzźż]{4,}', word.lower()):
                continue
            
            # Pomijanie wyrazów bez samogłosek (z wyjątkami)
            if not re.search(r'[aeiouyąęó]', word.lower()) and word.lower() not in ['w', 'z']:
                continue
            
            # Sprawdzanie czy wyraz zawiera przynajmniej 40% liter
            total_chars = len(word)
            letters = len(re.findall(r'[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', word))
            if letters / total_chars < 0.4:
                continue
            
            # Akceptowanie wyrazów z polskimi znakami
            if re.search(r'[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', word):
                polish_words.append(word)
                continue
            
            # Akceptowanie typowych polskich wzorców
            if re.search(r'(ość|anie|enie|cja|ować|[aeiou]ł[aeiou]|cz[yiae]|sz[yiae]|rz[yiae]|dzi[aeę]|ni[aeiou])$', word.lower()):
                polish_words.append(word)
                continue
        
        cleaned_text = ' '.join(polish_words).strip()
        
        # Jeśli tekst jest zbyt krótki, ignorujemy go
        if len(cleaned_text) < 5:
            return ''
            
        return cleaned_text

    def merge_text_segments(self, text_segments, max_gap=5.0, similarity_threshold=0.8):
        """
        Łączy segmenty tekstu, które są blisko siebie czasowo i zawierają podobny tekst.
        """
        if not text_segments:
            return []
            
        merged = []
        current_start, current_end, current_text = text_segments[0]
        
        for start, end, text in text_segments[1:]:
            # Sprawdzamy podobieństwo tekstów
            similarity = self.text_similarity(current_text, text)
            
            # Jeśli teksty są podobne i przerwa nie jest zbyt duża
            if (similarity > similarity_threshold and 
                start - current_end <= max_gap):
                current_end = end
                # Wybieramy dłuższy tekst jako reprezentatywny
                if len(text) > len(current_text):
                    current_text = text
            else:
                if current_text:  # Dodaj poprzedni segment
                    merged.append((current_start, current_end, current_text))
                current_start, current_end, current_text = start, end, text
                
        # Dodaj ostatni segment
        if current_text:
            merged.append((current_start, current_end, current_text))
            
        return merged

    def detect_text_in_frame(self, frame):
        """
        Wykrywa tekst w pojedynczej klatce wideo.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        custom_config = r'--oem 3 --psm 6 -l pol'
        text = pytesseract.image_to_string(binary, config=custom_config)
        return self.clean_and_filter_text(text)

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
                if current_text is None or self.text_similarity(current_text, detected_text) < 0.8:
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
        
        # Łączenie segmentów tekstu z większą tolerancją
        merged_segments = self.merge_text_segments(text_segments, max_gap=5.0, similarity_threshold=0.8)
        
        # Filtrowanie krótkich segmentów (krótszych niż 2 sekundy)
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
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video_path):
        print(f"Błąd: Plik {args.video_path} nie istnieje!")
        return
    
    if not args.output:
        base_name = os.path.splitext(args.video_path)[0]
        args.output = f"{base_name}_raport.txt"
    
    try:
        detector = VideoTextDetector(args.tesseract)
        text_segments = detector.process_video(args.video_path, args.sampling_rate)
        report = detector.generate_report(text_segments, args.output)
        
        print("\nPrzetwarzanie zakończone pomyślnie!")
        
    except Exception as e:
        print(f"Wystąpił błąd podczas przetwarzania: {str(e)}")

if __name__ == "__main__":
    main()