# Verwende ein leichtes Python-Image
FROM python:3.8-alpine

# Arbeitsverzeichnis festlegen
WORKDIR /app

# Abhängigkeiten installieren
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Anwendungsdateien kopieren
COPY bin /app/

# Standardport setzen
EXPOSE 5588

# Set Folder Rights
RUN chmod -R 755 /app

# Anwendung starten
CMD ["python", "/app/app.py"]