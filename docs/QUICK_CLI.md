# Quick CLI - Uproszczone Komendy Shell

Streamware Quick (`sq`) to uproszczony interfejs CLI z krótszymi komendami.

## 🚀 Instalacja

```bash
pip install -e .
```

Po instalacji dostępne są komendy:
- `streamware` - pełny CLI
- `sq` - quick CLI (uproszczony)

## 📝 Podstawowe Użycie

### Struktura Komendy

```bash
sq [komenda] [argumenty] [opcje]
```

## 🔥 Komendy

### 1. GET - HTTP GET Request

**Oryginalny sposób:**
```bash
streamware "http://api.example.com/data" \
  --pipe "transform://json" \
  --pipe "file://write?path=output.json"
```

**Quick sposób:**
```bash
sq get api.example.com/data --json --save output.json
```

**Przykłady:**
```bash
# Prosty GET
sq get api.example.com/users

# GET z JSON
sq get api.example.com/users --json

# GET i zapisz
sq get api.example.com/users --json --save users.json

# GET z pretty print
sq get api.example.com/users --json --pretty

# GET i konwertuj do CSV
sq get api.example.com/users --json --csv --save users.csv
```

### 2. POST - HTTP POST Request

```bash
# POST z danymi
sq post api.example.com/users --data '{"name":"Alice","age":30}'

# POST z pliku
sq post api.example.com/users --data @user.json --json

# POST i zapisz response
sq post api.example.com/users --data @user.json --json --save response.json
```

### 3. FILE - Operacje na Plikach

**Oryginalny:**
```bash
streamware "file://read?path=input.json" \
  --pipe "transform://json" \
  --pipe "transform://csv" \
  --pipe "file://write?path=output.csv"
```

**Quick:**
```bash
sq file input.json --json --csv --save output.csv
```

**Przykłady:**
```bash
# Czytaj i wyświetl
sq file data.json

# JSON do CSV
sq file data.json --json --csv --save output.csv

# Base64 encode
sq file image.png --base64 --save encoded.txt

# Base64 decode
sq file encoded.txt --base64 --decode --save image.png

# Transformuj JSON
sq file input.json --json --save output.json
```

### 4. KAFKA - Operacje Kafka

**Oryginalny:**
```bash
streamware "kafka://consume?topic=events&group=processor" \
  --pipe "transform://json" \
  --stream
```

**Quick:**
```bash
sq kafka events --consume --group processor --json --stream
```

**Przykłady:**
```bash
# Consume messages
sq kafka events --consume --group mygroup

# Consume z JSON parsing
sq kafka events --consume --json

# Stream mode
sq kafka events --consume --stream

# Produce message
sq kafka events --produce --data '{"event":"user_login"}'
```

### 5. POSTGRES - PostgreSQL

**Oryginalny:**
```bash
streamware "postgres://query?sql=SELECT * FROM users" \
  --pipe "transform://csv" \
  --pipe "file://write?path=users.csv"
```

**Quick:**
```bash
sq postgres "SELECT * FROM users" --csv --save users.csv
```

**Przykłady:**
```bash
# Query do JSON
sq postgres "SELECT * FROM users" --json

# Query do CSV
sq postgres "SELECT * FROM users WHERE active=true" --csv --save users.csv

# Query i wyświetl
sq postgres "SELECT COUNT(*) FROM orders"
```

### 6. EMAIL - Wysyłanie Email

**Oryginalny:**
```bash
streamware "email://send?to=user@example.com&subject=Hello" \
  --data "Message body"
```

**Quick:**
```bash
sq email user@example.com --subject "Hello" --body "Message body"
```

**Przykłady:**
```bash
# Prosta wiadomość
sq email user@example.com --subject "Test" --body "Hello World"

# Z pliku
sq email user@example.com --subject "Report" --file report.html

# HTML email
sq email user@example.com \
  --subject "Monthly Report" \
  --file report.html
```

### 7. SLACK - Slack Messages

**Oryginalny:**
```bash
streamware "slack://send?channel=general&token=xoxb-TOKEN" \
  --data "Hello team!"
```

**Quick:**
```bash
sq slack general --message "Hello team!" --token xoxb-TOKEN
```

**Przykłady:**
```bash
# Z tokenem
sq slack general --message "Deployment complete!" --token xoxb-TOKEN

# Z env variable (SLACK_BOT_TOKEN)
export SLACK_BOT_TOKEN=xoxb-your-token
sq slack general --message "Hello!"

# Alert message
sq slack alerts --message "Error occurred in production!"
```

### 8. TRANSFORM - Transformacje Danych

**Przykłady:**
```bash
# JSON transform
echo '{"name":"Alice"}' | sq transform json

# CSV transform
sq transform csv --input data.json --output data.csv

# Base64 encode
sq transform base64 --input file.txt --output encoded.txt

# Base64 decode
sq transform base64 --input encoded.txt --output file.txt --decode
```

## 🎯 Porównanie: Oryginalny vs Quick

### Przykład 1: HTTP GET i zapisz

**Oryginalny (długi):**
```bash
streamware "http://api.example.com/data" \
  --pipe "transform://json" \
  --pipe "file://write?path=output.json"
```

**Quick (krótki):**
```bash
sq get api.example.com/data --json --save output.json
```

**Oszczędność:** 80% mniej tekstu! ✨

### Przykład 2: File transformation

**Oryginalny:**
```bash
streamware "file://read?path=input.json" \
  --pipe "transform://json" \
  --pipe "transform://csv" \
  --pipe "file://write?path=output.csv"
```

