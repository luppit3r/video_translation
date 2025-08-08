import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import json
from pathlib import Path
import sys
from datetime import datetime
import webbrowser
import re
import time
import psutil
from dotenv import load_dotenv

# Import do obsługi plików Word
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️ python-docx nie jest dostępne. Zainstaluj: pip install python-docx")

def safe_read_docx(file_path):
    """Bezpiecznie wczytuje plik .docx z obsługą błędów"""
    try:
        # Sprawdź czy plik nie jest tymczasowy (z prefiksem ~)
        if file_path.name.startswith('~'):
            return None, f"Plik {file_path.name} jest plikiem tymczasowym/zablokowanym. Spróbuj ponownie za chwilę."
        
        doc = Document(file_path)
        content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        return content, None
    except Exception as e:
        if "File is not a zip file" in str(e):
            return None, f"Plik {file_path.name} nie jest w formacie .docx (prawdopodobnie stary format .doc)"
        else:
            return None, f"Błąd wczytywania pliku .docx: {str(e)}"

class VideoTranslationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Translation Studio v1")
        self.root.geometry("1200x800")
        
        # Zwiększenie domyślnych czcionek
        self.root.option_add('*TLabel*Font', ('Arial', 11))
        self.root.option_add('*TButton*Font', ('Arial', 12))
        self.root.option_add('*TLabelFrame*Font', ('Arial', 14, 'bold'))
        self.root.option_add('*TNotebook*Tab*Font', ('Arial', 12))
        
        # Wczytaj zmienne środowiskowe z .env
        load_dotenv()
        
        # Konfiguracja
        self.config_file = "video_translation_config.json"
        self.load_config()
        
        # Zmienne
        self.working_dir = tk.StringVar(value=self.config.get('working_dir', ''))
        self.youtube_url = tk.StringVar()
        self.video_path = tk.StringVar()
        self.current_step = tk.StringVar(value="Gotowy do rozpoczęcia")
        
        # Zmienne dla kluczy API
        self.openai_api_key = tk.StringVar(value=os.getenv('OPENAI_API_KEY', ''))
        self.elevenlabs_api_key = tk.StringVar(value=os.getenv('ELEVENLABS_API_KEY', ''))
        
        # Zmienne dla Facebook API (tymczasowo zahardkodowane na potrzeby testu)
        self.facebook_app_id = tk.StringVar(value='1839264433470173')
        self.facebook_app_secret = tk.StringVar(value='0f50c2f3c36c9eafe6767a3f6a9fa761')
        # PAGE ACCESS TOKEN (EduPandeEn)
        self.facebook_access_token = tk.StringVar(value='EAAaIzR80et0BPLJQqutgrSqT6PAF4HqCNBXFfioVDYvaHRXZBkFXNExYfHXmbd8gSL6AKlWE0OBswZANYiZCzlPeswaFB0TuWdtpnZAGHZAaE5ZAu2h0sxZCI4fy6ZAi0Imjr6vB94KF6EfcOFPZCBw8WwNw4eMehpmBSQfYZBWgI1ZBhatH1IBrKYiipKQZCbSStp96a8kRgo9WuMEimMJ9qhgFkXeNC9W4sIgct6pxSSdxIyIz10IZD')
        
        # Zmienne do śledzenia ostatnio pobranych plików
        self.last_downloaded_video = None
        self.last_transcription_file = None
        
        # Lista aktywnych wątków
        self.active_threads = []
        
        # Zmienne do postępu
        self.current_process = None
        self.progress_vars = {}
        self.progress_labels = {}
        self.progress_bars = {}
        self.stop_flags = {}
        
        # Zmienne dla checkboxów KOMBO (domyślnie wszystkie zaznaczone)
        self.combo_steps_enabled = {
            'translate': tk.BooleanVar(value=True),
            'generate': tk.BooleanVar(value=True), 
            'overlay': tk.BooleanVar(value=True),
            'delete_sm': tk.BooleanVar(value=True),
            'white_logo': tk.BooleanVar(value=True),
            'detect_polish': tk.BooleanVar(value=True),
            'intro_outro': tk.BooleanVar(value=True),
            'social_media': tk.BooleanVar(value=True)
        }
        
        # Zmienne dla intro/outro (używane w kombo)
        self.intro_video_path = tk.StringVar()
        self.outro_video_path = tk.StringVar()
        self.main_video_path = tk.StringVar()
        
        # Zmienne dla dodatkowych funkcji
        self.gap_numbers = tk.StringVar()
        
        # Zmienne dla YouTube upload
        self.youtube_title = tk.StringVar()
        self.youtube_description_part1 = tk.StringVar()  # Część 1 opisu
        self.youtube_description_part2 = tk.StringVar()  # Część 2 opisu
        self.youtube_tags = tk.StringVar()
        self.youtube_category = tk.StringVar(value="Education")
        self.youtube_privacy = tk.StringVar(value="private")
        self.youtube_thumbnail_path = tk.StringVar()
        
        # Zmienne dla listy wideo z kanału
        self.channel_videos = []
        self.selected_video_for_copy = None
        
        # Obsługa zamknięcia aplikacji
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.setup_ui()
        
    def load_config(self):
        """Ładuje konfigurację z pliku"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    'working_dir': '',
                    'api_keys': {},
                    'last_used_files': {}
                }
        except Exception as e:
            print(f"Błąd ładowania konfiguracji: {e}")
            self.config = {
                'working_dir': '',
                'api_keys': {},
                'last_used_files': {}
            }
    
    def save_config(self):
        """Zapisuje konfigurację do pliku"""
        try:
            self.config['working_dir'] = self.working_dir.get()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd zapisywania konfiguracji: {e}")
    
    def save_api_keys(self):
        """Zapisuje klucze API do pliku .env"""
        try:
            env_content = f"""# Video Translation Studio - Environment Variables
# This file contains API keys and should NOT be committed to Git

# OpenAI API Key (required for transcription and translation)
OPENAI_API_KEY={self.openai_api_key.get()}

# ElevenLabs API Key (optional, for voice generation)
ELEVENLABS_API_KEY={self.elevenlabs_api_key.get()}

