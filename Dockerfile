# On utilise une version légère de Python
FROM python:3.10-slim

# On installe FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Empêche Python de mettre en cache les logs 
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# On installe les bibliothèques
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# On copie tout le projet 

COPY . .

# On expose le port utilisé 
EXPOSE 5000

# On lance le serveur web
CMD ["python", "meetupKiller.py"]