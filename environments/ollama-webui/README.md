# Ollama + Open-WebUI dla UM790 Pro

Środowisko LLM z interfejsem webowym i obsługą GPU AMD Radeon 780M.

## Szybki start

```bash
# 1. Konfiguracja hosta (jednorazowo)
sudo ./setup-host.sh
# Zrestartuj system

# 2. Pobierz modele
./download-models.sh

# 3. Uruchom
./start.sh

# 4. Otwórz przeglądarkę
# http://localhost:3000
```

## Pliki

| Plik | Opis |
|------|------|
| `docker-compose.yml` | Konfiguracja Podman/Docker |
| `setup-host.sh` | Instalacja ROCm na hoście |
| `download-models.sh` | Pobieranie modeli dla offline |
| `start.sh` | Uruchomienie środowiska |
| `stop.sh` | Zatrzymanie środowiska |

## Porty

- **Ollama API:** http://localhost:11434
- **Open-WebUI:** http://localhost:3000

## Zarządzanie modelami

```bash
# Lista modeli
podman exec ollama ollama list

# Dodaj model
podman exec ollama ollama pull llama3.2:3b

# Usuń model
podman exec ollama ollama rm model_name
```

## Logi

```bash
podman logs -f ollama
podman logs -f open-webui
```
