# Streamware - Uproszczone DSL (Domain-Specific Language)

Przewodnik po różnych stylach tworzenia pipeline'ów w Streamware.

## 📋 Spis Treści

1. [Oryginalny DSL](#oryginalny-dsl)
2. [Fluent API](#1-fluent-api---method-chaining)
3. [Context Manager](#2-context-manager)
4. [Function Composition](#3-function-composition)
5. [Quick Shortcuts](#4-quick-shortcuts)
6. [Builder Pattern](#5-builder-pattern)
7. [Decorators](#6-decorators)
8. [Porównanie](#porównanie-stylów)

## Oryginalny DSL

**Obecny sposób** (URI-based):

```python
from streamware import flow

result = (
    flow("http://api.example.com/data")
    | "transform://json"
    | "file://write?path=output.json"
).run()
```

## 1. Fluent API - Method Chaining

**Najbardziej Pythonowy styl** 🐍

```python
from streamware.dsl import Pipeline

# Prosty przykład
result = (
    Pipeline()
    .http_get("https://api.example.com/data")
    .to_json()
    .save("output.json")
    .run()
)

# Złożony przykład
result = (
    Pipeline()
    .http_get("https://api.example.com/users")
    .to_json()
    .filter(lambda x: x['age'] > 18)
    .map(lambda x: {'name': x['name'], 'email': x['email']})
    .to_csv()
    .save("adults.csv")
    .run()
)

# Z bazą danych
result = (
    Pipeline()
    .from_postgres("SELECT * FROM users WHERE active=true")
    .to_json()
    .to_kafka("users-topic")
    .run()
)

# Email
result = (
    Pipeline()
    .read_file("report.html")
    .send_email(
        to="user@example.com",
        subject="Monthly Report"
    )
    .run()
)
```

### Dostępne Metody

**HTTP:**
- `.http_get(url, **params)`
- `.http_post(url, data=None)`

**File:**
- `.read_file(path)`
- `.save(path, mode="write")`

**Transform:**
- `.to_json(pretty=False)`
- `.to_csv(delimiter=",")`
- `.to_base64(decode=False)`
- `.jsonpath(query)`

**Processing:**
- `.filter(predicate)`
- `.map(func)`

**Messaging:**
- `.to_kafka(topic, **kwargs)`
- `.from_kafka(topic, group="default")`

**Database:**
- `.to_postgres(table, **kwargs)`
- `.from_postgres(sql)`

**Communication:**
- `.send_email(to, subject, **kwargs)`
- `.send_slack(channel, token)`

## 2. Context Manager

**Dla operacji krok-po-kroku:**

```python
from streamware.dsl import pipeline

# Prosty przykład
with pipeline() as p:
    data = p.read("input.json")
    data = p.transform(data, "json")
    p.save(data, "output.json")

# Złożony przykład
with pipeline() as p:
    # Pobierz dane
    data = p.http_get("https://api.example.com/users")
    
    # Przekształć
    json_data = p.transform(data, "json")
    
    # Filtruj (custom logic)
    adults = [user for user in json_data if user['age'] >= 18]
    
    # Zapisz
    csv_data = p.transform(adults, "csv")
    p.save(csv_data, "adults.csv")
```

## 3. Function Composition

**Funkcyjny styl:**

```python
from streamware.dsl import compose, read_file, to_json, to_csv, save_file

# Zdefiniuj pipeline
process_data = compose(
    read_file("input.json"),
    to_json,
    to_csv,
    save_file("output.csv")
)

# Wykonaj
result = process_data()

# Custom funkcje
def filter_adults(data):
    return [user for user in data if user['age'] >= 18]

def extract_emails(data):
    return [user['email'] for user in data]

# Złożony pipeline
process_users = compose(
    read_file("users.json"),
    to_json,
    filter_adults,
    extract_emails,
    save_file("emails.txt")
)

result = process_users()
```

## 4. Quick Shortcuts

**Dla szybkich operacji:**

```python
from streamware.dsl import quick

# Jedna linijka!
quick("http://api.example.com/data").json().save("data.json")

# Łańcuch operacji
quick("file://read?path=input.json").csv().save("output.csv")

# Z HTTP
quick("https://api.example.com/users").json().save("users.json")
```

## 5. Builder Pattern

**Dla czytelnych, złożonych pipeline'ów:**

```python
from streamware.dsl import PipelineBuilder

# ETL Pipeline
result = (
    PipelineBuilder()
    .source_postgres("SELECT * FROM raw_data WHERE date=CURRENT_DATE")
    .transform_json()
    .filter_by(lambda x: x['status'] == 'active')
    .transform_csv()
    .sink_file("processed.csv")
    .execute()
)

# Streaming pipeline
result = (
    PipelineBuilder()
    .source_kafka("events", group="processor")
    .transform_json()
    .sink_postgres("events_table")
    .execute()
)

# File processing
result = (
    PipelineBuilder()
    .source_file("input.json")
    .transform_json()
    .transform_base64(decode=False)
    .sink_file("encoded.txt")
    .execute()
)
```

## 6. Decorators

**Dla reużywalnych komponentów:**

```python
from streamware.dsl import as_component, pipeline_step

# Zarejestruj funkcję jako komponent
@as_component("uppercase")
def to_uppercase(data):
    return data.upper() if isinstance(data, str) else data

# Użyj
from streamware import flow
result = flow("uppercase://").run("hello world")  # "HELLO WORLD"

# Pipeline step wrapper
@pipeline_step("transform://json")
def process_users(data):
    # JSON już sparsowany przez transform://json
    return [u for u in data if u['active']]

# Custom transformacje
@as_component("extract_emails")
def extract_emails(data):
    if isinstance(data, list):
        return [item.get('email') for item in data if 'email' in item]
    return []

# Użyj w pipeline
result = (
    flow("file://read?path=users.json")
    | "transform://json"
    | "extract_emails://"
    | "file://write?path=emails.txt"
).run()
```

## Porównanie Stylów

### Przykład: Pobierz użytkowników, filtruj dorosłych, zapisz jako CSV

**1. Oryginalny DSL:**
```python
result = (
    flow("http://api.example.com/users")
    | "transform://json"
    | "transform://jsonpath?query=$[?(@.age>=18)]"
    | "transform://csv"
    | "file://write?path=adults.csv"
).run()
```

**2. Fluent API:**
```python
result = (
    Pipeline()
    .http_get("https://api.example.com/users")
    .to_json()
    .filter(lambda x: x['age'] >= 18)
    .to_csv()
    .save("adults.csv")
    .run()
)
```

**3. Context Manager:**
```python
with pipeline() as p:
    users = p.http_get("https://api.example.com/users")
    json_users = p.transform(users, "json")
    adults = [u for u in json_users if u['age'] >= 18]
    csv_data = p.transform(adults, "csv")
    p.save(csv_data, "adults.csv")
```

**4. Function Composition:**
```python
def filter_adults(users):
    return [u for u in users if u['age'] >= 18]

process = compose(
    http_get("https://api.example.com/users"),
    to_json,
    filter_adults,
    to_csv,
    save_file("adults.csv")
)
result = process()
```

**5. Builder Pattern:**
```python
result = (
    PipelineBuilder()
    .source_http("https://api.example.com/users")
    .transform_json()
    .filter_by(lambda x: x['age'] >= 18)
    .transform_csv()
    .sink_file("adults.csv")
    .execute()
)
```

## Zalety i Wady

### Oryginalny DSL (URI-based)
✅ **Zalety:**
- Elastyczny, uniwersalny
- Kompatybilny z CLI
- Łatwy do serializacji

❌ **Wady:**
- Długie URI stringi
- Mało Pythonowy
- Trudniejszy autocomplete

### Fluent API
✅ **Zalety:**
- Bardzo Pythonowy
- Świetny autocomplete
- Czytelny
- Type hints

❌ **Wady:**
- Więcej kodu
- Wymaga importu nowej klasy

### Context Manager
✅ **Zalety:**
- Krok-po-kroku logika
- Łatwo debugować
- Dobrze dla złożonej logiki

❌ **Wady:**
- Więcej boilerplate
- Mniej "pipeline-like"

### Function Composition
✅ **Zalety:**
- Funkcyjny styl
- Reużywalne komponenty
- Composable

❌ **Wady:**
- Mniej intuicyjny dla beginnersów
- Wymaga definicji funkcji

### Builder Pattern
✅ **Zalety:**
- Bardzo czytelny
- Nazwane metody
- IDE-friendly

❌ **Wady:**
- Więcej kodu
- Ograniczona elastyczność

## Rekomendacje

**Dla prostych zadań:**
```python
# Quick shortcuts
quick("http://api.example.com").json().save("data.json")
```

**Dla typowych pipeline'ów:**
```python
# Fluent API
Pipeline().http_get(url).to_json().save(path).run()
```

**Dla złożonej logiki:**
```python
# Context Manager
with pipeline() as p:
    # custom logic here
    pass
```

**Dla reużywalnych komponentów:**
```python
# Decorators
@as_component("my_transformer")
def transform(data):
    return processed_data
```

## Instalacja

Nowe DSL jest już zawarte w Streamware:

```python
# Import
from streamware.dsl import (
    Pipeline,          # Fluent API
    pipeline,          # Context Manager
    quick,             # Quick shortcuts
    PipelineBuilder,   # Builder pattern
    compose,           # Function composition
    as_component,      # Decorator
)
```

## Przykłady Praktyczne

### 1. Web Scraping z Fluent API

```python
from streamware.dsl import Pipeline

scrape_products = (
    Pipeline()
    .http_get("https://shop.example.com/products")
    .to_json()
    .jsonpath("$.products[*]")
    .filter(lambda p: p['price'] < 50)
    .map(lambda p: {'name': p['name'], 'price': p['price']})
    .to_csv()
    .save("cheap_products.csv")
)

result = scrape_products.run()
```

### 2. ETL z Builder Pattern

```python
from streamware.dsl import PipelineBuilder

etl = (
    PipelineBuilder()
    .source_postgres("SELECT * FROM orders WHERE date = CURRENT_DATE")
    .transform_json()
    .filter_by(lambda o: o['status'] == 'completed')
    .sink_kafka("completed-orders")
    .execute()
)
```

### 3. Data Processing z Context Manager

```python
from streamware.dsl import pipeline

with pipeline() as p:
    # Extract
    raw_data = p.read("raw_data.json")
    
    # Transform
    data = p.transform(raw_data, "json")
    cleaned = [d for d in data if d.get('valid')]
    
    # Load
    csv = p.transform(cleaned, "csv")
    p.save(csv, "clean_data.csv")
```

## Migracja z Oryginalnego DSL

Łatwa migracja krok po kroku:

**Przed:**
```python
flow("http://api.example.com") | "transform://json" | "file://write?path=out.json"
```

**Po (Fluent API):**
```python
Pipeline().http_get("http://api.example.com").to_json().save("out.json").run()
```

**Po (Quick):**
```python
quick("http://api.example.com").json().save("out.json")
```

---

Który styl preferujesz? Możesz używać wszystkich jednocześnie! 🚀
