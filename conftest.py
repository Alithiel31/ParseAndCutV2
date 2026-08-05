import os
import sys

# Permet à pytest de trouver le package `app` (à la racine du projet)
# quel que soit le répertoire depuis lequel pytest est lancé.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Les tests ne doivent pas dépendre du .env local (clé API réelle, valeurs
# spécifiques à la machine, etc.). On coupe le load_dotenv() de
# app/config.py en simulant un environnement "prod" avant l'import.
os.environ.setdefault("RAILWAY_ENVIRONMENT", "test")
