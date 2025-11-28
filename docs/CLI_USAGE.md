# Streamware CLI - Użycie w Shell

Kompletny przewodnik po używaniu Streamware z linii poleceń (terminala/shell).

## 📋 Spis Treści

1. [Instalacja](#instalacja)
2. [Podstawowe Użycie](#podstawowe-użycie)
3. [Przykłady](#przykłady)
4. [Wszystkie Opcje](#wszystkie-opcje)
5. [Protokół stream://](#protokół-stream)
6. [Zaawansowane Użycie](#zaawansowane-użycie)

## Instalacja

Po zainstalowaniu Streamware, dostępne są dwa polecenia:

```bash
# Główne CLI
streamware --help

# Handler protokołu stream://
stream-handler --help
```

## Podstawowe Użycie

### 1. Prosta Pipeline

```bash
# Pobierz dane z API i zapisz do pliku
streamware "http://api.example.com/data" \
  --pipe "transform://json" \
  --pipe "file://write?path=output.json"
```

### 2. Transformacja Danych

```bash
# Przekształć dane JSON
streamware "file://read?path=input.json" \
  --pipe "transform://jsonpath?query=$.items[*]" \
  --pipe "transform://csv" \
  --output results.csv
```

### 3. Z Danymi Wejściowymi

```bash
# Prześlij dane do pipeline
streamware "transform://json" \
  --data '{"name":"Alice","age":30}' \
  --output result.json

# Lub z pliku
streamware "transform://json" \
  --data @input.json \
  --output result.json
```

## Przykłady

### HTTP/REST API

```bash
# GET request
streamware "http://api.example.com/users"

# Z parametrami
streamware "http://api.example.com/users?limit=10"

# Zapisz wynik
streamware "http://api.example.com/users" --output users.json
```

### Przetwarzanie Plików

```bash
# Czytaj i transformuj
streamware "file://read?path=data.json" \
  --pipe "transform://jsonpath?query=$.users[*]" \
  --output users.json

# Base64 kodowanie
streamware "file://read?path=image.png" \
  --pipe "transform://base64" \
  --output encoded.txt

# CSV do JSON
streamware "file://read?path=data.csv" \
  --pipe "transform://csv" \
  --format json \
  --output data.json
```

### CurLLM - Web Automation

```bash
# Przeglądaj stronę z LLM
streamware "curllm://browse?url=https://example.com" \
  --instruction "Extract all product prices"

# Wypełnij formularz
streamware "curllm://browse?url=https://form.example.com" \
  --instruction "Fill form with name: John, email: john@example.com"

# BQL Query
streamware "curllm://bql?query={page(url:'https://example.com'){title,links}}"
```

### Kafka

```bash
# Konsumuj wiadomości
streamware "kafka://consume?topic=events&group=processor" \
  --pipe "transform://json" \
  --stream

# Produkuj wiadomości
streamware "kafka://produce?topic=events" \
  --data '{"event":"user_login","user_id":123}'
```

### RabbitMQ

```bash
# Konsumuj z kolejki
streamware "rabbitmq://consume?queue=tasks" \
  --pipe "transform://json" \
  --stream

# Publikuj wiadomość
streamware "rabbitmq://publish?exchange=events&routing_key=new" \
  --data '{"type":"notification","message":"Hello"}'
```

### PostgreSQL

```bash
# Wykonaj query
streamware "postgres://query?sql=SELECT * FROM users WHERE active=true" \
  --output users.json

# Insert danych
streamware "postgres://insert?table=logs" \
  --data '{"level":"info","message":"Test log"}'
```

### Email

```bash
# Wyślij email
streamware "email://send?to=user@example.com&subject=Hello" \
  --data "This is the email body"

# Czytaj emaile
streamware "email://read?imap_host=imap.gmail.com" \
  --output emails.json
```

### SMS/WhatsApp/Telegram

```bash
# SMS przez Twilio
streamware "sms://send?provider=twilio&to=+1234567890" \
  --data "Your verification code is 123456"

# WhatsApp
streamware "whatsapp://send?provider=twilio&to=+1234567890" \
  --data "Hello from Streamware!"

# Telegram
streamware "telegram://send?chat_id=@channel&token=BOT_TOKEN" \
  --data "Notification message"
```

## Wszystkie Opcje

### Podstawowe Argumenty

```bash
streamware [URI] [OPCJE]

Argumenty pozycyjne:
  URI                    Początkowy URI dla pipeline

Opcje:
  -h, --help            Pokaż pomoc
  --pipe, -p URI        Dodaj krok pipeline (można używać wielokrotnie)
  --data, -d DATA       Dane wejściowe (JSON lub @plik)
  --output, -o FILE     Ścieżka do pliku wyjściowego
  --format, -f FORMAT   Format wyjścia (json, csv, text)
  --stream, -s          Włącz tryb streaming
  --async               Uruchom w trybie async
  --debug               Włącz debug logging
  --trace               Włącz trace logging (bardzo szczegółowy)
  --list-components     Lista dostępnych komponentów
  --list-schemes        Lista dostępnych schematów URI
  --install-protocol    Zainstaluj handler protokołu stream://
  --version             Pokaż wersję
```

### Przykłady Użycia Opcji

```bash
# Debug mode
streamware --debug "http://api.example.com/data"

# Streaming mode
streamware --stream "kafka://consume?topic=events"

# Multiple pipes
streamware "http://api.example.com/data" \
  --pipe "transform://jsonpath?query=$.items" \
  --pipe "filter://condition?value>10" \
  --pipe "transform://csv" \
  --output filtered.csv

# Async mode
streamware --async "http://api.example.com/slow-endpoint"

# Format output
streamware "file://read?path=data.json" \
  --format csv \
  --output data.csv
```

## Protokół stream://

Streamware może obsługiwać URIe `stream://` bezpośrednio w systemie.

### Instalacja Protocol Handler

```bash
# Zainstaluj handler w systemie
streamware --install-protocol
```

Po instalacji możesz używać:

```bash
# W terminalu
curl stream://http/get?url=https://api.example.com

# W przeglądarce
stream://curllm/browse?url=https://example.com

# Z systemowych aplikacji
xdg-open "stream://file/read?path=/tmp/data.json"
```

### Przykłady stream://

```bash
# HTTP przez stream://
stream-handler "stream://http/get?url=https://api.example.com/data"

# Transformacja
stream-handler "stream://transform/json?pretty=true"

# File operations
stream-handler "stream://file/write?path=/tmp/output.txt"
```

## Zaawansowane Użycie

### 1. Złożone Pipeline z Wieloma Krokami

```bash
streamware "http://api.example.com/users" \
  --pipe "transform://jsonpath?query=$.data[*]" \
  --pipe "filter://condition?age>18" \
  --pipe "transform://template?file=user_report.j2" \
  --pipe "file://write?path=report.html" \
  --debug
```

### 2. Praca z Plikami JSON

```bash
# Wyciągnij dane z JSON
streamware "file://read?path=large_file.json" \
  --pipe "transform://jsonpath?query=$.items[?(@.status=='active')]" \
  --pipe "transform://csv" \
  --output active_items.csv
```

### 3. Batch Processing

```bash
# Przetwarzaj wiele plików
for file in data/*.json; do
  streamware "file://read?path=$file" \
    --pipe "transform://validate" \
    --pipe "postgres://insert?table=processed" \
    --debug
done
```

### 4. Streaming z Kafka

```bash
# Konsumuj i przetwarzaj ciągle
streamware --stream "kafka://consume?topic=events&group=processor" \
  --pipe "transform://json" \
  --pipe "transform://enrich" \
  --pipe "postgres://insert?table=events"
```

### 5. Web Scraping z CurLLM

```bash
# Ekstraktuj dane ze strony
streamware "curllm://browse?url=https://shop.example.com&stealth=true" \
  --instruction "Find all products under $50 with name and price" \
  --pipe "transform://csv" \
  --output products.csv
```

### 6. ETL Pipeline

```bash
# Extract, Transform, Load
streamware "postgres://query?sql=SELECT * FROM raw_data WHERE date=CURRENT_DATE" \
  --pipe "transform://clean" \
  --pipe "transform://validate" \
  --pipe "transform://enrich" \
  --pipe "postgres://insert?table=processed_data" \
  --debug
```

### 7. Monitoring i Alerty

```bash
# Sprawdź API i wyślij alert jeśli problem
streamware "http://api.example.com/health" \
  --pipe "transform://json" \
  --pipe "slack://send?channel=alerts&token=TOKEN" \
  --data "Health check failed!"
```

### 8. Data Export

```bash
# Eksportuj z bazy do pliku
streamware "postgres://query?sql=SELECT * FROM users" \
  --pipe "transform://csv" \
  --output users_export.csv

# Lub do Kafki
streamware "postgres://query?sql=SELECT * FROM events" \
  --pipe "kafka://produce?topic=events_backup"
```

## Zmienne Środowiskowe

Streamware respektuje następujące zmienne środowiskowe:

```bash
# Logging
export STREAMWARE_LOG_LEVEL=DEBUG
export STREAMWARE_LOG_FILE=/var/log/streamware.log

# Kafka
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# PostgreSQL
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=user
export POSTGRES_PASSWORD=password
export POSTGRES_DB=mydb

# Email
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your@email.com
export SMTP_PASSWORD=yourpassword

# Twilio (SMS/WhatsApp)
export TWILIO_ACCOUNT_SID=your_sid
export TWILIO_AUTH_TOKEN=your_token
export TWILIO_PHONE_NUMBER=+1234567890

# Telegram
export TELEGRAM_BOT_TOKEN=your_bot_token

# Slack
export SLACK_BOT_TOKEN=xoxb-your-token

# Discord
export DISCORD_BOT_TOKEN=your_bot_token
```

Użyj ich w pipeline:

```bash
# Ustaw zmienne
export SMTP_HOST=smtp.gmail.com
export SMTP_USER=your@email.com
export SMTP_PASSWORD=yourpassword

# Użyj w komendzie (pobierze z env)
streamware "email://send?to=user@example.com&subject=Test" \
  --data "Email from Streamware CLI"
```

## Lista Komponentów

Zobacz dostępne komponenty:

```bash
# Lista wszystkich komponentów
streamware --list-components

# Lista schematów URI
streamware --list-schemes
```

## Tips & Tricks

### 1. Użyj Aliasów

```bash
# W ~/.bashrc lub ~/.zshrc
alias sw='streamware'
alias swh='stream-handler'

# Teraz możesz używać:
sw "http://api.example.com/data" --output data.json
```

### 2. Funkcje Helper

```bash
# W ~/.bashrc
function sw-kafka-consume() {
  streamware --stream "kafka://consume?topic=$1&group=$2"
}

function sw-http-get() {
  streamware "http://$1" --output "${2:-output.json}"
}

# Użycie:
sw-kafka-consume events processor
sw-http-get api.example.com/data result.json
```

### 3. Pipe z innymi narzędziami

```bash
# Pobierz i przetwórz z jq
streamware "http://api.example.com/data" | jq '.items[]'

# Zapisz do pliku z tee
streamware "http://api.example.com/data" | tee output.json | jq '.count'

# Chain z curl
curl -s http://api.example.com/raw | \
  streamware "transform://json" --data @- | \
  streamware "transform://csv" --data @-
```

### 4. Cron Jobs

```bash
# W crontab -e
# Codziennie o 2:00 AM
0 2 * * * /usr/local/bin/streamware "postgres://query?sql=SELECT * FROM daily_stats" --output /backups/daily_$(date +\%Y\%m\%d).json

# Co godzinę, sprawdź health
0 * * * * /usr/local/bin/streamware "http://api.example.com/health" --pipe "slack://send?channel=monitoring&token=TOKEN"
```

### 5. Scripts

```bash
#!/bin/bash
# daily_etl.sh

set -e  # Exit on error

echo "Starting ETL pipeline..."

# Extract
streamware "postgres://query?sql=SELECT * FROM raw_data WHERE date=CURRENT_DATE" \
  --output /tmp/raw_data.json

# Transform
streamware "file://read?path=/tmp/raw_data.json" \
  --pipe "transform://clean" \
  --pipe "transform://validate" \
  --output /tmp/clean_data.json

# Load
streamware "file://read?path=/tmp/clean_data.json" \
  --pipe "postgres://insert?table=processed_data"

echo "ETL completed successfully!"

# Cleanup
rm /tmp/raw_data.json /tmp/clean_data.json
```

## Troubleshooting

### Problem: Command not found

```bash
# Sprawdź czy zainstalowane
which streamware

# Jeśli nie, reinstaluj
pip install -e .

# Lub dodaj do PATH
export PATH="$PATH:$HOME/.local/bin"
```

### Problem: Permission denied

```bash
# Nadaj uprawnienia wykonywania
chmod +x /usr/local/bin/streamware
chmod +x /usr/local/bin/stream-handler
```

### Problem: Module not found

```bash
# Reinstaluj w trybie development
pip install -e .

# Lub sprawdź PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/streamware"
```

## Dokumentacja

- 📚 [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- 📖 [USAGE_GUIDE.md](USAGE_GUIDE.md) - Kompletny przewodnik
- 🧪 [TESTING.md](TESTING.md) - Testing guide
- 💬 [COMMUNICATION.md](COMMUNICATION.md) - Communication components

## Wsparcie

- 🐛 [GitHub Issues](https://github.com/softreck/streamware/issues)
- 💬 [GitHub Discussions](https://github.com/softreck/streamware/discussions)
- 📧 Email: info@softreck.com

---

**Przykład kompletnego workflow:**

```bash
# 1. Pobierz dane z API
streamware "http://api.example.com/users" --output raw_users.json

# 2. Przetwórz i filtruj
streamware "file://read?path=raw_users.json" \
  --pipe "transform://jsonpath?query=$.users[?(@.active==true)]" \
  --output active_users.json

# 3. Konwertuj do CSV
streamware "file://read?path=active_users.json" \
  --pipe "transform://csv" \
  --output users.csv

# 4. Załaduj do bazy
streamware "file://read?path=users.csv" \
  --pipe "postgres://insert?table=users"

# 5. Wyślij powiadomienie
streamware "slack://send?channel=data-team&token=TOKEN" \
  --data "ETL completed: $(wc -l < users.csv) users processed"
```

Happy streaming! 🚀
