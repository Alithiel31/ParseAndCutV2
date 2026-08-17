# Politique de sécurité

🇬🇧 [English version](./SECURITY.md)

## Versions supportées

**Meetup Killer** (ParseAndCutV2) est un petit projet développé activement et déployé depuis la branche `main`. Seule la dernière version en ligne sur [parseandcut.alithiel31.dev](https://parseandcut.alithiel31.dev) est supportée — il n'y a pas d'anciennes versions maintenues.

## Signaler une vulnérabilité

Si vous trouvez une faille de sécurité (ex : contournement de la validation d'upload, abus de l'API pour faire gonfler la facture Groq, accès aux données d'un autre utilisateur, évasion du conteneur Docker), merci de **ne pas ouvrir d'issue GitHub publique**.

Signalez-la plutôt par email : **contact@alithiel31.dev**

Merci d'inclure :
- Une description du problème et de son impact potentiel
- Les étapes de reproduction (un exemple minimal est idéal)
- Une suggestion de correctif, si vous en avez une

Vous devriez recevoir un accusé de réception sous quelques jours. Ce projet étant maintenu par une seule personne, à titre non professionnel, il n'y a pas de délai garanti formel, mais les signalements valides seront corrigés en priorité et crédités dans le changelog (sauf préférence contraire de votre part).

## Périmètre

Ce périmètre couvre l'API backend (`app/`) et la PWA frontend (`frontend/`) de ce dépôt. Les services tiers dont dépend ce projet (Groq, Cloudflare) doivent être signalés directement à ces fournisseurs.
