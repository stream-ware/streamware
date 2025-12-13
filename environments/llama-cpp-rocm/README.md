# llama.cpp + ROCm dla UM790 Pro

Wysokowydajne środowisko LLM z pełną akceleracją GPU AMD Radeon 780M (RDNA3).

## Szybki start

```bash
# 1. Pobierz modele GGUF
./download-models.sh

# 2. Zbuduj i uruchom (pierwsze uruchomienie ~15 min)
./start.sh

# 3. Test API
curl http://localhost:8080/v1/models
```

## Pliki

| Plik | Opis |
|------|------|
| `Dockerfile` | Obraz z ROCm + llama.cpp |
| `docker-compose.yml` | Konfiguracja z WebUI |
| `download-models.sh` | Pobieranie modeli GGUF |
| `start.sh` | Uruchomienie serwera |
| `stop.sh` | Zatrzymanie serwera |
| `benchmark.sh` | Test wydajności |

## API (OpenAI-compatible)

```bash
# Lista modeli
curl http://localhost:8080/v1/models

# Chat completion
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Completion
curl http://localhost:8080/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a haiku about programming:"}'
```

## Zmiana modelu

```bash
# Uruchom z innym modelem
./start.sh mistral-7b-q4.gguf

# Lub zmień symlink
ln -sf mistral-7b-q4.gguf models/model.gguf
./start.sh
```

## Benchmark

```bash
./benchmark.sh
# lub z konkretnym modelem:
./benchmark.sh llama-3.2-3b-q4.gguf
```

## Oczekiwana wydajność na 780M

| Model | Rozmiar | Prompt | Generation |
|-------|---------|--------|------------|
| 3B Q4 | ~2GB | ~100 t/s | ~20 t/s |
| 7B Q4 | ~4GB | ~50 t/s | ~10 t/s |
