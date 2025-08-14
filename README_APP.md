# Video Translation Studio

Aplikacja do automatyzacji procesu tłumaczenia wideo z języka polskiego na angielski.

## Instalacja

### Wymagania systemowe
- Python 3.8+
- Windows 10/11 (testowane), macOS, Linux

### Instalacja zależności

```bash
# Zainstaluj wymagane pakiety
pip install -r requirements.txt

# Dla funkcji Facebook przez przeglądarkę (fallback)
pip install playwright
python -m playwright install
```

### Konfiguracja API
1. Uruchom aplikację
2. Przejdź do zakładki "Konfiguracja API"
3. Wprowadź klucze API:
   - OpenAI API Key (wymagane)
   - ElevenLabs API Key (opcjonalne)
   - Facebook API Keys (opcjonalne)

## Funkcje

### Główne funkcje
- **Krok 1**: Transkrypcja wideo
- **KOMBO**: Automatyczny przepływ pracy
- **Upload na YT**: Publikacja na YouTube
- **Post na social media**: Publikacja na Facebook/Instagram
- **Miniatura**: Generowanie miniatur
- **Logi**: Monitoring operacji

### Facebook - dwa tryby publikacji
1. **API** (standardowy): Wymaga konfiguracji Facebook Developer App
2. **Przeglądarka** (fallback): Automatyzacja przez Playwright - działa bez API

## Uruchomienie

```bash
python code/video_translation_app.py
```

## Rozwiązywanie problemów

### Facebook API nie działa?
Użyj przycisku "🌐 Publikuj przez przeglądarkę (fallback)" w zakładce "Post na social media".

### Playwright nie zainstalowany?
```bash
pip install playwright
python -m playwright install
```

## Struktura projektu

```
video_translation/
├── code/                    # Kod źródłowy
├── intro_outro/            # Pliki intro/outro
├── requirements.txt         # Zależności Python
└── README_APP.md           # Ten plik
```
