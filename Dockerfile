FROM python:3.11-slim

WORKDIR /app

# Installa Poetry
RUN pip install poetry

# Configura Poetry per non creare un virtualenv interno al container
RUN poetry config virtualenvs.create false

# Copia i file per le dipendenze
COPY pyproject.toml poetry.lock* ./

# Installa le dipendenze
RUN poetry install --no-interaction --no-ansi --no-root

# Copia il codice sorgente
COPY src/ ./src/

# Mantiene il container "acceso" e dormiente in attesa dei comandi cron
CMD ["tail", "-f", "/dev/null"]
