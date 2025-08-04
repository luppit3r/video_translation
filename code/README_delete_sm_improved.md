# Ulepszona wersja delete_sm.py - Usuwanie ciszy z wideo

## Problem z oryginalną wersją

Oryginalny skrypt `delete_sm.py` miał problem z błędnym wykrywaniem ciszy w miejscach gdzie jeszcze trwała ścieżka dźwiękowa. Problem polegał na:

1. **Za restrykcyjne parametry**: `silence_thresh=-40dB` było za niskie
2. **Za krótki min_silence_len**: 3 sekundy mogły być za mało
3. **Brak marginesu bezpieczeństwa**: skrypt nie uwzględniał pliku z tłumaczeniem
4. **Brak precyzyjnej analizy**: nie było informacji o tym gdzie na pewno jest dźwięk

## Rozwiązanie w ulepszonej wersji

### Kluczowe ulepszenia:

1. **Użycie pliku z tłumaczeniem**: Skrypt czyta timestampy z pliku tłumaczenia i używa ich do określenia obszarów z dźwiękiem
2. **Margines bezpieczeństwa**: Dodaje 2 sekundy marginesu przed i po każdym segmencie z dźwiękiem
3. **Lepsze parametry**: 
   - `min_silence_len=5000ms` (5 sekund zamiast 3)
   - `silence_thresh=-35dB` (mniej restrykcyjny próg)
4. **Minimalna długość gap'a**: Tylko gap'y >= 3 sekundy są rozważane
5. **Precyzyjna analiza**: Sprawdza konflikty z segmentami z dźwiękiem

### Format pliku z tłumaczeniem

Skrypt oczekuje pliku w formacie:
```
Start: 0.00, End: 5.23, Sentence: Witam w kursie z wytrzymałości materiałów.
Start: 5.50, End: 12.34, Sentence: Dzisiaj omówimy podstawowe pojęcia.
Start: 15.00, End: 25.67, Sentence: Zacznijmy od definicji naprężenia.
```

## Użycie

### Podstawowe użycie:
```bash
python delete_sm_improved.py video.mp4 translation.txt output.mp4
```

### Z niestandardowymi parametrami:
```bash
python delete_sm_improved.py video.mp4 translation.txt output.mp4 \
    --min_silence_len 5000 \
    --silence_thresh -35 \
    --safety_margin 2.0 \
    --min_gap_duration 3.0 \
    --replacement_duration 0.5
```

### Tylko raport (bez tworzenia wideo):
```bash
python delete_sm_improved.py video.mp4 translation.txt output.mp4 --report-only
```

### Tryb debug:
```bash
python delete_sm_improved.py video.mp4 translation.txt output.mp4 --debug
```

## Parametry

| Parametr | Domyślna wartość | Opis |
|----------|------------------|------|
| `--min_silence_len` | 5000ms | Minimalna długość ciszy do wykrycia |
| `--silence_thresh` | -35dB | Próg ciszy (wyższy = mniej restrykcyjny) |
| `--safety_margin` | 2.0s | Margines bezpieczeństwa przed/po segmencie z dźwiękiem |
| `--min_gap_duration` | 3.0s | Minimalna długość gap'a do rozważenia |
| `--replacement_duration` | 0.5s | Czas trwania zastępczego freeze frame |
| `--movement_threshold` | 15 | Próg wykrywania ruchu |
| `--min_static_pixels` | 100 | Minimalna liczba pikseli do uznania ruchu |
| `--debug` | False | Włącz szczegółową analizę ruchu |
| `--report-only` | False | Tylko raport, bez tworzenia wideo |

## Proces działania

1. **Parsowanie pliku tłumaczenia**: Wczytuje timestampy segmentów z dźwiękiem
2. **Wykrywanie ciszy**: Analizuje audio i znajduje potencjalne segmenty ciszy
3. **Filtrowanie bezpieczne**: Usuwa segmenty ciszy które kolidują z dźwiękiem
4. **Analiza ruchu**: Sprawdza czy w bezpiecznych gap'ach jest ruch
5. **Kompresja**: Zastępuje gap'y bez ruchu krótkimi freeze frame'ami
6. **Raport**: Generuje szczegółowy raport z timestampami

