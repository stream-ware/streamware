# 🎤🖱️ Voice Mouse - Sterowanie Głosowe

## Steruj myszką głosem + AI Vision!

Voice Mouse łączy:
- 🎤 **Rozpoznawanie głosu** (STT)
- 👁️ **AI Vision** (LLaVA) - znajduje przyciski
- 🖱️ **Automatyzacja** - klika w znalezione miejsce

## 🚀 Quick Start

### Tryb Interaktywny
```bash
# Ciągłe słuchanie i klikanie
python3 -m streamware.quick_cli voice-click listen_and_click

# Powiedz: "Kliknij w button zatwierdź"
# Bot: Robi screenshot → AI znajdzie przycisk → Kliknie!
```

### Pojedyncza Komenda
```bash
# Kliknij konkretny przycisk
python3 -m streamware.quick_cli voice-click click --command "kliknij w button approve"

# Po angielsku
python3 -m streamware.quick_cli voice-click click --command "click the submit button" --language en
```

## 💡 Jak to działa

### Przepływ:
```
1. 🎤 Słuchasz: "Kliknij w button zatwierdź"
2. 📸 Screenshot: Zrzut ekranu
3. 🤖 AI Vision (LLaVA): Znajduje przycisk na ekranie
4. 🖱️ Klik: Klika w znalezione współrzędne
5. 🔊 Potwierdza: "Klikam w button zatwierdź"
```

## 📝 Przykłady Komend

### Polski
```bash
# Podstawowe
"Kliknij w button zatwierdź"
"Kliknij w przycisk OK"
"Naciśnij button Approve"
"Wciśnij przycisk Submit"
"Wybierz opcję Continue"

# Z kontekstem
"Kliknij w zielony button"
"Kliknij w górny przycisk"
"Kliknij w prawy button"
```

### English
```bash
"Click the approve button"
"Click on submit"
"Press the OK button"
"Select continue"
"Tap the accept button"
```

## 🎯 Use Cases

### 1. Akceptowanie zmian w VSCode
```bash
python3 -m streamware.quick_cli voice-click listen_and_click

# Powiedz: "Kliknij w accept all"
# Bot znajdzie i kliknie "Accept All" button!
```

### 2. Nawigacja w aplikacjach
```bash
# Kliknij w dowolny przycisk głosem
"Kliknij w button settings"
"Kliknij w przycisk opcje"
"Kliknij w menu"
```

### 3. Automatyzacja testów
```bash
# Test scenariusz głosowo
"Kliknij w button login"
# Czeka 2s
"Kliknij w submit"
# Czeka 2s
"Kliknij w confirm"
```

## 🔧 Instalacja

### Wymagania
```bash
# 1. System packages
sudo apt-get install xdotool scrot

# 2. Ollama + LLaVA
ollama pull llava

# 3. Python (opcjonalne - dla głosu)
pip install SpeechRecognition PyAudio
```

### Test
```python
from streamware.components import voice_click

# Test pojedynczego kliknięcia
result = voice_click("kliknij w button OK")
print(result)
```

## 📊 API

### Python API
```python
from streamware import flow

# Pojedyncze kliknięcie
result = flow(
    "voice_mouse://click?"
    "command=kliknij w button zatwierdź&"
    "language=pl"
).run()

# Wynik
{
  "success": True,
  "target": "button zatwierdź",
  "x": 870,
  "y": 130,
  "method": "xdotool"
}

# Ciągłe słuchanie
result = flow(
    "voice_mouse://listen_and_click?"
    "iterations=10&"
    "delay=2.0"
).run()
```

### CLI
```bash
# Interaktywny mode
sq voice-click listen_and_click

# Pojedyncza komenda
sq voice-click click --command "kliknij w OK"

# Po angielsku
sq voice-click click --command "click submit" --language en

# Tylko przesunięcie (bez kliknięcia)
sq voice-click move --command "przesuń na button"
```

## 🎨 Zaawansowane

### 1. Custom Screenshot Path
```python
result = flow(
    "voice_mouse://click?"
    "command=kliknij w button&"
    "screenshot=/tmp/custom_screen.png"
).run()
```

### 2. Bez Voice Confirmation
```python
result = flow(
    "voice_mouse://click?"
    "command=kliknij w button&"
    "confirm=false"  # Nie mówi przed kliknięciem
).run()
```