**Quick:**
```bash
sq file input.json --json --csv --save output.csv
```

**Oszczędność:** 75% mniej tekstu! ✨

### Przykład 3: Kafka streaming

**Oryginalny:**
```bash
streamware "kafka://consume?topic=events&group=processor" \
  --pipe "transform://json" \
  --stream
```

**Quick:**
```bash
sq kafka events --consume --group processor --json --stream
```

**Oszczędność:** 60% mniej tekstu! ✨

## 🔧 Globalne Opcje

```bash
--debug         Włącz debug mode
--quiet, -q     Tryb cichy (bez output)
```

**Przykłady:**
```bash
# Debug mode
sq get api.example.com/data --json --debug

# Quiet mode
sq email user@example.com --subject "Test" --body "Hi" --quiet
```

## 💡 Praktyczne Przykłady

### 1. Web Scraping

```bash
# Pobierz, parsuj, zapisz
sq get shop.example.com/products --json --save products.json

# Przekształć do CSV
sq file products.json --json --csv --save products.csv
```

### 2. ETL Pipeline

```bash
# Extract
sq postgres "SELECT * FROM orders WHERE date=CURRENT_DATE" \
  --json --save raw_orders.json

# Transform
sq file raw_orders.json --json --csv --save orders.csv

# Load (przykład)
# psql -c "\COPY orders FROM orders.csv CSV HEADER"
```

### 3. Monitoring

```bash
# Sprawdź API i wyślij alert
sq get api.example.com/health --json || \
  sq slack alerts --message "API down!" --token $SLACK_TOKEN
```

### 4. Data Export

```bash
# Export z bazy do pliku
sq postgres "SELECT * FROM users WHERE active=true" \
  --csv --save active_users.csv

# Send via email
sq email manager@company.com \
  --subject "Active Users Report" \
  --file active_users.csv
```

### 5. Backup

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)

sq postgres "SELECT * FROM important_data" \
  --json --save backup_$DATE.json

sq slack backups \
  --message "Backup completed: backup_$DATE.json"
```

## 🚀 Aliasy i Funkcje Helper

Dodaj do `~/.bashrc` lub `~/.zshrc`:

```bash
# Aliasy
alias sqg='sq get'
alias sqf='sq file'
alias sqk='sq kafka'
alias sqp='sq postgres'

# Funkcje
sqget() {
  sq get "$1" --json --save "${2:-output.json}"
}

sqcsv() {
  sq file "$1" --json --csv --save "${2:-output.csv}"
}

sqdb() {
  sq postgres "$1" --csv --save "${2:-query_result.csv}"
}

# Użycie:
sqget api.example.com/data data.json
sqcsv data.json data.csv
sqdb "SELECT * FROM users" users.csv
```

## 📊 Cheat Sheet

```bash
# HTTP
sq get URL [--json] [--csv] [--save FILE]
sq post URL --data DATA [--json] [--save FILE]

# Files
sq file PATH [--json] [--csv] [--base64] [--save FILE]

# Messaging
sq kafka TOPIC [--consume|--produce] [--json] [--stream]

# Database  
sq postgres "SQL" [--json] [--csv] [--save FILE]

# Communication
sq email TO --subject SUBJECT [--body TEXT|--file FILE]
sq slack CHANNEL --message TEXT [--token TOKEN]

# Transform
sq transform TYPE [--input FILE] [--output FILE]
```

## 🎓 Tutorial: Pierwszy Pipeline

### Krok 1: Pobierz dane
```bash
sq get jsonplaceholder.typicode.com/users --json --save users.json
```

### Krok 2: Przekształć do CSV
```bash
sq file users.json --json --csv --save users.csv
```

### Krok 3: Sprawdź wynik
```bash
cat users.csv | head -5
```

Gotowe! 3 proste komendy. 🎉

## 🔄 Migracja z Oryginalnego CLI

| Oryginalny | Quick | Oszczędność |
|-----------|-------|-------------|
| `streamware "http://api.com"` | `sq get api.com` | 60% |
| `--pipe "transform://json"` | `--json` | 85% |
| `--pipe "file://write?path=out.json"` | `--save out.json` | 75% |

## ❓ FAQ

**Q: Czy mogę używać obu CLI jednocześnie?**  
A: Tak! `streamware` dla złożonych operacji, `sq` dla szybkich.

**Q: Czy wszystkie funkcje są dostępne w `sq`?**  
A: Najczęstsze operacje są. Dla zaawansowanych używaj `streamware`.

**Q: Jak ustawić domyślny token dla Slack?**  
A: `export SLACK_BOT_TOKEN=xoxb-your-token`

**Q: Czy `sq` działa z pipe?**  
A: Tak! `cat data.json | sq transform json`

## 📚 Więcej Informacji

- [CLI_USAGE.md](CLI_USAGE.md) - Pełny CLI guide
- [DSL_EXAMPLES.md](DSL_EXAMPLES.md) - Python DSL examples
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide

---

**Przykład kompletnego workflow:**

```bash
# 1. Pobierz użytkowników
sq get api.example.com/users --json --save users.json

# 2. Filtruj aktywnych (można użyć jq)
cat users.json | jq '.[] | select(.active==true)' > active.json

# 3. Konwertuj do CSV
sq file active.json --json --csv --save active.csv

# 4. Wyślij raport
sq email manager@company.com \
  --subject "Active Users" \
  --file active.csv

# 5. Notyfikacja
sq slack reports \
  --message "Users report sent to manager@company.com"
```

Quick, simple, powerful! 🚀
