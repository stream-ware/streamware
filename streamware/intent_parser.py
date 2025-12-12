#!/usr/bin/env python3
"""
Intent Parser - Semantic understanding of voice commands without hardcoded keywords.

Uses a combination of:
1. Fast embedding-based similarity (primary, offline)
2. LLM fallback for complex/ambiguous cases
3. Caching for performance

This replaces hardcoded keyword lists with semantic understanding.
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from functools import lru_cache

# Try to import sentence-transformers for fast embeddings
try:
    from sentence_transformers import SentenceTransformer, util
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False

# Try to import requests for LLM fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


@dataclass
class Intent:
    """Parsed intent from user input."""
    action: str  # track, describe, read_clock, read_display, read, help, stop, unknown
    target: Optional[str] = None  # person, car, animal, etc.
    modifiers: Dict[str, Any] = field(default_factory=dict)  # tts, email, duration, etc.
    confidence: float = 0.0
    raw_input: str = ""


# Intent definitions with semantic descriptions (not keywords!)
INTENT_DEFINITIONS = {
    "track": {
        "description": "Follow, monitor, or track objects in video. Detect movement of people, cars, animals.",
        "examples": ["track person", "follow the car", "monitor people", "śledź osobę", "verfolge person"],
        "requires_target": True,
    },
    "describe": {
        "description": "Describe what the camera sees. Explain the scene, objects, or situation.",
        "examples": ["describe", "what do you see", "opisz", "co widzisz", "beschreibe"],
        "requires_target": False,
    },
    "read_clock": {
        "description": "Read the time from a clock or watch. Tell what time it is.",
        "examples": ["what time is it", "read clock", "która godzina", "wie spät ist es", "quelle heure"],
        "requires_target": False,
    },
    "read_display": {
        "description": "Read text from a screen, display, or monitor using OCR.",
        "examples": ["read screen", "read display", "czytaj ekran", "bildschirm lesen"],
        "requires_target": False,
    },
    "read": {
        "description": "Read any text visible in the camera view using OCR.",
        "examples": ["read", "read text", "czytaj", "lesen", "lire"],
        "requires_target": False,
    },
    "help": {
        "description": "Show help, greet, or list available commands.",
        "examples": ["hello", "help", "hi", "cześć", "hallo", "hola", "bonjour"],
        "requires_target": False,
    },
    "stop": {
        "description": "Stop current operation, cancel, or quit.",
        "examples": ["stop", "cancel", "quit", "anuluj", "stopp", "arrêter"],
        "requires_target": False,
    },
}

# Target definitions
TARGET_DEFINITIONS = {
    "person": {
        "description": "Human being, person, people, someone",
        "examples": ["person", "people", "human", "osoba", "człowiek", "person", "personne"],
    },
    "car": {
        "description": "Car, vehicle, automobile, truck",
        "examples": ["car", "vehicle", "auto", "samochód", "fahrzeug", "coche", "voiture"],
    },
    "animal": {
        "description": "Animal, pet, dog, cat, bird",
        "examples": ["animal", "pet", "dog", "cat", "zwierzę", "tier", "animal"],
    },
    "motion": {
        "description": "Any movement or motion",
        "examples": ["motion", "movement", "ruch", "bewegung", "movimiento"],
    },
}

# Modifier definitions
MODIFIER_DEFINITIONS = {
    "with_voice": {
        "description": "With voice output, speak results, TTS enabled",
        "examples": ["with voice", "speak", "say", "mów", "głos", "sprechen", "parler"],
    },
    "silent": {
        "description": "Silent mode, no voice, quiet",
        "examples": ["silent", "quiet", "cicho", "leise", "silencio"],
    },
    "with_email": {
        "description": "Send email notification, alert by email",
        "examples": ["email", "mail", "send email", "wyślij email", "e-mail senden"],
    },
}


class IntentParser:
    """
    Semantic intent parser that understands commands without hardcoded keywords.
    
    Uses embedding similarity for fast matching, with LLM fallback for ambiguous cases.
    """
    
    def __init__(
        self,
        language: str = "en",
        use_embeddings: bool = True,
        use_llm_fallback: bool = True,
        llm_model: str = "llama3.2",
        ollama_url: str = "http://localhost:11434",
        similarity_threshold: float = 0.5,
    ):
        self.language = language
        self.use_llm_fallback = use_llm_fallback
        self.llm_model = llm_model
        self.ollama_url = ollama_url
        self.similarity_threshold = similarity_threshold
        
        # Initialize embedding model if available
        self.embedder = None
        if use_embeddings and HAS_EMBEDDINGS:
            try:
                # Use a small, fast multilingual model
                self.embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                self._precompute_embeddings()
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
        
        # Cache for parsed intents
        self._cache: Dict[str, Intent] = {}
    
    def _precompute_embeddings(self):
        """Precompute embeddings for all intent/target/modifier examples."""
        if not self.embedder:
            return
        
        # Combine descriptions and examples for each intent
        self.intent_texts = {}
        self.intent_embeddings = {}
        
        for intent_name, intent_def in INTENT_DEFINITIONS.items():
            texts = [intent_def["description"]] + intent_def["examples"]
            self.intent_texts[intent_name] = texts
            self.intent_embeddings[intent_name] = self.embedder.encode(texts, convert_to_tensor=True)
        
        # Same for targets
        self.target_texts = {}
        self.target_embeddings = {}
        
        for target_name, target_def in TARGET_DEFINITIONS.items():
            texts = [target_def["description"]] + target_def["examples"]
            self.target_texts[target_name] = texts
            self.target_embeddings[target_name] = self.embedder.encode(texts, convert_to_tensor=True)
        
        # Same for modifiers
        self.modifier_texts = {}
        self.modifier_embeddings = {}
        
        for mod_name, mod_def in MODIFIER_DEFINITIONS.items():
            texts = [mod_def["description"]] + mod_def["examples"]
            self.modifier_texts[mod_name] = texts
            self.modifier_embeddings[mod_name] = self.embedder.encode(texts, convert_to_tensor=True)
    
    def _match_with_embeddings(self, text: str, embeddings_dict: dict, threshold: float = None) -> Tuple[Optional[str], float]:
        """Match text against precomputed embeddings."""
        if not self.embedder or not embeddings_dict:
            return None, 0.0
        
        threshold = threshold or self.similarity_threshold
        text_embedding = self.embedder.encode(text, convert_to_tensor=True)
        
        best_match = None
        best_score = 0.0
        
        for name, embeddings in embeddings_dict.items():
            # Compute similarity with all examples
            similarities = util.cos_sim(text_embedding, embeddings)
            max_sim = similarities.max().item()
            
            if max_sim > best_score and max_sim >= threshold:
                best_score = max_sim
                best_match = name
        
        return best_match, best_score
    
    def _parse_with_llm(self, text: str) -> Optional[Intent]:
        """Use LLM to parse intent when embeddings fail or are unavailable."""
        if not self.use_llm_fallback or not HAS_REQUESTS:
            return None
        
        prompt = f"""Parse this voice command and extract the intent.

