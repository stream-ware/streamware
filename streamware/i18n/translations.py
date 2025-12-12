"""
Centralized translations for Voice Shell UI and conversations.
All UI strings, messages, and prompts should be defined here.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import os

# Language codes
SUPPORTED_LANGUAGES = ["en", "pl", "de", "es", "fr"]
DEFAULT_LANGUAGE = os.getenv("SQ_LANGUAGE", "en")


@dataclass
class UIStrings:
    """UI labels and buttons."""
    # Header
    title: str = "Streamware Voice Shell"
    connected: str = "Connected"
    voice_ready: str = "Ready"
    
    # Panel titles
    conversations: str = "Conversations"
    processes: str = "Processes"
    shell_output: str = "Shell Output"
    audio: str = "Audio"
    text_input: str = "Text Input"
    variables: str = "Variables"
    
    # Buttons
    new: str = "New"
    stop: str = "Stop"
    continuous: str = "Continuous"
    barge_in: str = "Barge-in"
    copy: str = "Copy"
    clear: str = "Clear"
    send: str = "Send"
    yes: str = "Yes"
    no: str = "No"
    reset: str = "Reset"
    move: str = "Move"
    expand: str = "Expand"
    
    # Quick actions
    track_person: str = "Track"
    track_email: str = "+Email"
    status: str = "Status"
    
    # Input
    type_command: str = "Type a command..."
    click_to_talk: str = "Click or press Space"
    choose_option: str = "Choose an option"
    
    # Variables panel
    name: str = "Name"
    value: str = "Value"
    synced: str = "Synced with server"
    
    # Context
    url_label: str = "URL"
    email_label: str = "Email"
    not_set: str = "(not set)"
    
    # Toggle states
    on: str = "ON"
    off: str = "OFF"
    
    # Session status
    lines: str = "lines"
    no_processes: str = "No running processes"


@dataclass
class StatusMessages:
    """Status and system messages."""
    connected: str = "Connected to Streamware Voice Shell"
    disconnected: str = "Disconnected. Reconnecting..."
    reconnecting: str = "Reconnecting..."
    new_conversation: str = "New conversation started. Say hello or a command."
    no_output: str = "(No output yet)"
    switched_to: str = "Switched to"
    creating_new_session: str = "Creating new session (current is busy)"
    previous_running: str = "previous session still running"
    
    # Voice status
    listening: str = "Listening..."
    listening_while_speaking: str = "Listening (while speaking)..."
    speaking: str = "Speaking..."
    voice_ready: str = "Ready"
    
    # Commands
    executing_command: str = "EXECUTING COMMAND"
    command_completed: str = "Command completed"
    command_started: str = "Command started"
    cancelled: str = "Cancelled"
    
    # Errors
    error: str = "Error"
    session_not_found: str = "Session not found"


@dataclass
class CommandStrings:
    """Command descriptions and results for functions."""
    # Detection
    detect_desc: str = "Detect objects in video stream"
    track_desc: str = "Track objects with ID assignment"
    count_desc: str = "Count objects in video"
    narrate_desc: str = "Track and narrate with voice"
    
    # Targets
    person: str = "person"
    car: str = "car"
    vehicle: str = "vehicle"
    animal: str = "animal"
    motion: str = "motion"
    
    # Actions
    tracking: str = "Tracking"
    detecting: str = "Detecting"
    counting: str = "Counting"
    
    # Results
    detected: str = "detected"
    entered_frame: str = "entered the frame"
    exited_frame: str = "exited the frame"
    no_detection: str = "No detection"
    
    # Notifications
    sending_email: str = "Sending email to"
    email_sent: str = "Email sent"
    notify_slack: str = "Sending to Slack"
    notify_telegram: str = "Sending to Telegram"


@dataclass
class ConversationMessages:
    """Messages for LLM conversation flow."""
    # Greetings
    hello: str = "Hello! I'm your video surveillance assistant. What would you like me to monitor?"
    how_can_help: str = "How can I help you?"
    
    # Options
    how_would_you_like: str = "How would you like to {action}?"
    option_tts: str = "with voice (TTS)"
    option_silent: str = "silently"
    option_email: str = "and email me"
    
    # Email
    email_saved: str = "I have your email saved as {email}. Say 'yes' to use it, or 'new' to enter a different email."
    using_email: str = "Using email {email}. Executing..."
    enter_new_email: str = "Please say your new email address."
    say_yes_or_new: str = "Say 'yes' to use {email}, or 'new' for different email."
    email_set: str = "Email set to {email}. Executing..."
    
    # Confirmations
    say_yes_confirm: str = "Say yes to confirm."
    say_yes_or_no: str = "Say 'yes' to execute or 'no' to cancel."
    executing: str = "Executing command."
    
    # Not understood
    not_understood: str = "Sorry, I didn't understand: {text}. Say 'hello' for options."
    
    # Detections
    person_detected: str = "Person detected"
    motion_detected: str = "Motion detected"
    no_target: str = "No {target} visible"
    
    # Reader / OCR commands
    reading_clock: str = "Reading time from clock..."
    reading_display: str = "Reading text from display..."
    reading_text: str = "Reading text from camera..."
    describing: str = "Describing what camera sees..."
    
    # Help
    help_intro: str = "Available commands:"
    help_track: str = "Track [person/car] - detect and follow objects"
    help_describe: str = "Describe / Opisz - describe what camera sees"
    help_read_clock: str = "Read clock / Która godzina - read time from clock"
    help_read_display: str = "Read display / Czytaj wyświetlacz - OCR text"
    help_stop: str = "Stop - stop current operation"


@dataclass
class VoicePrompts:
    """Voice prompts and TTS messages."""
    welcome: str = "Welcome! What would you like to monitor?"
    goodbye: str = "Goodbye!"
    confirm_action: str = "Do you want me to {action}?"
    starting: str = "Starting {action}..."
    completed: str = "Task completed."
    error_occurred: str = "An error occurred: {error}"


@dataclass 
class LanguagePack:
    """Complete language pack combining all string categories."""
    code: str
    name: str
    voice_code: str  # For speech recognition (e.g., 'en-US', 'pl-PL')
    ui: UIStrings = field(default_factory=UIStrings)
    status: StatusMessages = field(default_factory=StatusMessages)
    conversation: ConversationMessages = field(default_factory=ConversationMessages)
    voice: VoicePrompts = field(default_factory=VoicePrompts)
    commands: CommandStrings = field(default_factory=CommandStrings)


# =============================================================================
# Language Packs
# =============================================================================

ENGLISH = LanguagePack(
    code="en",
    name="English",
    voice_code="en-US",
    ui=UIStrings(),
    status=StatusMessages(),
    conversation=ConversationMessages(),
    voice=VoicePrompts(),
    commands=CommandStrings(),
)

POLISH = LanguagePack(
    code="pl",
    name="Polski",
    voice_code="pl-PL",
    ui=UIStrings(
        title="Streamware Voice Shell",
        connected="Połączono",
        voice_ready="Gotowy",
        conversations="Konwersacje",
        processes="Procesy",
        shell_output="Wyjście Shell",
        audio="Audio",
        text_input="Wprowadź tekst",
        variables="Zmienne",
        new="Nowy",
        stop="Stop",
        continuous="Ciągły",
        barge_in="Przerywanie",
        copy="Kopiuj",
        clear="Wyczyść",
        send="Wyślij",
        yes="Tak",
        no="Nie",
        reset="Reset",
        move="Przesuń",
        expand="Rozwiń",
        track_person="Śledź",
        track_email="+Email",
        status="Status",
        type_command="Wpisz polecenie...",
        click_to_talk="Kliknij lub naciśnij Spację",
        choose_option="Wybierz opcję",
        name="Nazwa",
        value="Wartość",
        synced="Zsynchronizowano z serwerem",
        url_label="URL",
        email_label="Email",
        not_set="(nie ustawiono)",
        on="WŁ",
        off="WYŁ",
        lines="linii",
        no_processes="Brak uruchomionych procesów",
    ),
    status=StatusMessages(
        connected="Połączono ze Streamware Voice Shell",
        disconnected="Rozłączono. Ponowne łączenie...",
        reconnecting="Ponowne łączenie...",
        new_conversation="Nowa rozmowa. Powiedz cześć lub wydaj polecenie.",
        no_output="(Brak wyjścia)",
        switched_to="Przełączono na",
        creating_new_session="Tworzenie nowej sesji (obecna zajęta)",
        previous_running="poprzednia sesja nadal działa",
        listening="Słucham...",
        listening_while_speaking="Słucham (podczas mówienia)...",
        speaking="Mówię...",
        voice_ready="Gotowy",
        executing_command="WYKONUJĘ POLECENIE",
        command_completed="Polecenie zakończone",
        command_started="Polecenie rozpoczęte",
        cancelled="Anulowano",
        error="Błąd",
        session_not_found="Sesja nie znaleziona",
    ),
    conversation=ConversationMessages(
        hello="Cześć! Jestem asystentem monitoringu wideo. Co chciałbyś śledzić?",
        how_can_help="Jak mogę pomóc?",
        how_would_you_like="Jak chcesz {action}?",
        option_tts="z głosem (TTS)",
        option_silent="cicho",
        option_email="i wyślij mi email",
        email_saved="Mam zapisany email {email}. Powiedz 'tak' aby użyć, lub 'nowy' aby podać inny.",
        using_email="Używam email {email}. Wykonuję...",
        enter_new_email="Podaj nowy adres email.",
        say_yes_or_new="Powiedz 'tak' aby użyć {email}, lub 'nowy' dla innego.",
        email_set="Email ustawiony na {email}. Wykonuję...",
        say_yes_confirm="Powiedz tak aby potwierdzić.",
        say_yes_or_no="Powiedz 'tak' aby wykonać lub 'nie' aby anulować.",
        executing="Wykonuję polecenie.",
        not_understood="Nie zrozumiałem: {text}. Powiedz 'cześć' aby zobaczyć opcje.",
        person_detected="Wykryto osobę",
        motion_detected="Wykryto ruch",
        no_target="Brak {target}",
        # Reader / OCR
        reading_clock="Czytam godzinę z zegara...",
        reading_display="Czytam tekst z wyświetlacza...",
        reading_text="Czytam tekst z kamery...",
        describing="Opisuję co widzi kamera...",
        # Help
        help_intro="Dostępne polecenia:",
        help_track="Śledź [osobę/samochód] - wykryj i śledź obiekty",
        help_describe="Opisz - opisz co widzi kamera",
        help_read_clock="Która godzina / Czytaj zegar - odczytaj godzinę",
        help_read_display="Czytaj wyświetlacz - OCR tekstu",
        help_stop="Stop - zatrzymaj bieżącą operację",
    ),
    voice=VoicePrompts(
        welcome="Witaj! Co chciałbyś monitorować?",
        goodbye="Do widzenia!",
        confirm_action="Czy chcesz {action}?",
        starting="Rozpoczynam {action}...",
        completed="Zadanie zakończone.",
        error_occurred="Wystąpił błąd: {error}",
    ),
    commands=CommandStrings(
        detect_desc="Wykryj obiekty w strumieniu wideo",
        track_desc="Śledź obiekty z przypisaniem ID",
        count_desc="Zliczaj obiekty w wideo",
        narrate_desc="Śledź i opisuj głosowo",
        person="osoba",
        car="samochód",
        vehicle="pojazd",
        animal="zwierzę",
        motion="ruch",
        tracking="Śledzenie",
        detecting="Wykrywanie",
        counting="Zliczanie",
        detected="wykryto",
        entered_frame="wszedł w kadr",
        exited_frame="wyszedł z kadru",
        no_detection="Brak wykrycia",
        sending_email="Wysyłanie emaila do",
        email_sent="Email wysłany",
        notify_slack="Wysyłanie do Slack",
        notify_telegram="Wysyłanie do Telegram",
    ),
)

GERMAN = LanguagePack(
    code="de",
    name="Deutsch",
    voice_code="de-DE",
    ui=UIStrings(
        title="Streamware Voice Shell",
        connected="Verbunden",
        voice_ready="Bereit",
        conversations="Unterhaltungen",
        processes="Prozesse",
        shell_output="Shell Ausgabe",
        audio="Audio",
        text_input="Texteingabe",
        variables="Variablen",
        new="Neu",
        stop="Stopp",
        continuous="Kontinuierlich",
        barge_in="Unterbrechen",
        copy="Kopieren",
        clear="Löschen",
        send="Senden",
        yes="Ja",
        no="Nein",
        reset="Zurücksetzen",
        move="Verschieben",
        expand="Erweitern",
        track_person="Verfolgen",
        track_email="+Email",
        status="Status",
        type_command="Befehl eingeben...",
        click_to_talk="Klicken oder Leertaste",
        choose_option="Option wählen",
        name="Name",
        value="Wert",
        synced="Mit Server synchronisiert",
        url_label="URL",
        email_label="E-Mail",
        not_set="(nicht gesetzt)",
        on="EIN",
        off="AUS",
        lines="Zeilen",
        no_processes="Keine laufenden Prozesse",
    ),
    status=StatusMessages(
        connected="Mit Streamware Voice Shell verbunden",
        disconnected="Getrennt. Verbinde erneut...",
        reconnecting="Verbinde erneut...",
        new_conversation="Neue Unterhaltung. Sag hallo oder einen Befehl.",
        no_output="(Keine Ausgabe)",
        switched_to="Gewechselt zu",
        creating_new_session="Erstelle neue Sitzung (aktuelle beschäftigt)",
        previous_running="vorherige Sitzung läuft noch",
        listening="Höre zu...",
        listening_while_speaking="Höre zu (während Sprechen)...",
        speaking="Spreche...",
        voice_ready="Bereit",
        executing_command="FÜHRE BEFEHL AUS",
        command_completed="Befehl abgeschlossen",
        command_started="Befehl gestartet",
        cancelled="Abgebrochen",
        error="Fehler",
        session_not_found="Sitzung nicht gefunden",
    ),
    conversation=ConversationMessages(
        hello="Hallo! Ich bin dein Video-Überwachungsassistent. Was möchtest du überwachen?",
        how_can_help="Wie kann ich helfen?",
        how_would_you_like="Wie möchtest du {action}?",
        option_tts="mit Stimme (TTS)",
        option_silent="leise",
        option_email="und mir eine E-Mail senden",
        email_saved="Ich habe deine E-Mail gespeichert: {email}. Sag 'ja' um sie zu verwenden, oder 'neu' für eine andere.",
        using_email="Verwende E-Mail {email}. Führe aus...",
        enter_new_email="Bitte sage deine neue E-Mail-Adresse.",
        say_yes_or_new="Sag 'ja' um {email} zu verwenden, oder 'neu' für eine andere.",
        email_set="E-Mail auf {email} gesetzt. Führe aus...",
        say_yes_confirm="Sag ja zum Bestätigen.",
        say_yes_or_no="Sag 'ja' zum Ausführen oder 'nein' zum Abbrechen.",
        executing="Führe Befehl aus.",
        not_understood="Entschuldigung, ich habe nicht verstanden: {text}. Sag 'hallo' für Optionen.",
        person_detected="Person erkannt",
        motion_detected="Bewegung erkannt",
        no_target="Kein {target} sichtbar",
    ),
    voice=VoicePrompts(
        welcome="Willkommen! Was möchtest du überwachen?",
        goodbye="Auf Wiedersehen!",
        confirm_action="Möchtest du {action}?",
        starting="Starte {action}...",
        completed="Aufgabe abgeschlossen.",
        error_occurred="Ein Fehler ist aufgetreten: {error}",
    ),
    commands=CommandStrings(
        detect_desc="Objekte im Videostream erkennen",
        track_desc="Objekte mit ID-Zuweisung verfolgen",
        count_desc="Objekte im Video zählen",
        narrate_desc="Verfolgen und mit Stimme beschreiben",
        person="Person",
        car="Auto",
        vehicle="Fahrzeug",
        animal="Tier",
        motion="Bewegung",
        tracking="Verfolgung",
        detecting="Erkennung",
        counting="Zählung",
        detected="erkannt",
        entered_frame="ist ins Bild getreten",
        exited_frame="hat das Bild verlassen",
        no_detection="Keine Erkennung",
        sending_email="Sende E-Mail an",
        email_sent="E-Mail gesendet",
        notify_slack="Sende an Slack",
        notify_telegram="Sende an Telegram",
    ),
)

# Language registry
LANGUAGES: Dict[str, LanguagePack] = {
    "en": ENGLISH,
    "pl": POLISH,
    "de": GERMAN,
}


def get_language(code: str) -> LanguagePack:
    """Get language pack by code, fallback to English."""
    return LANGUAGES.get(code, ENGLISH)


def get_ui_string(code: str, key: str) -> str:
    """Get UI string by language code and key."""
    lang = get_language(code)
    return getattr(lang.ui, key, key)


def get_status_message(code: str, key: str, **kwargs) -> str:
    """Get status message with optional formatting."""
    lang = get_language(code)
    msg = getattr(lang.status, key, key)
    if kwargs:
        try:
            return msg.format(**kwargs)
        except KeyError:
            return msg
    return msg


def get_conversation_message(code: str, key: str, **kwargs) -> str:
    """Get conversation message with optional formatting."""
    lang = get_language(code)
    msg = getattr(lang.conversation, key, key)
    if kwargs:
        try:
            return msg.format(**kwargs)
        except KeyError:
            return msg
    return msg


def get_voice_code(code: str) -> str:
    """Get voice recognition language code."""
    return get_language(code).voice_code


class Translator:
    """
    Reusable translator for server-side messages.
    Usage:
        t = Translator('pl')
        t.status('connected')  # Returns Polish translation
        t.conv('email_saved', email='tom@example.com')  # With interpolation
    """
    
    def __init__(self, language: str = "en"):
        self.language = language
        self._lang_pack = get_language(language)
    
    def set_language(self, language: str):
        """Change current language."""
        self.language = language
        self._lang_pack = get_language(language)
    
    def ui(self, key: str) -> str:
        """Get UI string."""
        return getattr(self._lang_pack.ui, key, key)
    
    def status(self, key: str) -> str:
        """Get status message."""
        return getattr(self._lang_pack.status, key, key)
    
    def conv(self, key: str, **kwargs) -> str:
        """Get conversation message with optional interpolation."""
        msg = getattr(self._lang_pack.conversation, key, key)
        if kwargs:
            try:
                return msg.format(**kwargs)
            except KeyError:
                return msg
        return msg
    
    def voice(self, key: str, **kwargs) -> str:
        """Get voice prompt with optional interpolation."""
        msg = getattr(self._lang_pack.voice, key, key)
        if kwargs:
            try:
                return msg.format(**kwargs)
            except KeyError:
                return msg
        return msg
    
    def cmd(self, key: str) -> str:
        """Get command string (for function descriptions, targets, etc.)."""
        return getattr(self._lang_pack.commands, key, key)
    
    def translate_target(self, target: str) -> str:
        """Translate detection target to current language."""
        return getattr(self._lang_pack.commands, target, target)
    
    def translate_action(self, action: str) -> str:
        """Translate action verb to current language."""
        action_map = {
            "track": "tracking",
            "detect": "detecting",
            "count": "counting",
        }
        key = action_map.get(action.lower(), action.lower())
        return getattr(self._lang_pack.commands, key, action)
    
    @property
    def voice_code(self) -> str:
        """Get speech recognition voice code."""
        return self._lang_pack.voice_code


# Global translator instance (singleton)
_translator = Translator()

def get_translator() -> Translator:
    """Get global translator instance."""
    return _translator

def set_global_language(language: str):
    """Set language for global translator."""
    _translator.set_language(language)


def export_js_translations() -> str:
    """Export translations as JavaScript object for frontend."""
    js_lines = ["const TRANSLATIONS = {"]
    
    for code, lang in LANGUAGES.items():
        js_lines.append(f"    '{code}': {{")
        js_lines.append(f"        name: '{lang.name}',")
        js_lines.append(f"        voiceCode: '{lang.voice_code}',")
        
        # UI strings
        js_lines.append("        ui: {")
        for field_name in UIStrings.__dataclass_fields__:
            value = getattr(lang.ui, field_name)
            js_lines.append(f"            {field_name}: '{value}',")
        js_lines.append("        },")
        
        # Status messages
        js_lines.append("        status: {")
        for field_name in StatusMessages.__dataclass_fields__:
            value = getattr(lang.status, field_name)
            js_lines.append(f"            {field_name}: '{value}',")
        js_lines.append("        },")
        
        # Conversation messages
        js_lines.append("        conversation: {")
        for field_name in ConversationMessages.__dataclass_fields__:
            value = getattr(lang.conversation, field_name)
            js_lines.append(f"            {field_name}: '{value}',")
        js_lines.append("        },")
        
        # Voice prompts
        js_lines.append("        voice: {")
        for field_name in VoicePrompts.__dataclass_fields__:
            value = getattr(lang.voice, field_name)
            js_lines.append(f"            {field_name}: '{value}',")
        js_lines.append("        },")
        
        js_lines.append("    },")
    
    js_lines.append("};")
    return "\n".join(js_lines)
