# test

Generated with Streamware WebApp component.

## Framework

Flask

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Run

```bash
# Using sq
sq webapp serve --framework flask --port 5000

# Or directly
python app.py
```

## Deploy

```bash
sq deploy k8s --apply --file deployment.yaml
```

## Built with Streamware

https://github.com/softreck/streamware