# Facebook API Keys (optional, for social media posting)
FACEBOOK_APP_ID={self.facebook_app_id.get()}
FACEBOOK_APP_SECRET={self.facebook_app_secret.get()}
FACEBOOK_ACCESS_TOKEN={self.facebook_access_token.get()}
"""
            
            # Spróbuj różne lokalizacje dla pliku .env (szczególnie ważne na macOS)
            env_locations = [
                '.env',  # Bieżący katalog
                os.path.expanduser('~/.env'),  # Katalog domowy użytkownika
                os.path.join(os.path.expanduser('~'), 'Documents', '.env'),  # Dokumenty
                os.path.join(os.path.expanduser('~'), 'Desktop', '.env')  # Pulpit
            ]
            
            saved = False
            saved_location = None
            
            for env_path in env_locations:
                try:
                    # Upewnij się, że katalog istnieje
                    dir_path = os.path.dirname(os.path.abspath(env_path))
                    if dir_path:  # Jeśli ścieżka zawiera katalog
                        os.makedirs(dir_path, exist_ok=True)
                    
                    with open(env_path, 'w', encoding='utf-8') as f:
                        f.write(env_content)
                    
                    saved = True
                    saved_location = env_path
                    break
                    
                except (PermissionError, OSError):
                    continue
            
            # Ustaw zmienne środowiskowe (zawsze)
            os.environ['OPENAI_API_KEY'] = self.openai_api_key.get()
            os.environ['ELEVENLABS_API_KEY'] = self.elevenlabs_api_key.get()
            os.environ['FACEBOOK_APP_ID'] = self.facebook_app_id.get()
            os.environ['FACEBOOK_APP_SECRET'] = self.facebook_app_secret.get()
            os.environ['FACEBOOK_ACCESS_TOKEN'] = self.facebook_access_token.get()
            
            if saved:
                self.log(f"✅ Klucze API zostały zapisane do: {saved_location}")
                messagebox.showinfo("Sukces", f"Klucze API zostały zapisane pomyślnie!\nLokalizacja: {saved_location}")
            else:
                self.log("⚠️ Nie udało się zapisać pliku .env, ale klucze zostały ustawione tymczasowo")
                messagebox.showwarning("Ostrzeżenie", 
                    "Nie udało się zapisać pliku .env (brak uprawnień).\n"
                    "Klucze zostały ustawione tymczasowo - będziesz musiał je wprowadzić ponownie po restarcie.\n\n"
                    "Rozwiązanie: Przenieś aplikację do folderu Dokumenty lub Pulpit.")
            
        except Exception as e:
            error_msg = f"Błąd zapisywania kluczy API: {e}"
            self.log(f"❌ {error_msg}")
            messagebox.showerror("Błąd", error_msg)
    
    def setup_ui(self):
        """Konfiguruje interfejs użytkownika z nowoczesnym wyglądem"""
        # Ustaw nowoczesny styl
        self.setup_modern_style()
        
        # Główny kontener
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Konfiguracja grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Nagłówek z nowoczesnym designem
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        title_label = ttk.Label(header_frame, text="🎬 Video Translation Studio", 
                               font=('Segoe UI', 24, 'bold'), foreground='#2c3e50')
        title_label.pack()
        
        # Status z nowoczesnym stylem
        status_label = ttk.Label(header_frame, textvariable=self.current_step, 
                                font=('Segoe UI', 11), foreground='#7f8c8d')
        status_label.pack(pady=(5, 0))
        
        # Panel wyboru folderu z nowoczesnym stylem
        folder_frame = ttk.LabelFrame(main_frame, text="📁 Folder roboczy (folder główny procesowanego wideo)", padding="12")
        folder_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        ttk.Label(folder_frame, text="Folder roboczy:", font=('Segoe UI', 10)).grid(row=0, column=0, sticky=tk.W)
        folder_entry = ttk.Entry(folder_frame, textvariable=self.working_dir, width=50, font=('Segoe UI', 10))
        folder_entry.grid(row=0, column=1, padx=(10, 10))
        select_btn = ttk.Button(folder_frame, text="📂 Wybierz", command=self.select_working_dir, style='Accent.TButton')
        select_btn.grid(row=0, column=2)
        
        # Notebook (zakładki) z nowoczesnym stylem
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        
        # Zakładka 1: Konfiguracja API
        self.api_tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(self.api_tab, text="🔑 Konfiguracja API")
        self.setup_api_tab()
        
        # Zakładka 2: Krok 1
        self.step1_tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(self.step1_tab, text="🎯 Krok 1")
        self.setup_step1_tab()
        
        # Zakładka 3: KOMBO
        self.combo_tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(self.combo_tab, text="⚡ KOMBO")
        self.setup_combo_tab()
        
        # Zakładka 4: Upload na YT
        self.upload_tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(self.upload_tab, text="📤 Upload na YT")
        self.setup_upload_tab()
        
        # Zakładka 5: Post na social media
        self.social_media_tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(self.social_media_tab, text="📱 Post na social media")
        self.setup_social_media_tab()
        
        # Zakładka 6: Dodatkowe funkcje
        self.extra_tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(self.extra_tab, text="🔧 Dodatkowe funkcje")
        self.setup_extra_tab()
        
        # Zakładka 7: Logi
        self.logs_tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(self.logs_tab, text="📋 Logi")
        self.setup_logs_tab()
        
        # Konfiguracja grid
        main_frame.rowconfigure(2, weight=1)
        
        # Wczytaj intro/outro po utworzeniu wszystkich widgetów
        self.load_intro_outro_files()
        
    def setup_modern_style(self):
        """Ustawia nowoczesny styl aplikacji"""
        try:
            # Próbuj użyć nowoczesnego stylu
            style = ttk.Style()
            
            # Ustaw nowoczesny motyw
            available_themes = style.theme_names()
            if 'clam' in available_themes:
                style.theme_use('clam')
            elif 'vista' in available_themes:
                style.theme_use('vista')
            
            # Konfiguruj kolory i style
            style.configure('TLabel', font=('Segoe UI', 10))
            style.configure('TButton', font=('Segoe UI', 10), padding=6)
            style.configure('TEntry', font=('Segoe UI', 10), padding=4)
            style.configure('TNotebook', font=('Segoe UI', 10))
            style.configure('TNotebook.Tab', font=('Segoe UI', 10), padding=[12, 6])
            style.configure('TLabelframe', font=('Segoe UI', 10, 'bold'))
            style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'))
            
            # Styl dla przycisków akcji
            style.configure('Accent.TButton', 
                          background='#3498db', 
                          foreground='white',
                          font=('Segoe UI', 10, 'bold'))
            
            # Styl dla czerwonego przycisku
            style.configure('Red.TButton', 
                          background='#e74c3c', 
                          foreground='white',
                          font=('Segoe UI', 10, 'bold'))
            
            # Styl dla małych przycisków
            style.configure('Small.TButton', 
                          font=('Segoe UI', 9),
                          padding=4)
            
            # Styl dla checkboxów
            style.configure('TCheckbutton', font=('Segoe UI', 10))
            
        except Exception as e:
            print(f"Nie udało się ustawić nowoczesnego stylu: {e}")
        
    def setup_api_tab(self):
        """Konfiguruje zakładkę Konfiguracja API"""
        # OpenAI API Key
        ttk.Label(self.api_tab, text="OpenAI API Key:", font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        openai_entry = ttk.Entry(self.api_tab, textvariable=self.openai_api_key, width=70, show="*", font=('Segoe UI', 10))
        openai_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # ElevenLabs API Key
        ttk.Label(self.api_tab, text="ElevenLabs API Key:", font=('Segoe UI', 11, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        elevenlabs_entry = ttk.Entry(self.api_tab, textvariable=self.elevenlabs_api_key, width=70, show="*", font=('Segoe UI', 10))
        elevenlabs_entry.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Facebook API Keys
        ttk.Label(self.api_tab, text="Facebook App ID:", font=('Segoe UI', 11, 'bold')).grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        facebook_app_id_entry = ttk.Entry(self.api_tab, textvariable=self.facebook_app_id, width=70, font=('Segoe UI', 10))
        facebook_app_id_entry.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(self.api_tab, text="Facebook App Secret:", font=('Segoe UI', 11, 'bold')).grid(row=6, column=0, sticky=tk.W, pady=(0, 5))
        facebook_app_secret_entry = ttk.Entry(self.api_tab, textvariable=self.facebook_app_secret, width=70, show="*", font=('Segoe UI', 10))
        facebook_app_secret_entry.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(self.api_tab, text="Facebook Access Token:", font=('Segoe UI', 11, 'bold')).grid(row=8, column=0, sticky=tk.W, pady=(0, 5))
        facebook_token_entry = ttk.Entry(self.api_tab, textvariable=self.facebook_access_token, width=70, show="*", font=('Segoe UI', 10))
        facebook_token_entry.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Przycisk zapisz klucze
        save_keys_btn = ttk.Button(self.api_tab, text="💾 Zapisz klucze", command=self.save_api_keys, style='Accent.TButton')
        save_keys_btn.grid(row=4, column=0, columnspan=2, pady=(0, 10))
        
        # Informacja
        info_text = "💡 Wprowadź swoje klucze API i kliknij 'Zapisz klucze'. Klucze zostaną zapisane lokalnie i będą automatycznie ładowane przy następnym uruchomieniu."
        info_label = ttk.Label(self.api_tab, text=info_text, wraplength=600, justify=tk.LEFT, 
                              font=('Segoe UI', 9), foreground='#7f8c8d')
        info_label.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Konfiguracja grid
        self.api_tab.columnconfigure(0, weight=1)
        
    def setup_combo_tab(self):
        """Konfiguruje zakładkę KOMBO"""
        # Checkboxy kroków
        steps_frame = ttk.LabelFrame(self.combo_tab, text="📋 Wybierz kroki do wykonania", padding="15")
        steps_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Grid dla checkboxów (2 kolumny)
        steps_frame.columnconfigure(0, weight=1)
        steps_frame.columnconfigure(1, weight=1)
        
        step_descriptions = {
            'translate': "1. 🌐 Tłumaczenie na angielski",
            'generate': "2. 🎵 Generowanie audio",
            'overlay': "3. 🎬 Nakładanie audio na wideo (STABILNIE)",
            'delete_sm': "4. 🔇 Usuwanie ciszy i bezruchu (STABILNIE)",
            'white_logo': "5. 🖼️ Usuń białą stopkę i dodaj logo",
            'detect_polish': "6. 🔍 Wykrywanie polskiego tekstu",
            'intro_outro': "7. 🎬 Dodawanie intro i outro (SZYBKO)",
            'social_media': "8. 📱 Generowanie posta social media"
        }
        
        row = 0
        col = 0
        for step_key, description in step_descriptions.items():
            cb = ttk.Checkbutton(steps_frame, text=description, variable=self.combo_steps_enabled[step_key])
            cb.grid(row=row, column=col, sticky=tk.W, padx=(0, 20), pady=2)
            
            if col == 0:
                col = 1
            else:
                col = 0
                row += 1
        
        # Przyciski kontrolne
        buttons_frame = ttk.Frame(self.combo_tab)
        buttons_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Button(buttons_frame, text="✅ Zaznacz wszystkie", 
                  command=self.select_all_combo_steps, style='Accent.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="❌ Odznacz wszystkie", 
                  command=self.deselect_all_combo_steps).pack(side=tk.LEFT, padx=(0, 20))
        
        # Przyciski uruchom/stop
        run_btn = ttk.Button(buttons_frame, text="🚀 Uruchom KOMBO", 
                           command=self.run_combo_workflow, style='Accent.TButton')
        run_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        stop_btn = ttk.Button(buttons_frame, text="⏹️ STOP", 
                             command=lambda: self.stop_operation('combo'), style='Red.TButton')
        stop_btn.pack(side=tk.RIGHT)
        
        # Postęp
        self.progress_vars['combo'] = tk.DoubleVar()
        self.progress_labels['combo'] = tk.StringVar(value="Gotowy do uruchomienia")
        
        progress_frame = ttk.LabelFrame(self.combo_tab, text="📊 Postęp", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_bars['combo'] = ttk.Progressbar(progress_frame, variable=self.progress_vars['combo'], 
                                                    maximum=100, length=400)
        self.progress_bars['combo'].pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(progress_frame, textvariable=self.progress_labels['combo'], 
                font=('Segoe UI', 9)).pack(anchor=tk.W)
        
    def setup_step1_tab(self):
        """Konfiguruje zakładkę Krok 1"""
        # Opis
        desc_text = """🎯 Krok 1: Pobieranie i transkrypcja. Aplikacja pobierze wideo z YouTube (ew. wskaż plik na dysku), wykona transkrypcję polskiego tekstu do pliku z odpowiednią strukturą sentencji, który następnie należy przejrzeć i ewentualnie poprawić."""
        ttk.Label(self.step1_tab, text=desc_text, wraplength=700, justify=tk.LEFT, 
                font=('Segoe UI', 10), foreground='#2c3e50').pack(anchor=tk.W, pady=(0, 20))
        
        # Input frame
        input_frame = ttk.LabelFrame(self.step1_tab, text="📹 Źródło wideo", padding="15")
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        # YouTube URL
        youtube_frame = ttk.Frame(input_frame)
        youtube_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(youtube_frame, text="YouTube URL:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        ttk.Entry(youtube_frame, textvariable=self.youtube_url, width=60, font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(5, 0))
        ttk.Button(youtube_frame, text="📥 Pobierz z YouTube i transkrybuj", 
                  command=lambda: self.run_step1("youtube"), style='Red.TButton').pack(anchor=tk.W, pady=(10, 0))
        
        # Separator
        separator1 = ttk.Separator(input_frame, orient='horizontal')
        separator1.pack(fill=tk.X, pady=15)
        
        # Plik wideo
        file_frame = ttk.Frame(input_frame)
        file_frame.pack(fill=tk.X)
        
        ttk.Label(file_frame, text="Plik wideo:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        file_select_frame = ttk.Frame(file_frame)
        file_select_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Entry(file_select_frame, textvariable=self.video_path, width=50, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_select_frame, text="📂 Wybierz plik", 
                  command=self.select_video_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_select_frame, text="🎬 Transkrybuj plik", 
                  command=lambda: self.run_step1("file"), style='Accent.TButton').pack(side=tk.LEFT)
        
    def setup_extra_tab(self):
        """Konfiguruje zakładkę Dodatkowe funkcje"""
        # Cofnij usunięcie luki
        gap_frame = ttk.LabelFrame(self.extra_tab, text="🔄 Cofnij usunięcie luki", padding="15")
        gap_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(gap_frame, text="Wprowadź numer lub numery luk:", font=('Segoe UI', 10)).pack(anchor=tk.W)
        ttk.Entry(gap_frame, textvariable=self.gap_numbers, width=30, font=('Segoe UI', 10)).pack(anchor=tk.W, pady=5)
        ttk.Button(gap_frame, text="↩️ Cofnij usunięcie", 
                  command=self.revert_gap_removal, style='Accent.TButton').pack(anchor=tk.W, pady=5)
        
    def setup_social_media_tab(self):
        """Konfiguruje zakładkę Post na social media"""
        # Główny kontener z dwoma kolumnami
        main_container = ttk.Frame(self.social_media_tab)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Konfiguracja kolumn i wierszy
        main_container.columnconfigure(0, weight=1)  # Lewa kolumna - Facebook
        main_container.columnconfigure(1, weight=1)  # Prawa kolumna - Instagram
        main_container.rowconfigure(0, weight=1)     # Wiersz - 100% wysokości
        
        # ===== LEWA KOLUMNA - FACEBOOK =====
        facebook_frame = ttk.LabelFrame(main_container, text="📘 Facebook", padding="15")
        facebook_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Wybór wideo
        video_frame = ttk.LabelFrame(facebook_frame, text="Wybór wideo", padding="10")
        video_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.facebook_video_path = tk.StringVar()
        ttk.Label(video_frame, text="Wideo do posta:").pack(anchor=tk.W)
        video_select_frame = ttk.Frame(video_frame)
        video_select_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(video_select_frame, text="Wybierz wideo", command=self.select_facebook_video, style='Accent.TButton').pack(side=tk.LEFT)
        ttk.Label(video_select_frame, textvariable=self.facebook_video_path, text="Nie wybrano wideo").pack(side=tk.LEFT, padx=(10, 0))

        # Wybór zdjęcia
        image_frame = ttk.LabelFrame(facebook_frame, text="Wybór zdjęcia", padding="10")
        image_frame.pack(fill=tk.X, pady=(0, 15))

        self.facebook_image_path = tk.StringVar()
        ttk.Label(image_frame, text="Zdjęcie do posta (opcjonalnie):").pack(anchor=tk.W)
        image_select_frame = ttk.Frame(image_frame)
        image_select_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(image_select_frame, text="Wybierz zdjęcie", command=self.select_facebook_image, style='Accent.TButton').pack(side=tk.LEFT)
        ttk.Label(image_select_frame, textvariable=self.facebook_image_path, text="Nie wybrano zdjęcia").pack(side=tk.LEFT, padx=(10, 0))
        
        # Treść posta
        content_frame = ttk.LabelFrame(facebook_frame, text="Treść posta", padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        ttk.Label(content_frame, text="Tekst posta:").pack(anchor=tk.W)
        self.facebook_post_text = tk.Text(content_frame, height=8, width=50, font=('Segoe UI', 10), wrap=tk.WORD)
        facebook_scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.facebook_post_text.yview)
        self.facebook_post_text.configure(yscrollcommand=facebook_scrollbar.set)
        
        text_container = ttk.Frame(content_frame)
        text_container.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.facebook_post_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        facebook_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Przycisk "Podczytaj z raportu"
        ttk.Button(content_frame, text="📄 Podczytaj z raportu", command=self.load_facebook_post_from_report, style='Small.TButton').pack(anchor=tk.W, pady=(10, 0))

        # Komentarz po publikacji (np. link do YouTube)
        ttk.Label(content_frame, text="Komentarz po publikacji (opcjonalnie, np. link do YouTube):").pack(anchor=tk.W, pady=(10, 2))
        self.facebook_comment_var = tk.StringVar()
        ttk.Entry(content_frame, textvariable=self.facebook_comment_var, font=('Segoe UI', 10)).pack(fill=tk.X)
        
        # Przyciski akcji
        actions_frame = ttk.Frame(facebook_frame)
        actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(actions_frame, text="📋 Kopiuj tekst", command=self.copy_facebook_post, style='Small.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(actions_frame, text="📤 Opublikuj na Facebook", command=self.publish_facebook_post, style='Accent.TButton').pack(side=tk.RIGHT)
        
        # ===== PRAWA KOLUMNA - INSTAGRAM =====
        instagram_frame = ttk.LabelFrame(main_container, text="📷 Instagram", padding="15")
        instagram_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        # Wybór wideo
        insta_video_frame = ttk.LabelFrame(instagram_frame, text="Wybór wideo", padding="10")
        insta_video_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.instagram_video_path = tk.StringVar()
        ttk.Label(insta_video_frame, text="Wideo do posta:").pack(anchor=tk.W)
        insta_video_select_frame = ttk.Frame(insta_video_frame)
        insta_video_select_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(insta_video_select_frame, text="Wybierz wideo", command=self.select_instagram_video, style='Accent.TButton').pack(side=tk.LEFT)
        ttk.Label(insta_video_select_frame, textvariable=self.instagram_video_path, text="Nie wybrano wideo").pack(side=tk.LEFT, padx=(10, 0))
        
        # Treść posta
        insta_content_frame = ttk.LabelFrame(instagram_frame, text="Treść posta", padding="10")
        insta_content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        ttk.Label(insta_content_frame, text="Tekst posta:").pack(anchor=tk.W)
        self.instagram_post_text = tk.Text(insta_content_frame, height=8, width=50, font=('Segoe UI', 10), wrap=tk.WORD)
        insta_scrollbar = ttk.Scrollbar(insta_content_frame, orient=tk.VERTICAL, command=self.instagram_post_text.yview)
        self.instagram_post_text.configure(yscrollcommand=insta_scrollbar.set)
        
        insta_text_container = ttk.Frame(insta_content_frame)
        insta_text_container.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.instagram_post_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        insta_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Przycisk "Podczytaj z raportu"
        ttk.Button(insta_content_frame, text="📄 Podczytaj z raportu", command=self.load_instagram_post_from_report, style='Small.TButton').pack(anchor=tk.W, pady=(10, 0))
        
        # Przyciski akcji
        insta_actions_frame = ttk.Frame(instagram_frame)
        insta_actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(insta_actions_frame, text="📋 Kopiuj tekst", command=self.copy_instagram_post, style='Small.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(insta_actions_frame, text="📤 Opublikuj na Instagram", command=self.publish_instagram_post, style='Accent.TButton').pack(side=tk.RIGHT)
        
    def setup_logs_tab(self):
        """Konfiguruje zakładkę Logi"""
        # Logi z nowoczesnym stylem
        log_frame = ttk.LabelFrame(self.logs_tab, text="📋 Logi operacji", padding="12")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=80, 
                                                font=('Consolas', 9), 
                                                bg='#f8f9fa', fg='#2c3e50',
                                                insertbackground='#3498db')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Przycisk czyszczenia logów
        clear_btn = ttk.Button(self.logs_tab, text="🗑️ Wyczyść logi", 
                              command=self.clear_logs, style='Accent.TButton')
        clear_btn.pack(anchor=tk.W, pady=(10, 0))
        
        # Konfiguracja grid
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.logs_tab.columnconfigure(0, weight=1)
        self.logs_tab.rowconfigure(0, weight=1)
    
    def setup_upload_tab(self):
        """Konfiguruje zakładkę Upload na YT"""
        # Główny kontener z dwoma kolumnami
        main_container = ttk.Frame(self.upload_tab)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Konfiguracja kolumn i wierszy
        main_container.columnconfigure(0, weight=7)  # Lewa kolumna - Upload na YouTube
        main_container.columnconfigure(1, weight=3)  # Prawa kolumna - Materiały na kanale
        main_container.rowconfigure(0, weight=1)     # Wiersz - 100% wysokości
        
        # ===== LEWA KOLUMNA - UPLOAD NA YOUTUBE =====
        left_frame = ttk.LabelFrame(main_container, text="📤 Upload na YouTube", padding="15")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Canvas i scrollbar dla lewej kolumny
        left_canvas = tk.Canvas(left_frame)
        left_scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=left_canvas.yview)
        left_scrollable_frame = ttk.Frame(left_canvas)
        
        left_scrollable_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        
        left_canvas.create_window((0, 0), window=left_scrollable_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        # Wybór wideo
        video_frame = ttk.LabelFrame(left_scrollable_frame, text="🎬 Wybór wideo do uploadu", padding="10")
        video_frame.pack(fill=tk.X, pady=(0, 15))
        
        select_video_btn = ttk.Button(video_frame, text="📁 Wybierz wideo", command=self.select_upload_video, style='Accent.TButton')
        select_video_btn.pack(anchor=tk.W, pady=(0, 10))
        
        self.upload_video_path_label = ttk.Label(video_frame, text="Nie wybrano wideo", font=('Segoe UI', 9), foreground='#e74c3c')
        self.upload_video_path_label.pack(anchor=tk.W)
        
        # Sekcja: Metadane wideo
        metadata_frame = ttk.LabelFrame(left_scrollable_frame, text="📝 Metadane wideo", padding="10")
        metadata_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Tytuł
        ttk.Label(metadata_frame, text="Tytuł wideo:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        title_entry = ttk.Entry(metadata_frame, textvariable=self.youtube_title, width=60, font=('Segoe UI', 10))
        title_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Opis - Część 1
        desc1_frame = ttk.Frame(metadata_frame)
        desc1_frame.pack(fill=tk.X, pady=(0, 10))
        
        desc1_label_frame = ttk.Frame(desc1_frame)
        desc1_label_frame.pack(fill=tk.X)
        
        ttk.Label(desc1_label_frame, text="Opis wideo - Część 1:", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        load_from_report_btn = ttk.Button(desc1_label_frame, text="📄 Podczytaj z raportu", 
                                        command=self.load_description_from_report, style='Small.TButton')
        load_from_report_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.desc_part1_text = tk.Text(metadata_frame, height=4, width=60, font=('Segoe UI', 10), wrap=tk.WORD)
        self.desc_part1_text.pack(fill=tk.X, pady=(0, 10))
        
        # Opis - Część 2 (rozciągalne)
        desc2_frame = ttk.Frame(metadata_frame)
        desc2_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        ttk.Label(desc2_frame, text="Opis wideo - Część 2 (opcjonalnie):", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        # Kontener z przewijaniem dla części 2
        desc2_container = ttk.Frame(desc2_frame)
        desc2_container.pack(fill=tk.BOTH, expand=True)
        
        self.desc_part2_text = tk.Text(desc2_container, height=9, width=60, font=('Segoe UI', 10), wrap=tk.WORD)
        desc2_scrollbar = ttk.Scrollbar(desc2_container, orient=tk.VERTICAL, command=self.desc_part2_text.yview)
        self.desc_part2_text.configure(yscrollcommand=desc2_scrollbar.set)
        
        self.desc_part2_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc2_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tagi
        tags_frame = ttk.Frame(metadata_frame)
        tags_frame.pack(fill=tk.X, pady=(0, 15))
        
        tags_label_frame = ttk.Frame(tags_frame)
        tags_label_frame.pack(fill=tk.X)
        
        ttk.Label(tags_label_frame, text="Tagi (oddzielone przecinkami):", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        load_tags_btn = ttk.Button(tags_label_frame, text="🏷️ Podczytaj tagi z raportu", 
                                  command=self.load_tags_from_report, style='Small.TButton')
        load_tags_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        tags_entry = ttk.Entry(tags_frame, textvariable=self.youtube_tags, width=60, font=('Segoe UI', 10))
        tags_entry.pack(fill=tk.X, pady=(5, 0))
        
        # Kategoria i prywatność
        settings_frame = ttk.Frame(metadata_frame)
        settings_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Kategoria
        ttk.Label(settings_frame, text="Kategoria:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        category_combo = ttk.Combobox(settings_frame, textvariable=self.youtube_category, 
                                     values=["Education", "Science & Technology", "Howto & Style", "Entertainment", "People & Blogs"],
                                     state="readonly", font=('Segoe UI', 10))
        category_combo.pack(anchor=tk.W, pady=(0, 15))
        
        # Prywatność
        ttk.Label(settings_frame, text="Prywatność:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        privacy_frame = ttk.Frame(settings_frame)
        privacy_frame.pack(anchor=tk.W, pady=(0, 15))
        
        ttk.Radiobutton(privacy_frame, text="Prywatne", variable=self.youtube_privacy, value="private").pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(privacy_frame, text="Niepubliczne", variable=self.youtube_privacy, value="unlisted").pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(privacy_frame, text="Publiczne", variable=self.youtube_privacy, value="public").pack(side=tk.LEFT)
        
        # Sekcja: Miniaturka
        thumbnail_frame = ttk.LabelFrame(left_scrollable_frame, text="🖼️ Miniaturka (opcjonalnie)", padding="10")
        thumbnail_frame.pack(fill=tk.X, pady=(0, 15))
        
        select_thumbnail_btn = ttk.Button(thumbnail_frame, text="🖼️ Wybierz miniaturkę", command=self.select_thumbnail, style='Accent.TButton')
        select_thumbnail_btn.pack(anchor=tk.W, pady=(0, 10))
        
        self.thumbnail_path_label = ttk.Label(thumbnail_frame, text="Nie wybrano miniaturki", font=('Segoe UI', 9), foreground='#7f8c8d')
        self.thumbnail_path_label.pack(anchor=tk.W)
        
        # Sekcja: Upload
        upload_frame = ttk.LabelFrame(left_scrollable_frame, text="🚀 Upload", padding="10")
        upload_frame.pack(fill=tk.X, pady=(0, 15))
        
        upload_btn = ttk.Button(upload_frame, text="📤 Upload na YouTube", command=self.upload_to_youtube, style='Red.TButton')
        upload_btn.pack(anchor=tk.W, pady=(0, 10))
        
        info_text = "⚠️ Wymagane: Konto Google z dostępem do YouTube API. Pierwszy upload może wymagać autoryzacji."
        info_label = ttk.Label(upload_frame, text=info_text, wraplength=400, justify=tk.LEFT, 
                              font=('Segoe UI', 9), foreground='#e67e22')
        info_label.pack(anchor=tk.W)
        
        # Konfiguracja scrollbara dla lewej kolumny
        left_canvas.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")
        
        # ===== PRAWA KOLUMNA - MATERIAŁY NA KANALE =====
        right_frame = ttk.LabelFrame(main_container, text="📋 Materiały na kanale", padding="15")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        # Canvas i scrollbar dla prawej kolumny
        right_canvas = tk.Canvas(right_frame)
        right_scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=right_canvas.yview)
        right_scrollable_frame = ttk.Frame(right_canvas)
        
        right_scrollable_frame.bind(
            "<Configure>",
            lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        )
        
        right_canvas.create_window((0, 0), window=right_scrollable_frame, anchor="nw")
        right_canvas.configure(yscrollcommand=right_scrollbar.set)
        
        # Tytuł prawej kolumny
        right_title = ttk.Label(right_scrollable_frame, text="📺 Materiały na kanale", font=('Segoe UI', 14, 'bold'))
        right_title.pack(anchor=tk.W, pady=(0, 20))
        
        # Przycisk odświeżania listy wideo
        refresh_btn = ttk.Button(right_scrollable_frame, text="🔄 Odśwież listę wideo", 
                                command=self.refresh_channel_videos, style='Accent.TButton')
        refresh_btn.pack(anchor=tk.W, pady=(0, 15))
        
        # Sekcja: Lista wideo
        videos_frame = ttk.LabelFrame(right_scrollable_frame, text="🎬 Ostatnie 3 wideo", padding="15")
        videos_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Lista wideo (zmniejszona wysokość)
        self.videos_listbox = tk.Listbox(videos_frame, height=4, font=('Segoe UI', 10))
        self.videos_listbox.pack(fill=tk.X, pady=(0, 10))
        
        # Sekcja: Szczegóły wybranego wideo
        details_frame = ttk.LabelFrame(right_scrollable_frame, text="📋 Szczegóły wybranego wideo", padding="15")
        details_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tytuł wideo
        title_frame = ttk.Frame(details_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text="Tytuł wideo:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        self.selected_video_title = ttk.Label(title_frame, text="Wybierz wideo z listy powyżej", 
                                            font=('Segoe UI', 9), foreground='#7f8c8d', wraplength=400)
        self.selected_video_title.pack(anchor=tk.W, pady=(2, 5))
        
        copy_title_btn = ttk.Button(title_frame, text="📋 Kopiuj tytuł", 
                                   command=self.copy_video_title, style='Small.TButton')
        copy_title_btn.pack(anchor=tk.W)
        
        # Opis wideo
        desc_frame = ttk.Frame(details_frame)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        ttk.Label(desc_frame, text="Opis wideo:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        
        # Kontener z przewijaniem dla opisu
        desc_container = ttk.Frame(desc_frame)
        desc_container.pack(fill=tk.BOTH, expand=True, pady=(2, 5))
        
        self.selected_video_description = tk.Text(desc_container, height=6, width=50, font=('Segoe UI', 9), 
                                                wrap=tk.WORD, state=tk.DISABLED)
        desc_scrollbar = ttk.Scrollbar(desc_container, orient=tk.VERTICAL, command=self.selected_video_description.yview)
        self.selected_video_description.configure(yscrollcommand=desc_scrollbar.set)
        
        self.selected_video_description.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        copy_desc_btn = ttk.Button(desc_frame, text="📋 Kopiuj opis", 
                                  command=self.copy_video_description, style='Small.TButton')
        copy_desc_btn.pack(anchor=tk.W)
        
        # Tagi wideo
        tags_frame = ttk.Frame(details_frame)
        tags_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(tags_frame, text="Tagi wideo:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        self.selected_video_tags = ttk.Label(tags_frame, text="Brak tagów", 
                                           font=('Segoe UI', 9), foreground='#7f8c8d', wraplength=400)
        self.selected_video_tags.pack(anchor=tk.W, pady=(2, 5))
        
        copy_tags_btn = ttk.Button(tags_frame, text="📋 Kopiuj tagi", 
                                  command=self.copy_video_tags, style='Small.TButton')
        copy_tags_btn.pack(anchor=tk.W)
        
        # Konfiguracja przewijania dla prawej kolumny
        right_canvas.pack(side="left", fill="both", expand=True)
        right_scrollbar.pack(side="right", fill="y")
        
        # Bind dla przewijania myszką
        def _on_mousewheel(event):
            right_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        right_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Bind dla wyboru wideo z listy
        self.videos_listbox.bind('<<ListboxSelect>>', self.on_video_selection_change)
        
        # Automatyczne załadowanie listy wideo przy starcie - WYŁĄCZONE
        # self.root.after(1000, self.refresh_channel_videos)
        
    # Usunięto setup_combo_content - zastąpione przez setup_combo_tab
    # Usunięto setup_extra_functions_content - zastąpione przez setup_extra_tab
    
    def select_all_combo_steps(self):
        """Zaznacza wszystkie kroki KOMBO"""
        for var in self.combo_steps_enabled.values():
            var.set(True)
    
    def deselect_all_combo_steps(self):
        """Odznacza wszystkie kroki KOMBO"""
        for var in self.combo_steps_enabled.values():
            var.set(False)
        

        

        

        

        
    def log(self, message):
        """Dodaje wiadomość do logów"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        # Usunięto self.root.update_idletasks() - może powodować problemy z GUI
        
    def run_combo_workflow(self):
        """Uruchamia wybrany przepływ KOMBO na podstawie zaznaczonych checkboxów"""
        from datetime import datetime
        
        # Reset flagi stop
        self.stop_flags['combo'] = False
        
        # Sprawdź czy jakikolwiek krok jest zaznaczony
        enabled_steps = [key for key, var in self.combo_steps_enabled.items() if var.get()]
        
        if not enabled_steps:
            messagebox.showwarning("Brak kroków", "Nie wybrano żadnego kroku do wykonania!")
            return
        
        self.combo_start_time = datetime.now()
        self.combo_step_times = {}  # Słownik na czasy kroków
        
        enabled_steps_text = ", ".join(enabled_steps)
        self.log(f"[KOMBO] Rozpoczynam wybrany przepływ KOMBO o {self.combo_start_time.strftime('%H:%M:%S')}")
        self.log(f"[KOMBO] Wybrane kroki: {enabled_steps_text}")
        self.show_stop_button('combo')
        
        # Wszystkie dostępne kroki z mapowaniem
        all_steps = {
            'translate': ("Tłumaczenie na angielski", self.run_translate_for_combo),
            'generate': ("Generowanie audio", self.run_generate_for_combo),
            'overlay': ("Nakładanie audio na wideo (STABILNIE)", self.run_overlay_for_combo),
            'delete_sm': ("Usuwanie ciszy i bezruchu (STABILNIE)", self.run_delete_sm_for_combo),
            'white_logo': ("Usuń białą stopkę i dodaj logo", self.run_white_logo_for_combo),
            'detect_polish': ("Wykrywanie polskiego tekstu", self.run_detect_polish_for_combo),
            'intro_outro': ("Dodawanie intro i outro (SZYBKO)", self.run_intro_outro_for_combo),
            'social_media': ("Generowanie posta social media", self.run_social_media_for_combo)
        }
        
        # Buduj listę kroków do wykonania na podstawie checkboxów
        self.combo_steps = []
        for step_key in ['translate', 'generate', 'overlay', 'delete_sm', 'white_logo', 'detect_polish', 'intro_outro', 'social_media']:
            if self.combo_steps_enabled[step_key].get():
                self.combo_steps.append(all_steps[step_key])
        
        self.current_combo_step = 0
        self.combo_failed = False
        self.execute_next_combo_step()
        
    def execute_next_combo_step(self):
        """Wykonuje następny krok w przepływie KOMBO"""
        from datetime import datetime
        
        # Sprawdź czy użytkownik zatrzymał proces
        if self.stop_flags.get('combo', False):
            self.log("[KOMBO] Przepływ KOMBO zatrzymany przez użytkownika")
            self.update_progress('combo', 0, "Zatrzymano")
            self.hide_stop_button('combo')
            self.stop_flags['combo'] = False  # Reset flagi
            return
        
        if self.combo_failed or self.current_combo_step >= len(self.combo_steps):
            if self.combo_failed:
                self.log("[KOMBO] Przepływ KOMBO przerwany z powodu błędu")
                self.update_progress('combo', 0, "Błąd")
            else:
                # Generuj końcowy raport
                self.generate_combo_final_report()
                self.update_progress('combo', 100, "Ukończono")
            self.hide_stop_button('combo')
            return
            
        step_name, step_function = self.combo_steps[self.current_combo_step]
        progress = (self.current_combo_step / len(self.combo_steps)) * 100
        
        # Rozpocznij śledzenie czasu kroku
        self.current_step_start_time = datetime.now()
        
        self.update_progress('combo', progress, f"Krok {self.current_combo_step + 1}/{len(self.combo_steps)}: {step_name}")
        self.log(f"[KOMBO] Krok {self.current_combo_step + 1}: {step_name} - START")
        
        # Wykonaj krok
        try:
            step_function()
        except Exception as e:
            self.log(f"[KOMBO] Błąd w kroku {step_name}: {str(e)}")
            self.combo_failed = True
            self.execute_next_combo_step()
            
    def finish_current_combo_step(self):
        """Kończy bieżący krok i zapisuje czas wykonania"""
        from datetime import datetime
        
        if hasattr(self, 'current_step_start_time'):
            step_name = self.combo_steps[self.current_combo_step][0]
            step_duration = datetime.now() - self.current_step_start_time
            self.combo_step_times[step_name] = step_duration
            
            duration_str = self.format_duration(step_duration)
            self.log(f"[KOMBO] Krok {self.current_combo_step + 1}: {step_name} - KONIEC (czas: {duration_str})")
        
        self.current_combo_step += 1
        self.execute_next_combo_step()
        
    def format_duration(self, duration):
        """Formatuje czas trwania na czytelny format"""
        total_seconds = int(duration.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
            
    def generate_combo_final_report(self):
        """Generuje końcowy raport z czasami wykonania"""
        from datetime import datetime
        
        total_duration = datetime.now() - self.combo_start_time
        
        self.log("=" * 60)
        self.log("[KOMBO] RAPORT KOŃCOWY - PEŁNY PRZEPŁYW KOMBO")
        self.log("=" * 60)
        self.log(f"Czas rozpoczęcia: {self.combo_start_time.strftime('%H:%M:%S')}")
        self.log(f"Czas zakończenia: {datetime.now().strftime('%H:%M:%S')}")
        self.log(f"CAŁKOWITY CZAS: {self.format_duration(total_duration)}")
        self.log("")
        self.log("CZASY POSZCZEGÓLNYCH KROKÓW:")
        
        for i, (step_name, _) in enumerate(self.combo_steps):
            if step_name in self.combo_step_times:
                duration = self.combo_step_times[step_name]
                duration_str = self.format_duration(duration)
                self.log(f"  {i+1}. {step_name}: {duration_str}")
            else:
                self.log(f"  {i+1}. {step_name}: nie ukończono")
        
        self.log("")
        self.log("[KOMBO] Przepływ KOMBO zakończony pomyślnie!")
        self.log("=" * 60)
            
    def run_translate_for_combo(self):
        """Uruchamia translate.py dla przepływu KOMBO"""
        thread = threading.Thread(target=self._run_translate_combo_thread, daemon=False)
        thread.start()
        
    def _run_translate_combo_thread(self):
        """Thread dla translate w przepływie KOMBO"""
        try:
            working_dir = Path(self.working_dir.get()) if self.working_dir.get() else Path.cwd()
            
            # Znajdź plik _sentences.txt
            sentences_files = list(working_dir.rglob("*_sentences.txt"))
            if not sentences_files:
                raise Exception("Nie znaleziono pliku *_sentences.txt")
                
            sentences_file = sentences_files[0]
            
            # Wygeneruj nazwę pliku wyjściowego (zamień _sentences.txt na _en.txt)
            output_file = sentences_file.with_name(sentences_file.stem.replace("_sentences", "_en") + ".txt")
            
            python_exe = Path(__file__).parent.parent / "myenv" / "Scripts" / "python.exe"
            translate_script = Path(__file__).parent / "translate.py"
            
            result = subprocess.run([
                str(python_exe), str(translate_script), str(sentences_file), str(output_file)
            ], capture_output=True, text=True, cwd=working_dir)
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.log("[KOMBO] Tłumaczenie zakończone pomyślnie"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Output: {result.stdout.strip()}"))
                self.root.after(0, self.finish_current_combo_step)
            else:
                error_msg = result.stderr.strip() if result.stderr else "Nieznany błąd"
                self.root.after(0, lambda: self.log(f"[KOMBO] Błąd translate.py: {error_msg}"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Stdout: {result.stdout.strip()}"))
                raise Exception(f"Błąd translate.py: {error_msg}")
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"[KOMBO] Błąd tłumaczenia: {str(e)}"))
            self.combo_failed = True
            self.root.after(0, self.execute_next_combo_step)
            
    def run_generate_for_combo(self):
        """Uruchamia generate.py dla przepływu KOMBO"""
        thread = threading.Thread(target=self._run_generate_combo_thread, daemon=False)
        thread.start()
        
    def _run_generate_combo_thread(self):
        """Thread dla generate w przepływie KOMBO"""
        try:
            working_dir = Path(self.working_dir.get()) if self.working_dir.get() else Path.cwd()
            
            # Znajdź plik _en.txt (przetłumaczony)
            en_files = list(working_dir.rglob("*_en.txt"))
            if not en_files:
                raise Exception("Nie znaleziono pliku *_en.txt")
                
            en_file = en_files[0]
            
            # Znajdź oryginalny plik wideo
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
            video_files = []
            for ext in video_extensions:
                video_files.extend(working_dir.rglob(f"*{ext}"))
            
            if not video_files:
                raise Exception("Nie znaleziono pliku wideo")
                
            video_file = video_files[0]
            
            python_exe = Path(__file__).parent.parent / "myenv" / "Scripts" / "python.exe"
            generate_script = Path(__file__).parent / "generate.py"
            
            result = subprocess.run([
                str(python_exe), str(generate_script), str(en_file), str(video_file)
            ], capture_output=True, text=True, cwd=working_dir)
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.log("[KOMBO] Generowanie audio zakończone pomyślnie"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Output: {result.stdout.strip()}"))
                self.root.after(0, self.finish_current_combo_step)
            else:
                error_msg = result.stderr.strip() if result.stderr else "Nieznany błąd"
                self.root.after(0, lambda: self.log(f"[KOMBO] Błąd generate.py: {error_msg}"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Stdout: {result.stdout.strip()}"))
                raise Exception(f"Błąd generate.py: {error_msg}")
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"[KOMBO] Błąd generowania audio: {str(e)}"))
            self.combo_failed = True
            self.root.after(0, self.execute_next_combo_step)
        
    def run_overlay_for_combo(self):
        """Uruchamia overlay_fixed.py dla przepływu KOMBO"""
        thread = threading.Thread(target=self._run_overlay_combo_thread, daemon=False)
        thread.start()
        
    def _run_overlay_combo_thread(self):
        """Thread dla overlay_fixed w przepływie KOMBO"""
        try:
            working_dir = Path(self.working_dir.get()) if self.working_dir.get() else Path.cwd()
            
            # Znajdź plik _en.txt (przetłumaczony)
            en_files = list(working_dir.rglob("*_en.txt"))
            if not en_files:
                raise Exception("Nie znaleziono pliku *_en.txt")
                
            en_file = en_files[0]
            
            # Znajdź oryginalny plik wideo
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
            video_files = []
            for ext in video_extensions:
                video_files.extend(working_dir.rglob(f"*{ext}"))
            
            if not video_files:
                raise Exception("Nie znaleziono pliku wideo")
                
            video_file = video_files[0]
            
            python_exe = Path(__file__).parent.parent / "myenv" / "Scripts" / "python.exe"
            overlay_script = Path(__file__).parent / "overlay_fixed.py"
            
            result = subprocess.run([
                str(python_exe), str(overlay_script), str(en_file), str(video_file)
            ], capture_output=True, text=True, cwd=working_dir)
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.log("[KOMBO] Nakładanie audio zakończone pomyślnie"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Output: {result.stdout.strip()}"))
                self.root.after(0, self.finish_current_combo_step)
            else:
                error_msg = result.stderr.strip() if result.stderr else "Nieznany błąd"
                self.root.after(0, lambda: self.log(f"[KOMBO] Błąd overlay_fixed.py: {error_msg}"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Stdout: {result.stdout.strip()}"))
                raise Exception(f"Błąd overlay_fixed.py: {error_msg}")
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"[KOMBO] Błąd nakładania audio: {str(e)}"))
            self.combo_failed = True
            self.root.after(0, self.execute_next_combo_step)
        
    def run_delete_sm_for_combo(self):
        """Uruchamia delete_sm.py dla przepływu KOMBO"""
        thread = threading.Thread(target=self._run_delete_sm_combo_thread, daemon=False)
        thread.start()
        
    def _run_delete_sm_combo_thread(self):
        """Thread dla delete_sm w przepływie KOMBO"""
        try:
            working_dir = Path(self.working_dir.get()) if self.working_dir.get() else Path.cwd()
            
            # Oryginalny delete_sm.py nie wymaga pliku tłumaczenia
            
            # Znajdź plik *_synchronized.* (po overlay, przed usuwaniem ciszy)
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
            video_files = []
            for ext in video_extensions:
                # Szukaj konkretnie plików *_synchronized.* (nie *_no_silence.*)
                pattern = f"*_synchronized{ext}"
                video_files.extend(working_dir.rglob(pattern))
            
            if video_files:
                # Jeśli jest kilka, weź najnowszy
                video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                video_file = video_files[0]
            else:
                raise Exception("Nie znaleziono pliku *_synchronized.* - uruchom najpierw overlay audio")
            
            # Wygeneruj nazwę pliku wyjściowego
            output_file = video_file.with_name(video_file.stem + "_no_silence" + video_file.suffix)
            
            python_exe = Path(__file__).parent.parent / "myenv" / "Scripts" / "python.exe"
            delete_sm_script = Path(__file__).parent / "delete_sm.py" # Używamy stabilnej wersji
            
            # Uruchom delete_sm.py (bez logowania w czasie rzeczywistym)
            result = subprocess.run([
                str(python_exe), str(delete_sm_script),
                str(video_file), str(output_file)
            ], capture_output=True, text=True, cwd=working_dir)
            
            # Sprawdź wynik
            if result.returncode == 0:
                self.root.after(0, lambda: self.log("[KOMBO] Usuwanie ciszy i bezruchu zakończone pomyślnie"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Output: {result.stdout.strip()}"))
                self.root.after(0, self.finish_current_combo_step)
            else:
                error_msg = result.stderr.strip() if result.stderr else "Nieznany błąd"
                self.root.after(0, lambda: self.log(f"[KOMBO] Błąd delete_sm.py: {error_msg}"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Stdout: {result.stdout.strip()}"))
                raise Exception(f"Błąd delete_sm.py: {error_msg}")
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"[KOMBO] Błąd usuwania ciszy: {str(e)}"))
            self.combo_failed = True
            self.root.after(0, self.execute_next_combo_step)
        
    def run_white_logo_for_combo(self):
        """Uruchamia white-bottom-logo.py dla przepływu KOMBO"""
        thread = threading.Thread(target=self._run_white_logo_combo_thread, daemon=False)
        thread.start()
        
    def _run_white_logo_combo_thread(self):
        """Thread dla white-bottom-logo.py w przepływie KOMBO"""
        try:
            working_dir = self.working_dir.get()
            if not working_dir:
                self.root.after(0, lambda: self.log("[KOMBO] Błąd: Nie ustawiono folderu roboczego"))
                self.combo_failed = True
                self.root.after(0, self.execute_next_combo_step)
                return
            
            # Uruchom skrypt w trybie KOMBO (bez argumentów)
            self.run_script("white-bottom-logo.py", [], "Usuń białą stopkę i dodaj logo", 
                          on_success=lambda output: self._on_white_logo_success(output))
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"[KOMBO] Błąd dodawania logo: {str(e)}"))
            self.combo_failed = True
            self.root.after(0, self.execute_next_combo_step)
    
    def _on_white_logo_success(self, output):
        """Callback po pomyślnym dodaniu logo"""
        self.root.after(0, lambda: self.log(f"[KOMBO] Dodawanie logo zakończone pomyślnie"))
        if output:
            self.root.after(0, lambda: self.log(f"[KOMBO] Output: {output}"))
        self.root.after(0, self.execute_next_combo_step)
        
    def run_detect_polish_for_combo(self):
        """Uruchamia detect_polish_text.py dla przepływu KOMBO"""
        thread = threading.Thread(target=self._run_detect_polish_combo_thread, daemon=False)
        thread.start()
        
    def _run_detect_polish_combo_thread(self):
        """Thread dla detect_polish w przepływie KOMBO"""
        try:
            working_dir = Path(self.working_dir.get()) if self.working_dir.get() else Path.cwd()
            
            # Znajdź najnowszy plik wideo (powinien być po delete_sm)
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
            video_files = []
            for ext in video_extensions:
                video_files.extend(working_dir.rglob(f"*{ext}"))
            
            # Sortuj według czasu modyfikacji - najnowszy najprawdopodobniej po delete_sm
            if video_files:
                video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                video_file = video_files[0]
            else:
                raise Exception("Nie znaleziono pliku wideo")
            
            python_exe = Path(__file__).parent.parent / "myenv" / "Scripts" / "python.exe"
            detect_script = Path(__file__).parent / "detect_polish_text.py"
            
            # Użyj domyślnych wartości z krokiem 40s jak user wcześniej wspomniał
            result = subprocess.run([
                str(python_exe), str(detect_script), str(video_file),
                "--interval", "40.0",
                "--confidence", "0.6"
            ], capture_output=True, text=True, cwd=working_dir)
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.log("[KOMBO] Wykrywanie polskiego tekstu zakończone pomyślnie"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Output: {result.stdout.strip()}"))
                self.root.after(0, self.finish_current_combo_step)
            else:
                error_msg = result.stderr.strip() if result.stderr else "Nieznany błąd"
                self.root.after(0, lambda: self.log(f"[KOMBO] Błąd detect_polish_text.py: {error_msg}"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Stdout: {result.stdout.strip()}"))
                raise Exception(f"Błąd detect_polish_text.py: {error_msg}")
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"[KOMBO] Błąd wykrywania polskiego tekstu: {str(e)}"))
            self.combo_failed = True
            self.root.after(0, self.execute_next_combo_step)
        
    def run_intro_outro_for_combo(self):
        """Uruchamia add_intro_outro.py dla przepływu KOMBO"""
        thread = threading.Thread(target=self._run_intro_outro_combo_thread, daemon=False)
        thread.start()
        
    def _run_intro_outro_combo_thread(self):
        """Thread dla intro_outro w przepływie KOMBO"""
        try:
            working_dir = Path(self.working_dir.get()) if self.working_dir.get() else Path.cwd()
            
            # Szukaj pliku po dodaniu logo (krok 5)
            logo_files = list(working_dir.rglob("*_with_logo.mp4"))
            
            if logo_files:
                # Użyj pliku po dodaniu logo
                video_file = logo_files[0]
                self.root.after(0, lambda: self.log(f"[KOMBO] Używam pliku po dodaniu logo: {video_file.name}"))
            else:
                # Fallback - szukaj pliku po detect_polish (jeśli krok logo był wyłączony)
                polish_files = list(working_dir.rglob("*_polish_text_detection.mp4"))
                if polish_files:
                    video_file = polish_files[0]
                    self.root.after(0, lambda: self.log(f"[KOMBO] Używam pliku po detect_polish: {video_file.name}"))
                else:
                    # Ostatni fallback - najnowszy plik
                    video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
                    video_files = []
                    for ext in video_extensions:
                        video_files.extend(working_dir.rglob(f"*{ext}"))
                    
                    if video_files:
                        video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                        video_file = video_files[0]
                        self.root.after(0, lambda: self.log(f"[KOMBO] Używam najnowszy plik: {video_file.name}"))
                    else:
                        raise Exception("Nie znaleziono pliku wideo")
            
            python_exe = Path(__file__).parent.parent / "myenv" / "Scripts" / "python.exe"
            intro_outro_script = Path(__file__).parent / "add_intro_outro_fast.py"  # Użyj szybkiej wersji
            
            # Podstawowe wywołanie - skrypt używa domyślnych ścieżek dla intro/outro
            # Uruchom z folderu głównego projektu, żeby znaleźć intro_outro
            project_root = Path(__file__).parent.parent
            result = subprocess.run([
                str(python_exe), str(intro_outro_script), str(video_file)
            ], capture_output=True, text=True, cwd=project_root)
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.log("[KOMBO] Dodawanie intro i outro zakończone pomyślnie"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Output: {result.stdout.strip()}"))
                self.root.after(0, self.finish_current_combo_step)
            else:
                error_msg = result.stderr.strip() if result.stderr else "Nieznany błąd"
                self.root.after(0, lambda: self.log(f"[KOMBO] Błąd add_intro_outro.py: {error_msg}"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Stdout: {result.stdout.strip()}"))
                raise Exception(f"Błąd add_intro_outro.py: {error_msg}")
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"[KOMBO] Błąd dodawania intro/outro: {str(e)}"))
            self.combo_failed = True
            self.root.after(0, self.execute_next_combo_step)
        
    def run_social_media_for_combo(self):
        """Uruchamia social_media_post.py dla przepływu KOMBO"""
        thread = threading.Thread(target=self._run_social_media_combo_thread, daemon=False)
        thread.start()
        
    def _run_social_media_combo_thread(self):
        """Thread dla social_media w przepływie KOMBO"""
        try:
            working_dir = Path(self.working_dir.get()) if self.working_dir.get() else Path.cwd()
            
            # Znajdź plik _sentences.txt (oryginalny polski)
            sentences_files = list(working_dir.rglob("*_sentences.txt"))
            if not sentences_files:
                raise Exception("Nie znaleziono pliku *_sentences.txt")
                
            sentences_file = sentences_files[0]
            
            python_exe = Path(__file__).parent.parent / "myenv" / "Scripts" / "python.exe"
            social_media_script = Path(__file__).parent / "social_media_post.py"
            
            result = subprocess.run([
                str(python_exe), str(social_media_script), str(sentences_file),
                "--format", "docx"
            ], capture_output=True, text=True, cwd=working_dir)
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.log("[KOMBO] Generowanie posta social media zakończone pomyślnie"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Output: {result.stdout.strip()}"))
                self.root.after(0, self.finish_current_combo_step)
            else:
                error_msg = result.stderr.strip() if result.stderr else "Nieznany błąd"
                self.root.after(0, lambda: self.log(f"[KOMBO] Błąd social_media_post.py: {error_msg}"))
                if result.stdout:
                    self.root.after(0, lambda: self.log(f"[KOMBO] Stdout: {result.stdout.strip()}"))
                raise Exception(f"Błąd social_media_post.py: {error_msg}")
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"[KOMBO] Błąd generowania posta social media: {str(e)}"))
            self.combo_failed = True
            self.root.after(0, self.execute_next_combo_step)
        
    def clear_logs(self):
        """Czyści logi"""
        self.log_text.delete(1.0, tk.END)
        
    def update_progress(self, step, progress, message, estimated_time=None):
        """Aktualizuje pasek postępu i etykietę"""
        try:
            self.progress_vars[step].set(progress)
            if estimated_time:
                self.progress_labels[step].set(f"{message} ({progress:.1f}%) - Pozostało: {estimated_time}")
            else:
                self.progress_labels[step].set(f"{message} ({progress:.1f}%)")
        except Exception as e:
            self.log(f"Błąd aktualizacji postępu: {e}")
            
    def show_stop_button(self, step):
        """Pokazuje przycisk stop dla danego kroku"""
        try:
            if step == 'step1':
                self.step1_stop_btn.pack(anchor=tk.E, pady=(5, 0))
            elif step == 'step2':
                self.step2_stop_btn.pack(anchor=tk.E, pady=(5, 0))
            elif step == 'step3':
                self.step3_stop_btn.pack(anchor=tk.E, pady=(5, 0))
        except Exception as e:
            self.log(f"Błąd pokazywania przycisku stop: {e}")
            
    def hide_stop_button(self, step):
        """Ukrywa przycisk stop dla danego kroku"""
        try:
            if step == 'step1':
                self.step1_stop_btn.pack_forget()
            elif step == 'step2':
                self.step2_stop_btn.pack_forget()
            elif step == 'step3':
                self.step3_stop_btn.pack_forget()
        except Exception as e:
            self.log(f"Błąd ukrywania przycisku stop: {e}")
            
    def stop_operation(self, step):
        """Przerywa operację dla danego kroku"""
        try:
            self.stop_flags[step] = True
            if self.current_process:
                self.current_process.terminate()
                self.log(f"Próba przerwania operacji {step}...")
            self.update_progress(step, 0, "Przerywanie...")
        except Exception as e:
            self.log(f"Błąd przerwania operacji: {e}")
            
    def parse_progress_from_output(self, line, script_name):
        """Parsuje postęp z outputu skryptu"""
        try:
            # Wzorce dla różnych skryptów
            patterns = {
                'transcribe_api.py': [
                    r'Starting audio extraction',
                    r'Audio extraction successful',
                    r'Starting transcription using OpenAI API',
                    r'Transcription completed successfully',
                    r'Processing complete'
                ],
                'transcribe_improved.py': [
                    r'Processing frame (\d+)/(\d+)',
                    r'Transcribing.*?(\d+)%',
                    r'Loading Whisper model',
                    r'Transcription completed'
                ],
                'detect_polish_text.py': [
                    r'Processing frame (\d+)/(\d+)',
                    r'Analyzing frame (\d+)/(\d+)',
                    r'Detection completed'
                ],
                'delete_sm.py': [
                    r'Processing frame (\d+)/(\d+)',
                    r'Analyzing gap (\d+)/(\d+)',
                    r'Compression completed'
                ],
                'youtube_downloader.py': [
                    r'(\d+\.?\d*)%',
                    r'Download completed',
                    r'Pobrano pomyślnie'
                ]
            }
            
            if script_name in patterns:
                for pattern in patterns[script_name]:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        if script_name == 'transcribe_api.py':
                            if 'Starting audio extraction' in pattern:
                                return 10, "Ekstrakcja audio..."
                            elif 'Audio extraction successful' in pattern:
                                return 30, "Audio wyekstraktowane"
                            elif 'Starting transcription using OpenAI API' in pattern:
                                return 50, "Transkrypcja przez API..."
                            elif 'Transcription completed successfully' in pattern:
                                return 80, "Transkrypcja zakończona"
                            elif 'Processing complete' in pattern:
                                return 100, "Przetwarzanie zakończone"
                        elif 'frame' in pattern:
                            current, total = int(match.group(1)), int(match.group(2))
                            return (current / total) * 100, f"Przetwarzanie klatki {current}/{total}"
                        elif '%' in pattern:
                            percent = float(match.group(1))
                            return percent, f"Postęp: {percent:.1f}%"
                        elif 'completed' in pattern or 'pomyślnie' in pattern:
                            return 100, "Zakończone"
                        elif 'Loading' in pattern:
                            return 10, "Ładowanie modelu..."
                            
            # Sprawdź czy to jest błąd
            if 'error' in line.lower() or 'błąd' in line.lower():
                return None, f"Błąd: {line}"
                
            return None, None
            
        except Exception as e:
            return None, None
            
    def estimate_remaining_time(self, start_time, progress):
        """Szacuje pozostały czas na podstawie postępu"""
        try:
            if progress <= 0:
                return "obliczanie..."
                
            elapsed = time.time() - start_time
            if progress >= 100:
                return "zakończone"
                
            # Szacuj czas pozostały
            total_estimated = elapsed / (progress / 100)
            remaining = total_estimated - elapsed
            
            if remaining < 60:
                return f"{remaining:.0f}s"
            elif remaining < 3600:
                minutes = remaining // 60
                seconds = remaining % 60
                return f"{minutes:.0f}m {seconds:.0f}s"
            else:
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                return f"{hours:.0f}h {minutes:.0f}m"
                
        except Exception:
            return "obliczanie..."
            
    def get_system_info(self):
        """Pobiera informacje o systemie"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            return f"CPU: {cpu_percent:.1f}% | RAM: {memory_percent:.1f}%"
        except Exception:
            return "Informacje o systemie niedostępne"
        
    def select_working_dir(self):
        """Wybiera folder roboczy"""
        directory = filedialog.askdirectory()
        if directory:
            self.working_dir.set(directory)
            self.save_config()
            self.log(f"Ustawiono folder roboczy: {directory}")
            
    def select_video_file(self):
        """Wybiera plik wideo i automatycznie uruchamia transkrypcję"""
        file_path = filedialog.askopenfilename(
            title="Wybierz plik wideo",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")]
        )
        if file_path:
            self.video_path.set(file_path)
            self.log(f"Wybrano plik wideo: {file_path}")
            # Automatycznie uruchom transkrypcję
            self.run_transcription(file_path)
            
    def select_logo_video(self):
        """Wybiera plik wideo do dodania logo"""
        file_path = filedialog.askopenfilename(
            title="Wybierz plik wideo",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")]
        )
        if file_path:
            self.logo_video_path.set(file_path)
            

            
    def find_latest_video_file(self, directory):
        """Znajduje najnowszy plik wideo w katalogu"""
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(Path(directory).glob(f"*{ext}"))
        
        if not video_files:
            return None
            
        # Sortuj po czasie modyfikacji (najnowszy pierwszy)
        latest_file = max(video_files, key=lambda x: x.stat().st_mtime)
        return latest_file
    
    def run_script(self, script_name, args=None, step_name="Operacja", on_success=None, step_key=None):
        """Uruchamia skrypt w osobnym wątku z obsługą postępu"""
        def run():
            nonlocal args
            start_time = time.time()
            current_progress = 0
            
            try:
                self.log(f"Rozpoczynam {step_name}...")
                self.current_step.set(f"W trakcie: {step_name}")
                
                # Inicjalizuj postęp
                if step_key:
                    self.stop_flags[step_key] = False
                    self.update_progress(step_key, 0, "Rozpoczynanie...")
                    self.show_stop_button(step_key)
                
                # Upewnij się, że args jest zdefiniowane
                if args is None:
                    args = []
                
                # Przygotuj ścieżkę do skryptu
                if hasattr(sys, '_MEIPASS'):
                    # Uruchomione z .exe - skrypt jest w bundled resources
                    bundled_script_path = Path(sys._MEIPASS) / script_name
                    
                    if bundled_script_path.exists():
                        import shutil
                        
                        # Spróbuj różne lokalizacje do skopiowania skryptu (macOS compatibility)
                        copy_locations = [
                            Path.cwd() / script_name,  # Bieżący katalog
                            Path.home() / "Documents" / script_name,  # Dokumenty użytkownika
                            Path.home() / "Desktop" / script_name,  # Pulpit użytkownika
                            Path("/tmp") / script_name if Path("/tmp").exists() else None,  # /tmp na macOS/Linux
                        ]
                        
                        script_path = None
                        copied = False
                        
                        for working_script_path in copy_locations:
                            if working_script_path is None:
                                continue
                                
                            try:
                                # Upewnij się, że katalog istnieje
                                working_script_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(bundled_script_path, working_script_path)
                                script_path = working_script_path
                                self.log(f"Skopiowano skrypt do: {working_script_path}")
                                copied = True
                                break
                            except (OSError, PermissionError):
                                continue
                        
                        if not copied:
                            # Jeśli nie udało się skopiować, spróbuj uruchomić bezpośrednio z bundled
                            script_path = bundled_script_path
                            self.log(f"⚠️ Nie udało się skopiować skryptu - używam bezpośrednio z bundle: {script_name}")
                    else:
                        self.log(f"⚠️ Nie znaleziono skryptu w bundled resources: {bundled_script_path}")
                        script_path = Path(__file__).parent / script_name
                    
                    # Jeśli to add_intro_outro.py, musimy też skopiować pliki intro/outro
                    if script_name == "add_intro_outro.py" and args:
                        # Znajdź argumenty --intro i --outro i zamień ścieżki
                        new_args = []
                        i = 0
                        # Utwórz unikalny folder tymczasowy dla intro/outro
                        temp_intro_outro_dir = None
                        
                        while i < len(args):
                            if args[i] == "--intro" and i + 1 < len(args):
                                # Skopiuj plik intro do dostępnej lokalizacji
                                bundled_intro = Path(args[i + 1])
                                if bundled_intro.exists() and "_MEI" in str(bundled_intro):
                                    # Utwórz unikalny folder tymczasowy
                                    if temp_intro_outro_dir is None:
                                        temp_intro_outro_dir = Path.cwd() / f"intro_outro_temp_{int(time.time())}"
                                        temp_intro_outro_dir.mkdir(exist_ok=True)
                                        self.log(f"Utworzono tymczasowy folder: {temp_intro_outro_dir.name}")
                                    
                                    local_intro = temp_intro_outro_dir / bundled_intro.name
                                    shutil.copy2(bundled_intro, local_intro)
                                    new_args.extend(["--intro", str(local_intro)])
                                    self.log(f"Skopiowano intro: {bundled_intro.name}")
                                else:
                                    new_args.extend([args[i], args[i + 1]])
                                i += 2
                            elif args[i] == "--outro" and i + 1 < len(args):
                                # Skopiuj plik outro do dostępnej lokalizacji
                                bundled_outro = Path(args[i + 1])
                                if bundled_outro.exists() and "_MEI" in str(bundled_outro):
                                    # Użyj tego samego folderu tymczasowego
                                    if temp_intro_outro_dir is None:
                                        temp_intro_outro_dir = Path.cwd() / f"intro_outro_temp_{int(time.time())}"
                                        temp_intro_outro_dir.mkdir(exist_ok=True)
                                        self.log(f"Utworzono tymczasowy folder: {temp_intro_outro_dir.name}")
                                    
                                    local_outro = temp_intro_outro_dir / bundled_outro.name
                                    shutil.copy2(bundled_outro, local_outro)
                                    new_args.extend(["--outro", str(local_outro)])
                                    self.log(f"Skopiowano outro: {bundled_outro.name}")
                                else:
                                    new_args.extend([args[i], args[i + 1]])
                                i += 2
                            else:
                                new_args.append(args[i])
                                i += 1
                        args = new_args
                else:
                    # Uruchomione z kodu źródłowego
                    script_path = Path(__file__).parent / script_name
                
                # Sprawdź czy jesteśmy w środowisku wirtualnym lub .exe
                if hasattr(sys, '_MEIPASS'):
                    # Uruchomione z .exe (PyInstaller)
                    # Musimy użyć Pythona ze środowiska wirtualnego, nie .exe
                    # Znajdź katalog zawierający .exe (powinien być w dist/)
                    exe_dir = Path(sys.executable).parent
                    # Sprawdź różne możliwe lokalizacje środowiska wirtualnego
                    possible_venv_paths = [
                        exe_dir.parent / "myenv" / "Scripts" / "python.exe",  # ../myenv/Scripts/python.exe
                        Path.cwd() / "myenv" / "Scripts" / "python.exe",      # ./myenv/Scripts/python.exe
                        Path.cwd().parent / "myenv" / "Scripts" / "python.exe" # ../myenv/Scripts/python.exe
                    ]
                    
                    python_executable = None
                    for venv_path in possible_venv_paths:
                        if venv_path.exists():
                            python_executable = str(venv_path)
                            self.log(f"Uruchomione z .exe, znaleziono Pythona: {python_executable}")
                            break
                    
                    if not python_executable:
                        # Fallback - spróbuj znaleźć Python w systemie
                        python_executable = "python"
                        self.log(f"⚠️ Nie znaleziono środowiska wirtualnego, używam: {python_executable}")
                elif hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                    # Jesteśmy w środowisku wirtualnym
                    python_executable = sys.executable
                    self.log(f"Używam Pythona ze środowiska wirtualnego: {python_executable}")
                else:
                    # Spróbuj znaleźć środowisko wirtualne
                    venv_python = Path(__file__).parent.parent / "myenv" / "Scripts" / "python.exe"
                    if venv_python.exists():
                        python_executable = str(venv_python)
                        self.log(f"Znaleziono środowisko wirtualne: {python_executable}")
                    else:
                        python_executable = sys.executable
                        self.log(f"⚠️ Nie znaleziono środowiska wirtualnego, używam: {python_executable}")
                
                cmd = [python_executable, str(script_path)]
                if args:
                    cmd.extend(args)
                
                self.log(f"Komenda: {' '.join(cmd)}")
                
                # Uruchom proces
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=self.working_dir.get() if self.working_dir.get() else None
                )
                
                # Zapisz referencję do procesu
                self.current_process = process
                
                # Czytaj output w czasie rzeczywistym
                stdout_lines = []
                stderr_lines = []
                
                while True:
                    # Sprawdź czy użytkownik chce przerwać
                    if step_key and self.stop_flags.get(step_key, False):
                        process.terminate()
                        self.log(f"Operacja {step_name} przerwana przez użytkownika")
                        break
                    
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        stdout_lines.append(line)
                        self.log(line)
                        
                        # Parsuj postęp z outputu
                        if step_key:
                            progress, message = self.parse_progress_from_output(line, script_name)
                            if progress is not None:
                                current_progress = progress
                                estimated_time = self.estimate_remaining_time(start_time, progress)
                                self.update_progress(step_key, progress, message, estimated_time)
                                
                                # Dodaj informacje o systemie co 10%
                                if int(progress) % 10 == 0 and int(progress) > 0:
                                    system_info = self.get_system_info()
                                    self.log(f"[INFO] {system_info}")
                
                # Sprawdź błędy
                return_code = process.poll()
                stderr = process.stderr.read()
                
                # Sprawdź czy proces zakończył się sukcesem
                success_indicators = ["✅", "Pobrano pomyślnie", "zakończone pomyślnie", "Download completed", "Transcription completed", "API transcription completed successfully", "Processing complete", "[SUKCES] Pobrano pomyślnie", "[SUKCES] Pobieranie zakończone pomyślnie"]
                stdout_text = " ".join(stdout_lines)
                
                if return_code == 0 or any(indicator in stdout_text for indicator in success_indicators):
                    self.log(f"✅ {step_name} zakończone pomyślnie!")
                    self.current_step.set("Gotowy")
                    
                    # Aktualizuj postęp na 100%
                    if step_key:
                        self.update_progress(step_key, 100, "Zakończone pomyślnie", "zakończone")
                        self.hide_stop_button(step_key)
                    
                    # Wywołaj funkcję on_success jeśli została podana
                    if on_success:
                        try:
                            self.root.after(100, on_success)  # Dodano opóźnienie 100ms
                        except Exception as e:
                            self.log(f"[BLAD] Błąd wywołania callback: {e}")
                else:
                    self.log(f"[BLAD] Błąd w {step_name} (kod: {return_code})")
                    if stderr:
                        self.log(f"Błąd stderr: {stderr}")
                    if stdout_lines:
                        self.log(f"Ostatnie linie stdout: {stdout_lines[-5:]}")  # Ostatnie 5 linii
                    self.current_step.set("Błąd")
                    
                    # Aktualizuj postęp na błąd
                    if step_key:
                        self.update_progress(step_key, 0, "Błąd - sprawdź logi")
                        self.hide_stop_button(step_key)
                    
            except Exception as e:
                self.log(f"[BLAD] Błąd podczas {step_name}: {e}")
                import traceback
                self.log(f"Szczegóły błędu: {traceback.format_exc()}")
                self.current_step.set("Błąd")
                
                # Aktualizuj postęp na błąd
                if step_key:
                    self.update_progress(step_key, 0, "Błąd - sprawdź logi")
                    self.hide_stop_button(step_key)
            finally:
                # Wyczyść referencję do procesu
                self.current_process = None
                
                # Wyczyść skopiowane pliki jeśli uruchomiono z .exe
                if hasattr(sys, '_MEIPASS'):
                    try:
                        # Usuń skopiowany skrypt z różnych możliwych lokalizacji
                        cleanup_locations = [
                            Path.cwd() / script_name,
                            Path.home() / "Documents" / script_name,
                            Path.home() / "Desktop" / script_name,
                            Path("/tmp") / script_name if Path("/tmp").exists() else None,
                        ]
                        
                        for script_path in cleanup_locations:
                            if script_path and script_path.exists():
                                try:
                                    script_path.unlink()
                                    self.log(f"Usunięto tymczasowy skrypt: {script_path}")
                                except Exception as e:
                                    self.log(f"⚠️ Nie udało się usunąć {script_path}: {e}")
                        
                        # Usuń skopiowane pliki intro/outro jeśli to był add_intro_outro.py
                        if script_name == "add_intro_outro.py":
                            # Usuń tylko tymczasowe foldery intro_outro_temp_*
                            import glob
                            temp_dirs = glob.glob(str(Path.cwd() / "intro_outro_temp_*"))
                            for temp_dir in temp_dirs:
                                try:
                                    import shutil
                                    shutil.rmtree(temp_dir)
                                    self.log(f"Usunięto tymczasowy folder: {Path(temp_dir).name}")
                                except Exception as e:
                                    self.log(f"⚠️ Nie udało się usunąć {temp_dir}: {e}")
                    except Exception as e:
                        self.log(f"⚠️ Nie udało się usunąć tymczasowych plików {script_name}: {e}")
                
                # Usuń zakończony wątek z listy
                if hasattr(self, 'active_threads') and thread in self.active_threads:
                    self.active_threads.remove(thread)
        
        # Uruchom w osobnym wątku
        thread = threading.Thread(target=run)
        thread.daemon = False  # Zmienione z True na False - daemon threads mogą być zabijane
        thread.start()
        
        # Zapisz referencję do wątku aby zapobiec jego usunięciu
        if not hasattr(self, 'active_threads'):
            self.active_threads = []
        self.active_threads.append(thread)
        
    def run_transcription(self, video_path):
        """Uruchamia transkrypcję pliku wideo"""
        self.log(f"Rozpoczynam transkrypcję pliku: {video_path}")
        self.run_script("transcribe_api.py", [video_path], "Transkrypcja", 
                       lambda: self.on_transcription_complete(video_path), "step1")
        
    def on_transcription_complete(self, video_path):
        """Wywoływane po zakończeniu transkrypcji"""
        # Znajdź plik transkrypcji
        video_name = Path(video_path).stem
        working_dir = Path(self.working_dir.get()) if self.working_dir.get() else Path.cwd()
        
        self.log(f"Szukam pliku transkrypcji dla: {video_name}")
        
        # Szukaj pliku transkrypcji
        transcription_file = None
        for txt_file in working_dir.rglob(f"{video_name}*.txt"):
            if "_sentences" in txt_file.name:
                transcription_file = txt_file
                self.log(f"Znaleziono plik transkrypcji: {transcription_file}")
                break
        
        if transcription_file:
            self.last_transcription_file = transcription_file
            self.show_transcription_complete_dialog(video_path, transcription_file)
        else:
            self.log("[BLAD] Nie znaleziono pliku transkrypcji")
            self.log(f"Szukane wzorce: {video_name}*_sentences.txt")
            # Pokaż dostępne pliki txt
            txt_files = list(working_dir.rglob("*.txt"))
            if txt_files:
                self.log("Dostępne pliki .txt:")
                for txt_file in txt_files:
                    self.log(f"  - {txt_file.name}")
            else:
                self.log("Brak plików .txt w folderze roboczym")
            
    def show_transcription_complete_dialog(self, video_path, transcription_file):
        """Pokazuje dialog po zakończeniu transkrypcji"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Transkrypcja zakończona")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centruj dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"400x200+{x}+{y}")
        
        # Zawartość dialogu
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="✅ Transkrypcja zakończona pomyślnie!", 
                 font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        ttk.Label(main_frame, text="Porównaj transkrypcję z wideo:", 
                 font=('Arial', 10)).pack(pady=(0, 20))
        
        # Przyciski
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        def open_files():
            try:
                # Otwórz plik wideo
                os.startfile(video_path)
                # Otwórz plik transkrypcji
                os.startfile(transcription_file)
            except Exception as e:
                self.log(f"[BLAD] Błąd podczas otwierania plików: {e}")
            dialog.destroy()
            
        def close_dialog():
            dialog.destroy()
            
        ttk.Button(button_frame, text="[FOLDER] Otwórz plik wideo i transkrypcję tekstową",
                  command=open_files).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="[CANCEL] Nie teraz", 
                  command=close_dialog).pack(side=tk.LEFT)
        
    def run_step1(self, source_type):
        """Uruchamia krok 1"""
        if source_type == 'youtube':
            if not self.youtube_url.get():
                messagebox.showerror("Błąd", "Wprowadź link do YouTube!")
                return
            
            # Sprawdź folder roboczy
            working_dir = self.working_dir.get()
            if not working_dir:
                messagebox.showerror("Błąd", "Ustaw folder roboczy przed pobieraniem!")
                return
                
            self.log(f"Folder roboczy: {working_dir}")
            
            # Uruchom pobieranie z automatyczną transkrypcją po zakończeniu
            def on_download_complete():
                # Znajdź najnowszy plik wideo
                latest_video = self.find_latest_video_file(working_dir)
                if latest_video:
                    self.last_downloaded_video = latest_video
                    self.log(f"Znaleziono pobrany plik: {latest_video}")
                    # Automatycznie uruchom transkrypcję
                    self.run_transcription(str(latest_video))
                else:
                    self.log("[BLAD] Nie znaleziono pobranego pliku wideo")
            
            self.run_script("youtube_downloader.py", [self.youtube_url.get(), "-o", working_dir], 
                           "Pobieranie z YouTube", on_download_complete, "step1")
        else:
            if not self.video_path.get():
                messagebox.showerror("Błąd", "Wybierz plik wideo!")
                return
            self.run_transcription(self.video_path.get())
            

                

            
    def revert_gap_removal(self):
        """Cofa usunięcie luki"""
        if not self.gap_numbers.get():
            messagebox.showerror("Błąd", "Wprowadź numery luk!")
            return
            
        working_dir = Path(self.working_dir.get()) if self.working_dir.get() else Path.cwd()
        video_files = list(working_dir.rglob("*_synchronized.mp4"))
        
        if not video_files:
            messagebox.showerror("Błąd", "Nie znaleziono plików *_synchronized.mp4!")
            return
            
        for video_file in video_files:
            self.run_script("reprocess_delete_sm.py", [str(video_file), self.gap_numbers.get()], 
                          f"Cofanie luki {video_file.name}")
            
    def add_logo(self):
        """Dodaje logo i białą stopkę"""
        if not self.logo_video_path.get():
            messagebox.showerror("Błąd", "Wybierz plik wideo!")
            return
            
        self.run_script("white-bottom-logo.py", [self.logo_video_path.get()], "Dodawanie logo")
        
    def add_intro_outro(self, on_success=None):
        """Dodaje intro i outro"""
        if not all([self.intro_video_path.get(), self.main_video_path.get(), self.outro_video_path.get()]):
            messagebox.showerror("Błąd", "Wybierz wszystkie pliki (intro, główne wideo, outro)!")
            return
            
        args = [
            self.main_video_path.get(),  # Główny plik wideo jako pierwszy argument pozycyjny
            "--intro", self.intro_video_path.get(),
            "--outro", self.outro_video_path.get()
        ]
        self.run_script("add_intro_outro.py", args, "Dodawanie intro/outro", on_success)
        
    def add_intro_outro_fast(self):
        """Szybko dodaje intro i outro używając ffmpeg"""
        if not self.main_video_path.get():
            messagebox.showerror("Błąd", "Wybierz główne wideo!")
            return
        
        args = [self.main_video_path.get()]
        
        # Dodaj argumenty intro/outro jeśli są dostępne
        if self.intro_video_path.get():
            args.extend(["--intro", self.intro_video_path.get()])
        if self.outro_video_path.get():
            args.extend(["--outro", self.outro_video_path.get()])
        
        self.run_script("add_intro_outro_fast.py", args, "Szybkie dodawanie intro/outro")
        

            
    def show_available_files(self):
        """Pokazuje dostępne pliki w folderze roboczym"""
        working_dir = Path(self.working_dir.get()) if self.working_dir.get() else Path.cwd()
        
        self.log("=== DOSTĘPNE PLIKI W FOLDERZE ROBOCZYM ===")
        if not working_dir.exists():
            self.log("[BLAD] Folder roboczy nie istnieje!")
            return
            
        for file_path in working_dir.rglob("*"):
            if file_path.is_file():
                file_size = file_path.stat().st_size
                size_str = f"({file_size / (1024*1024):.1f} MB)" if file_size > 1024*1024 else f"({file_size / 1024:.1f} KB)"
                self.log(f"[PLIK] {file_path.relative_to(working_dir)} {size_str}")
                
    def refresh_files(self):
        """Odświeża listę plików - funkcja zastępcza"""
        pass

    def load_intro_outro_files(self):
        """Automatycznie wczytuje pliki intro/outro z folderu intro_outro"""
        # Sprawdź różne możliwe lokalizacje plików intro/outro
        possible_paths = []
        
        # 1. Jeśli uruchomione z kodu źródłowego
        if hasattr(sys, '_MEIPASS'):
            # Uruchomione z .exe (PyInstaller)
            base_path = Path(sys._MEIPASS)
        else:
            # Uruchomione z kodu źródłowego
            base_path = Path(__file__).parent.parent
        
        # Dodaj możliwe ścieżki
        possible_paths.append(base_path / "intro_outro")
        possible_paths.append(Path.cwd() / "intro_outro")
        possible_paths.append(Path.cwd() / "dist" / "intro_outro")
        
        intro_outro_dir = None
        for path in possible_paths:
            if path.exists():
                intro_outro_dir = path
                break
        
        if intro_outro_dir and intro_outro_dir.exists():
            intro_video_path = None
            outro_video_path = None
            
            for file in intro_outro_dir.iterdir():
                if file.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                    file_name_lower = file.name.lower()
                    if 'intro' in file_name_lower:
                        intro_video_path = file
                    elif 'outro' in file_name_lower:
                        outro_video_path = file
            
            if intro_video_path:
                self.intro_video_path.set(str(intro_video_path))
                self.log(f"Wczytano intro video: {intro_video_path.name}")
            else:
                self.intro_video_path.set("")
                self.log("Nie znaleziono pliku intro w folderze intro_outro")
                
            if outro_video_path:
                self.outro_video_path.set(str(outro_video_path))
                self.log(f"Wczytano outro video: {outro_video_path.name}")
            else:
                self.outro_video_path.set("")
                self.log("Nie znaleziono pliku outro w folderze intro_outro")
        else:
            self.intro_video_path.set("")
            self.outro_video_path.set("")
            self.log("Folder intro_outro nie istnieje. Nie można wczytać plików intro/outro.")
            self.log("Sprawdź czy folder intro_outro znajduje się w tym samym katalogu co aplikacja.")

    def select_upload_video(self):
        """Wybiera wideo do uploadu na YouTube"""
        video_path = filedialog.askopenfilename(
            title="Wybierz wideo do uploadu na YouTube",
            filetypes=[
                ("Pliki wideo", "*.mp4 *.avi *.mov *.mkv *.wmv"),
                ("Wszystkie pliki", "*.*")
            ]
        )
        
        if video_path:
            self.upload_video_path = video_path
            # Skróć ścieżkę do wyświetlenia
            display_path = Path(video_path).name
            self.upload_video_path_label.config(text=f"✅ {display_path}", foreground='#27ae60')
            
            # Automatycznie wypełnij tytuł na podstawie nazwy pliku
            if not self.youtube_title.get():
                title = Path(video_path).stem.replace('_', ' ').title()
                self.youtube_title.set(title)
    
    def select_thumbnail(self):
        """Wybiera miniaturkę dla wideo"""
        thumbnail_path = filedialog.askopenfilename(
            title="Wybierz miniaturkę (obrazek)",
            filetypes=[
                ("Obrazki", "*.jpg *.jpeg *.png *.bmp"),
                ("Wszystkie pliki", "*.*")
            ]
        )
        
        if thumbnail_path:
            self.youtube_thumbnail_path.set(thumbnail_path)
            # Skróć ścieżkę do wyświetlenia
            display_path = Path(thumbnail_path).name
            self.thumbnail_path_label.config(text=f"✅ {display_path}", foreground='#27ae60')
    
    def upload_to_youtube(self):
        """Uploaduje wideo na YouTube"""
        # Sprawdź czy wybrano wideo
        if not hasattr(self, 'upload_video_path') or not self.upload_video_path:
            messagebox.showerror("Błąd", "Nie wybrano wideo do uploadu!")
            return
        
        # Sprawdź czy wypełniono wymagane pola
        if not self.youtube_title.get().strip():
            messagebox.showerror("Błąd", "Wprowadź tytuł wideo!")
            return
        
        # Pobierz opis z dwóch części
        desc_part1 = self.desc_part1_text.get("1.0", tk.END).strip()
        desc_part2 = self.desc_part2_text.get("1.0", tk.END).strip()
        
        # Połącz opisy z dwoma enterami między nimi
        if desc_part1 and desc_part2:
            description = f"{desc_part1}\n\n{desc_part2}"
        elif desc_part1:
            description = desc_part1
        elif desc_part2:
            description = desc_part2
        else:
            description = ""
        
        # Przygotuj dane do uploadu
        upload_data = {
            'video_path': self.upload_video_path,
            'title': self.youtube_title.get().strip(),
            'description': description,
            'tags': [tag.strip() for tag in self.youtube_tags.get().split(',') if tag.strip()],
            'category': self.youtube_category.get(),
            'privacy': self.youtube_privacy.get(),
            'thumbnail_path': self.youtube_thumbnail_path.get() if self.youtube_thumbnail_path.get() else None
        }
        
        # Uruchom upload w osobnym wątku
        self.log("[YOUTUBE] Rozpoczynam upload wideo na YouTube...")
        threading.Thread(target=self._upload_to_youtube_thread, args=(upload_data,), daemon=True).start()
    
    def _upload_to_youtube_thread(self, upload_data):
        """Wykonuje upload na YouTube w osobnym wątku"""
        try:
            # Import YouTube uploader
            try:
                from youtube_uploader import YouTubeUploader
            except ImportError:
                self.log("[YOUTUBE] ❌ YouTube API nie jest dostępne. Zainstaluj wymagane biblioteki.")
                self.root.after(0, lambda: messagebox.showerror("Błąd", 
                    "YouTube API nie jest dostępne.\n\nZainstaluj wymagane biblioteki:\n"
                    "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"))
                return
            
            # Sprawdź czy istnieje plik client_secrets.json
            client_secrets_file = Path(__file__).parent / "client_secrets.json"
            if not client_secrets_file.exists():
                self.log("[YOUTUBE] ❌ Brak pliku client_secrets.json")
                self.root.after(0, lambda: messagebox.showerror("Błąd", 
                    "Brak pliku client_secrets.json\n\n"
                    "1. Przejdź do Google Cloud Console\n"
                    "2. Utwórz OAuth 2.0 Client ID\n"
                    "3. Pobierz plik JSON\n"
                    "4. Zapisz jako 'client_secrets.json' w folderze 'code/'"))
                return
            
            self.log("[YOUTUBE] Inicjalizacja YouTube Uploader...")
            
            # Utwórz uploader
            uploader = YouTubeUploader(str(client_secrets_file))
            
            # Funkcja callback do raportowania postępu
            def progress_callback(progress, message):
                self.log(f"[YOUTUBE] {message}")
                # Można tu dodać aktualizację progress bar w GUI
            
            self.log("[YOUTUBE] Autoryzacja z YouTube...")
            
            # Autoryzuj
            if not uploader.authenticate():
                self.log("[YOUTUBE] ❌ Błąd autoryzacji z YouTube")
                self.root.after(0, lambda: messagebox.showerror("Błąd", "Nie udało się autoryzować z YouTube API"))
                return
            
            self.log("[YOUTUBE] ✅ Autoryzacja udana!")
            self.log(f"[YOUTUBE] Tytuł: {upload_data['title']}")
            self.log(f"[YOUTUBE] Kategoria: {upload_data['category']}")
            self.log(f"[YOUTUBE] Prywatność: {upload_data['privacy']}")
            
            if upload_data['tags']:
                self.log(f"[YOUTUBE] Tagi: {', '.join(upload_data['tags'])}")
            
            if upload_data['thumbnail_path']:
                self.log(f"[YOUTUBE] Miniaturka: {Path(upload_data['thumbnail_path']).name}")
            
            # Wykonaj upload
            self.log("[YOUTUBE] Rozpoczynam upload wideo...")
            result = uploader.upload_video(
                video_path=upload_data['video_path'],
                title=upload_data['title'],
                description=upload_data['description'],
                tags=upload_data['tags'],
                category=upload_data['category'],
                privacy=upload_data['privacy'],
                thumbnail_path=upload_data['thumbnail_path'],
                progress_callback=progress_callback
            )
            
            if result['success']:
                self.log("[YOUTUBE] ✅ Upload zakończony pomyślnie!")
                self.log(f"[YOUTUBE] ID wideo: {result['video_id']}")
                self.log(f"[YOUTUBE] URL: {result['video_url']}")
                
                # Pokaż komunikat o sukcesie z linkiem
                success_msg = f"Wideo zostało pomyślnie opublikowane na YouTube!\n\n"
                success_msg += f"Tytuł: {result['title']}\n"
                success_msg += f"Prywatność: {result['privacy']}\n"
                success_msg += f"URL: {result['video_url']}"
                
                self.root.after(0, lambda: messagebox.showinfo("Sukces", success_msg))
                
                # Otwórz wideo w przeglądarce
                try:
                    import webbrowser
                    webbrowser.open(result['video_url'])
                except:
                    pass
                    
            else:
                error_msg = f"Błąd podczas uploadu: {result['error']}"
                self.log(f"[YOUTUBE] ❌ {error_msg}")
                self.root.after(0, lambda: messagebox.showerror("Błąd", error_msg))
            
        except Exception as e:
            error_msg = f"Błąd podczas uploadu na YouTube: {str(e)}"
            self.log(f"[YOUTUBE] ❌ {error_msg}")
            self.root.after(0, lambda: messagebox.showerror("Błąd", error_msg))

    def refresh_channel_videos(self):
        """Odświeża listę wideo z kanału YouTube"""
        try:
            self.log("[YOUTUBE] Odświeżanie listy wideo z kanału...")
            
            # Sprawdź czy istnieje plik client_secrets.json
            client_secrets_file = Path(__file__).parent / "client_secrets.json"
            if not client_secrets_file.exists():
                self.log("[YOUTUBE] ❌ Brak pliku client_secrets.json")
                messagebox.showerror("Błąd", "Brak pliku client_secrets.json w folderze code/")
                return
            
            # Utwórz uploader
            try:
                from youtube_uploader import YouTubeUploader
                uploader = YouTubeUploader(str(client_secrets_file))
            except ImportError as e:
                self.log(f"[YOUTUBE] ❌ Błąd importu YouTubeUploader: {e}")
                messagebox.showerror("Błąd", "Nie można zaimportować YouTubeUploader. Sprawdź czy plik youtube_uploader.py istnieje.")
                return
            
            # Autoryzuj
            self.log("[YOUTUBE] Autoryzacja z YouTube...")
            if not uploader.authenticate():
                self.log("[YOUTUBE] ❌ Błąd autoryzacji z YouTube")
                messagebox.showerror("Błąd", "Nie udało się autoryzować z YouTube API")
                return
            
            self.log("[YOUTUBE] ✅ Autoryzacja udana!")
            
            # Pobierz wideo z kanału
            self.log("[YOUTUBE] Pobieranie listy wideo...")
            result = uploader.get_channel_videos(max_results=3)
            
            if result.get('success'):
                self.channel_videos = result['videos']
                self.update_videos_listbox()
                self.log(f"[YOUTUBE] ✅ Pobrano {len(self.channel_videos)} wideo z kanału")
                
                # Komunikaty sukcesu usunięte - tylko logi
                if len(self.channel_videos) > 0:
                    self.log(f"[YOUTUBE] ✅ Pobrano {len(self.channel_videos)} wideo z kanału YouTube")
                else:
                    self.log(f"[YOUTUBE] ℹ️ Nie znaleziono wideo na kanale")
            else:
                error_msg = f"Błąd pobierania wideo: {result.get('error')}"
                self.log(f"[YOUTUBE] ❌ {error_msg}")
                messagebox.showerror("Błąd", error_msg)
                
        except Exception as e:
            error_msg = f"Błąd odświeżania listy wideo: {str(e)}"
            self.log(f"[YOUTUBE] ❌ {error_msg}")
            messagebox.showerror("Błąd", error_msg)

    def update_videos_listbox(self):
        """Aktualizuje listę wideo w listbox"""
        self.videos_listbox.delete(0, tk.END)
        
        if not self.channel_videos:
            self.videos_listbox.insert(tk.END, "Brak wideo do wyświetlenia")
            return
        
        for i, video in enumerate(self.channel_videos, 1):
            # Skróć tytuł jeśli jest za długi
            title = video['title']
            if len(title) > 50:
                title = title[:47] + "..."
            
            # Dodaj informacje o wyświetleniach
            views = video['view_count']
            list_item = f"{i}. {title} ({views} wyświetleń)"
            self.videos_listbox.insert(tk.END, list_item)
            
        self.log(f"[YOUTUBE] Zaktualizowano listę: {len(self.channel_videos)} wideo")

    def on_video_selection_change(self, event):
        """Obsługuje zmianę wyboru wideo w listbox"""
        selection = self.videos_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.channel_videos):
                self.selected_video_for_copy = self.channel_videos[index]
                video = self.selected_video_for_copy
                
                # Aktualizuj tytuł
                self.selected_video_title.config(text=video['title'])
                
                # Aktualizuj opis
                self.selected_video_description.config(state=tk.NORMAL)
                self.selected_video_description.delete(1.0, tk.END)
                self.selected_video_description.insert(1.0, video['description'])
                self.selected_video_description.config(state=tk.DISABLED)
                
                # Aktualizuj tagi
                tags = video.get('tags', [])
                if tags:
                    tags_text = ', '.join(tags)
                    self.selected_video_tags.config(text=tags_text)
                else:
                    self.selected_video_tags.config(text="Brak tagów")
                    
            else:
                self.selected_video_for_copy = None
                self.selected_video_title.config(text="Wybierz wideo z listy powyżej")
                self.selected_video_description.config(state=tk.NORMAL)
                self.selected_video_description.delete(1.0, tk.END)
                self.selected_video_description.config(state=tk.DISABLED)
                self.selected_video_tags.config(text="Brak tagów")

    def copy_video_description(self):
        """Kopiuje opis wybranego wideo do schowka"""
        if not self.selected_video_for_copy:
            messagebox.showwarning("Ostrzeżenie", "Najpierw wybierz wideo z listy")
            return
        
        description = self.selected_video_for_copy['description']
        self.root.clipboard_clear()
        self.root.clipboard_append(description)
        
        self.log(f"[YOUTUBE] Skopiowano opis wideo: {self.selected_video_for_copy['title']}")

    def copy_video_title(self):
        """Kopiuje tytuł wybranego wideo do schowka"""
        if not self.selected_video_for_copy:
            messagebox.showwarning("Ostrzeżenie", "Najpierw wybierz wideo z listy")
            return
        
        title = self.selected_video_for_copy['title']
        self.root.clipboard_clear()
        self.root.clipboard_append(title)
        
        self.log(f"[YOUTUBE] Skopiowano tytuł wideo: {title}")

    def copy_video_tags(self):
        """Kopiuje tagi wybranego wideo do schowka"""
        if not self.selected_video_for_copy:
            messagebox.showwarning("Ostrzeżenie", "Najpierw wybierz wideo z listy")
            return
        
        tags = self.selected_video_for_copy.get('tags', [])
        if tags:
            tags_text = ', '.join(tags)
            self.root.clipboard_clear()
            self.root.clipboard_append(tags_text)
            
            self.log(f"[YOUTUBE] Skopiowano tagi wideo: {self.selected_video_for_copy['title']}")
        else:
            self.log(f"[YOUTUBE] Wideo nie ma tagów: {self.selected_video_for_copy['title']}")

    def load_description_from_report(self):
        """Ładuje opis z raportu social media do części 1 opisu"""
        try:
            # Znajdź najnowszy raport social media
            working_dir = Path(self.working_dir.get())
            if not working_dir.exists():
                messagebox.showerror("Błąd", "Nie wybrano folderu roboczego")
                return
            
            # Szukaj plików raportu (różne wzorce)
            report_patterns = [
                "*raport*.docx",
                "*social*.docx", 
                "*post*.docx",
                "*report*.docx",
                "*generated*.docx",
                "*raport*.txt",
                "*social*.txt", 
                "*post*.txt",
                "*report*.txt",
                "*generated*.txt"
            ]
            
            report_files = []
            for pattern in report_patterns:
                report_files.extend(list(working_dir.rglob(pattern)))
            
            # Usuń duplikaty
            report_files = list(set(report_files))
            
            if not report_files:
                # Spróbuj znaleźć pliki w podfolderach
                all_docx_files = list(working_dir.rglob("*.docx"))
                all_txt_files = list(working_dir.rglob("*.txt"))
                all_files = all_docx_files + all_txt_files
                
                if all_files:
                    # Pokaż dialog wyboru pliku
                    file_path = filedialog.askopenfilename(
                        title="Wybierz plik raportu social media",
                        initialdir=str(working_dir),
                        filetypes=[
                            ("Pliki Word", "*.docx"), 
                            ("Pliki tekstowe", "*.txt"), 
                            ("Wszystkie pliki", "*.*")
                        ]
                    )
                    if file_path:
                        report_files = [Path(file_path)]
                    else:
                        return
                else:
                    messagebox.showwarning("Ostrzeżenie", 
                        "Nie znaleziono plików raportu social media.\n\n"
                        "Szukane wzorce:\n" + "\n".join(report_patterns))
                    return
            
            # Wybierz najnowszy plik
            latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
            
            self.log(f"[YOUTUBE] Znaleziono {len(report_files)} plików raportu")
            self.log(f"[YOUTUBE] Wybrano najnowszy: {latest_report.name}")
            self.log(f"[YOUTUBE] Ścieżka: {latest_report}")
            
            # Wczytaj zawartość pliku
            if latest_report.suffix.lower() == '.docx':
                if not DOCX_AVAILABLE:
                    messagebox.showerror("Błąd", 
                        "Nie można wczytać pliku .docx\n\n"
                        "Zainstaluj bibliotekę:\n"
                        "pip install python-docx")
                    return
                
                content, error = safe_read_docx(latest_report)
                if error:
                    self.log(f"[YOUTUBE] ❌ {error}")
                    messagebox.showerror("Błąd", error)
                    return
                self.log(f"[YOUTUBE] Wczytano plik .docx: {len(content)} znaków")
            else:
                # Plik .txt
                with open(latest_report, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.log(f"[YOUTUBE] Wczytano plik .txt: {len(content)} znaków")
            
            # Znajdź sekcję "POST PO ANGIELSKU"
            lines = content.split('\n')
            post_start = None
            post_end = None
            
            # Szukaj różnych wariantów nazwy sekcji
            search_terms = ["POST PO ANGIELSKU", "POST IN ENGLISH", "ENGLISH POST", "POST ANGIELSKI"]
            
            for i, line in enumerate(lines):
                for term in search_terms:
                    if term in line.upper():
                        post_start = i + 1
                        self.log(f"[YOUTUBE] Znaleziono sekcję: '{line.strip()}' w linii {i+1}")
                        break
                if post_start is not None:
                    break
            
            if post_start is None:
                # Pokaż pierwsze 10 linii pliku dla debugowania
                preview = "\n".join(lines[:10])
                self.log(f"[YOUTUBE] Nie znaleziono sekcji. Pierwsze 10 linii:\n{preview}")
                messagebox.showwarning("Ostrzeżenie", 
                    "Nie znaleziono sekcji 'POST PO ANGIELSKU' w raporcie.\n\n"
                    "Szukane sekcje:\n" + "\n".join(search_terms))
                return
            
            # Znajdź koniec posta (następna sekcja lub koniec pliku)
            for i in range(post_start, len(lines)):
                if lines[i].strip() and not lines[i].startswith(' ') and ':' in lines[i]:
                    post_end = i
                    break
            
            if post_end is None:
                post_end = len(lines)
            
            # Wyciągnij post
            post_lines = lines[post_start:post_end]
            post_text = '\n'.join(post_lines).strip()
            
            if post_text:
                # Wyczyść pole i wstaw tekst
                self.desc_part1_text.delete(1.0, tk.END)
                self.desc_part1_text.insert(1.0, post_text)
                
                self.log(f"[YOUTUBE] ✅ Załadowano opis z raportu: {latest_report.name} ({len(post_text)} znaków)")
            else:
                messagebox.showwarning("Ostrzeżenie", "Nie znaleziono treści posta w raporcie")
                
        except Exception as e:
            error_msg = f"Błąd podczas ładowania opisu z raportu: {str(e)}"
            self.log(f"[YOUTUBE] ❌ {error_msg}")
            messagebox.showerror("Błąd", error_msg)

    def load_tags_from_report(self):
        """Ładuje tagi z raportu social media"""
        try:
            # Znajdź najnowszy raport social media
            working_dir = Path(self.working_dir.get())
            if not working_dir.exists():
                messagebox.showerror("Błąd", "Nie wybrano folderu roboczego")
                return
            
            # Szukaj plików raportu (różne wzorce)
            report_patterns = [
                "*raport*.docx",
                "*social*.docx", 
                "*post*.docx",
                "*report*.docx",
                "*generated*.docx",
                "*raport*.txt",
                "*social*.txt", 
                "*post*.txt",
                "*report*.txt",
                "*generated*.txt"
            ]
            
            report_files = []
            for pattern in report_patterns:
                report_files.extend(list(working_dir.rglob(pattern)))
            
            # Usuń duplikaty
            report_files = list(set(report_files))
            
            if not report_files:
                # Spróbuj znaleźć pliki w podfolderach
                all_docx_files = list(working_dir.rglob("*.docx"))
                all_txt_files = list(working_dir.rglob("*.txt"))
                all_files = all_docx_files + all_txt_files
                
                if all_files:
                    # Pokaż dialog wyboru pliku
                    file_path = filedialog.askopenfilename(
                        title="Wybierz plik raportu social media",
                        initialdir=str(working_dir),
                        filetypes=[
                            ("Pliki Word", "*.docx"), 
                            ("Pliki tekstowe", "*.txt"), 
                            ("Wszystkie pliki", "*.*")
                        ]
                    )
                    if file_path:
                        report_files = [Path(file_path)]
                    else:
                        return
                else:
                    messagebox.showwarning("Ostrzeżenie", 
                        "Nie znaleziono plików raportu social media.\n\n"
                        "Szukane wzorce:\n" + "\n".join(report_patterns))
                    return
            
            # Wybierz najnowszy plik
            latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
            
            self.log(f"[YOUTUBE] Znaleziono {len(report_files)} plików raportu")
            self.log(f"[YOUTUBE] Wybrano najnowszy: {latest_report.name}")
            self.log(f"[YOUTUBE] Ścieżka: {latest_report}")
            
            # Wczytaj zawartość pliku
            if latest_report.suffix.lower() == '.docx':
                if not DOCX_AVAILABLE:
                    messagebox.showerror("Błąd", 
                        "Nie można wczytać pliku .docx\n\n"
                        "Zainstaluj bibliotekę:\n"
                        "pip install python-docx")
                    return
                
                content, error = safe_read_docx(latest_report)
                if error:
                    self.log(f"[YOUTUBE] ❌ {error}")
                    messagebox.showerror("Błąd", error)
                    return
                self.log(f"[YOUTUBE] Wczytano plik .docx: {len(content)} znaków")
            else:
                # Plik .txt
                with open(latest_report, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.log(f"[YOUTUBE] Wczytano plik .txt: {len(content)} znaków")
            
            # Znajdź sekcję "POST PO ANGIELSKU" i z niej wyciągnij hashtags
            lines = content.split('\n')
            english_section_start = None
            
            # Szukaj sekcji angielskiej
            search_terms = ["POST PO ANGIELSKU", "POST IN ENGLISH", "ENGLISH POST", "POST ANGIELSKI"]
            
            for i, line in enumerate(lines):
                for term in search_terms:
                    if term in line.upper():
                        english_section_start = i + 1
                        self.log(f"[YOUTUBE] Znaleziono sekcję angielską: '{line.strip()}' w linii {i+1}")
                        break
                if english_section_start is not None:
                    break
            
            if english_section_start is None:
                # Pokaż pierwsze 10 linii pliku dla debugowania
                preview = "\n".join(lines[:10])
                self.log(f"[YOUTUBE] Nie znaleziono sekcji angielskiej. Pierwsze 10 linii:\n{preview}")
                messagebox.showwarning("Ostrzeżenie", 
                    "Nie znaleziono sekcji angielskiej w raporcie.\n\n"
                    "Szukane sekcje:\n" + "\n".join(search_terms))
                return
            
            # Znajdź koniec sekcji angielskiej
            english_section_end = len(lines)
            for i in range(english_section_start, len(lines)):
                if lines[i].strip() and not lines[i].startswith(' ') and ':' in lines[i]:
                    english_section_end = i
                    break
            
            # Wyciągnij całą sekcję angielską
            english_section_lines = lines[english_section_start:english_section_end]
            english_section_text = '\n'.join(english_section_lines)
            
            # Znajdź linię z hashtags w sekcji angielskiej
            hashtags_line = None
            for line in english_section_lines:
                if any(term in line.upper() for term in ["HASHTAGS:", "HASHTAGS", "TAGS:", "TAGS"]):
                    hashtags_line = line
                    break
            
            # Wyciągnij hashtagi z linii (usuń [PIN] i inne oznaczenia)
            import re
            hashtags = []
            if hashtags_line:
                hashtags = re.findall(r'#\w+', hashtags_line)
            
            if hashtags:
                # Usuń # z początku każdego tagu
                tags = [tag[1:] for tag in hashtags]
                tags_text = ', '.join(tags)
                
                # Wstaw tagi do pola
                self.youtube_tags.set(tags_text)
                
                self.log(f"[YOUTUBE] ✅ Załadowano {len(tags)} angielskich tagów z raportu: {latest_report.name}")
                self.log(f"[YOUTUBE] Angielskie tagi: {tags_text}")
            else:
                messagebox.showwarning("Ostrzeżenie", "Nie znaleziono angielskich tagów w sekcji POST PO ANGIELSKU")
                
        except Exception as e:
            error_msg = f"Błąd podczas ładowania tagów z raportu: {str(e)}"
            self.log(f"[YOUTUBE] ❌ {error_msg}")
            messagebox.showerror("Błąd", error_msg)

    # ===== FUNKCJE SOCIAL MEDIA =====
    
    def select_facebook_video(self):
        """Wybiera wideo dla posta na Facebook"""
        file_path = filedialog.askopenfilename(
            title="Wybierz wideo dla posta na Facebook",
            filetypes=[
                ("Pliki wideo", "*.mp4 *.avi *.mov *.mkv"),
                ("Wszystkie pliki", "*.*")
            ]
        )
        if file_path:
            # Zapisujemy pełną ścieżkę, aby nie zależeć od working_dir
            self.facebook_video_path.set(file_path)
            self.log(f"[SOCIAL] Wybrano wideo dla Facebook: {Path(file_path).name}")
    
    def select_facebook_image(self):
        """Wybiera obraz dla posta na Facebook"""
        file_path = filedialog.askopenfilename(
            title="Wybierz obraz do posta na Facebook",
            filetypes=[
                ("Obrazy", "*.jpg *.jpeg *.png *.bmp"),
                ("Wszystkie pliki", "*.*")
            ]
        )
        if file_path:
            # Zapisujemy pełną ścieżkę, aby nie zależeć od working_dir
            self.facebook_image_path.set(file_path)
            self.log(f"[SOCIAL] Wybrano obraz dla Facebook: {Path(file_path).name}")

    def select_instagram_video(self):
        """Wybiera wideo dla posta na Instagram"""
        file_path = filedialog.askopenfilename(
            title="Wybierz wideo dla posta na Instagram",
            filetypes=[
                ("Pliki wideo", "*.mp4 *.avi *.mov *.mkv"),
                ("Wszystkie pliki", "*.*")
            ]
        )
        if file_path:
            self.instagram_video_path.set(Path(file_path).name)
            self.log(f"[SOCIAL] Wybrano wideo dla Instagram: {Path(file_path).name}")
    
    def load_facebook_post_from_report(self):
        """Ładuje treść posta na Facebook z raportu"""
        try:
            # Znajdź najnowszy raport social media
            working_dir = Path(self.working_dir.get())
            if not working_dir.exists():
                messagebox.showerror("Błąd", "Nie wybrano folderu roboczego")
                return
            
            # Szukaj plików raportu
            report_patterns = [
                "*raport*.docx", "*social*.docx", "*post*.docx", "*report*.docx",
                "*raport*.txt", "*social*.txt", "*post*.txt", "*report*.txt"
            ]
            
            report_files = []
            for pattern in report_patterns:
                report_files.extend(list(working_dir.rglob(pattern)))
            
            if not report_files:
                messagebox.showwarning("Ostrzeżenie", "Nie znaleziono plików raportu social media")
                return
            
            # Wybierz najnowszy plik
            latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
            
            # Wczytaj zawartość pliku
            if latest_report.suffix.lower() == '.docx':
                content, error = safe_read_docx(latest_report)
                if error:
                    self.log(f"[SOCIAL] ❌ {error}")
                    messagebox.showerror("Błąd", error)
                    return
            else:
                with open(latest_report, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Znajdź sekcję "POST PO ANGIELSKU" (taka sama jak w YouTube)
            lines = content.split('\n')
            post_start = None
            
            search_terms = ["POST PO ANGIELSKU", "POST IN ENGLISH", "ENGLISH POST", "POST ANGIELSKI"]
            
            for i, line in enumerate(lines):
                for term in search_terms:
                    if term in line.upper():
                        post_start = i + 1
                        self.log(f"[SOCIAL] Znaleziono sekcję Facebook: '{line.strip()}' w linii {i+1}")
                        break
                if post_start is not None:
                    break
            
            if post_start is None:
                messagebox.showwarning("Ostrzeżenie", 
                    "Nie znaleziono sekcji angielskiej w raporcie.\n\n"
                    "Szukane sekcje:\n" + "\n".join(search_terms))
                return
            
            # Znajdź koniec posta
            post_end = len(lines)
            for i in range(post_start, len(lines)):
                if lines[i].strip() and not lines[i].startswith(' ') and ':' in lines[i]:
                    post_end = i
                    break
            
            # Wyciągnij post
            post_lines = lines[post_start:post_end]
            post_text = '\n'.join(post_lines).strip()
            
            if post_text:
                self.facebook_post_text.delete(1.0, tk.END)
                self.facebook_post_text.insert(1.0, post_text)
                self.log(f"[SOCIAL] ✅ Załadowano angielski post Facebook z raportu: {latest_report.name}")
            else:
                messagebox.showwarning("Ostrzeżenie", "Nie znaleziono treści angielskiego posta w raporcie")
                
        except Exception as e:
            error_msg = f"Błąd podczas ładowania posta Facebook: {str(e)}"
            self.log(f"[SOCIAL] ❌ {error_msg}")
            messagebox.showerror("Błąd", error_msg)
    
    def load_instagram_post_from_report(self):
        """Ładuje treść posta na Instagram z raportu"""
        try:
            # Znajdź najnowszy raport social media
            working_dir = Path(self.working_dir.get())
            if not working_dir.exists():
                messagebox.showerror("Błąd", "Nie wybrano folderu roboczego")
                return
            
            # Szukaj plików raportu
            report_patterns = [
                "*raport*.docx", "*social*.docx", "*post*.docx", "*report*.docx",
                "*raport*.txt", "*social*.txt", "*post*.txt", "*report*.txt"
            ]
            
            report_files = []
            for pattern in report_patterns:
                report_files.extend(list(working_dir.rglob(pattern)))
            
            if not report_files:
                messagebox.showwarning("Ostrzeżenie", "Nie znaleziono plików raportu social media")
                return
            
            # Wybierz najnowszy plik
            latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
            
            # Wczytaj zawartość pliku
            if latest_report.suffix.lower() == '.docx':
                content, error = safe_read_docx(latest_report)
                if error:
                    self.log(f"[SOCIAL] ❌ {error}")
                    messagebox.showerror("Błąd", error)
                    return
            else:
                with open(latest_report, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Znajdź sekcję "POST PO ANGIELSKU" (taka sama jak w YouTube)
            lines = content.split('\n')
            post_start = None
            
            search_terms = ["POST PO ANGIELSKU", "POST IN ENGLISH", "ENGLISH POST", "POST ANGIELSKI"]
            
            for i, line in enumerate(lines):
                for term in search_terms:
                    if term in line.upper():
                        post_start = i + 1
                        self.log(f"[SOCIAL] Znaleziono sekcję Instagram: '{line.strip()}' w linii {i+1}")
                        break
                if post_start is not None:
                    break
            
            if post_start is None:
                messagebox.showwarning("Ostrzeżenie", 
                    "Nie znaleziono sekcji angielskiej w raporcie.\n\n"
                    "Szukane sekcje:\n" + "\n".join(search_terms))
                return
            
            # Znajdź koniec posta
            post_end = len(lines)
            for i in range(post_start, len(lines)):
                if lines[i].strip() and not lines[i].startswith(' ') and ':' in lines[i]:
                    post_end = i
                    break
            
            # Wyciągnij post
            post_lines = lines[post_start:post_end]
            post_text = '\n'.join(post_lines).strip()
            
            if post_text:
                self.instagram_post_text.delete(1.0, tk.END)
                self.instagram_post_text.insert(1.0, post_text)
                self.log(f"[SOCIAL] ✅ Załadowano angielski post Instagram z raportu: {latest_report.name}")
            else:
                messagebox.showwarning("Ostrzeżenie", "Nie znaleziono treści angielskiego posta w raporcie")
                
        except Exception as e:
            error_msg = f"Błąd podczas ładowania posta Instagram: {str(e)}"
            self.log(f"[SOCIAL] ❌ {error_msg}")
            messagebox.showerror("Błąd", error_msg)
    
    def copy_facebook_post(self):
        """Kopiuje tekst posta Facebook do schowka"""
        text = self.facebook_post_text.get("1.0", tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.log(f"[SOCIAL] Skopiowano post Facebook ({len(text)} znaków)")
        else:
            messagebox.showwarning("Ostrzeżenie", "Brak tekstu do skopiowania")
    
    def copy_instagram_post(self):
        """Kopiuje tekst posta Instagram do schowka"""
        text = self.instagram_post_text.get("1.0", tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.log(f"[SOCIAL] Skopiowano post Instagram ({len(text)} znaków)")
        else:
            messagebox.showwarning("Ostrzeżenie", "Brak tekstu do skopiowania")
    
    def publish_facebook_post(self):
        """Publikuje post na Facebook"""
        try:
            text = self.facebook_post_text.get("1.0", tk.END).strip()
            if not text:
                messagebox.showwarning("Ostrzeżenie", "Brak tekstu do publikacji")
                return
            
            # Sprawdź czy są skonfigurowane klucze API
            app_id = self.facebook_app_id.get().strip()
            app_secret = self.facebook_app_secret.get().strip()
            access_token = self.facebook_access_token.get().strip()
            
            if not all([app_id, app_secret, access_token]):
                messagebox.showerror("Błąd", 
                    "Brak kluczy Facebook API.\n\n"
                    "Przejdź do zakładki 'Konfiguracja API' i wprowadź:\n"
                    "- Facebook App ID\n"
                    "- Facebook App Secret\n"
                    "- Facebook Access Token")
                return
            
            # Importuj Facebook SDK
            try:
                import facebook
            except ImportError:
                messagebox.showerror("Błąd", 
                    "Brak biblioteki Facebook SDK.\n\n"
                    "Zainstaluj: pip install facebook-sdk")
                return
            
            # Utwórz obiekt Graph API
            graph = facebook.GraphAPI(access_token=access_token, version="3.1")

            # Weryfikacja: na jaką stronę/konto pójdzie post
            try:
                me_obj = graph.get_object(id='me', fields='id,name')
                target_name = me_obj.get('name', 'unknown')
                self.log(f"[SOCIAL] Używany token publikuje jako: {target_name}")
            except Exception:
                # Brakujące uprawnienia nie powinny blokować dalszej próby publikacji
                pass
            
            # Publikuj post
            self.log(f"[SOCIAL] 📤 Publikowanie posta na Facebook ({len(text)} znaków)")
            
            # Ścieżki multimediów
            working_dir = Path(self.working_dir.get()) if self.working_dir.get() else Path.cwd()
            video_path = self.facebook_video_path.get().strip()
            image_path = getattr(self, 'facebook_image_path', tk.StringVar()).get().strip()

            response = None
            # 1) Priorytet: jeśli wybrano wideo – publikuj wideo
            if video_path:
                full_video_path = Path(video_path)
                if not full_video_path.is_absolute():
                    full_video_path = working_dir / video_path
                if full_video_path.exists():
                    with open(full_video_path, 'rb') as video_file:
                        response = graph.put_video(
                            video=video_file,
                            title="Nowe wideo edukacyjne",
                            description=text,
                            privacy={'value': 'EVERYONE'}
                        )
                    self.log(f"[SOCIAL] ✅ Wideo opublikowane na Facebook: {response.get('id', 'N/A')}")
                    messagebox.showinfo("Sukces", "Wideo zostało opublikowane na Facebook!")
                else:
                    messagebox.showerror("Błąd", f"Nie znaleziono pliku wideo: {full_video_path}")
                    return
            # 2) W przeciwnym razie, jeśli wybrano obraz – publikuj zdjęcie z podpisem
            elif image_path:
                full_image_path = Path(image_path)
                if not full_image_path.is_absolute():
                    full_image_path = working_dir / image_path
                if full_image_path.exists():
                    with open(full_image_path, 'rb') as image_file:
                        response = graph.put_photo(image=image_file, message=text)
                    self.log(f"[SOCIAL] ✅ Zdjęcie opublikowane na Facebook: {response.get('post_id', response.get('id', 'N/A'))}")
                    messagebox.showinfo("Sukces", "Zdjęcie zostało opublikowane na Facebook!")
                else:
                    messagebox.showerror("Błąd", f"Nie znaleziono pliku obrazu: {full_image_path}")
                    return
            # 3) Brak multimediów – publikuj sam tekst
            else:
                response = graph.put_object(
                    parent_object='me',
                    connection_name='feed',
                    message=text
                )
                self.log(f"[SOCIAL] ✅ Post opublikowany na Facebook: {response.get('id', 'N/A')}")
                messagebox.showinfo("Sukces", "Post został opublikowany na Facebook!")

            # Opcjonalny komentarz (np. link do YouTube)
            comment_text = getattr(self, 'facebook_comment_var', tk.StringVar()).get().strip()
            if response and comment_text:
                # Uzyskaj ID obiektu do komentowania
                object_id = response.get('post_id') or response.get('id')
                if object_id:
                    try:
                        graph.put_object(object_id, 'comments', message=comment_text)
                        self.log("[SOCIAL] 💬 Dodano komentarz pod postem")
                    except Exception as ce:
                        self.log(f"[SOCIAL] ⚠️ Nie udało się dodać komentarza: {ce}")
                
        except facebook.GraphAPIError as e:
            error_msg = f"Błąd Facebook API: {str(e)}"
            self.log(f"[SOCIAL] ❌ {error_msg}")
            messagebox.showerror("Błąd Facebook", error_msg)
        except Exception as e:
            error_msg = f"Błąd podczas publikacji na Facebook: {str(e)}"
            self.log(f"[SOCIAL] ❌ {error_msg}")
            messagebox.showerror("Błąd", error_msg)
    
    def publish_instagram_post(self):
        """Publikuje post na Instagram (placeholder)"""
        text = self.instagram_post_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Ostrzeżenie", "Brak tekstu do publikacji")
            return
        
        # TODO: Implementacja API Instagram
        self.log(f"[SOCIAL] 📤 Publikowanie posta na Instagram ({len(text)} znaków)")
        messagebox.showinfo("Informacja", "Funkcja publikacji na Instagram będzie dostępna wkrótce")

    def on_closing(self):
        """Obsługuje zamknięcie aplikacji"""
        if messagebox.askokcancel("Wyjście", "Czy na pewno chcesz wyjść z aplikacji?"):
            self.root.destroy()
            # Czekaj na zakończenie wszystkich wątków
            for thread in self.active_threads:
                if thread.is_alive():
                    thread.join(timeout=5) # Poczekaj na zakończenie wątku
            sys.exit(0)

def main():
    root = tk.Tk()
    app = VideoTranslationApp(root)
    

    
    root.mainloop()

if __name__ == "__main__":
    main() 