## Przykład wyjścia

```
Improved silence-based gap detection - FULL PROCESSING
Video: kurs_wytrzymalosc.mp4
Translation file: kurs_wytrzymalosc.txt
Output: kurs_wytrzymalosc_compressed.mp4
Min silence: 5000ms, Threshold: -35dB
Safety margin: 2.0s, Min gap duration: 3.0s
------------------------------------------------------------
Video duration: 45.2 minutes

Parsing translation file: kurs_wytrzymalosc.txt
Found 127 audio segments in translation file

Extracting audio for silence detection...
Detecting silent segments...
Found 23 potential silent segments

✅ Safe gap 1: 8.45s to 12.67s (4.22s)
❌ Rejected gap 2: 15.23s to 18.45s - conflicts with audio segment Line 5: 13.0s-20.0s
✅ Safe gap 3: 25.12s to 30.34s (5.22s)

📊 Summary: 15 safe gaps found out of 23 potential segments

Analyzing movement in silent gaps: 100%|██████████| 15/15 [00:45<00:00]

  Gap 1: 8.5s-12.7s (4.2s)
    Movement timeline:
      8.5s-9.5s: bezruch
      9.5s-10.5s: bezruch
      10.5s-11.5s: bezruch
      11.5s-12.7s: bezruch
    📊 Analiza dominacji: 4.2s bezruch / 4.2s total = 100%
    ✅ KOMPRESUJ CAŁY GAP: Bezruch dominuje (100% >= 60%)

📊 Summary: Found 12 gaps to compress based on 60% dominance rule

Compressing 12 gaps...
Processing gaps: 100%|██████████| 12/12 [02:30<00:00]
  Compressed gap 1: 8.45s-12.67s (4.22s) -> 0.5s
  Compressed gap 2: 25.12s-30.34s (5.22s) -> 0.5s

Creating final video...
Writing to: kurs_wytrzymalosc_compressed.mp4

✅ Success! Compressed 12 gaps
Output: kurs_wytrzymalosc_compressed.mp4
```

## Rozwiązywanie problemów

### Problem: "No safe silent segments found!"
- **Przyczyna**: Wszystkie segmenty ciszy kolidują z dźwiękiem
- **Rozwiązanie**: Zwiększ `--safety_margin` lub sprawdź czy plik tłumaczenia jest poprawny

### Problem: "All silent segments have movement"
- **Przyczyna**: W wykrytych gap'ach jest ruch
- **Rozwiązanie**: Zmniejsz `--movement_threshold` lub `--min_static_pixels`

### Problem: Za dużo/uszkodzone segmenty ciszy
- **Przyczyna**: Nieprawidłowe parametry wykrywania ciszy
- **Rozwiązanie**: Dostosuj `--silence_thresh` lub `--min_silence_len`

## Porównanie z oryginalną wersją

| Aspekt | Oryginalna wersja | Ulepszona wersja |
|--------|-------------------|------------------|
| Wykrywanie ciszy | Tylko audio | Audio + plik tłumaczenia |
| Margines bezpieczeństwa | Brak | 2 sekundy |
| Parametry ciszy | -40dB, 3s | -35dB, 5s |
| Minimalna długość gap'a | Brak | 3 sekundy |
| Precyzja | Niska | Wysoka |
| Bezpieczeństwo | Niskie | Wysokie |

## Integracja z process_video.py

Aby użyć ulepszonej wersji w głównym procesie, zaktualizuj `process_video.py`:

```python
# W funkcji process_final() lub podobnej
def process_final(self):
    """Final processing with improved silence removal"""
    command = [
        sys.executable, str(self.scripts_dir / "delete_sm_improved.py"),
        str(self.video_path),
        str(self.translated_txt),  # Plik z tłumaczeniem
        str(self.final_output),
        "--safety_margin", "2.0",
        "--min_gap_duration", "3.0"
    ]
    
    result = self.run_command(command, "Improved silence removal")
    return result.returncode == 0
```

## Testowanie

Uruchom testy:
```bash
python test_improved_delete_sm.py
```

Test sprawdza:
- Parsowanie pliku z tłumaczeniem
- Logikę marginesu bezpieczeństwa
- Rekomendacje parametrów 