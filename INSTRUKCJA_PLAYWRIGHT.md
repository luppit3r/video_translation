# 🌐 Instrukcja instalacji Playwright Fallback dla Facebook

## Co to jest?

**Playwright Fallback** to alternatywna metoda publikowania postów na Facebook, która **nie wymaga konfiguracji Facebook API**. Zamiast tego używa automatyzacji przeglądarki.

## Zalety

✅ **Działa od razu** - bez konfiguracji Facebook Developer App  
✅ **Bez problemów z uprawnieniami** - używa Twojej sesji Facebook  
✅ **Logowanie tylko raz** - sesja zapisana lokalnie  
✅ **Publikuje jako Strona** - tak jakbyś robił to ręcznie  

## Instalacja

### Krok 1: Zainstaluj Playwright
```bash
pip install playwright
```

### Krok 2: Zainstaluj przeglądarki
```bash
python -m playwright install
```

### Krok 3: Uruchom aplikację
```bash
python code/video_translation_app.py
```

## Jak używać

1. **Przejdź do zakładki "Post na social media"**
2. **Wypełnij treść posta** (tekst + zdjęcie/wideo)
3. **Kliknij przycisk "🌐 Publikuj przez przeglądarkę (fallback)"**
4. **Pierwszy raz**: Zaloguj się do Facebook w otwartej przeglądarce
5. **Kolejne razy**: Działa automatycznie

## Co się dzieje

1. **Otwiera się przeglądarka Chrome** (widoczna dla Ciebie)
2. **Przechodzi na Facebook** i sprawdza czy jesteś zalogowany
3. **Idzie na stronę EduPanda En** (Twoja strona)
4. **Tworzy nowy post** z Twoim tekstem i zdjęciem/wideo
5. **Publikuje post** jako Twoja strona
6. **Zostawia przeglądarkę otwartą** (możesz ją zamknąć ręcznie)

## Rozwiązywanie problemów

### ❌ "Playwright nie zainstalowany"
```bash
pip install playwright
python -m playwright install
```

### ❌ Przeglądarka się nie otwiera
- Sprawdź czy Chrome jest zainstalowany
- Spróbuj: `python -m playwright install chromium`

### ❌ Błąd logowania
- Zaloguj się ręcznie w otwartej przeglądarce
- Zamknij okno informacyjne i spróbuj ponownie

### ❌ Nie może znaleźć przycisku "Opublikuj"
- Facebook mógł zmienić interfejs
- Aplikacja automatycznie zapisuje screenshot i HTML debug
- Sprawdź pliki `facebook_debug_*.png` i `facebook_debug_*.html`
- Zgłoś błąd z tymi plikami - zaktualizuję selektory

## Bezpieczeństwo

- **Sesja zapisana lokalnie** - tylko na Twoim komputerze
- **Bez dostępu do Twoich danych** - tylko automatyzacja interfejsu
- **Możesz przerwać w każdej chwili** - zamknij przeglądarkę

## Wsparcie

Jeśli coś nie działa:
1. Sprawdź logi w zakładce "Logi"
2. Upewnij się że Playwright jest zainstalowany
3. Sprawdź czy jesteś zalogowany do Facebook

## Debugowanie

Aplikacja automatycznie zapisuje pliki debug w przypadku błędu:
- **Screenshot**: `facebook_debug_YYYYMMDD_HHMMSS.png` - zrzut ekranu strony
- **HTML**: `facebook_debug_YYYYMMDD_HHMMSS.html` - kod źródłowy strony

Te pliki pomagają zidentyfikować problem z selektorami Facebook.

---

**🎯 To rozwiązanie omija wszystkie problemy z Facebook API i pozwala publikować posty bez konfiguracji uprawnień!**
