import cv2
import numpy as np
import easyocr
import argparse
from pathlib import Path
from moviepy.editor import VideoFileClip
from tqdm import tqdm
import json
from datetime import datetime
from deep_translator import GoogleTranslator

class PolishTextDetector:
    def __init__(self, confidence_threshold=0.6, min_text_length=3):
        """
        Inicjalizacja detektora polskich tekstów.
        
        Args:
            confidence_threshold: Próg pewności OCR (0.0-1.0)
            min_text_length: Minimalna długość tekstu do rozważenia
        """
        print("Inicjalizacja EasyOCR z językiem polskim...")
        self.reader = easyocr.Reader(['pl'], gpu=False)
        self.confidence_threshold = confidence_threshold
        self.min_text_length = min_text_length
        
    def preprocess_frame(self, frame):
        """Przetwarzanie klatki przed OCR."""
        # Konwersja do RGB jeśli potrzebna
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            frame_rgb = frame
            
        # Zwiększ rozmiar dla lepszego OCR
        height, width = frame_rgb.shape[:2]
        scale_factor = 2
        frame_resized = cv2.resize(frame_rgb, (width * scale_factor, height * scale_factor), 
                                 interpolation=cv2.INTER_CUBIC)
        
        # Zwiększ kontrast
        lab = cv2.cvtColor(frame_resized, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
        
        return enhanced, scale_factor
    
    def detect_text_in_frame(self, frame, timestamp):
        """Wykryj tekst w pojedynczej klatce."""
        try:
            # Przetwórz klatkę
            processed_frame, scale_factor = self.preprocess_frame(frame)
            
            # Wykonaj OCR
            results = self.reader.readtext(processed_frame, detail=1, paragraph=False)
            
            detected_texts = []
            for bbox, text, confidence in results:
                # Sprawdź próg pewności i długość tekstu
                if confidence < self.confidence_threshold or len(text.strip()) < self.min_text_length:
                    continue
                
                # Sprawdź czy tekst zawiera polskie znaki lub jest w języku polskim
                if not self._contains_polish_chars(text) and not self._is_polish_text(text) and not self._is_cd_with_polish_context(text):
                    continue
                
                # Ignoruj bardzo krótkie fragmenty i błędy OCR
                text_clean = text.strip()
                if len(text_clean) < 2 or text_clean.isdigit() or text_clean in ['6ś =6)', 'cm', 'GPa']:
                    continue
                
                # Skaluj współrzędne z powrotem do oryginalnego rozmiaru
                scaled_bbox = []
                for point in bbox:
                    x = point[0] / scale_factor
                    y = point[1] / scale_factor
                    scaled_bbox.append([x, y])
                
                detected_texts.append({
                    'text': text.strip(),
                    'confidence': confidence,
                    'bbox': scaled_bbox,
                    'timestamp': timestamp,
                    'center_x': sum(point[0] for point in scaled_bbox) / 4,
                    'center_y': sum(point[1] for point in scaled_bbox) / 4
                })
                
            return detected_texts
            
        except Exception as e:
            print(f"Błąd podczas wykrywania tekstu w klatce {timestamp}s: {e}")
            return []
    
    def _contains_polish_chars(self, text):
        """Sprawdź czy tekst zawiera polskie znaki."""
        polish_chars = 'ąćęłńóśźżĄĆĘŁŃÓŚŹŻ'
        return any(char in polish_chars for char in text)
    
    def _is_polish_text(self, text):
        """Sprawdź czy tekst jest w języku polskim (nawet bez polskich znaków)."""
        polish_words = [
            'sprawdzenie', 'sprawwdzenie', 'lewej', 'prawej', 'strony', 'strona',
            'przykład', 'obliczyć', 'narysować', 'wykres', 'sił', 'wewnętrznych',
            'równania', 'równowagi', 'statycznej', 'część', 'siły', 'wewnętrzne',
            'linia', 'dopuszczalnych', 'przemieszczeń', 'pręta', 'wytrzymałościowy'
        ]
        text_lower = text.lower().strip()
        return any(word in text_lower for word in polish_words)
    
    def _is_cd_with_polish_context(self, text):
        """Sprawdź czy to 'CD' z polskim kontekstem w nawiasach."""
        text_clean = text.strip()
        if text_clean.startswith('CD') and '(' in text_clean and ')' in text_clean:
            # Sprawdź czy w nawiasach są polskie słowa
            start = text_clean.find('(')
            end = text_clean.find(')')
            if start != -1 and end != -1 and end > start:
                content = text_clean[start+1:end].lower()
                polish_context_words = ['lewej', 'prawej', 'strony', 'strona']
                return any(word in content for word in polish_context_words)
        return False
    
    def group_text_occurrences(self, all_detections, time_threshold=120.0, position_threshold=100):
        """
        Grupuj wykrycia tekstu w sekwencje czasowe.
        
        Args:
            all_detections: Lista wszystkich wykryć
            time_threshold: Maksymalny odstęp czasowy między klatkami (sekundy)
            position_threshold: Maksymalna różnica pozycji (piksele)
        """
        if not all_detections:
            return []
        
        # Sortuj według czasu
        all_detections.sort(key=lambda x: x['timestamp'])
        
        # Grupuj według podobieństwa tekstu i pozycji
        text_groups = {}
        
        for detection in all_detections:
            # Klucz grupowania: tekst + przybliżona pozycja
            text_key = detection['text'].strip()
            pos_key = f"({detection['center_x']//50*50}, {detection['center_y']//50*50})"
            group_key = f"{text_key}|{pos_key}"
            
            if group_key not in text_groups:
                text_groups[group_key] = []
            text_groups[group_key].append(detection)
        
        # Konwertuj grupy na sekwencje
        text_sequences = []
        
        for group_key, detections in text_groups.items():
            if len(detections) < 2:
                # Pojedyncze wykrycie - dodaj jako sekwencję
                text_sequences.append(detections)
                continue
            
            # Sortuj detections w grupie według czasu
            detections.sort(key=lambda x: x['timestamp'])
            
            # Sprawdź czy detections są ciągłe czasowo
            current_sequence = [detections[0]]
            
            for i in range(1, len(detections)):
                current_detection = detections[i]
                last_detection = current_sequence[-1]
                
                time_diff = current_detection['timestamp'] - last_detection['timestamp']
                
                if time_diff <= time_threshold:
                    # Dodaj do obecnej sekwencji
                    current_sequence.append(current_detection)
                else:
                    # Zakończ obecną sekwencję i zacznij nową
                    if current_sequence:
                        text_sequences.append(current_sequence)
                    current_sequence = [current_detection]
            
            # Dodaj ostatnią sekwencję z tej grupy
            if current_sequence:
                text_sequences.append(current_sequence)
        
        return text_sequences
    
    def analyze_video(self, video_path, sample_interval=1.0):
        """
        Przeanalizuj całe wideo w poszukiwaniu polskich tekstów.
        
        Args:
            video_path: Ścieżka do pliku wideo
            sample_interval: Interwał próbkowania w sekundach
        """
        print(f"Analizowanie wideo: {video_path}")
        
        video = VideoFileClip(str(video_path))
        duration = video.duration
        
        print(f"Czas trwania wideo: {duration:.1f}s")
        print(f"Interwał próbkowania: {sample_interval}s")
        
        # Generuj punkty czasowe do analizy
        time_points = np.arange(0, duration, sample_interval)
        print(f"Liczba klatek do analizy: {len(time_points)}")
        
        all_detections = []
        
        # Analizuj klatki
        for timestamp in tqdm(time_points, desc="Analizowanie klatek"):
            try:
                frame = video.get_frame(timestamp)
                detections = self.detect_text_in_frame(frame, timestamp)
                all_detections.extend(detections)
                
            except Exception as e:
                print(f"Błąd przy timestamp {timestamp}s: {e}")
                continue
        
        video.close()
        
        print(f"Wykryto {len(all_detections)} fragmentów tekstu")
        
        # Grupuj w sekwencje
        text_sequences = self.group_text_occurrences(all_detections)
        
        print(f"Znaleziono {len(text_sequences)} sekwencji tekstowych")
        
        return text_sequences
    
    def _seconds_to_mm_ss_sss(self, seconds):
        """Konwertuj sekundy na format mm:ss:sss"""
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        milliseconds = int((remaining_seconds % 1) * 1000)
        seconds_int = int(remaining_seconds)
        return f"{minutes:02d}:{seconds_int:02d}:{milliseconds:03d}"
    
    def _translate_to_english(self, text):
        """Przetłumacz tekst na angielski"""
        try:
            translator = GoogleTranslator(source='pl', target='en')
            translation = translator.translate(text)
            return translation
        except Exception as e:
            print(f"Błąd tłumaczenia: {e}")
            return text  # Zwróć oryginalny tekst jeśli tłumaczenie się nie powiedzie
    
    def generate_report(self, text_sequences, output_path):
        """Generuj raport z wykrytych tekstów."""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_sequences': len(text_sequences),
            'sequences': []
        }
        
        for i, sequence in enumerate(text_sequences):
            if not sequence:
                continue
                
            first_detection = sequence[0]
            last_detection = sequence[-1]
            
            # Oblicz średnią pewność
            avg_confidence = sum(d['confidence'] for d in sequence) / len(sequence)
            
            sequence_info = {
                'id': i + 1,
                'text': first_detection['text'],
                'appears_at': first_detection['timestamp'],
                'disappears_at': last_detection['timestamp'],
                'duration': last_detection['timestamp'] - first_detection['timestamp'],
                'confidence': avg_confidence,
                'detection_count': len(sequence),
                'center_position': {
                    'x': first_detection['center_x'],
                    'y': first_detection['center_y']
                }
            }
            
            report_data['sequences'].append(sequence_info)
        
        # Zapisz raport JSON (zakomentowane na razie)
        # json_path = Path(output_path).with_suffix('.json')
        # with open(json_path, 'w', encoding='utf-8') as f:
        #     json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        # Zapisz raport tekstowy
        txt_path = Path(output_path).with_suffix('.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("RAPORT WYKRYWANIA POLSKICH TEKSTÓW W WIDEO\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Data analizy: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Liczba znalezionych sekwencji: {len(text_sequences)}\n\n")
            
            for seq in report_data['sequences']:
                # Przetłumacz tekst na angielski
                english_translation = self._translate_to_english(seq['text'])
                
                f.write(f"SEKWENCJA {seq['id']}:\n")
                f.write(f"  Tekst: '{seq['text']}'\n")
                f.write(f"  Tłumaczenie: '{english_translation}'\n")
                f.write(f"  Pojawia się: {self._seconds_to_mm_ss_sss(seq['appears_at'])}\n")
                f.write(f"  Znika: {self._seconds_to_mm_ss_sss(seq['disappears_at'])}\n\n")
        
        # print(f"Raport JSON zapisany: {json_path}")
        print(f"Raport TXT zapisany: {txt_path}")
        
        return report_data

def main():
    parser = argparse.ArgumentParser(description="Wykryj polskie teksty w wideo")
    parser.add_argument("video_path", help="Ścieżka do pliku wideo")
    parser.add_argument("--confidence", type=float, default=0.6, 
                       help="Próg pewności OCR (0.0-1.0, domyślnie 0.6)")
    parser.add_argument("--min-length", type=int, default=3,
                       help="Minimalna długość tekstu (domyślnie 3)")
    parser.add_argument("--interval", type=float, default=1.0,
                       help="Interwał próbkowania w sekundach (domyślnie 1.0)")
    parser.add_argument("--output", help="Ścieżka do pliku wyjściowego (bez rozszerzenia)")
    
    args = parser.parse_args()
    
    # Sprawdź plik wideo
    video_path = Path(args.video_path)
    if not video_path.exists():
        print(f"Błąd: Plik wideo nie istnieje: {video_path}")
        return
    
    # Ustaw ścieżkę wyjściową
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = video_path.with_stem(video_path.stem + "_polish_text_detection")
    
    # Inicjalizuj detektor
    detector = PolishTextDetector(
        confidence_threshold=args.confidence,
        min_text_length=args.min_length
    )
    
    try:
        # Analizuj wideo
        text_sequences = detector.analyze_video(video_path, args.interval)
        
        # Generuj raport
        report = detector.generate_report(text_sequences, output_path)
        
        print(f"\n[SUKCES] Analiza zakończona!")
        print(f"Znaleziono {len(text_sequences)} sekwencji tekstowych")
        
        # Wyświetl podsumowanie
        if text_sequences:
            print("\nPODSUMOWANIE:")
            for seq in report['sequences']:
                print(f"  {seq['id']:2d}. '{seq['text']}' - {seq['appears_at']:.1f}s → {seq['disappears_at']:.1f}s ({seq['duration']:.1f}s)")
        
    except Exception as e:
        print(f"Błąd podczas analizy: {e}")
        return

if __name__ == "__main__":
    main() 