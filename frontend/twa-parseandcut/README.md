# TWA — ParseAndCut

`twa-manifest.json` est prêt (package `dev.alithiel31.parseandcut`, domaine
`parseandcut.alithiel31.dev`), ainsi que les workflows CI (`.github/workflows/build-twa.yml`
et `deploy-twa.yml`), calqués sur QcWeather.

**Étape manquante, à faire une fois le PWA en ligne sur son domaine** : générer le
projet Android réel (gradlew, `build.gradle`, ressources, keystore) avec Bubblewrap.
Ça ne peut pas être fait à l'avance car l'outil va chercher le `manifest.webmanifest`
en direct sur `https://parseandcut.alithiel31.dev`.

```bash
npm install -g @bubblewrap/cli
cd twa-parseandcut
bubblewrap init --manifest https://parseandcut.alithiel31.dev/manifest.webmanifest
```

Bubblewrap va reprendre les valeurs de `twa-manifest.json` existant comme défauts,
générer le keystore de signature (`android.keystore`) et le projet Gradle complet.

Ensuite :
1. Récupérer l'empreinte SHA-256 du keystore (`keytool -list -v -keystore android.keystore`)
   et l'ajouter dans `fingerprints` du `twa-manifest.json`.
2. Publier `/.well-known/assetlinks.json` sur le PWA avec cette empreinte (déjà servi
   par le `nginx.conf` du frontend, il ne manque que le fichier `public/.well-known/assetlinks.json`).
3. Configurer les secrets GitHub (`KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_PASSWORD`,
   `PLAY_SERVICE_ACCOUNT_JSON`) comme pour QcWeather.
4. Créer l'appli `dev.alithiel31.parseandcut` dans Play Console et faire une première
   soumission manuelle (obligatoire avant que `deploy-twa.yml` puisse publier via API).
