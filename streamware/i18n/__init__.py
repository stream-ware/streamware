"""
Internationalization (i18n) support for Streamware Voice Shell.

Usage:
    from streamware.i18n import get_messages, set_language
    
    msg = get_messages()
    print(msg.hello_options)  # "What would you like to do?"
    
    set_language("pl")
    msg = get_messages()
    print(msg.hello_options)  # "Co chciałbyś zrobić?"
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

# Current language setting
_current_lang = "en"


@dataclass
class Messages:
    """All UI/TTS messages in one place."""
    
    # General
    connected: str = "Connected to Streamware Voice Shell"
    new_conversation: str = "New conversation started. Say hello or a command."
    cancelled: str = "Cancelled. What would you like to do?"
    not_understood: str = "Sorry, I didn't understand: {text}. Say 'hello' for options."
    
    # Confirmation
    say_yes_confirm: str = "Say yes to confirm."
    say_yes_or_no: str = "Say 'yes' to execute or 'no' to cancel."
    executing: str = "Executing command."
    command_completed: str = "Command completed."
    process_stopped: str = "Process stopped."
    
    # Options menu
    hello_options: str = "What would you like to do? Say a number:"
    option_track_speak: str = "Track person with voice (TTS)"
    option_track_silent: str = "Track person silently"
    option_track_email: str = "Track person and email me"
    option_detect: str = "Detect person"
    option_detect_email: str = "Detect and email me"
    option_functions: str = "Show all functions"
    please_say_number: str = "Please say a number: 1, 2, 3, or 4."
    
    # Email input
    email_prompt: str = "Please say your email address. You can spell it letter by letter."
    email_got: str = "Got: {text}. Current: {buffer}. Say 'done' when finished or 'clear' to restart."
    email_got_full: str = "Got email: {email}. Say 'done' to confirm or 'clear' to restart."
    email_cleared: str = "Cleared. Please say your email again."
    email_deleted: str = "Deleted. Current: {buffer}"
    email_set: str = "Email set to {email}. Say yes to confirm."
    
    # Errors
    missing_params: str = "Missing {params}. Please provide the value."
    error_occurred: str = "Error: {error}"
    
    # Session management
    session_created: str = "Session created"
    session_switched: str = "Switched to session"
    no_output_yet: str = "(No output yet)"
    
    # Voice recognition
    voice_ready: str = "Voice Ready"
    listening: str = "Listening..."
    speaking: str = "Speaking..."
    listening_while_speaking: str = "Listening (while speaking)..."
    barge_in_interrupted: str = "Barge-in: TTS interrupted"


# Language-specific message overrides
TRANSLATIONS: Dict[str, Messages] = {
    "en": Messages(),
    
    "pl": Messages(
        # General
        connected="Połączono ze Streamware Voice Shell",
        new_conversation="Nowa rozmowa rozpoczęta. Powiedz 'cześć' lub wydaj polecenie.",
        cancelled="Anulowano. Co chciałbyś zrobić?",
        not_understood="Przepraszam, nie zrozumiałem: {text}. Powiedz 'cześć' aby zobaczyć opcje.",
        
        # Confirmation
        say_yes_confirm="Powiedz 'tak' żeby potwierdzić.",
        say_yes_or_no="Powiedz 'tak' żeby wykonać lub 'nie' żeby anulować.",
        executing="Wykonuję polecenie.",
        command_completed="Polecenie wykonane.",
        process_stopped="Proces zatrzymany.",
        
        # Options menu
        hello_options="Co chciałbyś zrobić? Powiedz numer:",
        option_track_speak="Śledź osobę z głosem",
        option_track_silent="Śledź osobę cicho",
        option_track_email="Śledź osobę i wyślij email",
        option_detect="Wykryj osobę",
        option_detect_email="Wykryj i wyślij email",
        option_functions="Pokaż wszystkie funkcje",
        please_say_number="Proszę powiedz numer: 1, 2, 3 lub 4.",
        
        # Email input
        email_prompt="Podaj swój adres email. Możesz przeliterować.",
        email_got="Otrzymałem: {text}. Aktualnie: {buffer}. Powiedz 'gotowe' gdy skończysz lub 'wyczyść' żeby zacząć od nowa.",
        email_got_full="Otrzymałem email: {email}. Powiedz 'gotowe' żeby potwierdzić lub 'wyczyść' żeby zacząć od nowa.",
        email_cleared="Wyczyszczono. Podaj email ponownie.",
        email_deleted="Usunięto. Aktualnie: {buffer}",
        email_set="Email ustawiony na {email}. Powiedz 'tak' żeby potwierdzić.",
        
        # Errors
        missing_params="Brakuje {params}. Proszę podaj wartość.",
        error_occurred="Błąd: {error}",
        
        # Session management
        session_created="Sesja utworzona",
        session_switched="Przełączono na sesję",
        no_output_yet="(Brak outputu)",
        
        # Voice recognition
        voice_ready="Gotowy",
        listening="Słucham...",
        speaking="Mówię...",
        listening_while_speaking="Słucham (podczas mówienia)...",
        barge_in_interrupted="Przerwanie: TTS przerwany",
    ),
    
    "de": Messages(
        connected="Mit Streamware Voice Shell verbunden",
        new_conversation="Neue Konversation gestartet. Sag 'hallo' oder einen Befehl.",
        hello_options="Was möchtest du tun? Sag eine Nummer:",
        say_yes_confirm="Sag 'ja' zum Bestätigen.",
        cancelled="Abgebrochen. Was möchtest du tun?",
        executing="Führe Befehl aus.",
    ),
}

# Word mappings for different languages (for voice recognition)
WORD_MAPPINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "one": "1", "two": "2", "three": "3", "four": "4",
        "first": "1", "second": "2", "third": "3", "fourth": "4",
        "yes": "yes", "no": "no", "cancel": "cancel",
        "done": "done", "clear": "clear", "delete": "delete",
        "at": "@", "dot": ".",
    },
    "pl": {
        "jeden": "1", "dwa": "2", "trzy": "3", "cztery": "4",
        "pierwszy": "1", "drugi": "2", "trzeci": "3", "czwarty": "4",
        "tak": "yes", "nie": "no", "anuluj": "cancel",
        "gotowe": "done", "wyczyść": "clear", "usuń": "delete",
        "małpa": "@", "kropka": ".",
    },
    "de": {
        "eins": "1", "zwei": "2", "drei": "3", "vier": "4",
        "ja": "yes", "nein": "no", "abbrechen": "cancel",
        "fertig": "done", "löschen": "clear",
        "at": "@", "punkt": ".",
    },
}

# Confirmation words for different languages
CONFIRM_WORDS: Dict[str, set] = {
    "en": {"yes", "yeah", "okay", "ok", "execute", "do it", "run"},
    "pl": {"tak", "dobrze", "okej", "wykonaj", "zrób to"},
    "de": {"ja", "okay", "ausführen"},
}

CANCEL_WORDS: Dict[str, set] = {
    "en": {"no", "cancel", "stop", "nevermind"},
    "pl": {"nie", "anuluj", "stop", "nieważne"},
    "de": {"nein", "abbrechen", "stopp"},
}

DONE_WORDS: Dict[str, set] = {
    "en": {"done", "confirm", "that's it", "finished"},
    "pl": {"gotowe", "koniec", "to wszystko", "skończone"},
    "de": {"fertig", "bestätigen", "das ist es"},
}

CLEAR_WORDS: Dict[str, set] = {
    "en": {"clear", "reset", "start over"},
    "pl": {"wyczyść", "od nowa", "reset"},
    "de": {"löschen", "neu anfangen", "zurücksetzen"},
}


def get_messages(lang: Optional[str] = None) -> Messages:
    """Get messages for the specified or current language."""
    lang = lang or _current_lang
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"])


def set_language(lang: str) -> bool:
    """Set the current language. Returns True if language exists."""
    global _current_lang
    if lang in TRANSLATIONS:
        _current_lang = lang
        return True
    return False


def get_language() -> str:
    """Get the current language code."""
    return _current_lang


def get_available_languages() -> list:
    """Get list of available language codes."""
    return list(TRANSLATIONS.keys())


def normalize_input(text: str, lang: Optional[str] = None) -> str:
    """Normalize input using language-specific word mappings."""
    lang = lang or _current_lang
    mappings = WORD_MAPPINGS.get(lang, {})
    
    words = text.lower().split()
    normalized = []
    for word in words:
        normalized.append(mappings.get(word, word))
    
    return " ".join(normalized)


def is_confirm(text: str, lang: Optional[str] = None) -> bool:
    """Check if text is a confirmation word."""
    lang = lang or _current_lang
    words = CONFIRM_WORDS.get(lang, CONFIRM_WORDS["en"])
    return any(w in text.lower() for w in words)


def is_cancel(text: str, lang: Optional[str] = None) -> bool:
    """Check if text is a cancel word."""
    lang = lang or _current_lang
    words = CANCEL_WORDS.get(lang, CANCEL_WORDS["en"])
    return any(w in text.lower() for w in words)


def is_done(text: str, lang: Optional[str] = None) -> bool:
    """Check if text is a done/confirm word."""
    lang = lang or _current_lang
    words = DONE_WORDS.get(lang, DONE_WORDS["en"])
    return any(w in text.lower() for w in words)


def is_clear(text: str, lang: Optional[str] = None) -> bool:
    """Check if text is a clear/reset word."""
    lang = lang or _current_lang
    words = CLEAR_WORDS.get(lang, CLEAR_WORDS["en"])
    return any(w in text.lower() for w in words)
