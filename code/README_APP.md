# 🎬 Video Translation Studio - Aplikacja Desktopowa

## 📋 Opis

Video Translation Studio to aplikacja desktopowa, która integruje wszystkie skrypty do przetwarzania wideo w jeden, łatwy w użyciu interfejs. Aplikacja pozwala na automatyczne wykonywanie wszystkich kroków procesu tłumaczenia wideo z polskiego na angielski.

## 🚀 Uruchomienie

```bash
python code/video_translation_app.py
```

## 📁 Struktura aplikacji

### Krok 1: Pobieranie i transkrypcja
- **Pobieranie z YouTube**: Wklej link do YouTube i pobierz wideo
- **Transkrypcja pliku**: Wybierz lokalny plik wideo do transkrypcji
- **Skrypty**: `youtube_downloader.py`, `transcribe_improved.py`
- **Output**: Pliki `.txt` z transkrypcją

### Krok 2: Tłumaczenie i generowanie wideo
- **Automatyczne wykrywanie**: Znajduje pliki `*_sentences.txt`
- **Tłumaczenie**: Przetłumacza tekst na angielski
- **Generowanie audio**: Tworzy pliki audio z lektorem
- **Overlay wideo**: Łączy audio z wideo
- **Skrypty**: `translate.py`, `generate.py`, `overlay_fixed.py`
- **Output**: Pliki `*_synchronized.mp4`

### Krok 3: Optymalizacja
- **Usuwanie ciszy**: Automatycznie usuwa ciszę i bezruch
- **Detekcja tekstu**: Wykrywa polski tekst w wideo
- **Raporty**: Generuje szczegółowe raporty
- **Skrypty**: `delete_sm.py`, `detect_polish_text.py`
- **Output**: Zoptymalizowane wideo + raporty

### Dodatkowe funkcje
- **Cofnij usunięcie luki**: Przywraca usunięte fragmenty
- **Dodaj logo**: Dodaje białą stopkę i logo
- **Intro/Outro**: Łączy intro, główne wideo i outro
- **Post social media**: Generuje posty na social media

## 🎯 Funkcjonalności

### 📁 Zarządzanie folderami
- **Folder roboczy**: Ustaw główny folder dla wszystkich operacji
- **Automatyczne wykrywanie**: Aplikacja automatycznie znajduje odpowiednie pliki
- **Zapisywanie konfiguracji**: Ustawienia są zapisywane między sesjami

### 📋 Logi i monitoring
- **Logi w czasie rzeczywistym**: Śledź postęp operacji
- **Status operacji**: Informacje o aktualnym kroku
- **Obsługa błędów**: Szczegółowe komunikaty błędów
- **Czyszczenie logów**: Możliwość wyczyszczenia historii

### 🔄 Automatyzacja
- **Automatyczne wykrywanie plików**: Nie musisz ręcznie wskazywać plików
- **Sekwencyjne przetwarzanie**: Wszystkie kroki są wykonywane automatycznie
- **Wielowątkowość**: Operacje nie blokują interfejsu

## 📖 Instrukcja użytkowania

### 1. Pierwsze uruchomienie
1. Uruchom aplikację: `python code/video_translation_app.py`
2. Ustaw folder roboczy (gdzie będą zapisywane wszystkie pliki)
3. Zapisz konfigurację

### 2. Krok 1 - Pobieranie i transkrypcja
1. Przejdź do zakładki "Krok 1"
2. Wybierz źródło:
   - **YouTube**: Wklej link do YouTube
   - **Plik lokalny**: Wybierz plik wideo z dysku
3. Kliknij odpowiedni przycisk:
   - "📥 Pobierz z YouTube" lub
   - "🎬 Transkrybuj plik"
4. Poczekaj na zakończenie operacji

### 3. Krok 2 - Tłumaczenie i wideo
1. Przejdź do zakładki "Krok 2"
2. Sprawdź czy pliki zostały wykryte automatycznie
3. Jeśli nie, kliknij "🔄 Odśwież listę plików"
4. Kliknij "🎬 Uruchom tłumaczenie i generowanie"
5. Poczekaj na zakończenie wszystkich operacji

### 4. Krok 3 - Optymalizacja
1. Przejdź do zakładki "Krok 3"
2. Sprawdź czy pliki `*_synchronized.mp4` zostały wykryte
3. Kliknij "🔇 Usuń ciszę i bezruch"
4. Kliknij "🔍 Wykryj tekst polski"
5. Sprawdź wygenerowane raporty

### 5. Dodatkowe funkcje
1. Przejdź do zakładki "Dodatkowe funkcje"
2. **Cofnij luki**: Wprowadź numery luk do przywrócenia
3. **Dodaj logo**: Wybierz wideo i dodaj logo
4. **Intro/Outro**: Wybierz pliki i połącz je
5. **Post social media**: Wygeneruj posty z emotikonami

## ⚙️ Konfiguracja

### Plik konfiguracyjny
Aplikacja zapisuje ustawienia w pliku `video_translation_config.json`:
```json
{
  "working_dir": "ścieżka/do/folderu/roboczego",
  "api_keys": {},
  "last_used_files": {}
}
```

### Wymagane zależności
Upewnij się, że masz zainstalowane wszystkie wymagane pakiety:
```bash
pip install -r requirements.txt
```

## 🐛 Rozwiązywanie problemów

### Aplikacja się nie uruchamia
- Sprawdź czy masz zainstalowany Python 3.7+
- Sprawdź czy masz zainstalowane wszystkie zależności
- Sprawdź czy wszystkie skrypty są w folderze `code/`

### Błędy podczas operacji
- Sprawdź logi w dolnej części aplikacji
- Upewnij się, że folder roboczy jest poprawnie ustawiony
- Sprawdź czy pliki źródłowe istnieją

### Problemy z automatycznym wykrywaniem
- Kliknij "🔄 Odśwież pliki"
- Sprawdź czy pliki mają odpowiednie nazwy (np. `*_sentences.txt`)
- Upewnij się, że folder roboczy jest poprawny

## 📝 Uwagi

- Wszystkie operacje są wykonywane w osobnym wątku - interfejs nie zawiesza się
- Logi są wyświetlane w czasie rzeczywistym
- Konfiguracja jest automatycznie zapisywana
- Aplikacja automatycznie wykrywa pliki między krokami

## 🎉 Korzyści

- **Jeden interfejs** dla wszystkich operacji
- **Automatyzacja** - nie musisz pamiętać o kolejności kroków
- **Wizualizacja** - widzisz postęp i status operacji
- **Łatwość użytkowania** - intuicyjny interfejs
- **Obsługa błędów** - szczegółowe komunikaty
- **Zapisywanie ustawień** - nie musisz konfigurować za każdym razem

---

**Video Translation Studio** - Twój kompletny zestaw narzędzi do tłumaczenia wideo! 🚀 