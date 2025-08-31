from typing import Dict, Any, Optional, List
import json
import shutil
import sys, os, pygame
import random
import tkinter as tk
from collections import defaultdict
from datetime import datetime, timedelta
from tkinter import ttk, messagebox, filedialog
import logging

# Set up logging (Linux)
log_dir = os.path.expanduser("~/.word_wizard")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, 'word_wizard.log')

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class WordWizardApp:
    def __init__(self, master: tk.Tk) -> None:
        self.star_btn = None
        self.progress_bar: Optional[ttk.Progressbar] = None
        self.progress_label: Optional[ttk.Label] = None
        self.streak_label: Optional[ttk.Label] = None
        self.correct_streak: int = 0
        self.master = master
        self.sound_enabled = True
        self._initialize_pygame_mixer()
        self.master.title("")
        self.master.geometry(
            f"{int(self.master.winfo_screenwidth() * 0.35)}x{int(self.master.winfo_screenheight() * 0.45)}")
        self.master.minsize(int(self.master.winfo_screenwidth() * 0.35), int(self.master.winfo_screenheight() * 0.45))

        self._fade_after_id = None

        # Initialize variables with type hints
        self.current_card: Optional[Dict[str, Any]] = None
        self.current_card_idx: int = 0
        self.review_cards: List[Dict[str, Any]] = []
        self.card_front: bool = True
        self.feedback_given: bool = False
        self.session_start_time: Optional[datetime] = None
        self.dark_mode: bool = False
        self.sound_enabled: bool = True
        self.keyboard_enabled: bool = True
        self.max_cards: int = 20
        self.transition_delay: int = 500
        self.save_pending = False
        self._resize_after_id = None
        self._save_scheduled = False

        # Tkinter variables
        self.status_var: tk.StringVar = tk.StringVar()
        self.word_count_var: tk.StringVar = tk.StringVar()
        self.level_var: tk.StringVar = tk.StringVar()
        self.category_var: tk.StringVar = tk.StringVar()
        self.progress_var: tk.StringVar = tk.StringVar()
        self.dark_mode_var: tk.BooleanVar = tk.BooleanVar()
        self.sound_var: tk.BooleanVar = tk.BooleanVar()
        self.keyboard_enabled_var: tk.BooleanVar = tk.BooleanVar(value=True)
        self.default_cards_var: tk.StringVar = tk.StringVar(value="20")
        self.transition_delay_var: tk.StringVar = tk.StringVar()
        self.stats_var: tk.StringVar = tk.StringVar(value="No difficult words yet")

        # Data structures
        self.entry_vars: Dict[str, tk.StringVar] = {}
        self.flashcards: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {
            'total_reviews': 0,
            'correct': 0,
            'incorrect': 0,
            'streak': 0,
            'last_review_date': None,
            'by_level': defaultdict(lambda: {'correct': 0, 'incorrect': 0}),
            'by_category': defaultdict(lambda: {'correct': 0, 'incorrect': 0}),
            'difficult_words': defaultdict(int)
        }
        self.user_config: Dict[str, Any] = {}

        # UI theme variables
        self.style: ttk.Style = ttk.Style()
        self.light_colors: Dict[str, str] = {
            'bg': '#D6F0FF',
            'fg': '#333333',
            'card_bg': '#E1F5FE',
            'button_bg': '#80DEEA',
            'button_hover': '#4DD0E1',
            'highlight': '#4CAF50',
            'incorrect': '#FF5252',
            'streak_bg': '#FFF9B0'
        }
        self.dark_colors: Dict[str, str] = {
            'bg': '#000000',
            'fg': '#E0E0E0',
            'card_bg': '#1E1E1E',
            'button_bg': '#404040',
            'button_hover': '#606060',
            'highlight': '#66BB6A',
            'incorrect': '#EF5350',
            'streak_bg': '#66BB6A'
        }

        # App data paths
        if getattr(sys, 'frozen', False):
            resource_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            data_path = os.path.join(os.getenv('APPDATA'), 'WordWizard')
        else:
            resource_path = os.path.dirname(os.path.abspath(__file__))
            data_path = resource_path

        self.app_data_dir = os.path.join(data_path, 'data')  # Explicitly set data directory
        self.app_config_dir = os.path.join(data_path, 'config')  # Explicitly set config directory
        self.sounds_dir = os.path.join(resource_path, 'sounds')
        self.vocab_file = os.path.join(self.app_data_dir, 'german_flashcards.json')  # Move vocab to data directory
        self.backup_vocab_file = os.path.join(self.app_data_dir, 'backup', 'backup.json')  # Backup in data/backup
        self.stats_file = os.path.join(self.app_config_dir, 'stats.json')
        self.user_config_file = os.path.join(self.app_config_dir, 'config.json')

        # Ensure directories exist
        os.makedirs(self.app_data_dir, exist_ok=True)
        os.makedirs(self.app_config_dir, exist_ok=True)
        os.makedirs(os.path.join(self.app_data_dir, 'backup'), exist_ok=True)

        # Initialize config and stats if they don't exist
        if not os.path.exists(self.user_config_file):
            with open(self.user_config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'dark_mode': self.dark_mode,
                    'sound_enabled': self.sound_enabled,
                    'max_cards': self.max_cards,
                    'transition_delay': self.transition_delay,
                    'keyboard_enabled': self.keyboard_enabled
                }, f, indent=2)
        if not os.path.exists(self.stats_file):
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2)

        # Widget placeholders
        self.main_frame: Optional[ttk.Frame] = None
        self.menu_frame: Optional[ttk.Frame] = None
        self.review_frame: Optional[ttk.Frame] = None
        self.custom_frame: Optional[ttk.Frame] = None
        self.stats_frame: Optional[ttk.Frame] = None
        self.add_word_frame: Optional[ttk.Frame] = None
        self.settings_frame: Optional[ttk.Frame] = None
        self.card_label: Optional[ttk.Label] = None
        self.example_label: Optional[ttk.Label] = None
        self.correct_btn: Optional[ttk.Button] = None
        self.incorrect_btn: Optional[ttk.Button] = None
        self.flip_btn: Optional[ttk.Button] = None
        self.back_btn: Optional[ttk.Button] = None
        self.status_bar: Optional[ttk.Label] = None
        self.stats_text: Optional[tk.Text] = None
        self.stats_labels = None
        self.level_stats_labels = None

        # Load data and setup UI
        self.load_data()
        self.setup_ui()
        self.apply_theme()
        self.master.bind('<Configure>', lambda event: self.update_fonts_on_resize())
        self.master.bind('<Escape>', lambda event: self.show_menu())
        self.master.bind('<Return>', lambda event: "break")
        self.master.bind('<space>', lambda event: "break")
        self.bind_keyboard_events()

    def bind_keyboard_events(self):
        """Bind keyboard events for review_frame when visible. Up toggles between German and English until feedback is given. Left/Right only work when card is flipped (English translation visible)."""
        # Unbind previous bindings to avoid duplicates
        if self.review_frame:
            self.review_frame.unbind('<Up>')
            self.review_frame.unbind('<Left>')
            self.review_frame.unbind('<Right>')
        # Only bind if keyboard is enabled, review_frame exists, and is visible
        if not self.keyboard_enabled or not self.review_frame or not self.review_frame.winfo_ismapped():
            return

        def handle_keypress(event):
            """Handle keypress events for Up, Left, Right keys."""
            if not self.current_card:
                return
            # Up toggles between German and English until feedback is given
            if event.keysym == 'Up' and not self.feedback_given:
                self.flip_card()
            # Left (correct) and Right (incorrect) only when card is flipped and no feedback given
            elif event.keysym == 'Left' and not self.card_front and not self.feedback_given:
                self.answer_feedback(True)
            elif event.keysym == 'Right' and not self.card_front and not self.feedback_given:
                self.answer_feedback(False)

        # Bind keys to review frame
        self.review_frame.bind('<Up>', handle_keypress)
        self.review_frame.bind('<Left>', handle_keypress)
        self.review_frame.bind('<Right>', handle_keypress)
        # Ensure review_frame is focused with a slight delay
        self.master.after(100, lambda: self.review_frame.focus_set())
        self.master.after(100, lambda: self.review_frame.focus_force())

    def show_menu(self):
        """Show the main menu, hide other frames, unbind keyboard events, and reset custom review selections."""
        # Hide all frames in main_frame to prevent overlap
        for frame in self.main_frame.winfo_children():
            frame.pack_forget()
        if self.menu_frame:
            self.menu_frame.pack(fill="both", expand=True)

        # Unbind all keyboard events when returning to menu
        if self.review_frame:
            self.review_frame.unbind('<Up>')
            self.review_frame.unbind('<Left>')
            self.review_frame.unbind('<Right>')
            self.review_frame.unbind('<Down>')

        # Clear status bar
        self.update_status("Welcome to Word Wizard")

        # Reset custom review selections to 'All'
        self.level_var.set("All")
        self.category_var.set("All")

        # Ensure menu_frame is focused
        self.menu_frame.focus_set()

    def toggle_keyboard_navigation(self):
        """Toggle keyboard navigation based on settings."""
        self.keyboard_enabled = self.keyboard_enabled_var.get()
        self.bind_keyboard_events()

    def _initialize_pygame_mixer(self) -> None:
        try:
            import platform
            if platform.system() == "Windows":
                os.environ['SDL_AUDIODRIVER'] = 'directsound'
            else:
                os.environ['SDL_AUDIODRIVER'] = 'pulseaudio' if 'pulseaudio' in os.environ.get('SDL_AUDIODRIVER',
                                                                                               '').lower() else 'alsa'

            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
                pygame.mixer.init()
                if pygame.mixer.get_num_channels() == 0:
                    self.sound_enabled = False
                    messagebox.showwarning("Sound Error", "No audio channels detected. Sounds will be disabled.")
        except pygame.error as e:
            print(f"Pygame mixer initialization failed: {e}")
            self.sound_enabled = False
            messagebox.showwarning("Sound Error", f"Sound initialization failed: {str(e)}. Sounds will be disabled.")

    @staticmethod
    def _validate_json_file(file_path: str, min_size: int = 1000) -> bool:
        """Validate JSON file by checking existence, size, and syntax."""
        try:
            if not os.path.exists(file_path):
                logging.error(f"JSON file not found: {file_path}")
                return False
            if os.path.getsize(file_path) < min_size:
                logging.error(f"JSON file too small: {file_path} (size: {os.path.getsize(file_path)} bytes)")
                return False
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                logging.error(f"JSON file does not contain a list: {file_path}")
                return False
            logging.info(f"JSON file validated successfully: {file_path}")
            return True
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logging.error(f"Invalid JSON in {file_path}: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"Error validating JSON file {file_path}: {str(e)}")
            return False

    def _repair_json_file(self) -> bool:
        """Attempt to repair missing or corrupted JSON file by copying from resource directory."""
        system_vocab_file = os.path.join(self.sounds_dir, "..",
                                         "german_flashcards.json")  # Use resource_path relative to sounds_dir
        try:
            if not os.path.exists(system_vocab_file):
                logging.error(f"System JSON file not found: {system_vocab_file}")
                return False
            if not self._validate_json_file(system_vocab_file):
                logging.error(f"System JSON file is invalid: {system_vocab_file}")
                return False
            if os.path.exists(self.vocab_file):
                shutil.copy(self.vocab_file, self.backup_vocab_file)
                logging.info(f"Backed up existing user JSON to {self.backup_vocab_file}")
            shutil.copy(system_vocab_file, self.vocab_file)
            logging.info(f"Copied system JSON from {system_vocab_file} to {self.vocab_file}")
            os.chmod(self.vocab_file, 0o644)
            logging.info(f"Set permissions (644) for {self.vocab_file}")
            if self._validate_json_file(self.vocab_file):
                logging.info(f"Successfully repaired JSON file: {self.vocab_file}")
                return True
            else:
                logging.error(f"Copied JSON file is invalid: {self.vocab_file}")
                return False
        except Exception as e:
            logging.error(f"Failed to repair JSON file: {str(e)}")
            return False

    def load_data(self):
        """Load and validate data, repairing if necessary."""
        try:
            os.makedirs(self.app_data_dir, exist_ok=True)
            os.makedirs(self.app_config_dir, exist_ok=True)
            os.makedirs(os.path.join(self.app_data_dir, 'backup'), exist_ok=True)
            logging.info(f"Ensured directories exist: {self.app_data_dir}, {self.app_config_dir}")

            # Load vocab file
            if not self._validate_json_file(self.vocab_file):
                logging.warning(f"User JSON file invalid or missing: {self.vocab_file}. Attempting repair.")
                if not self._repair_json_file():
                    messagebox.showwarning("Warning",
                                           "Failed to repair vocabulary file. Creating a default one with sample words.")
                    default_flashcards = [
                        {
                            "german": "Haus",
                            "english": "House",
                            "level": "A1",
                            "category": "Noun",
                            "gender": "Das",
                            "examples": ["Das Haus ist groß."],
                            "box": 1,
                            "favorite": False
                        },
                        {
                            "german": "gehen",
                            "english": "to go",
                            "level": "A1",
                            "category": "Verb",
                            "gender": "",
                            "examples": ["Ich gehe zur Schule."],
                            "box": 1,
                            "favorite": False
                        }
                    ]
                    with open(self.vocab_file, 'w', encoding='utf-8') as f:
                        json.dump(default_flashcards, f, ensure_ascii=False, indent=2)
                    logging.info(f"Created default JSON file with sample words: {self.vocab_file}")
            with open(self.vocab_file, 'r', encoding='utf-8') as f:
                self.flashcards = json.load(f)
            logging.info(f"Loaded flashcards from {self.vocab_file}")
            shutil.copy(self.vocab_file, self.backup_vocab_file)
            logging.info(f"Created backup: {self.backup_vocab_file}")

            # Load stats file
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
                logging.info(f"Loaded stats from {self.stats_file}")
            else:
                with open(self.stats_file, 'w', encoding='utf-8') as f:
                    json.dump(self.stats, f, indent=2)
                logging.info(f"Created new stats file: {self.stats_file}")

            # Load user config file
            if os.path.exists(self.user_config_file):
                with open(self.user_config_file, 'r', encoding='utf-8') as f:
                    self.user_config = json.load(f)
                    self.dark_mode = self.user_config.get('dark_mode', self.dark_mode)
                    self.sound_enabled = self.user_config.get('sound_enabled', self.sound_enabled)
                    self.max_cards = self.user_config.get('max_cards', self.max_cards)
                    self.transition_delay = self.user_config.get('transition_delay', self.transition_delay)
                    self.keyboard_enabled = self.user_config.get('keyboard_enabled', self.keyboard_enabled)
                    self.dark_mode_var.set(self.dark_mode)
                    self.sound_var.set(self.sound_enabled)
                    self.default_cards_var.set(str(self.max_cards))
                    self.transition_delay_var.set(str(self.transition_delay))
                    self.keyboard_enabled_var.set(self.keyboard_enabled)
                logging.info(f"Loaded user config from {self.user_config_file}")
            else:
                with open(self.user_config_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'dark_mode': self.dark_mode,
                        'sound_enabled': self.sound_enabled,
                        'max_cards': self.max_cards,
                        'transition_delay': self.transition_delay,
                        'keyboard_enabled': self.keyboard_enabled
                    }, f, indent=2)
                logging.info(f"Created new user config file: {self.user_config_file}")

            # Standardize flashcards
            allowed_categories = ["Noun", "Verb", "Adjective", "Adverb", "Pronoun", "Preposition", "Conjunction",
                                  "Interjection"]
            allowed_levels = ["A1", "A2", "B1", "B2", "C1"]
            for card in self.flashcards:
                category = card.get('category', '').strip()
                if category:
                    standardized_category = category.title()
                    card['category'] = standardized_category if standardized_category in allowed_categories else ""
                else:
                    card['category'] = ""
                level = card.get('level', '').strip().upper()
                card['level'] = level if level in allowed_levels else ""
                if 'example' in card and 'examples' not in card:
                    card['examples'] = [card['example']] if card['example'] else []
                    del card['example']
                if 'box' not in card:
                    card['box'] = 1
                if 'favorite' not in card:
                    card['favorite'] = False
            self.save_data()
            logging.info("Data standardization complete")
        except Exception as e:
            logging.error(f"Unexpected error in load_data: {str(e)}")
            messagebox.showerror("Error", f"Failed to load data: {str(e)}. Please check the log file.")
            self.flashcards = []

    @staticmethod
    def _validate_level(level: str) -> bool:
        """Validate if the given level is valid."""
        return level.upper() in ['A1', 'A2', 'B1', 'B2', 'C1']

    @staticmethod
    def _validate_category(category: str) -> bool:
        """Validate if the given category is valid."""
        allowed_categories = ["", "Noun", "Verb", "Adjective", "Adverb", "Pronoun", "Preposition", "Conjunction",
                              "Interjection"]
        return category.strip().title() in allowed_categories

    def save_data(self) -> None:
        """Save data immediately without debouncing."""
        self._perform_save()  # Directly call perform_save to ensure immediate saving

    def _perform_save(self) -> None:
        try:
            # Save vocab file to data directory
            with open(self.vocab_file, 'w', encoding='utf-8') as f:
                json.dump(self.flashcards, f, ensure_ascii=False, indent=2)
            shutil.copy(self.vocab_file, self.backup_vocab_file)
            # Save stats and config files
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2)
            with open(self.user_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_config, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")
            messagebox.showerror("Save Error", f"Failed to save data: {str(e)}")

    def setup_ui(self):
        """Set up the main UI elements"""
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Main container
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill="both", expand=True)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.master, textvariable=self.status_var, relief='sunken')
        self.status_bar.pack(side='bottom', fill='x')

        # Setup all frames
        self.setup_menu()
        self.setup_review_frame()
        self.setup_custom_review_frame()
        self.setup_stats_frame()
        self.setup_add_word_frame()
        self.setup_settings_frame()

        # Start with menu
        self.show_menu()

    def apply_theme(self):
        """Apply the current theme with explicit Combobox and Checkbutton styling to prevent reset issues."""
        colors = self.dark_colors if self.dark_mode else self.light_colors

        # Calculate dynamic font sizes
        window_height = self.master.winfo_height()
        window_width = self.master.winfo_width()
        base_size = min(window_height, window_width)
        card_font_size = max(18, int(base_size * 0.08))
        title_font_size = max(16, int(base_size * 0.04))
        stats_font_size = max(10, int(base_size * 0.025))
        example_font_size = 14

        # Configure general styles
        self.master.configure(bg=colors['bg'])
        self.style.configure('.', background=colors['bg'], foreground=colors['fg'])
        self.style.configure('TFrame', background=colors['bg'])
        self.style.configure('TLabel', background=colors['bg'], foreground=colors['fg'])
        self.style.configure('TLabelframe', background=colors['bg'], foreground=colors['fg'])
        self.style.configure('TLabelframe.Label', background=colors['bg'], foreground=colors['fg'])

        # Button styling
        self.style.configure('TButton',
                             background=colors['button_bg'],
                             foreground=colors['fg'],
                             borderwidth=1,
                             relief='solid',
                             font=('Segoe UI', 12),
                             focuscolor='none')
        self.style.map('TButton',
                       background=[('active', colors['button_hover']),
                                   ('pressed', colors['button_hover']),
                                   ('disabled', '#A0A0A0')],
                       foreground=[('active', colors['fg']),
                                   ('pressed', colors['fg']),
                                   ('disabled', '#666666')])

        # No-hover Checkbutton styling with background matching the frame's background
        self.style.configure('NoHover.TCheckbutton',
                             background=colors['bg'],  # Match frame background
                             foreground=colors['fg'],
                             font=('Segoe UI', 12),
                             relief='flat')
        self.style.map('NoHover.TCheckbutton',
                       background=[('active', colors['bg']),  # Keep same background on hover
                                   ('selected', colors['bg']),  # Keep same background when selected
                                   ('disabled', colors['bg'])],  # Keep same background when disabled
                       foreground=[('active', colors['fg']),
                                   ('selected', colors['fg']),
                                   ('disabled', '#666666')])

        # Explicit Combobox styling to prevent reset issues
        self.style.configure('TCombobox',
                             fieldbackground=colors['card_bg'],
                             foreground=colors['fg'],
                             background=colors['bg'],
                             selectbackground=colors['button_hover'],
                             selectforeground=colors['fg'],
                             font=('Segoe UI', 12))
        self.style.map('TCombobox',
                       fieldbackground=[('readonly', colors['card_bg'])],
                       selectbackground=[('readonly', colors['button_hover'])],
                       selectforeground=[('readonly', colors['fg'])])

        # Other widget styles
        self.style.configure('Horizontal.TProgressbar',
                             background=colors['highlight'],
                             troughcolor=colors['bg'],
                             borderwidth=0,
                             thickness=10)
        self.style.configure('Title.TLabel', font=('Segoe UI', title_font_size, 'bold'))
        self.style.configure('Card.TLabel', font=('Segoe UI', card_font_size),
                             background=colors['card_bg'], foreground=colors['fg'])
        self.style.configure('Example.TLabel', font=('Segoe UI', example_font_size, 'italic'),
                             background=colors['card_bg'], foreground=colors['fg'])
        self.style.configure('Stats.TLabel', font=('Segoe UI', max(8, int(stats_font_size * 0.8))),
                             padding=(0, 0, 0, 0))
        self.style.configure('TEntry', fieldbackground=colors['card_bg'])

        # Update existing widgets
        if hasattr(self, 'card_label') and self.card_label:
            self.card_label.configure(background=colors['card_bg'], wraplength=int(window_width * 0.8),
                                      foreground=colors['fg'])
        if hasattr(self, 'example_label') and self.example_label:
            self.example_label.configure(background=colors['card_bg'], wraplength=int(window_width * 0.8),
                                         foreground=colors['fg'])
        if hasattr(self, 'stats_text') and self.stats_text:
            self.stats_text.configure(bg=colors['card_bg'], fg=colors['fg'])
        if hasattr(self, 'progress_bar') and self.progress_bar:
            self.progress_bar.configure(style='Horizontal.TProgressbar')

    def update_fonts_on_resize(self):
        """Update font sizes dynamically with debouncing to prevent frequent calls."""
        import tkinter.font as tkfont

        # Debounce mechanism
        if getattr(self, '_resize_after_id', None):
            self.master.after_cancel(self._resize_after_id)

        def perform_resize():
            # Get window dimensions
            window_height = self.master.winfo_height()
            window_width = self.master.winfo_width()
            base_size = min(window_height, window_width)

            # Base font sizes
            title_font_size = max(16, int(base_size * 0.04))
            stats_font_size = max(10, int(base_size * 0.025))
            example_font_size = 14  # Initial font size for example sentences
            card_font_size = max(18, int(base_size * 0.08))  # Initial font size for flashcards

            # Get current theme colors
            colors = self.dark_colors if self.dark_mode else self.light_colors

            # Update wraplength for labels
            wraplength = int(window_width * 0.8)

            def adjust_font_size(label, initial_font_size, text, max_lines=2):
                """Dynamically adjust font size to fit text within max_lines."""
                if not text or not label.winfo_exists():
                    return initial_font_size

                font_size = initial_font_size
                font = tkfont.Font(family="Segoe UI", size=font_size)
                max_width = wraplength

                # Measure text size and adjust font size to fit within max_lines
                while font_size > 8:  # Minimum font size
                    lines = []
                    current_line = ""
                    words = text.split()
                    for word in words:
                        test_line = current_line + word + " "
                        if font.measure(test_line) <= max_width:
                            current_line = test_line
                        else:
                            lines.append(current_line)
                            current_line = word + " "
                    if current_line:
                        lines.append(current_line)

                    # Check if text fits within max_lines
                    if len(lines) <= max_lines:
                        break
                    font_size -= 1
                    font.configure(size=font_size)

                return font_size

            # Adjust font sizes for card_label and example_label if they exist
            if hasattr(self, 'card_label') and self.card_label and self.card_label.cget("text"):
                card_text = self.card_label.cget("text")
                card_font_size = adjust_font_size(self.card_label, card_font_size, card_text, max_lines=2)

            if hasattr(self, 'example_label') and self.example_label and self.example_label.cget("text"):
                example_text = self.example_label.cget("text")
                example_font_size = adjust_font_size(self.example_label, example_font_size, example_text, max_lines=2)

            # Update styles
            self.style.configure('Title.TLabel', font=('Segoe UI', title_font_size, 'bold'))
            self.style.configure('Card.TLabel', font=('Segoe UI', card_font_size), foreground=colors['fg'])
            self.style.configure('Example.TLabel', font=('Segoe UI', example_font_size, 'italic'),
                                 foreground=colors['fg'])
            self.style.configure('Stats.TLabel', font=('Segoe UI', max(8, int(stats_font_size * 0.8))),
                                 padding=(0, 0, 0, 0))

            # Update wraplength for labels
            if hasattr(self, 'card_label') and self.card_label:
                self.card_label.configure(wraplength=wraplength, foreground=colors['fg'])
            if hasattr(self, 'example_label') and self.example_label:
                self.example_label.configure(wraplength=wraplength, foreground=colors['fg'])

            self._resize_after_id = None  # Reset after_id after resize is complete

        self._resize_after_id = self.master.after(200, perform_resize)

    def setup_menu(self):
        """Set up the main menu with buttons that disable default Return and Space bindings."""
        self.menu_frame = ttk.Frame(self.main_frame)
        self.menu_frame.pack(fill="both", expand=True)
        # Main container for centering content vertically and spanning full width
        main_container = ttk.Frame(self.menu_frame)
        main_container.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0)
        # Title centered with slight top padding
        title_label = ttk.Label(main_container, text="Word Wizard", style='Title.TLabel')
        title_label.pack(pady=(10, 10))
        # Button container
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill="x", pady=(10, 10))
        # Menu buttons
        buttons = [
            ("Review All Cards", self.start_review_session),
            ("Custom Review", self.show_custom_review_options),
            ("Favorites", self.review_favorites),
            ("Difficult Words", self.review_difficult_words),
            ("Add New Word", self.show_add_word_frame),
            ("Statistics", self.show_stats),
            ("Settings", self.show_settings),
            ("Import Vocabulary", self.show_import_dialog),
            ("Export Vocabulary", self.show_export_dialog),
            ("Exit", self.master.quit)
        ]
        for text, command in buttons:
            btn = ttk.Button(button_frame, text=text, command=lambda c=command: [self.play_sound(), c()])
            btn.pack(fill="x", padx=0, pady=5)
            # Disable default Return and Space bindings for the button
            btn.bind('<Return>', lambda event: "break")
            btn.bind('<space>', lambda event: "break")

    def setup_review_frame(self):
        """Set up the review frame with card display filling to the top and progress bar"""
        self.review_frame = ttk.Frame(self.main_frame)

        # Main container with reduced top padding to shift everything up
        main_container = ttk.Frame(self.review_frame)
        main_container.pack(fill="both", expand=True, padx=20, pady=(15, 20))

        # Progress bar and progress label container with increased height
        progress_container = ttk.Frame(main_container, height=33)  # Increased height to prevent clipping
        progress_container.pack(fill="x", side="top")
        progress_container.pack_propagate(False)

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            progress_container,
            orient='horizontal',
            mode='determinate',
            style='Horizontal.TProgressbar',
            maximum=100
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=(10, 5))

        # Progress label (e.g., 1/15) aligned with progress bar
        self.progress_label = ttk.Label(
            progress_container,
            text="0/0",
            style='Stats.TLabel',
            width=8,
            anchor="center",
            font=('Segoe UI', 12),
        )
        self.progress_label.pack(side="right", padx=(0, 10), pady=(2, 10),
                                 anchor="center")  # Fine-tuned pady to ensure visibility

        # Card display container
        card_container = ttk.LabelFrame(
            main_container,
            text="Flashcard",
            padding=0
        )
        card_container.pack(fill="both", expand=True, pady=(20, 10))

        # Card label for displaying the word
        self.card_label = ttk.Label(
            card_container,
            text="",
            anchor="center",
            style='Card.TLabel',
            wraplength=int(self.master.winfo_screenwidth() * 0.8),
            justify="center",
            padding=20
        )
        self.card_label.pack(fill="both", expand=True)

        # Streak celebration label
        self.streak_label = ttk.Label(
            card_container,
            text="",
            anchor="center",
            style='Card.TLabel',
            wraplength=int(self.master.winfo_screenwidth() * 0.8),
            justify="center",
            padding=20
        )

        # Star button for favoriting
        self.star_btn = ttk.Button(
            card_container,
            text="☆",
            command=self.toggle_favorite,
            width=3
        )
        self.star_btn.place(relx=1.0, rely=0.0, anchor="ne", x=0, y=0)

        # Example sentences frame
        example_frame = ttk.LabelFrame(
            main_container,
            text="Example Sentences",
            padding=0,
            height=130
        )
        example_frame.pack(fill="x", pady=(20, 10))
        example_frame.pack_propagate(False)

        # Example label
        self.example_label = ttk.Label(
            example_frame,
            text="Click 'Flip Card' to see the translation and examples",
            anchor="center",
            style='Example.TLabel',
            wraplength=int(self.master.winfo_screenwidth() * 0.8),
            justify="center",
            padding=10
        )
        self.example_label.pack(fill="both", expand=True)

        # Buttons for interaction
        btn_frame = ttk.Frame(main_container)
        btn_frame.pack(side="bottom", pady=(20, 10))

        self.flip_btn = ttk.Button(btn_frame, text="Flip Card",
                                   command=lambda: [self.play_sound(), self.flip_card()])
        self.flip_btn.pack(side="left", padx=10)

        self.correct_btn = ttk.Button(btn_frame, text="Correct",
                                      command=lambda: [self.play_sound(), self.answer_feedback(True)],
                                      state='disabled')
        self.correct_btn.pack(side="left", padx=10)

        self.incorrect_btn = ttk.Button(btn_frame, text="Incorrect",
                                        command=lambda: [self.play_sound(), self.answer_feedback(False)],
                                        state='disabled')
        self.incorrect_btn.pack(side="left", padx=10)

        ttk.Button(btn_frame, text="Back to Menu",
                   command=lambda: [self.play_sound(), self.show_menu()]).pack(side="left", padx=10)

        # Ensure the review frame is focused
        self.review_frame.focus_set()
        self.review_frame.focus_force()

    def show_streak_celebration(self):
        """Show streak celebration message with proper layout preservation and dynamic font sizing."""
        import tkinter.font as tkfont

        if not self.current_card or not self.streak_label:
            print("Error: Missing current_card or streak_label")
            self.show_next_card()
            return

        # Check if streak is a multiple of 10
        if self.correct_streak % 10 != 0 or self.correct_streak == 0:
            print(f"Invalid streak value: {self.correct_streak}. Skipping celebration.")
            self.show_next_card()
            return

        # Define celebration message with random congratulatory word
        streak = self.correct_streak
        congrats_words = [
            "Congratulations", "Outstanding", "Amazing", "Fantastic", "Superb",
            "Excellent", "Brilliant", "Awesome", "Spectacular", "Wonderful"
        ]
        congrats = random.choice(congrats_words)
        message = f"{congrats}! {streak} Correct Answers in a Row! 🚀"

        # Get current theme colors
        colors = self.dark_colors if self.dark_mode else self.light_colors
        streak_bg = colors['streak_bg']

        # Get the card container (LabelFrame)
        card_container = self.card_label.master
        if not isinstance(card_container, ttk.LabelFrame):
            print("Error: card_container is not a ttk.LabelFrame")
            self.show_next_card()
            return

        # Store star button position info before making changes
        star_info = self.star_btn.place_info()

        # Temporarily hide card_label content but keep it packed to maintain layout
        self.card_label.configure(text="")

        # Create temporary celebration frame that overlays the card area
        celebration_frame = ttk.Frame(card_container)
        celebration_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Configure celebration background
        try:
            self.style.configure('Celebration.TFrame', background=streak_bg)
            celebration_frame.configure(style='Celebration.TFrame')
        except tk.TclError:
            # Fallback if style configuration fails
            pass

        # Calculate dynamic font size and wraplength
        window_width = self.master.winfo_width()
        wraplength = int(window_width * 0.8)
        initial_font_size = max(18, int(min(self.master.winfo_height(), window_width) * 0.08))

        def adjust_font_size(text, max_lines=2):
            """Dynamically adjust font size to fit text within max_lines without requiring a label."""
            if not text:
                return initial_font_size

            font_size = initial_font_size
            font = tkfont.Font(family="Segoe UI", size=font_size)
            max_width = wraplength

            while font_size > 8:  # Minimum font size
                lines = []
                current_line = ""
                words = text.split()
                for word in words:
                    test_line = current_line + word + " "
                    if font.measure(test_line) <= max_width:
                        current_line = test_line
                    else:
                        lines.append(current_line)
                        current_line = word + " "
                if current_line:
                    lines.append(current_line)

                if len(lines) <= max_lines:
                    break
                font_size -= 1
                font.configure(size=font_size)

            return font_size

        # Create celebration label with dynamic font size
        celebration_font_size = adjust_font_size(message, max_lines=2)
        celebration_label = ttk.Label(
            celebration_frame,
            text=message,
            foreground=colors['fg'],
            background=streak_bg,
            font=('Segoe UI', celebration_font_size),
            anchor="center",
            justify="center",
            wraplength=wraplength
        )
        celebration_label.pack(fill="both", expand=True)

        # Ensure star button stays in its original position
        if star_info:
            self.star_btn.place(**star_info)
        else:
            self.star_btn.place(relx=1.0, rely=0.0, anchor="ne", x=0, y=0)

        # Apply fade-in effect
        try:
            self._fade_transition(celebration_label, 0.0, 1.0, steps=10, delay=500 // 10)
        except Exception as fade_in_err:
            print(f"Fade-in error: {fade_in_err}")

        # Schedule cleanup and move to next card
        def cleanup():
            try:
                # Remove the celebration overlay
                celebration_frame.destroy()

                # Ensure star button is still properly positioned
                self.star_btn.place(relx=1.0, rely=0.0, anchor="ne", x=0, y=0)

                # Move to next card without restoring previous text
                self.current_card_idx += 1
                self.show_next_card()

            except Exception as restore_err:
                print(f"Restore error: {restore_err}")
                self.current_card_idx += 1
                self.show_next_card()

        # Schedule cleanup after 4 seconds
        self.master.after(4000, cleanup)

    def setup_custom_review_frame(self):
        """Set up custom review options frame with robust Combobox handling and disabled Return/Space bindings."""
        # Clear existing custom_frame to prevent duplicate widgets
        if self.custom_frame:
            for widget in self.custom_frame.winfo_children():
                widget.destroy()
            self.custom_frame.pack_forget()
        else:
            self.custom_frame = ttk.Frame(self.main_frame)
        # Title
        ttk.Label(self.custom_frame, text="Custom Review Options", style='Title.TLabel').pack(pady=20)
        # Number of cards
        ttk.Label(self.custom_frame, text="Number of cards:").pack()
        self.word_count_var = tk.StringVar(value=str(self.max_cards))
        ttk.Entry(self.custom_frame, textvariable=self.word_count_var, font=('Helvetica', 14)).pack(pady=10)
        # Level filter
        ttk.Label(self.custom_frame, text="Select level:").pack()
        self.level_var = tk.StringVar(value="All")
        level_menu = ttk.Combobox(self.custom_frame, textvariable=self.level_var,
                                  values=["All", "A1", "A2", "B1", "B2", "C1"], state="readonly")
        level_menu.pack(pady=5)
        # Ensure selection is preserved
        level_menu.bind('<<ComboboxSelected>>', lambda event: self._preserve_combobox_selection('level'))
        # Category filter
        ttk.Label(self.custom_frame, text="Select category:").pack()
        self.category_var = tk.StringVar(value="All")
        categories = ["All"] + sorted(set(
            card.get('category', '').strip().title() for card in self.flashcards if card.get('category', '').strip()))
        category_menu = ttk.Combobox(self.custom_frame, textvariable=self.category_var, values=categories,
                                     state="readonly")
        category_menu.pack(pady=5)
        # Ensure selection is preserved
        category_menu.bind('<<ComboboxSelected>>', lambda event: self._preserve_combobox_selection('category'))
        # Buttons
        btn_frame = ttk.Frame(self.custom_frame)
        btn_frame.pack(pady=20)
        start_btn = ttk.Button(btn_frame, text="Start Review",
                               command=lambda: [self.play_sound(), self.start_custom_review()])
        start_btn.pack(side="left", padx=10)
        start_btn.bind('<Return>', lambda event: "break")
        start_btn.bind('<space>', lambda event: "break")
        back_btn = ttk.Button(btn_frame, text="Back to Menu", command=lambda: [self.play_sound(), self.show_menu()])
        back_btn.pack(side="left", padx=10)
        back_btn.bind('<Return>', lambda event: "break")
        back_btn.bind('<space>', lambda event: "break")
        # Apply theme after setting up widgets
        self.apply_theme()
        # Pack the custom frame
        self.custom_frame.pack(fill="both", expand=True)

    def _preserve_combobox_selection(self, combobox_type: str):
        """Preserve the selected value in the specified combobox without affecting others."""
        if combobox_type == 'level':
            self.level_var.set(self.level_var.get())
        elif combobox_type == 'category':
            self.category_var.set(self.category_var.get())
        self.custom_frame.focus_set()

    def setup_stats_frame(self):
        # Clear existing stats_frame to prevent duplicate widgets
        if self.stats_frame:
            for widget in self.stats_frame.winfo_children():
                widget.destroy()
            self.stats_frame.pack_forget()
        else:
            self.stats_frame = ttk.Frame(self.main_frame)
        # Title
        ttk.Label(self.stats_frame, text="Your Statistics", style='Title.TLabel').pack(pady=0)
        # Stats container
        stats_container = ttk.Frame(self.stats_frame)
        stats_container.pack(pady=0, padx=20, fill="both")
        # Configure all rows to have minimum height
        for i in range(20):  # Configure enough rows
            stats_container.grid_rowconfigure(i, minsize=0, weight=0)
        # Configure columns to minimize spacing
        stats_container.grid_columnconfigure(0, weight=0, minsize=0)
        stats_container.grid_columnconfigure(1, weight=1, minsize=0)
        # General statistics
        ttk.Label(stats_container, text="General Statistics", style='Title.TLabel').grid(row=0, column=0, columnspan=2,
                                                                                         sticky="w")
        labels = [
            ("Total Reviews:", "total_reviews"),
            ("Correct:", "correct"),
            ("Incorrect:", "incorrect"),
            ("Accuracy:", "accuracy"),
            ("Streak:", "streak")
        ]
        self.stats_labels = {}
        for i, (text, key) in enumerate(labels, 1):
            # Combine label and value in single label to eliminate column spacing
            combined_label = ttk.Label(stats_container, text=f"{text} 0", style='Stats.TLabel')
            combined_label.grid(row=i, column=0, columnspan=2, sticky="w", padx=0, pady=0, ipady=0)
            self.stats_labels[key] = combined_label
        # Statistics by level
        ttk.Label(stats_container, text="By Level", style='Title.TLabel').grid(row=len(labels) + 1, column=0,
                                                                               columnspan=2, sticky="w")
        self.level_stats_labels = {}
        for i, level in enumerate(['A1', 'A2', 'B1', 'B2', 'C1'], len(labels) + 2):
            # Combine level and value in single label to eliminate column spacing
            combined_label = ttk.Label(stats_container, text=f"{level}: 0% (0/0)", style='Stats.TLabel')
            combined_label.grid(row=i, column=0, columnspan=2, sticky="w", padx=0, pady=0, ipady=0)
            self.level_stats_labels[level] = combined_label
        # Difficult words Combobox
        ttk.Label(stats_container, text="Difficult Words", style='Title.TLabel').grid(row=len(labels) + 7, column=0,
                                                                                      columnspan=2, sticky="w")
        difficult_words_menu = ttk.Combobox(stats_container, textvariable=self.stats_var, state="readonly")
        difficult_words_menu.grid(row=len(labels) + 8, column=0, columnspan=2, sticky="we", padx=5, pady=5)
        difficult_words = self.stats.get('difficult_words', {})
        if difficult_words:
            sorted_words = sorted(difficult_words.items(), key=lambda x: x[1], reverse=True)
            word_list = [f"{word} ({count})" for word, count in sorted_words]
            difficult_words_menu['values'] = word_list
            self.stats_var.set(f"Difficult Words ({len(sorted_words)} Unique Words)")
        else:
            difficult_words_menu['values'] = ["No difficult words yet"]
            self.stats_var.set("No difficult words yet")
        # Show Chart button
        chart_btn = ttk.Button(self.stats_frame, text="Show Statistics Chart",
                               command=lambda: [self.play_sound(), self.show_stats_chart()])
        chart_btn.pack(pady=(10, 5))
        chart_btn.bind('<Return>', lambda event: "break")
        chart_btn.bind('<space>', lambda event: "break")
        # Back button
        back_btn = ttk.Button(self.stats_frame, text="Back to Menu",
                              command=lambda: [self.play_sound(), self.show_menu()])
        back_btn.pack(pady=(5, 10))
        back_btn.bind('<Return>', lambda event: "break")
        back_btn.bind('<space>', lambda event: "break")

    def setup_add_word_frame(self):
        """Set up frame for adding new words with Combobox for gender, category, and level, and entry fields for others."""
        self.add_word_frame = ttk.Frame(self.main_frame)
        # Title
        ttk.Label(self.add_word_frame, text="Add New Word", style='Title.TLabel').pack(pady=20)
        # Form fields
        fields = [
            ("German Word:", "german"),
            ("English Translation:", "english"),
            ("Level (A1, A2, B1, B2, C1):", "level"),
            ("Category (Noun, Verb, etc.):", "category"),
            ("Gender (None, Der, Die, Das):", "gender"),
            ("Example Sentence 1:", "example1"),
            ("Example Sentence 2:", "example2"),
        ]
        self.entry_vars = {}
        for label_text, field_name in fields:
            frame = ttk.Frame(self.add_word_frame)
            frame.pack(fill="x", padx=20, pady=5)
            ttk.Label(frame, text=label_text).pack(side="left")
            if field_name == "gender":
                var = tk.StringVar()
                gender_menu = ttk.Combobox(frame, textvariable=var, values=["", "Der", "Die", "Das"], state="readonly")
                gender_menu.pack(side="right", expand=True, fill="x")
                self.entry_vars[field_name] = var
            elif field_name == "category":
                var = tk.StringVar()
                category_menu = ttk.Combobox(frame, textvariable=var,
                                             values=["Noun", "Verb", "Adjective", "Adverb", "Pronoun",
                                                     "Preposition", "Conjunction", "Interjection"], state="readonly")
                category_menu.pack(side="right", expand=True, fill="x")
                self.entry_vars[field_name] = var
            elif field_name == "level":
                var = tk.StringVar()
                level_menu = ttk.Combobox(frame, textvariable=var, values=["A1", "A2", "B1", "B2", "C1"],
                                          state="readonly")
                level_menu.pack(side="right", expand=True, fill="x")
                self.entry_vars[field_name] = var
            else:
                var = tk.StringVar()
                entry = ttk.Entry(frame, textvariable=var)
                entry.pack(side="right", expand=True, fill="x")
                self.entry_vars[field_name] = var
        # Buttons
        btn_frame = ttk.Frame(self.add_word_frame)
        btn_frame.pack(pady=20)
        add_btn = ttk.Button(btn_frame, text="Add Word", command=lambda: [self.play_sound(), self.add_new_word()])
        add_btn.pack(side="left", padx=10)
        add_btn.bind('<Return>', lambda event: "break")
        add_btn.bind('<space>', lambda event: "break")
        back_btn = ttk.Button(btn_frame, text="Back to Menu", command=lambda: [self.play_sound(), self.show_menu()])
        back_btn.pack(side="left", padx=10)
        back_btn.bind('<Return>', lambda event: "break")
        back_btn.bind('<space>', lambda event: "break")

    def setup_settings_frame(self):
        """Set up settings frame with a slider for transition delay, keyboard navigation toggle, and disabled Return/Space bindings."""
        # Clear existing widgets in settings_frame to prevent duplicates
        if hasattr(self, 'settings_frame') and self.settings_frame:
            for widget in self.settings_frame.winfo_children():
                widget.destroy()
            self.settings_frame.pack_forget()
        else:
            self.settings_frame = ttk.Frame(self.main_frame)

        # Apply theme to ensure styles are up to date
        self.apply_theme()

        # Title
        ttk.Label(self.settings_frame, text="Settings", style='Title.TLabel').pack(pady=20)
        # Dark mode toggle
        self.dark_mode_var = tk.BooleanVar(value=self.dark_mode)
        dark_mode_check = ttk.Checkbutton(self.settings_frame, text="Dark Mode", variable=self.dark_mode_var,
                                          command=self.toggle_dark_mode, style='NoHover.TCheckbutton')
        dark_mode_check.pack(pady=5, anchor='w', padx=20)
        # Sound toggle
        self.sound_var = tk.BooleanVar(value=self.sound_enabled)
        sound_check = ttk.Checkbutton(self.settings_frame, text="Enable Sounds", variable=self.sound_var,
                                      command=self.toggle_sound, style='NoHover.TCheckbutton')
        sound_check.pack(pady=5, anchor='w', padx=20)
        # Keyboard navigation toggle
        self.keyboard_enabled_var = tk.BooleanVar(value=self.keyboard_enabled)
        keyboard_check = ttk.Checkbutton(self.settings_frame,
                                         text="Enable Keyboard Navigation (Up: Flip, Left: Correct, Right: incorrect, Down: Back)",
                                         variable=self.keyboard_enabled_var, command=self.toggle_keyboard_navigation,
                                         style='NoHover.TCheckbutton')
        keyboard_check.pack(pady=5, anchor='w', padx=20)
        # Default card count
        frame = ttk.Frame(self.settings_frame)
        frame.pack(fill="x", padx=20, pady=5)
        ttk.Label(frame, text="Default number of cards:").pack(side="left")
        self.default_cards_var = tk.StringVar(value=str(self.max_cards))
        ttk.Entry(frame, textvariable=self.default_cards_var, width=5).pack(side="left", padx=5)
        # Card transition delay slider
        frame = ttk.Frame(self.settings_frame)
        frame.pack(fill="x", padx=20, pady=5)
        ttk.Label(frame, text="Card transition delay (ms):").pack(side="left")
        self.transition_delay_var = tk.StringVar(value=str(self.transition_delay))

        def update_slider_value(value):
            """Ensure slider value is an integer."""
            self.transition_delay_var.set(str(int(float(value))))

        slider = ttk.Scale(frame, from_=400, to=1200, orient="horizontal", variable=self.transition_delay_var,
                           length=200, command=update_slider_value)
        slider.pack(side="left", padx=5)
        ttk.Label(frame, textvariable=self.transition_delay_var).pack(side="left", padx=5)  # Display current value
        # Buttons
        frame = ttk.Frame(self.settings_frame)
        frame.pack(pady=20)
        save_btn = ttk.Button(frame, text="Save Settings", command=lambda: [self.play_sound(), self.save_settings()])
        save_btn.pack(side="left", padx=10)
        save_btn.bind('<Return>', lambda event: "break")
        save_btn.bind('<space>', lambda event: "break")
        back_btn = ttk.Button(frame, text="Back to Menu", command=lambda: [self.play_sound(), self.show_menu()])
        back_btn.pack(side="left", padx=10)
        back_btn.bind('<Return>', lambda event: "break")
        back_btn.bind('<space>', lambda event: "break")
        # Pack the settings frame
        self.settings_frame.pack(fill="both", expand=True)

    def play_sound(self):
        if not self.sound_enabled:
            print("Sound disabled: Skipping click sound playback.")
            return
        try:
            sound_file = os.path.join(self.sounds_dir, "click.wav")
            if not os.path.exists(sound_file):
                print(f"Click sound file not found: {sound_file}")
                messagebox.showwarning("Sound Error",
                                       f"Click sound file not found. Please ensure the application is installed correctly.")
                self.sound_enabled = False
                return
            sound = pygame.mixer.Sound(sound_file)
            sound.set_volume(1.0)
            channel = sound.play()
            if channel is None:
                print("No available channel for click sound playback.")
                messagebox.showwarning("Sound Error", "No available audio channel for click sound.")
        except pygame.error as e:
            print(f"Click sound playback error: {e}")
            messagebox.showwarning("Sound Error", f"Failed to play click sound: {str(e)}")
            self.sound_enabled = False

    # Play feedback sound for correct/incorrect answers
    def play_feedback_sound(self, correct: bool) -> None:
        if not self.sound_enabled:
            print("Sound disabled: Skipping feedback sound playback.")
            return
        try:
            sound_file = os.path.join(self.sounds_dir, "correct.wav" if correct else "incorrect.wav")
            if not os.path.exists(sound_file):
                print(f"Feedback sound file not found: {sound_file}")
                messagebox.showwarning("Sound Error",
                                       f"Feedback sound file not found. Please ensure the application is installed correctly.")
                self.sound_enabled = False
                return
            sound = pygame.mixer.Sound(sound_file)
            sound.set_volume(1.0)
            channel = sound.play()
            if channel is None:
                print("No available channel for feedback sound playback.")
                messagebox.showwarning("Sound Error", "No available audio channel for feedback sound.")
        except pygame.error as e:
            print(f"Feedback sound playback error: {e}")
            messagebox.showwarning("Sound Error", f"Failed to play feedback sound: {str(e)}")
            self.sound_enabled = False

    # Play streak sound with enhanced diagnostics
    def play_streak_sound(self):
        if not self.sound_enabled:
            print("Sound disabled: Skipping streak sound playback.")
            return
        try:
            sound_file = os.path.join(self.sounds_dir, "streak.wav")
            if not os.path.exists(sound_file):
                print(f"Streak sound file not found: {sound_file}")
                messagebox.showwarning("Sound Error",
                                       f"Streak sound file not found. Please ensure the application is installed correctly.")
                self.sound_enabled = False
                return
            sound = pygame.mixer.Sound(sound_file)
            sound.set_volume(1.0)
            channel = sound.play()
            if channel is None:
                print("No available channel for streak sound playback.")
                messagebox.showwarning("Sound Error", "No available audio channel for streak sound.")

                def fade_out(step=10, delay=2000 // 10):
                    try:
                        if step <= 0:
                            sound.set_volume(0.0)
                            sound.stop()
                            return
                        current_volume = sound.get_volume()
                        sound.set_volume(max(0.0, current_volume - 0.1))
                        self.master.after(delay, lambda: fade_out(step - 1, delay))
                    except pygame.error as fade_err:
                        print(f"Fade-out error: {fade_err}")
                        messagebox.showwarning("Sound Error", f"Error during streak sound fade-out: {str(fade_err)}")

                self.master.after(3000, lambda: fade_out(10))
        except pygame.error as e:
            print(f"Streak sound playback error: {e}")
            messagebox.showwarning("Sound Error", f"Failed to play streak sound: {str(e)}")
            self.sound_enabled = False

    def hide_all_frames(self):
        # Hide all frames
        for frame in [self.menu_frame, self.review_frame, self.custom_frame,
                      self.stats_frame, self.add_word_frame, self.settings_frame]:
            if frame:
                frame.pack_forget()

    # Değiştirilecek: start_review_session fonksiyonu
    def start_review_session(self, level=None, category=None):
        """Start a review session for all cards or filtered by level/category"""
        self.correct_streak = 0
        self.session_start_time = datetime.now()
        self.review_cards = self.flashcards.copy()

        if level and level != "All":
            if not self._validate_level(level):
                messagebox.showinfo("Invalid Level",
                                    f"Level '{level}' is not valid. Available levels: A1, A2, B1, B2, C1")
                return
            available_levels = sorted(set(card.get('level', '') for card in self.flashcards if card.get('level')))
            if level not in available_levels:
                messagebox.showinfo("No Cards Available",
                                    f"No {level}-level cards available.\nAvailable levels: {', '.join(available_levels) if available_levels else 'None'}")
                return
            self.review_cards = [card for card in self.review_cards if card.get('level', '').upper() == level]

        if category and category != "All":
            if not self._validate_category(category):
                messagebox.showinfo("Invalid Category",
                                    f"Category '{category}' is not valid. Available categories: Noun, Verb, Adjective, Adverb, Pronoun, Preposition, Conjunction, Interjection")
                return
            available_categories = sorted(
                set(card.get('category', '') for card in self.flashcards if card.get('category')))
            if category not in available_categories:
                messagebox.showinfo("No Cards Available",
                                    f"No cards in '{category}' category.\nAvailable categories: {', '.join(available_categories) if available_categories else 'None'}")
                return
            self.review_cards = [card for card in self.review_cards if card.get('category', '').title() == category]

        if not self.review_cards:
            available_levels = sorted(set(card.get('level', '') for card in self.flashcards if card.get('level')))
            available_categories = sorted(
                set(card.get('category', '') for card in self.flashcards if card.get('category')))
            messagebox.showinfo("No Cards",
                                f"No cards available for Level: {level or 'All'}, Category: {category or 'All'}\n"
                                f"Available levels: {', '.join(available_levels) if available_levels else 'None'}\n"
                                f"Available categories: {', '.join(available_categories) if available_categories else 'None'}")
            return

        weights = [1 / (card.get('box', 1)) for card in self.review_cards]
        self.review_cards = random.choices(self.review_cards, weights=weights, k=len(self.review_cards))
        self.current_card_idx = 0
        self.hide_all_frames()
        self.review_frame.pack(fill="both", expand=True)

        # Update status with levels and categories
        levels = sorted(set(card.get('level', '') for card in self.review_cards if card.get('level')))
        categories = sorted(set(card.get('category', '') for card in self.review_cards if card.get('category')))
        levels_text = "All levels" if len(levels) >= 5 else ', '.join(levels) if levels else "No levels"
        categories_text = "All categories" if len(categories) >= 8 else ', '.join(
            categories) if categories else "No categories"
        self.update_status(f"Reviewing {len(self.review_cards)} cards ({levels_text}) ({categories_text})")

        # Show the first card and ensure keyboard bindings are applied
        self.show_next_card()
        self.master.after(100, self.bind_keyboard_events)

    def show_next_card(self):
        """Show the next card in the review session with fade transition effect for non-first cards."""
        if self.current_card_idx >= len(self.review_cards):
            self.end_review_session()
            return

        self.current_card = self.review_cards[self.current_card_idx]
        self.card_front = True
        self.feedback_given = False  # Reset feedback flag for new card
        display_text = self._capitalize_german_word(self.current_card['german'])
        is_favorite = self.current_card.get('favorite', False)

        # Get current theme colors
        colors = self.dark_colors if self.dark_mode else self.light_colors

        def update_card():
            # Update card label with dynamic font from style and reset color
            self.card_label.config(text=display_text, style='Card.TLabel', foreground=colors['fg'])

            # Update star button
            self.star_btn.config(text="★" if is_favorite else "☆")

            # Update example label with static font from style and reset color
            self.example_label.config(text="",
                                      background=colors['bg'],
                                      style='Example.TLabel',
                                      foreground=colors['fg'])

            self.correct_btn.config(state='disabled')
            self.incorrect_btn.config(state='disabled')

            # Update progress bar and progress label
            if self.progress_bar:
                progress = (self.current_card_idx / len(self.review_cards)) * 100
                self.progress_bar['value'] = progress
            if self.progress_label:
                self.progress_label.config(text=f"{self.current_card_idx + 1}/{len(self.review_cards)}")

            # Apply fade-in effect only for non-first cards
            if self.current_card_idx > 0:
                self._fade_transition(self.card_label, 0.0, 1.0, steps=10, delay=self.transition_delay // 2)

            # Ensure the review frame is focused and keyboard bindings are active
            self.master.after(100, lambda: self.review_frame.focus_set())
            self.master.after(100, lambda: self.review_frame.focus_force())
            self.master.after(100, self.bind_keyboard_events)

        # Apply fade-out effect only for non-first cards
        if self.current_card_idx > 0:
            self._fade_transition(self.card_label, 1.0, 0.0, steps=10, delay=self.transition_delay // 2)
            self.master.after(self.transition_delay // 2, update_card)
        else:
            update_card()

    def end_review_session(self):
        # End the review session and return to main menu
        self.review_cards = []
        self.current_card_idx = 0
        self.hide_all_frames()
        self.show_menu()
        self.update_status("Welcome to Word Wizard")

    def _fade_transition(self, widget, start_ratio, end_ratio, steps=10, delay=50):
        """Apply a fade transition effect by interpolating between foreground and background colors."""
        # Cancel any existing fade transition
        if self._fade_after_id:
            self.master.after_cancel(self._fade_after_id)
            self._fade_after_id = None

        step_size = (end_ratio - start_ratio) / steps
        current_ratio = start_ratio
        colors = self.dark_colors if self.dark_mode else self.light_colors
        fg = colors['fg']
        bg = colors['bg']

        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        def rgb_to_hex(rgb):
            return f'#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}'

        fg_rgb = hex_to_rgb(fg)
        bg_rgb = hex_to_rgb(bg)

        def update_color():
            nonlocal current_ratio
            if abs(current_ratio - end_ratio) < abs(step_size):
                current_ratio = end_ratio
                widget.config(foreground=fg if end_ratio == 1.0 else bg)
                self._fade_after_id = None
                return
            blended_rgb = [
                bg_rgb[i] + (fg_rgb[i] - bg_rgb[i]) * current_ratio
                for i in range(3)
            ]
            new_color = rgb_to_hex(blended_rgb)
            widget.config(foreground=new_color)
            current_ratio += step_size
            self._fade_after_id = self.master.after(delay // steps, update_color)

        update_color()

    def flip_card(self):
        """Flip the card with proper capitalization and fade transition effect.
        Allow toggling between German and English until feedback is given.
        """
        if self.feedback_given:
            return  # Prevent flipping after feedback is given

        self.card_front = not self.card_front

        # Cancel any ongoing fade transition
        if self._fade_after_id:
            self.master.after_cancel(self._fade_after_id)
            self._fade_after_id = None

        # Apply fade-out effect before changing text
        self._fade_transition(self.card_label, 1.0, 0.0, steps=10, delay=self.transition_delay // 2)

        def update_card():
            colors = self.dark_colors if self.dark_mode else self.light_colors
            if self.card_front:
                # Show German side with proper capitalization
                display_text = self._capitalize_german_word(self.current_card['german'])
                self.card_label.config(text=display_text, foreground=colors['fg'])
                self.example_label.config(text="",
                                          background=colors['bg'],
                                          foreground=colors['fg'])
            else:
                # Show English side with proper capitalization and spacing for slashes
                english_text = self.current_card['english']
                if '/' in english_text:
                    words = english_text.split('/')
                    capitalized_english = ' / '.join(word.strip().capitalize() for word in words)
                else:
                    capitalized_english = ' '.join(word.capitalize() for word in english_text.split())
                self.card_label.config(text=capitalized_english, foreground=colors['fg'])
                if 'examples' in self.current_card:
                    examples_text = "\n".join(f"• {ex}" for ex in self.current_card['examples'])
                    self.example_label.config(text=examples_text,
                                              background=colors['card_bg'],
                                              foreground=colors['fg'])
                elif 'example' in self.current_card:
                    self.example_label.config(text=self.current_card['example'],
                                              background=colors['card_bg'],
                                              foreground=colors['fg'])

            # Apply fade-in effect after changing text
            self._fade_transition(self.card_label, 0.0, 1.0, steps=10, delay=self.transition_delay // 2)

            # Update button states
            self.correct_btn.config(state='normal' if not self.card_front else 'disabled')
            self.incorrect_btn.config(state='normal' if not self.card_front else 'disabled')

            # Rebind keyboard events to ensure correct behavior
            self.bind_keyboard_events()

        # Schedule text update after fade-out
        self.master.after(self.transition_delay // 2, update_card)

    @staticmethod
    def _capitalize_german_word(word: str) -> str:
        """Capitalize German word, handling articles (der, die, das) correctly"""
        articles = ['der', 'die', 'das']
        words = word.strip().split(maxsplit=1)  # Split only on first space
        if len(words) == 2 and words[0].lower() in articles:
            # If word starts with an article, capitalize both article and main word
            return f"{words[0].capitalize()} {words[1].capitalize()}"
        # Otherwise, capitalize only the first word
        return word.capitalize()

    def answer_feedback(self, correct: bool):
        """Handle feedback for correct/incorrect answers, allowing only one feedback per card."""
        if not self.current_card or self.feedback_given:
            return

        self.feedback_given = True
        colors = self.dark_colors if self.dark_mode else self.light_colors

        # Cancel any ongoing fade transition
        if self._fade_after_id:
            self.master.after_cancel(self._fade_after_id)
            self._fade_after_id = None

        # Update card appearance and play feedback sound
        if correct:
            self.card_label.config(foreground=colors['highlight'])
            try:
                self.play_feedback_sound(True)
            except Exception as e:
                print(f"Feedback sound error in answer_feedback: {e}")
            self.stats['correct'] += 1
            self.correct_streak += 1
            level = self.current_card.get('level')
            if level:
                if level not in self.stats['by_level']:
                    self.stats['by_level'][level] = {'correct': 0, 'incorrect': 0}
                self.stats['by_level'][level]['correct'] += 1
            category = self.current_card.get('category')
            if category:
                if category not in self.stats['by_category']:
                    self.stats['by_category'][category] = {'correct': 0, 'incorrect': 0}
                self.stats['by_category'][category]['correct'] += 1
        else:
            self.card_label.config(foreground=colors['incorrect'])
            try:
                self.play_feedback_sound(False)
            except Exception as e:
                print(f"Feedback sound error in answer_feedback: {e}")
            self.stats['incorrect'] += 1
            self.correct_streak = 0
            level = self.current_card.get('level')
            if level:
                if level not in self.stats['by_level']:
                    self.stats['by_level'][level] = {'correct': 0, 'incorrect': 0}
                self.stats['by_level'][level]['incorrect'] += 1
            category = self.current_card.get('category')
            if category:
                if category not in self.stats['by_category']:
                    self.stats['by_category'][category] = {'correct': 0, 'incorrect': 0}
                self.stats['by_category'][category]['incorrect'] += 1

            german_word = self.current_card.get('german')
            if german_word:
                if german_word not in self.stats['difficult_words']:
                    self.stats['difficult_words'][german_word] = 0
                self.stats['difficult_words'][german_word] += 1

        # Update daily streak
        today = datetime.now().date()
        last_review_date = self.stats.get('last_review_date')

        if last_review_date:
            if isinstance(last_review_date, str):
                last_date = datetime.fromisoformat(last_review_date).date()
            else:
                last_date = last_review_date

            if today == last_date + timedelta(days=1):
                self.stats['streak'] += 1
            elif today > last_date + timedelta(days=1):
                self.stats['streak'] = 1
        else:
            self.stats['streak'] = 1

        self.stats['last_review_date'] = today.isoformat()
        self.stats['total_reviews'] += 1

        # Update Leitner box
        if correct:
            self.current_card['box'] = min(self.current_card.get('box', 1) + 1, 5)
        else:
            self.current_card['box'] = max(self.current_card.get('box', 1) - 1, 1)

        self.save_data()

        # Check for streak milestones
        if correct and self.correct_streak % 10 == 0:
            self.play_streak_sound()
            # Delay the streak celebration to show the green highlight
            self.master.after(1000, self.show_streak_celebration)
        else:
            # Disable buttons immediately to prevent further clicks
            self.correct_btn.config(state='disabled')
            self.incorrect_btn.config(state='disabled')

            # Move to next card after delay
            self.current_card_idx += 1
            self.master.after(self.transition_delay, self.show_next_card)

    def show_custom_review_options(self):
        """Show custom review options screen"""
        self.hide_all_frames()
        self.custom_frame.pack(fill="both", expand=True)
        self.update_status("Customize your review session")

    def setup_custom_frame(self):
        """Set up the custom review frame with level, category, and card count selection"""
        self.custom_frame = ttk.Frame(self.main_frame)
        self.custom_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        ttk.Label(self.custom_frame, text="Custom Review", style='Title.TLabel').pack(pady=10)

        # Level selection
        ttk.Label(self.custom_frame, text="Select Level:").pack(anchor="w")
        levels = ["All", "A1", "A2", "B1", "B2", "C1", "C2"]
        ttk.Combobox(self.custom_frame, textvariable=self.level_var, values=levels, state="readonly").pack(fill="x",
                                                                                                           pady=5)

        # Category selection
        ttk.Label(self.custom_frame, text="Select Category:").pack(anchor="w")
        categories = ["All"] + sorted(set(card.get('category', 'Unknown') for card in self.flashcards))
        ttk.Combobox(self.custom_frame, textvariable=self.category_var, values=categories, state="readonly").pack(
            fill="x", pady=5)

        # Card count selection
        ttk.Label(self.custom_frame, text="Select Number of Cards:").pack(anchor="w")
        card_counts = ["10", "20", "50", "100"]
        ttk.Combobox(self.custom_frame, textvariable=self.default_cards_var, values=card_counts, state="readonly").pack(
            fill="x", pady=5)

        # Start and back buttons
        btn_frame = ttk.Frame(self.custom_frame)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Start Review",
                   command=lambda: [self.play_sound(), self.start_custom_review()]).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Back to Menu", command=lambda: [self.play_sound(), self.show_menu()]).pack(
            side="left", padx=10)

    def start_custom_review(self):
        """Start a custom review session based on selected level, category, and card count"""
        self.correct_streak = 0
        selected_level = self.level_var.get()
        selected_category = self.category_var.get()
        try:
            max_cards = int(self.word_count_var.get())
            if max_cards <= 0:
                raise ValueError("Number of cards must be positive")
        except ValueError:
            max_cards = self.max_cards
            self.word_count_var.set(str(self.max_cards))  # Reset to default if invalid

        # Filter cards based on level and category
        filtered_cards = self.flashcards.copy()
        if selected_level and selected_level != "All":
            filtered_cards = [card for card in filtered_cards if card.get('level') == selected_level]
        if selected_category and selected_category != "All":
            filtered_cards = [card for card in filtered_cards if card.get('category') == selected_category]

        # Ensure we don't exceed available cards
        if not filtered_cards:
            messagebox.showinfo("No Cards", "No cards available for the selected level or category.")
            return

        # Select exactly max_cards unique cards
        try:
            self.review_cards = random.sample(filtered_cards, k=min(max_cards, len(filtered_cards)))
            # Sort selected cards by Leitner box to prioritize lower-box cards
            self.review_cards.sort(key=lambda card: card.get('box', 1))
        except ValueError as e:
            messagebox.showerror("Error", f"Failed to select cards: {str(e)}")
            return

        self.current_card_idx = 0
        self.session_start_time = datetime.now()

        # Update status with levels and categories
        levels = sorted(set(card.get('level', '') for card in self.review_cards if card.get('level')))
        categories = sorted(set(card.get('category', '') for card in self.review_cards if card.get('category')))
        levels_text = "All levels" if len(levels) >= 5 else ', '.join(levels) if levels else "No levels"
        categories_text = "All categories" if len(categories) >= 8 else ', '.join(
            categories) if categories else "No categories"
        self.update_status(f"Reviewing {len(self.review_cards)} cards ({levels_text}) ({categories_text})")

        self.hide_all_frames()
        self.review_frame.pack(fill="both", expand=True)
        self.show_next_card()

    def review_difficult_words(self):
        """Review words marked as difficult"""
        if not self.stats['difficult_words']:
            messagebox.showinfo("No Difficult Words", "You haven't marked any words as difficult yet.")
            return

        difficult_words = [word for word in self.stats['difficult_words'].keys()]

        self.review_cards = [card for card in self.flashcards if card['german'] in difficult_words]

        if not self.review_cards:
            messagebox.showinfo("No Cards", "No cards available for review.")
            return

        random.shuffle(self.review_cards)
        self.current_card_idx = 0
        self.max_cards = len(self.review_cards)
        self.show_next_card()
        self.hide_all_frames()
        self.review_frame.pack(fill="both", expand=True)
        self.update_status(f"Reviewing {len(self.review_cards)} difficult words")

    def show_stats(self):
        """Show statistics screen"""
        self.hide_all_frames()

        # Recreate stats frame completely to prevent duplicates
        self.setup_stats_frame()

        self.stats_frame.pack(fill="both", expand=True)
        self.update_status("Viewing statistics")

        # Calculate accuracy
        total = self.stats['correct'] + self.stats['incorrect']
        accuracy = (self.stats['correct'] / total * 100) if total > 0 else 0

        # Update general stats - now combined in single labels
        self.stats_labels['total_reviews'].config(text=f"Total Reviews: {self.stats['total_reviews']}")
        self.stats_labels['correct'].config(text=f"Correct: {self.stats['correct']}")
        self.stats_labels['incorrect'].config(text=f"Incorrect: {self.stats['incorrect']}")
        self.stats_labels['accuracy'].config(text=f"Accuracy: {accuracy:.1f}%")
        self.stats_labels['streak'].config(text=f"Streak: {self.stats.get('streak', 0)} day")

        # Update level stats - now combined in single label
        for level in ['A1', 'A2', 'B1', 'B2', 'C1']:
            if level in self.stats['by_level']:
                correct = self.stats['by_level'][level]['correct']
                incorrect = self.stats['by_level'][level]['incorrect']
                total = correct + incorrect
                level_acc = (correct / total * 100) if total > 0 else 0
                self.level_stats_labels[level].config(text=f"{level}: {level_acc:.1f}% ({correct}/{total})")
            else:
                self.level_stats_labels[level].config(text=f"{level}: 0% (0/0)")

    def show_stats_chart(self):
        """Show a bar chart of accuracy by level"""
        import matplotlib.pyplot as plt

        # Calculate accuracy by level
        levels = ['A1', 'A2', 'B1', 'B2', 'C1']
        accuracies = []
        for level in levels:
            if level in self.stats['by_level']:
                correct = self.stats['by_level'][level]['correct']
                incorrect = self.stats['by_level'][level]['incorrect']
                total = correct + incorrect
                accuracy = (correct / total * 100) if total > 0 else 0
                accuracies.append(accuracy)
            else:
                accuracies.append(0)

        # Create bar chart
        plt.figure(figsize=(8, 4))
        plt.bar(levels, accuracies, color=['#4CAF50', '#81C784', '#FFB300', '#FF5722', '#0288D1'])
        plt.title('Accuracy by Level (%)')
        plt.xlabel('Level')
        plt.ylabel('Accuracy (%)')
        plt.ylim(0, 100)
        plt.show()

    def show_add_word_frame(self):
        self.hide_all_frames()
        self.add_word_frame.pack(fill="both", expand=True)
        self.update_status("Add new vocabulary")

        # Clear all entry fields
        for var in self.entry_vars.values():
            var.set("")

    def add_new_word(self) -> None:
        """Add a new word to the flashcards and verify file save."""
        new_word = {field: var.get().strip() for field, var in self.entry_vars.items()}
        errors = []
        examples = []

        if not new_word['german']:
            errors.append("German word is required.")
        if not new_word['english']:
            errors.append("English translation is required.")
        if not new_word['level']:
            errors.append("Level (A1, A2, B1, B2, C1) is required.")
        elif not WordWizardApp._validate_level(new_word['level']):
            errors.append("Level must be A1, A2, B1, B2, or C1.")
        if new_word['german'] in [card['german'] for card in self.flashcards]:
            errors.append("This German word already exists.")
        if new_word['category'] and not WordWizardApp._validate_category(new_word['category']):
            errors.append(
                "Category must be Noun, Verb, Adjective, Adverb, Pronoun, Preposition, Conjunction, Interjection, or empty.")

        # Collect example sentences
        for field in ['example1', 'example2']:
            if new_word[field]:
                if len(new_word[field]) > 200:
                    errors.append(f"Example sentence '{field}' must be under 200 characters.")
                else:
                    examples.append(new_word[field])

        if errors:
            messagebox.showerror("Error", "\n".join(errors))
            return

        new_word['examples'] = examples
        new_word['box'] = 1
        # Remove temporary example fields from new_word
        del new_word['example1']
        del new_word['example2']
        self.flashcards.append(new_word)
        self.save_data()

        # Verify the word was saved to the file
        try:
            with open(self.vocab_file, 'r', encoding='utf-8') as f:
                saved_flashcards = json.load(f)
            if any(card['german'] == new_word['german'] for card in saved_flashcards):
                messagebox.showinfo("Success", f"New word added: {new_word['german']}")
            else:
                messagebox.showerror("Error", f"Word {new_word['german']} was not saved to file.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to verify saved word: {str(e)}")

        self.show_menu()

    def show_settings(self):
        """Show settings screen"""
        self.hide_all_frames()
        self.settings_frame.pack(fill="both", expand=True)
        self.update_status("Adjust application settings")

    def toggle_dark_mode(self):
        """Toggle dark mode on/off"""
        self.dark_mode = self.dark_mode_var.get()
        self.user_config['dark_mode'] = self.dark_mode
        self.apply_theme()

    def toggle_favorite(self):
        """Toggle the favorite status of the current card and ensure keyboard bindings remain active."""
        if not self.current_card:
            return
        german_word = self.current_card['german']
        for card in self.flashcards:
            if card['german'] == german_word:
                card['favorite'] = not card.get('favorite', False)
                self.star_btn.config(text="★" if card['favorite'] else "☆")
                self.save_data()  # Ensure data is saved immediately
                break
        # Rebind keyboard events to ensure they remain active
        self.bind_keyboard_events()

    def review_favorites(self):
        """Review favorited words."""
        self.review_cards = [card for card in self.flashcards if card.get('favorite', False)]
        if not self.review_cards:
            messagebox.showinfo("No Favorites", "You haven't marked any words as favorites yet.")
            return
        random.shuffle(self.review_cards)
        self.current_card_idx = 0
        self.max_cards = len(self.review_cards)
        self.show_next_card()
        self.hide_all_frames()
        self.review_frame.pack(fill="both", expand=True)
        self.update_status(f"Reviewing {len(self.review_cards)} favorite words")

    def toggle_sound(self):
        """Toggle sound effects on/off"""
        self.sound_enabled = self.sound_var.get()
        self.user_config['sound_enabled'] = self.sound_enabled

    def save_settings(self):
        """Save all settings including transition delay and keyboard navigation."""
        self.max_cards = int(self.default_cards_var.get())
        self.transition_delay = int(self.transition_delay_var.get())
        self.keyboard_enabled = self.keyboard_enabled_var.get()  # Save keyboard navigation setting
        self.user_config['max_cards'] = self.max_cards
        self.user_config['transition_delay'] = self.transition_delay
        self.user_config['keyboard_enabled'] = self.keyboard_enabled
        self.save_data()
        messagebox.showinfo("Success", "Settings saved successfully!")
        self.show_menu()

    def show_import_dialog(self):
        """Show file dialog for importing vocabulary"""
        filepath = filedialog.askopenfilename(
            title="Select Vocabulary JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            self.import_vocabulary(filepath)

    def import_vocabulary(self, filepath):
        """Import vocabulary from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                new_words = json.load(f)

            if not isinstance(new_words, list):
                raise ValueError("JSON file should contain an array of word objects")

            # Merge with existing words (avoid duplicates)
            existing_words = {word['german'] for word in self.flashcards}
            added_count = 0

            for word in new_words:
                if word['german'] not in existing_words:
                    self.flashcards.append(word)
                    added_count += 1
                    existing_words.add(word['german'])

            self.save_data()
            messagebox.showinfo("Success", f"Added {added_count} new words!")
            return True

        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import vocabulary: {str(e)}")
            return False

    def show_export_dialog(self):
        """Show file dialog for exporting vocabulary"""
        filepath = filedialog.asksaveasfilename(
            title="Save Vocabulary As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            self.export_vocabulary(filepath)

    def export_vocabulary(self, filepath):
        """Export vocabulary to JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.flashcards, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Success", "Vocabulary exported successfully!")
            return True
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export vocabulary: {str(e)}")
            return False

    def update_status(self, message):
        """Update the status bar"""
        self.status_var.set(message)

    def on_closing(self):
        # Handle window closing event
        self.save_data()
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = WordWizardApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
