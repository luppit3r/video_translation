# 📤 Instrukcja konfiguracji YouTube API

## 🎯 Cel
Konfiguracja YouTube API do automatycznego uploadu wideo z aplikacji Video Translation Studio.

## 📋 Wymagania
- Konto Google z dostępem do YouTube
- Przeglądarka internetowa
- Aplikacja Video Translation Studio

## 🔧 Krok 1: Utworzenie Google Cloud Project

### 1.1 Przejdź do Google Cloud Console
1. Otwórz przeglądarkę i przejdź na: https://console.cloud.google.com/
2. Zaloguj się swoim kontem Google
3. Jeśli to pierwszy raz, zaakceptuj warunki użytkowania

### 1.2 Utwórz nowy projekt
1. Kliknij "Select a project" w górnej części strony
2. Kliknij "New Project"
3. Wprowadź nazwę projektu: `Video Translation Studio`
4. Kliknij "Create"
5. Poczekaj na utworzenie projektu (może potrwać kilka sekund)

## 🔧 Krok 2: Włączenie YouTube Data API v3

### 2.1 Przejdź do biblioteki API
1. W menu po lewej stronie kliknij "APIs & Services" → "Library"
2. W polu wyszukiwania wpisz: `YouTube Data API v3`
3. Kliknij na wynik "YouTube Data API v3"

### 2.2 Włącz API
1. Kliknij przycisk "Enable"
2. Poczekaj na włączenie API

## 🔧 Krok 3: Utworzenie credentials (kluczy API)

### 3.1 Przejdź do credentials
1. W menu po lewej kliknij "APIs & Services" → "Credentials"
2. Kliknij "Create Credentials" → "OAuth 2.0 Client IDs"

### 3.2 Skonfiguruj OAuth consent screen
1. Jeśli to pierwszy raz, zostaniesz poproszony o skonfigurowanie OAuth consent screen
2. Wybierz "External" i kliknij "Create"
3. Wypełnij wymagane pola:
   - **App name**: `Video Translation Studio`
   - **User support email**: Twój email
   - **Developer contact information**: Twój email
4. Kliknij "Save and Continue"
5. Na następnych ekranach kliknij "Save and Continue" (możesz pominąć opcjonalne sekcje)
6. Na końcu kliknij "Back to Dashboard"

### 3.3 Utwórz OAuth 2.0 Client ID
1. Wróć do "Credentials"
2. Kliknij "Create Credentials" → "OAuth 2.0 Client IDs"
3. W polu "Application type" wybierz "Desktop application"
4. W polu "Name" wpisz: `Video Translation Studio Desktop`
5. Kliknij "Create"

### 3.4 Pobierz plik credentials
1. Po utworzeniu kliknij na nazwę klienta OAuth
2. Kliknij przycisk "Download JSON"
3. Zapisz plik jako `client_secrets.json` w folderze `code/` aplikacji

## 🔧 Krok 4: Instalacja wymaganych bibliotek

### 4.1 Zainstaluj biblioteki Python
Otwórz terminal w folderze projektu i wykonaj:

```bash
# Aktywuj środowisko wirtualne (jeśli używasz)
myenv\Scripts\activate  # Windows
source myenv/bin/activate  # macOS/Linux

# Zainstaluj biblioteki YouTube API
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 4.2 Sprawdź instalację
```bash
python -c "import googleapiclient; print('✅ YouTube API zainstalowane')"
```

## 🔧 Krok 5: Test konfiguracji

### 5.1 Uruchom test
```bash
cd code
python youtube_uploader.py
```

### 5.2 Pierwsza autoryzacja
1. Po uruchomieniu testu otworzy się przeglądarka
2. Zaloguj się swoim kontem Google
3. Kliknij "Continue" na ekranie uprawnień
4. Jeśli pojawi się ostrzeżenie o niezweryfikowanej aplikacji:
   - Kliknij "Advanced"
   - Kliknij "Go to Video Translation Studio (unsafe)"
5. Kliknij "Allow" aby udzielić uprawnień

### 5.3 Sprawdź wynik
- W terminalu powinieneś zobaczyć: `✅ Autoryzacja YouTube API udana!`
- W folderze `code/` powinien pojawić się plik `token.pickle`

## 🎯 Krok 6: Użycie w aplikacji

### 6.1 Uruchom aplikację
```bash
python code/video_translation_app.py
```

### 6.2 Przetestuj upload
1. Przejdź do zakładki "📤 Upload na YT"
2. Wybierz wideo do uploadu
3. Wypełnij metadane (tytuł, opis, tagi)
4. Kliknij "📤 Upload na YouTube"
5. Pierwszy raz może być wymagana ponowna autoryzacja

## ⚠️ Ważne uwagi

### Bezpieczeństwo
- **Nie udostępniaj** pliku `client_secrets.json` publicznie
- **Nie commit** tego pliku do Git (jest już w .gitignore)
- Plik `token.pickle` zawiera Twoje dane logowania - chroń go

### Limity API
- YouTube API ma dzienne limity (zwykle 10,000 jednostek/dzień)
- Jeden upload = ~1,600 jednostek
- Możesz sprawdzić limity w Google Cloud Console

### Rozwiązywanie problemów

#### Błąd: "Brak pliku client_secrets.json"
- Sprawdź czy plik jest w folderze `code/`
- Sprawdź czy nazwa pliku jest dokładnie `client_secrets.json`

#### Błąd: "Nie udało się autoryzować"
- Usuń plik `token.pickle` i spróbuj ponownie
- Sprawdź czy masz połączenie z internetem
- Sprawdź czy konto Google ma dostęp do YouTube

#### Błąd: "Quota exceeded"
- Sprawdź limity API w Google Cloud Console
- Poczekaj do następnego dnia lub zwiększ limity

## 🎉 Gotowe!

Po wykonaniu wszystkich kroków będziesz mógł:
- ✅ Automatycznie uploadować wideo na YouTube
- ✅ Ustawiać metadane (tytuł, opis, tagi, kategoria)
- ✅ Dodawać miniaturki
- ✅ Kontrolować prywatność wideo
- ✅ Otrzymywać linki do opublikowanych wideo

**Powodzenia! 🚀** 