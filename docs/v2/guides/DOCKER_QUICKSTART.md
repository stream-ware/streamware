# Docker Quick Start - Streamware

Szybki start ze środowiskiem Docker dla Streamware! 🐳

## 🚀 Uruchomienie w 3 Krokach

### Krok 1: Zbuduj i Uruchom

```bash
# Przejdź do katalogu projektu
cd /home/tom/github/stream-ware/streamware

# Zbuduj i uruchom wszystkie serwisy
docker-compose up -d

# Sprawdź status (wszystkie powinny być "Up")
docker-compose ps
```

### Krok 2: Wejdź do Kontenera

```bash
# Interaktywny shell w kontenerze Streamware
docker-compose exec streamware bash
```

### Krok 3: Testuj!

```bash
# W kontenerze wykonaj:

# Test 1: Mock API
sq get mock-api:8080/users --json

# Test 2: Zapisz do pliku
sq get mock-api:8080/products --json --save /data/products.json

# Test 3: PostgreSQL
sq postgres "SELECT * FROM users WHERE active=true" --csv

# Test 4: Transformacja
sq file /data/products.json --json --csv --save /data/products.csv
```

## ✅ Pierwszy Test - Potwierdzenie Działania

```bash
# 1. Uruchom środowisko
docker-compose up -d

# 2. Poczekaj ~30 sekund na uruchomienie wszystkich serwisów

# 3. Sprawdź czy wszystko działa
docker-compose exec streamware bash -c "sq get mock-api:8080/health --json"

# Powinieneś zobaczyć:
# {"status": "healthy", "timestamp": "...", "uptime": "..."}
```

## 🎯 Gotowe Przykłady

### Przykład 1: HTTP → JSON → CSV

```bash
docker-compose exec streamware bash

# W kontenerze:
sq get mock-api:8080/users --json --save /data/users.json
sq file /data/users.json --json --csv --save /data/users.csv
cat /data/users.csv
```

### Przykład 2: PostgreSQL → Export

```bash
docker-compose exec streamware bash

# Query i export
sq postgres "SELECT * FROM users" --csv --save /data/db_export.csv
sq postgres "SELECT * FROM products WHERE price > 100" --json
```

### Przykład 3: Kafka Streaming

```bash
# Terminal 1: Produce
docker-compose exec streamware bash
echo '{"event":"test","data":"hello"}' | \
  streamware "kafka://produce?topic=events" --data @-

# Terminal 2: Consume
docker-compose exec streamware bash
streamware "kafka://consume?topic=events&group=test" --stream
```

### Przykład 4: Python DSL

```bash
docker-compose exec streamware python3

# W Python:
from streamware import Pipeline, quick

# Quick API
result = quick("http://mock-api:8080/users").json().run()
print(f"Users: {len(result)}")

# Fluent API
result = (
    Pipeline()
    .http_get("http://mock-api:8080/products")
    .to_json()
    .filter(lambda p: p['price'] > 100)
    .run()
)
print(f"Expensive products: {len(result)}")
```

## 🧪 Automatyczne Testy

```bash
# Uruchom zestaw testów
docker-compose exec streamware bash /app/docker/test-basic.sh

# Testy streamingowe
docker-compose exec streamware bash /app/docker/test-streaming.sh
```

## 📊 Dostępne Endpointy

### Mock API (localhost:8080)

```bash
# Wszystkie dostępne z kontenera jako mock-api:8080

curl http://localhost:8080/health
curl http://localhost:8080/users
curl http://localhost:8080/products
curl http://localhost:8080/orders
curl http://localhost:8080/data
```

### PostgreSQL (localhost:5432)

```bash
# Z hosta
psql -h localhost -U streamware -d streamware

# Z kontenera
docker-compose exec postgres psql -U streamware -d streamware

# Dostępne tabele:
# - users
# - products
# - orders
# - events
# - logs
```

### RabbitMQ Management (localhost:15672)

