# Video Translation Studio

Aplikacja do automatycznego tłumaczenia i przetwarzania wideo z funkcjami usuwania ciszy, dodawania intro/outro i wykrywania polskiego tekstu.

## 🚀 Funkcje

- **Transkrypcja wideo** - automatyczne rozpoznawanie mowy
- **Tłumaczenie** - tłumaczenie na język angielski
- **Usuwanie ciszy i bezruchu** - automatyczne skracanie wideo
- **Dodawanie intro/outro** - dodawanie wstępu i zakończenia
- **Wykrywanie polskiego tekstu** - analiza zawartości wideo
- **Generowanie raportów** - szczegółowe raporty z przetwarzania

## 📦 Pobieranie aplikacji

### Automatyczne budowanie (GitHub Actions)

Aplikacja jest automatycznie budowana dla wszystkich platform przy każdym push na główną gałąź.

**Pobierz gotowe pliki:**
1. Przejdź do zakładki **Actions** w tym repozytorium
2. Wybierz najnowszy workflow **Build Video Translation Studio**
3. Pobierz artifacts dla swojej platformy:
   - **Windows**: `Video_Translation_Studio-Windows` → `Video_Translation_Studio.exe`
   - **macOS**: `Video_Translation_Studio-macOS` → `Video_Translation_Studio.app`
   - **Linux**: `Video_Translation_Studio-Ubuntu` → `Video_Translation_Studio`

### Ręczne budowanie

Jeśli chcesz zbudować aplikację lokalnie:

```bash
# Klonuj repozytorium
git clone https://github.com/twoj-username/video_translation.git
cd video_translation

# Zainstaluj zależności
pip install -r requirements.txt
pip install pyinstaller

# Zbuduj aplikację
pyinstaller --onefile --windowed --icon=logo.png --name="Video_Translation_Studio" --add-data="logo.png;." --add-data="video_translation_config.json;." --add-data="Readme;." --add-data="intro_outro;intro_outro" --add-data="code/*.py;." code/video_translation_app.py
```

## 🖥️ Wymagania systemowe

### Windows
- Windows 10/11 (64-bit)
- 4GB RAM
- 500MB wolnego miejsca

### macOS
- macOS 10.15 lub nowszy
- 4GB RAM
- 500MB wolnego miejsca

### Linux
- Ubuntu 20.04 lub nowszy
- 4GB RAM
- 500MB wolnego miejsca

## 📁 Struktura projektu

```
video_translation/
├── code/                          # Kod źródłowy aplikacji
│   ├── video_translation_app.py   # Główna aplikacja GUI
│   ├── transcribe_api.py          # Transkrypcja wideo
│   ├── translate.py               # Tłumaczenie tekstu
│   ├── delete_sm_improved.py      # Usuwanie ciszy/bezruchu
│   ├── add_intro_outro.py         # Dodawanie intro/outro
│   └── detect_polish_text.py      # Wykrywanie polskiego tekstu
├── intro_outro/                   # Pliki intro/outro (dodaj własne)
├── logo.png                       # Logo aplikacji
├── video_translation_config.json  # Konfiguracja
├── requirements.txt               # Zależności Python
└── README_GITHUB.md              # Ten plik
```

## 🔧 Konfiguracja

### Pliki intro/outro

1. Umieść pliki intro/outro w folderze `intro_outro/`
2. Nazwij je odpowiednio (np. `intro.mp4`, `outro.mp4`)
3. Aplikacja automatycznie je wykryje

### Konfiguracja API

Edytuj `video_translation_config.json`:

```json
{
  "openai_api_key": "twój-klucz-api",
  "whisper_model": "base",
  "translation_model": "gpt-3.5-turbo"
}
```

## 🎯 Jak używać

1. **Uruchom aplikację** - `Video_Translation_Studio.exe` (Windows) lub `Video_Translation_Studio.app` (macOS)
2. **Wybierz folder roboczy** - folder z plikami wideo do przetworzenia
3. **Wybierz operacje** - zaznacz funkcje które chcesz użyć
4. **Uruchom przetwarzanie** - kliknij "Start"
5. **Sprawdź wyniki** - w folderze `output/`

## 🔄 Workflow przetwarzania

1. **Transkrypcja** - rozpoznanie mowy w wideo
2. **Tłumaczenie** - tłumaczenie na angielski
3. **Usuwanie ciszy** - automatyczne skracanie
4. **Dodawanie intro/outro** - dodanie wstępu i zakończenia
5. **Wykrywanie tekstu** - analiza zawartości
6. **Generowanie raportów** - podsumowanie operacji

## 📊 Raporty

Aplikacja generuje szczegółowe raporty:
- **Raport usuwania ciszy** - informacje o usuniętych fragmentach
- **Raport wykrywania tekstu** - analiza polskiego tekstu w wideo
- **Logi operacji** - szczegółowe logi z przetwarzania

## 🛠️ Rozwój

### Dodawanie nowych funkcji

1. Stwórz nowy skrypt w folderze `code/`
2. Dodaj funkcję do głównej aplikacji
3. Zaktualizuj `requirements.txt` jeśli potrzebne
4. Przetestuj na wszystkich platformach

### Testowanie

```bash
# Uruchom z kodu źródłowego
cd code
python video_translation_app.py

# Testuj poszczególne moduły
python transcribe_api.py
python translate.py
python delete_sm_improved.py
```

## 🤝 Współpraca

1. Fork repozytorium
2. Stwórz branch dla nowej funkcji
3. Zrób commit zmian
4. Stwórz Pull Request

## 📝 Licencja

Ten projekt jest dostępny na licencji MIT.

## 🆘 Wsparcie

Jeśli masz problemy:
1. Sprawdź [Issues](https://github.com/twoj-username/video_translation/issues)
2. Stwórz nowy Issue z opisem problemu
3. Dołącz logi błędów i informacje o systemie

## 🔄 Aktualizacje

Aplikacja jest automatycznie budowana przy każdej zmianie kodu. Sprawdź zakładkę **Actions** dla najnowszych wersji.

---

**Video Translation Studio** - Automatyczne przetwarzanie i tłumaczenie wideo 🎬✨ 