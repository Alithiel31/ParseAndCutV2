# Troubleshooting

🇬🇧 [English version](./Troubleshooting.en.md)

Ce document retrace un incident réel rencontré lors du premier hébergement du projet (Railway), reconstitué à partir de l'historique git (`c37f8ba`, `db7cfa6`, `bdd1e6d`). Les messages de commit de l'époque sont courts ; ce qui suit décrit ce qui est confirmé par le diff du code et ce qui reste une hypothèse.

---

## 1. `GROQ_API_KEY` invisible pour le process Python sur Railway

### Symptôme

Au démarrage sur Railway, la clé API Groq n'était pas lue correctement par l'application : le log de démarrage affichait l'erreur définie dans le code de l'époque (`CRITICAL ERROR: GROQ_API_KEY is not set in environment variables.`) alors que la variable était bien configurée côté dashboard Railway.

### Ce qui a été tenté

Le code a été modifié en plusieurs passes successives (commits `db7cfa6` « deploy troubleshooting » puis `c37f8ba` « troubleshooting railway ») :

1. Passage de `os.getenv("GROQ_API_KEY")` à `os.environ.get("GROQ_API_KEY")` pour la lecture de la clé.
2. Ajout d'un log affichant les 5 premiers caractères de la clé si elle est bien lue, pour confirmer visuellement dans les logs Railway que la variable arrive au process.
3. **Initialisation prudente du client Groq** : le client n'est plus instancié au chargement du module si la clé est absente — l'app ne crashe donc plus au boot, et l'absence de client est gérée explicitement dans la route `/process` (retour d'une erreur claire plutôt qu'un crash).

```python
# avant
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("CRITICAL ERROR: GROQ_API_KEY is not set in environment variables.")
    client = None
else:
    print(f"Succès : Clé chargée (début: {api_key[:5]})")
client = Groq(api_key=api_key)  # instancié même si la clé est vide !

# après
api_key = os.environ.get("GROQ_API_KEY")
client = None
if api_key:
    try:
        client = Groq(api_key=api_key)
        print(f"✅ Groq Client initialisé (Clé: {api_key[:5]}...)")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation Groq: {e}")
else:
    print("⚠️ WARNING: GROQ_API_KEY est toujours invisible pour Python.")
```

### Root cause

**Non confirmée avec certitude dans l'historique disponible.** Le diff corrige un vrai bug logique (`client = Groq(api_key=api_key)` était exécuté même dans la branche `if not api_key`, ce qui pouvait lever une exception non gérée au chargement du module et faire crasher l'app avant même d'atteindre les routes). Que la variable Railway elle-même ait été mal propagée au process (delay de propagation, mauvais environnement/service ciblé) n'est pas documenté avec certitude — seule la correction défensive côté code est tracée.

### Ce qui a résolu le problème

Le fait de ne plus instancier `Groq(...)` de façon inconditionnelle a supprimé le crash au démarrage, quelle que soit la cause exacte côté Railway. Le projet a par la suite quitté Railway pour un déploiement auto-hébergé Docker + Raspberry Pi (voir [`DEPLOY_PI.md`](./DEPLOY_PI.md)), qui ne dépend plus de l'injection de variables d'environnement par une plateforme tierce.

### Point de vigilance pour l'hébergement actuel

Sur le déploiement Docker/Pi actuel, `GROQ_API_KEY` est lu depuis le fichier `.env` local via `docker-compose.yml` (`env_file: .env`) — un mécanisme différent, plus direct, qui n'a pas reproduit ce problème depuis la migration.

---

## Signaler un nouveau problème

Si votre incident n'est pas celui documenté ci-dessus, ouvrez une issue en suivant le template fourni. Incluez les logs pertinents (`docker logs <container>` en prod, sortie console en local) et ne collez jamais de vraie valeur de `GROQ_API_KEY`.