```bash
# Otwórz w przeglądarce
http://localhost:15672

# Login: streamware / streamware
```

### Jupyter Lab (localhost:8888)

```bash
# Otwórz w przeglądarce
http://localhost:8888

# Bez hasła (development only!)
```

## 🐛 Troubleshooting

### Problem: Kontenery nie startują

```bash
# Sprawdź logi
docker-compose logs

# Restart wszystkiego
docker-compose down
docker-compose up -d
```

### Problem: "Cannot connect to mock-api"

```bash
# Sprawdź czy mock-api działa
docker-compose ps mock-api

# Sprawdź logi mock-api
docker-compose logs mock-api

# Restart mock-api
docker-compose restart mock-api
```

### Problem: "PostgreSQL connection failed"

```bash
# Poczekaj na inicjalizację (~30 sekund)
docker-compose logs postgres | grep "ready to accept"

# Jeśli długo się inicjalizuje, restart
docker-compose restart postgres
```

### Problem: "Kafka not available"

```bash
# Kafka wymaga czasu na start
docker-compose logs kafka | grep "started"

# Sprawdź czy zookeeper działa
docker-compose ps zookeeper
```

## 🔄 Przykładowy Workflow

```bash
# 1. Start
docker-compose up -d

# 2. Poczekaj na inicjalizację
sleep 30

# 3. Test connection
docker-compose exec streamware sq get mock-api:8080/health --json

# 4. Pobierz dane
docker-compose exec streamware sq get mock-api:8080/users --json --save /data/users.json

# 5. Przekształć
docker-compose exec streamware sq file /data/users.json --json --csv --save /data/users.csv

# 6. Załaduj do bazy
docker-compose exec streamware sq postgres "SELECT * FROM users" --csv

# 7. Sprawdź pliki
docker-compose exec streamware ls -lh /data/

# 8. Gotowe!
```

## 📚 Więcej Dokumentacji

- **[docker/README.md](docker/README.md)** - Pełna dokumentacja Docker
- **[docs/QUICK_CLI.md](docs/QUICK_CLI.md)** - Quick CLI guide
- **[docs/DSL_EXAMPLES.md](docs/DSL_EXAMPLES.md)** - Python DSL examples
- **[SUMMARY.md](SUMMARY.md)** - Complete project summary

## 🛑 Zatrzymanie

```bash
# Zatrzymaj kontenery (zachowaj dane)
docker-compose stop

# Zatrzymaj i usuń kontenery (zachowaj dane)
docker-compose down

# Usuń wszystko włącznie z danymi
docker-compose down -v

# Usuń obrazy
docker-compose down --rmi all
```

## 🎉 Przykłady "One-liner"

```bash
# Quick test z zewnątrz kontenera
docker-compose exec streamware sq get mock-api:8080/users --json | head -20

# Python one-liner
docker-compose exec streamware python3 -c "from streamware import quick; print(quick('http://mock-api:8080/health').json().run())"

# PostgreSQL query
docker-compose exec streamware sq postgres "SELECT COUNT(*) FROM users" --json

# File transform
docker-compose exec streamware bash -c "echo '{\"test\":1}' > /tmp/t.json && sq file /tmp/t.json --json"
```

## 🚀 Co Dalej?

1. **Eksploruj przykłady:**
   ```bash
   docker-compose exec streamware python examples/basic_usage.py
   docker-compose exec streamware python examples/dsl_examples.py
   ```

2. **Testuj w Jupyter:**
   ```bash
   open http://localhost:8888
   # Create new notebook and experiment!
   ```

3. **Stwórz własny pipeline:**
   ```bash
   docker-compose exec streamware bash
   # Your creativity here!
   ```

## 📞 Pomoc

Jeśli coś nie działa:
1. Sprawdź `docker-compose logs`
2. Zobacz `docker/README.md` dla szczegółów
3. Uruchom testy: `docker/test-basic.sh`

---

**Happy streaming! 🎉**