Command: "{text}"

Available intents:
- track: Follow/monitor objects (person, car, animal)
- describe: Describe what camera sees
- read_clock: Read time from clock
- read_display: Read text from screen/display
- read: Read any visible text
- help: Show help/greet
- stop: Stop/cancel operation

Respond with JSON only:
{{"action": "intent_name", "target": "person/car/animal/null", "with_voice": true/false, "with_email": true/false, "confidence": 0.0-1.0}}
"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=10,
            )
            
            if response.ok:
                result = response.json()
                content = result.get("response", "{}")
                data = json.loads(content)
                
                return Intent(
                    action=data.get("action", "unknown"),
                    target=data.get("target"),
                    modifiers={
                        "with_voice": data.get("with_voice", False),
                        "with_email": data.get("with_email", False),
                    },
                    confidence=data.get("confidence", 0.7),
                    raw_input=text,
                )
        except Exception as e:
            print(f"LLM parsing failed: {e}")
        
        return None
    
    def _parse_with_patterns(self, text: str) -> Optional[Intent]:
        """
        Fast pattern-based parsing using semantic word groups.
        This is a fallback when embeddings are not available.
        """
        lower = text.lower().strip()
        
        # Use simple semantic matching based on common patterns
        # This is more flexible than exact keyword matching
        
        # Check for stop/cancel first (high priority)
        if self._semantic_match(lower, ["stop", "cancel", "quit", "abort", "end", "anuluj", "przerwij", "stopp", "abbrechen", "arrêter", "parar"]):
            return Intent(action="stop", confidence=0.9, raw_input=text)
        
        # Check for greetings/help
        if self._semantic_match(lower, ["hello", "hi", "hey", "help", "cześć", "hej", "pomoc", "hallo", "hilfe", "hola", "bonjour", "salut"]):
            return Intent(action="help", confidence=0.9, raw_input=text)
        
        # Check for time/clock reading
        if self._semantic_match(lower, ["time", "clock", "hour", "godzina", "zegar", "uhr", "zeit", "hora", "heure"]):
            return Intent(action="read_clock", confidence=0.85, raw_input=text)
        
        # Check for screen/display reading
        if self._semantic_match(lower, ["screen", "display", "monitor", "ekran", "wyświetlacz", "bildschirm", "pantalla", "écran"]):
            return Intent(action="read_display", confidence=0.85, raw_input=text)
        
        # Check for describe
        if self._semantic_match(lower, ["describe", "see", "look", "show", "opisz", "widzisz", "pokaż", "beschreib", "siehst", "mira", "regarde"]):
            return Intent(action="describe", confidence=0.85, raw_input=text)
        
        # Check for tracking
        if self._semantic_match(lower, ["track", "follow", "monitor", "detect", "watch", "find", "śledź", "wykryj", "obserwuj", "znajdź", "szukaj", "verfolg", "erkenn", "finde", "such", "sigue", "busca", "suis", "cherche"]):
            target = self._extract_target(lower)
            modifiers = self._extract_modifiers(lower)
            return Intent(action="track", target=target, modifiers=modifiers, confidence=0.8, raw_input=text)
        
        # Check for general reading
        if self._semantic_match(lower, ["read", "text", "czytaj", "lesen", "leer", "lire"]):
            return Intent(action="read", confidence=0.75, raw_input=text)
        
        return None
    
    def _semantic_match(self, text: str, patterns: List[str]) -> bool:
        """Check if text semantically matches any pattern (substring or word boundary)."""
        for pattern in patterns:
            # Check for word boundary match (more flexible than exact match)
            if re.search(rf'\b{re.escape(pattern)}\b', text, re.IGNORECASE):
                return True
            # Also check for substring (for agglutinative languages)
            if pattern in text:
                return True
        return False
    
    def _extract_target(self, text: str) -> Optional[str]:
        """Extract target from text using semantic matching."""
        # Person patterns
        if self._semantic_match(text, ["person", "people", "human", "someone", "osoba", "osobę", "człowiek", "ludzi", "person", "mensch", "persona", "personne", "gens"]):
            return "person"
        
        # Car/vehicle patterns
        if self._semantic_match(text, ["car", "vehicle", "auto", "truck", "samochód", "pojazd", "fahrzeug", "wagen", "coche", "voiture", "véhicule"]):
            return "car"
        
        # Animal patterns
        if self._semantic_match(text, ["animal", "pet", "dog", "cat", "bird", "zwierzę", "pies", "kot", "tier", "hund", "katze", "animal", "mascota"]):
            return "animal"
        
        # Motion patterns
        if self._semantic_match(text, ["motion", "movement", "ruch", "bewegung", "movimiento", "mouvement"]):
            return "motion"
        
        # Default to person for tracking commands
        return "person"
    
    def _extract_modifiers(self, text: str) -> Dict[str, Any]:
        """Extract modifiers from text."""
        modifiers = {}
        
        # Voice/TTS
        if self._semantic_match(text, ["voice", "speak", "say", "tell", "głos", "mów", "powiedz", "sprechen", "sagen", "habla", "parle"]):
            modifiers["with_voice"] = True
        
        # Silent
        if self._semantic_match(text, ["silent", "quiet", "mute", "cicho", "leise", "silencio", "silencieux"]):
            modifiers["silent"] = True
        
        # Email
        if self._semantic_match(text, ["email", "mail", "notify", "alert", "wyślij", "powiadom", "e-mail", "correo", "courriel"]):
            modifiers["with_email"] = True
        
        return modifiers
    
    def parse(self, text: str) -> Intent:
        """
        Parse user input to extract intent, target, and modifiers.
        
        Uses a cascade of methods:
        1. Cache lookup
        2. Embedding similarity (fast, multilingual)
        3. Pattern matching (fallback)
        4. LLM parsing (for complex cases)
        """
        if not text or not text.strip():
            return Intent(action="unknown", confidence=0.0, raw_input=text)
        
        text = text.strip()
        
        # Check cache
        cache_key = text.lower()
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        intent = None
        
        # Try embedding-based matching first (fastest for known patterns)
        if self.embedder:
            action, action_score = self._match_with_embeddings(text, self.intent_embeddings)
            
            if action and action_score >= self.similarity_threshold:
                target = None
                target_score = 0.0
                
                # Extract target if needed
                if INTENT_DEFINITIONS.get(action, {}).get("requires_target"):
                    target, target_score = self._match_with_embeddings(text, self.target_embeddings, threshold=0.4)
                    if not target:
                        target = "person"  # Default
                
                # Extract modifiers
                modifiers = {}
                for mod_name in MODIFIER_DEFINITIONS:
                    _, mod_score = self._match_with_embeddings(text, {mod_name: self.modifier_embeddings[mod_name]}, threshold=0.5)
                    if mod_score >= 0.5:
                        modifiers[mod_name] = True
                
                intent = Intent(
                    action=action,
                    target=target,
                    modifiers=modifiers,
                    confidence=action_score,
                    raw_input=text,
                )
        
        # Fallback to pattern matching
        if not intent or intent.confidence < 0.6:
            pattern_intent = self._parse_with_patterns(text)
            if pattern_intent and (not intent or pattern_intent.confidence > intent.confidence):
                intent = pattern_intent
        
        # LLM fallback for low confidence or unknown
        if (not intent or intent.confidence < 0.5) and self.use_llm_fallback:
            llm_intent = self._parse_with_llm(text)
            if llm_intent and llm_intent.confidence > (intent.confidence if intent else 0):
                intent = llm_intent
        
        # Final fallback
        if not intent:
            intent = Intent(action="unknown", confidence=0.0, raw_input=text)
        
        # Cache result
        self._cache[cache_key] = intent
        
        return intent
    
    def clear_cache(self):
        """Clear the intent cache."""
        self._cache.clear()


# Singleton instance
_parser: Optional[IntentParser] = None


def get_intent_parser(language: str = "en", **kwargs) -> IntentParser:
    """Get or create the global intent parser."""
    global _parser
    if _parser is None or _parser.language != language:
        _parser = IntentParser(language=language, **kwargs)
    return _parser


def parse_intent(text: str, language: str = "en") -> Intent:
    """Quick function to parse intent from text."""
    parser = get_intent_parser(language)
    return parser.parse(text)


# For testing
if __name__ == "__main__":
    parser = IntentParser(language="pl", use_embeddings=False)  # Test without embeddings
    
    test_commands = [
        "track person",
        "śledź osobę",
        "która godzina",
        "what time is it",
        "opisz co widzisz",
        "describe the scene",
        "verfolge das auto",
        "stop",
        "anuluj",
        "cześć",
        "hello",
        "read the screen",
        "czytaj ekran",
    ]
    
    print("Testing IntentParser (pattern mode):\n")
    for cmd in test_commands:
        intent = parser.parse(cmd)
        print(f"  '{cmd}'")
        print(f"    → action={intent.action}, target={intent.target}, confidence={intent.confidence:.2f}")
        print()
