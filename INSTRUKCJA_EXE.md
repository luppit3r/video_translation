# 🎬 Video Translation Studio - Instrukcja Użytkowania

## 📦 Plik Wykonywalny (.exe)

Aplikacja została spakowana do pliku `Video_Translation_Studio.exe` o rozmiarze ~288 MB.

### 🚀 Jak Uruchomić

1. **Przejdź do folderu `dist/`**
2. **Kliknij dwukrotnie na `Video_Translation_Studio.exe`**
3. **Aplikacja uruchomi się automatycznie**

### ⚠️ Wymagania Systemowe

- **Windows 10/11** (64-bit)
- **Minimum 4 GB RAM** (zalecane 8 GB)
- **Wolne miejsce na dysku**: minimum 2 GB
- **Połączenie internetowe** (dla pobierania z YouTube i API)

### 🔧 Funkcje Aplikacji

#### Krok 1: Pobieranie Wideo
- **YouTube URL**: Wklej link do filmu z YouTube
- **Plik lokalny**: Wybierz plik wideo z komputera
- **Formaty obsługiwane**: MP4, AVI, MOV, MKV, WMV

#### Krok 2: Transkrypcja i Tłumaczenie
- **Automatyczna transkrypcja** (OpenAI Whisper)
- **Tłumaczenie na angielski**
- **Synchronizacja napisów**

#### Krok 3: Generowanie Finalnego Wideo
- **Dodawanie napisów**
- **Synchronizacja z audio**
- **Eksport do MP4**

#### Dodatkowe Funkcje
- 🎨 **Dodawanie logo**
- 🎬 **Intro/Outro**
- 📱 **Posty social media**
- 🔍 **Wykrywanie polskiego tekstu**

### 📁 Struktura Plików

Po uruchomieniu aplikacja utworzy następujące foldery:
```
Video_Translation_Studio/
├── text/           # Transkrypcje i tłumaczenia
├── generated/      # Pliki tymczasowe
├── output/         # Finalne wideo
└── temp_audio/     # Pliki audio tymczasowe
```

### 🛠️ Rozwiązywanie Problemów

#### Aplikacja się nie uruchamia
1. Sprawdź czy masz Windows 10/11 (64-bit)
2. Uruchom jako administrator
3. Sprawdź czy antywirus nie blokuje

#### Błąd podczas transkrypcji
1. Sprawdź połączenie internetowe
2. Upewnij się, że plik wideo nie jest uszkodzony
3. Sprawdź czy masz wystarczająco miejsca na dysku

#### Wolne działanie
1. Zamknij inne aplikacje
2. Sprawdź czy masz wystarczająco RAM
3. Użyj SSD zamiast HDD

### 🔑 Klucze API

Aplikacja używa domyślnych kluczy API, ale możesz dodać własne w pliku konfiguracyjnym.

### 📞 Wsparcie

W przypadku problemów:
1. Sprawdź logi w aplikacji
2. Uruchom aplikację ponownie
3. Sprawdź czy wszystkie wymagania są spełnione

### 🎉 Gotowe!

Twoja aplikacja Video Translation Studio jest gotowa do użycia bez konieczności instalowania Pythona! 