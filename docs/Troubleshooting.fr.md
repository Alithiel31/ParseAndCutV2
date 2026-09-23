# Troubleshooting

🇬🇧 [English version](./Troubleshooting.md)

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

## 2. Les gros uploads (>100 Mo) restent bloqués indéfiniment derrière Cloudflare

### Symptôme

Uploader un gros fichier audio (ex. 174 Mo) via le domaine public
(`parseandcut.alithiel31.dev`, derrière le tunnel Cloudflare) laisse l'interface bloquée
indéfiniment sur l'étape « Transcription Whisper… ». `docker compose logs -f backend` n'affiche
jamais de ligne `📥 Fichier reçu` pour cette requête, et `docker compose logs -f frontend` (log
d'accès nginx) n'affiche pas non plus le `POST /api/transcribe` correspondant — la requête
n'atteint jamais le Pi. Un petit fichier (quelques Mo) sur exactement le même chemin de code
aboutit normalement en quelques secondes.

### Root cause

Cloudflare impose sa propre taille maximale de requête pour tout le trafic qui transite par son
edge — tunnel inclus, puisqu'un tunnel n'a pas d'IP publique permettant de contourner le proxy via
un enregistrement DNS-only. Ce plafond est de **100 Mo sur les plans Free et Pro**, 200 Mo sur
Business, 500 Mo+ sur Enterprise (voir la
[doc Cloudflare sur les limites d'upload](https://developers.cloudflare.com/cache/concepts/default-cache-behavior/#upload-limits)).
Avant ce diagnostic, `MAX_UPLOAD_SIZE_MB` (backend) et la vérification de taille côté frontend
avaient toutes deux été relevées à 300 Mo, laissant les utilisateurs sélectionner et commencer à
uploader des fichiers que Cloudflare bloquait ensuite silencieusement avant même qu'ils
n'atteignent nginx ou le backend — sans aucune erreur affichée, juste un indicateur de progression
qui tourne indéfiniment.

### Ce qui a résolu le problème

`MAX_UPLOAD_SIZE_MB` et le `MAX_SIZE_MB` côté frontend ont tous les deux été ramenés à **100 Mo**,
alignés sur le vrai plafond Cloudflare Free/Pro, pour que les fichiers trop volumineux soient
rejetés immédiatement avec une erreur claire plutôt que de rester bloqués en silence.

### Point de vigilance pour l'hébergement actuel

Le `client_max_body_size` de nginx (500 Mo, `frontend/nginx.conf`) est volontairement laissé plus
haut — ce n'est pas lui la contrainte bloquante ici, il n'a pas besoin de suivre la limite
Cloudflare. Si un plafond d'upload plus élevé devient nécessaire un jour, les seules vraies options
sont de monter en gamme sur Cloudflare (Business → 200 Mo) ou de découper l'upload en plusieurs
morceaux côté client ; désactiver le proxy Cloudflare (DNS-only) n'est pas compatible avec un
tunnel Cloudflare.

---

## 3. Fichiers longs (>10-15 min) : HTTP 524 malgré une taille sous la limite

### Symptôme

Un fichier audio qui passe la limite de taille (ex. 80 Mo, ~1h d'audio en AAC) échoue avec une
erreur HTTP 524 pendant l'étape « Transcription Whisper… », contrairement à un petit fichier de
test qui aboutit normalement. Contrairement à l'incident n°2, ce n'est pas silencieux : le
navigateur reçoit une vraie réponse d'erreur — juste très en retard.

### Root cause

**524 est un code d'erreur spécifique à Cloudflare** : « A timeout occurred », renvoyé quand la
connexion entre Cloudflare et l'origine (ici, le tunnel vers le Pi) s'établit bien, mais que
l'origine ne renvoie pas de réponse complète dans le délai imparti. Ce délai (« Edge Response
Timeout ») est fixé à **100 secondes sur les plans Free/Pro/Business**, et n'est réglable qu'en
Enterprise.

Or `/api/transcribe` était un endpoint entièrement synchrone : upload, découpage FFmpeg,
transcription Whisper **chunk par chunk en boucle séquentielle** (`CHUNK_DURATION` = 10 min, donc
6 appels API pour 1h d'audio), puis éventuellement résumé LLM — le tout dans une seule requête
HTTP. Le code prévoyait déjà jusqu'à 480-600s pour ce pipeline côté nginx/Groq (voir
`app/config.py`), ce qui ne servait à rien : Cloudflare tranche la connexion à 100s quoi qu'il
arrive, avant même que le Pi ait fini son traitement.

### Ce qui a résolu le problème

Le pipeline a été rendu asynchrone : `POST /api/transcribe/start` sauvegarde le fichier et
répond immédiatement (202 + `job_id`) pendant que le traitement tourne en tâche de fond sur le
Pi ; le frontend interroge ensuite `GET /api/transcribe/status/{job_id}` toutes les ~3s jusqu'à
obtenir un statut terminal. Chaque requête individuelle reste rapide (bien sous 100s), seul le
traitement de fond peut prendre le temps qu'il faut. L'ancien endpoint synchrone (`/process` et
l'alias `/api/transcribe`) est conservé tel quel pour ne pas casser d'éventuels autres clients de
l'API (ex. la PWA séparée).

### Point de vigilance pour l'hébergement actuel

Le store de jobs est un simple fichier JSON par job sur disque (`app/services/jobs.py`), pas une
solution en mémoire : le backend tourne avec 2 workers Uvicorn (`Dockerfile`), et un dict en
mémoire ne serait pas visible d'un worker à l'autre selon celui qui reçoit la requête de statut.
Un job jamais récupéré par le client (onglet fermé en cours de route, etc.) est nettoyé
automatiquement au bout de 2h.

---

## Signaler un nouveau problème

Si votre incident n'est pas celui documenté ci-dessus, ouvrez une issue en suivant le template fourni. Incluez les logs pertinents (`docker logs <container>` en prod, sortie console en local) et ne collez jamais de vraie valeur de `GROQ_API_KEY`.