### 3. Custom Timeout dla AI
```python
# W komponencie media można ustawić timeout
# Domyślnie 60s, można zwiększyć
```

## 🔍 Jak AI Znajduje Przyciski

### Prompt do LLaVA:
```
Analyze this screenshot and find the 'button zatwierdź' button or element.

Give me the EXACT pixel coordinates (x, y) of the CENTER of this element.

The screenshot resolution is typically 1920x1080 or similar.
Respond ONLY with coordinates in format: x,y
For example: 850,130

If you can't find the element, respond with: NOT_FOUND

Target to find: button zatwierdź
```

### AI Odpowiada:
```
850, 130
```

### Bot Klika:
```bash
xdotool mousemove 850 130
xdotool click 1
```

## 🛠️ Troubleshooting

### AI nie znajduje przycisku
**Problem:** AI odpowiada "NOT_FOUND"

**Rozwiązania:**
1. Opisz precyzyjniej: "kliknij w zielony button OK w górnym rogu"
2. Użyj dokładnej nazwy z ekranu
3. Sprawdź czy przycisk jest widoczny na screenshocie

### Timeout na AI
**Problem:** `Read timed out (60s)`

**Rozwiązanie:**
```python
# Screenshot w niższej rozdzielczości
subprocess.run(['scrot', '-q', '50', 'screen.png'])  # 50% quality
```

### xdotool not found
**Problem:** `FileNotFoundError: xdotool`

**Rozwiązanie:**
```bash
sudo apt-get install xdotool
```

## 📈 Performance

### Czas Wykonania:
- Screenshot: ~0.1s
- AI Vision (LLaVA): 5-60s (zależy od obrazu)
- Kliknięcie: <0.1s
- **Total:** ~5-60s per command

### Optymalizacja:
1. Zmniejsz rozdzielczość screenshota
2. Użyj szybszego modelu AI
3. Cache screenshotów jeśli interfejs się nie zmienia

## 🎉 Examples

### Example 1: VSCode Automation
```python
from streamware import flow

# Akceptuj wszystkie zmiany głosem
flow("voice://speak?text=Zaczynam automatyzację").run()

# Słuchaj i klikaj
result = flow(
    "voice_mouse://listen_and_click?iterations=5"
).run()

# Mów: "Kliknij w accept all"
# Bot znajdzie i kliknie!
```

### Example 2: Form Filling
```bash
#!/bin/bash
# Wypełnij formularz głosowo

echo "Wypełniam formularz..."

# Kliknij każde pole
sq voice-click click --command "kliknij w pole name"
sq auto type --text "Jan Kowalski"

sq voice-click click --command "kliknij w pole email"
sq auto type --text "jan@example.com"

sq voice-click click --command "kliknij w button submit"
```

### Example 3: Testing
```bash
#!/bin/bash
# Test UI głosowo

test_steps=(
    "kliknij w button start"
    "kliknij w option 1"
    "kliknij w next"
    "kliknij w confirm"
    "kliknij w finish"
)

for step in "${test_steps[@]}"; do
    echo "Executing: $step"
    sq voice-click click --command "$step"
    sleep 2
done

echo "Test complete!"
```

## 🌟 Highlights

### Zalety:
- ✅ Nie musisz znać współrzędnych!
- ✅ AI znajduje przyciski automatycznie
- ✅ Działa z każdą aplikacją
- ✅ Polski i angielski
- ✅ Tryb interaktywny
- ✅ Voice feedback

### Use Cases:
- 🎯 Automatyzacja VSCode
- 🎯 Testy UI
- 🎯 Accessibility
- 🎯 Hands-free control
- 🎯 Demo/prezentacje

---

**Steruj komputerem głosem jak w filmach sci-fi! 🎤🖱️✨**

## Quick Reference

```bash
# Tryb interaktywny
sq voice-click listen_and_click

# Pojedyncza komenda
sq voice-click click --command "kliknij w OK"

# Po angielsku
sq voice-click click --command "click submit" --language en

# Więcej iteracji
sq voice-click listen_and_click --iterations 20

# Python
from streamware.components import voice_click
result = voice_click("kliknij w button")
```
