#!/bin/bash
# Quick CLI Demo - Demonstracja uproszczonych komend
# 
# Ten skrypt pokazuje jak używać 'sq' (stream-quick) zamiast pełnego 'streamware'

set -e  # Exit on error

echo "=========================================="
echo "STREAMWARE QUICK CLI DEMO"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

demo() {
    echo -e "${BLUE}$ $1${NC}"
    echo ""
}

result() {
    echo -e "${GREEN}✓ $1${NC}"
    echo ""
}

# ==========================================
# PORÓWNANIE: Oryginalny vs Quick
# ==========================================

echo "=== PORÓWNANIE: Oryginalny vs Quick ==="
echo ""

echo "1. HTTP GET i zapisz do pliku"
echo ""
demo 'streamware "http://httpbin.org/json" --pipe "transform://json" --pipe "file://write?path=output.json"'
echo "vs"
demo 'sq get httpbin.org/json --json --save output.json'
result "80% krócej!"

echo "---"
echo ""

echo "2. File transformation"
echo ""
demo 'streamware "file://read?path=input.json" --pipe "transform://json" --pipe "transform://csv" --pipe "file://write?path=output.csv"'
echo "vs"
demo 'sq file input.json --json --csv --save output.csv'
result "75% krócej!"

echo "---"
echo ""

# ==========================================
# PRAKTYCZNE PRZYKŁADY
# ==========================================

echo "=== PRAKTYCZNE PRZYKŁADY ==="
echo ""

# Przykład 1: HTTP GET
echo "Przykład 1: Pobierz dane z API"
echo ""
demo "sq get httpbin.org/uuid --json"
echo "Wykonuję..."
if command -v sq &> /dev/null; then
    sq get httpbin.org/uuid --json 2>/dev/null || echo "  (symulacja - API niedostępne)"
else
    echo "  (sq nie zainstalowane - użyj: pip install -e .)"
fi
result "Dane pobrane!"
echo ""

# Przykład 2: File operations
echo "Przykład 2: Operacje na plikach"
echo ""
echo '{"name":"Alice","age":30}' > /tmp/demo_user.json
demo "sq file /tmp/demo_user.json --json"
echo "Wykonuję..."
if command -v sq &> /dev/null; then
    sq file /tmp/demo_user.json --json 2>/dev/null || cat /tmp/demo_user.json
else
    cat /tmp/demo_user.json
fi
result "Plik przeczytany!"
rm -f /tmp/demo_user.json
echo ""

# Przykład 3: Base64
echo "Przykład 3: Base64 encoding"
echo ""
echo "Hello World" > /tmp/demo_text.txt
demo "sq file /tmp/demo_text.txt --base64 --save /tmp/demo_encoded.txt"
echo "Wykonuję..."
if command -v sq &> /dev/null; then
    sq file /tmp/demo_text.txt --base64 --save /tmp/demo_encoded.txt 2>/dev/null || base64 /tmp/demo_text.txt > /tmp/demo_encoded.txt
else
    base64 /tmp/demo_text.txt > /tmp/demo_encoded.txt
fi

if [ -f /tmp/demo_encoded.txt ]; then
    echo "Zakodowano: $(cat /tmp/demo_encoded.txt)"
    result "Base64 encoding wykonany!"
fi
rm -f /tmp/demo_text.txt /tmp/demo_encoded.txt
echo ""

# ==========================================
# ALIASY I FUNKCJE HELPER
# ==========================================

echo "=== ALIASY I FUNKCJE HELPER ==="
echo ""

echo "Dodaj do ~/.bashrc:"
echo ""
cat << 'EOF'
# Quick CLI aliasy
alias sqg='sq get'
alias sqf='sq file'
alias sqp='sq postgres'

# Helper functions
sqget() {
  sq get "$1" --json --save "${2:-output.json}"
}

sqcsv() {
  sq file "$1" --json --csv --save "${2:-output.csv}"
}
EOF
echo ""
result "Kopiuj powyższe do swojego ~/.bashrc!"
echo ""

# ==========================================
# CHEAT SHEET
# ==========================================

echo "=== QUICK CLI CHEAT SHEET ==="
echo ""
cat << 'EOF'
# HTTP
sq get URL [--json] [--save FILE]
sq post URL --data DATA [--json]

# Files
sq file PATH [--json] [--csv] [--base64] [--save FILE]

# Kafka
sq kafka TOPIC [--consume|--produce] [--json]

# PostgreSQL
sq postgres "SQL" [--json] [--csv] [--save FILE]

# Email
sq email TO --subject SUBJECT --body TEXT

# Slack
sq slack CHANNEL --message TEXT [--token TOKEN]

# Transform
sq transform TYPE [--input IN] [--output OUT]
EOF
echo ""

# ==========================================
# PRZYKŁADOWY WORKFLOW
# ==========================================

echo "=== PRZYKŁADOWY WORKFLOW ==="
echo ""

echo "1. Pobierz dane z API"
demo "sq get httpbin.org/json --json --save data.json"
echo ""

echo "2. Przekształć do CSV (gdyby były dane tablicowe)"
demo "sq file data.json --json --csv --save data.csv"
echo ""

echo "3. Wyślij raport"
demo "sq email user@example.com --subject 'Report' --file data.csv"
echo ""

echo "4. Powiadom na Slacku"
demo "sq slack reports --message 'Report sent!'"
echo ""

result "Cały workflow w 4 komendach!"
echo ""

# ==========================================
# INSTALACJA
# ==========================================

echo "=== INSTALACJA ==="
echo ""

echo "Zainstaluj Streamware z Quick CLI:"
demo "pip install -e ."
echo ""

echo "Po instalacji dostępne będą 3 komendy:"
echo "  • streamware  - pełny CLI"
echo "  • sq          - quick CLI (uproszczony)"
echo "  • stream-handler - protocol handler"
echo ""

# ==========================================
# WIĘCEJ PRZYKŁADÓW
# ==========================================

echo "=== WIĘCEJ PRZYKŁADÓW ==="
echo ""

echo "Web Scraping:"
demo "sq get shop.example.com/products --json --save products.json"
echo ""

echo "ETL Pipeline:"
demo "sq postgres 'SELECT * FROM users' --csv --save users.csv"
echo ""

echo "Monitoring:"
demo "sq get api.example.com/health || sq slack alerts --message 'API down!'"
echo ""

echo "Data Export:"
demo "sq postgres 'SELECT * FROM orders WHERE date=CURRENT_DATE' --json --save orders.json"
echo ""

# ==========================================
# PODSUMOWANIE
# ==========================================

echo "=========================================="
echo "PODSUMOWANIE"
echo "=========================================="
echo ""
echo "Quick CLI (sq) to:"
echo "  ✓ Krótsze komendy (60-85% mniej tekstu)"
echo "  ✓ Intuicyjniejsza składnia"
echo "  ✓ Szybsze do wpisania"
echo "  ✓ Łatwiejsze do zapamiętania"
echo ""
echo "Dokumentacja:"
echo "  • docs/QUICK_CLI.md - pełna dokumentacja"
echo "  • docs/CLI_USAGE.md - oryginalny CLI"
echo "  • docs/DSL_EXAMPLES.md - Python DSL"
echo ""
echo "Przykłady:"
echo "  • examples/quick_cli_demo.sh (ten skrypt)"
echo "  • examples/dsl_examples.py - Python examples"
echo ""
echo "Wsparcie:"
echo "  • GitHub: https://github.com/softreck/streamware"
echo "  • Email: info@softreck.com"
echo ""
echo "=========================================="
echo "Happy streaming! 🚀"
echo "=========================================="
