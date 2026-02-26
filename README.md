# CROUS Notifier

Surveille [trouverunlogement.lescrous.fr](https://trouverunlogement.lescrous.fr) et envoie une alerte Telegram dès qu'un nouveau logement étudiant est disponible. Déployable sur Heroku.

## Fonctionnalités

- Vérifie les nouvelles annonces CROUS à intervalle configurable
- Envoie des notifications Telegram avec nom, adresse, loyer et lien
- Filtrage par ville et loyer maximum optionnel
- Interface web pour consulter les annonces suivies, les logs en direct et les paramètres
- Bot Telegram : envoyer n'importe quel message affiche l'état du système, envoyer `Logs` affiche tout l'historique
- Compatible mode anonyme ou mode connecté (via cookies sauvegardés)

## Installation

### 1. Créer un bot Telegram

1. Écrire à [@BotFather](https://t.me/BotFather) → `/newbot` → copier le **token**
2. Écrire à [@userinfobot](https://t.me/userinfobot) → copier votre **chat ID**

### 2. Configurer l'environnement

```bash
cp .env.example .env
```

Éditer `.env` :

```env
TELEGRAM_BOT_TOKEN=votre_token
TELEGRAM_CHAT_ID=votre_chat_id
LOCATIONS=Paris,Evry          # villes à surveiller (séparées par des virgules)
CHECK_INTERVAL_MINUTES=10
MAX_PRICE=                    # loyer maximum en € (optionnel)
USE_AUTH=false
WEB_PASSWORD=choisir_un_mot_de_passe
```

### 3. Lancer en local

```bash
pip install -r requirements.txt
python main.py --web           # démarre l'interface web + le notifier
```

L'interface web est disponible sur `http://localhost:5000`.

## Mode connecté

Les sessions connectées peuvent afficher plus d'annonces. Pour l'activer :

1. Installer Playwright : `pip install playwright && playwright install chromium`
2. Lancer `python main.py --login` — une fenêtre navigateur s'ouvre, se connecter au CROUS puis la fermer
3. Les cookies sont sauvegardés dans `cookies.json` et envoyés automatiquement sur Heroku (si `HEROKU_API_KEY` est défini)
4. Activer `USE_AUTH=true` dans les paramètres ou dans `.env`

> Les cookies expirent régulièrement. Relancer `--login` en cas d'erreur de scraping.

## Commandes du bot Telegram

| Message | Réponse |
|---------|---------|
| N'importe quoi | État du système (dernière vérification, annonces suivies, mode auth, logs récents) |
| `Logs` | Historique complet des logs (100 dernières lignes) |

## Déploiement sur Heroku

### Prérequis

- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
- Docker installé en local

### Étapes

```bash
heroku create nom-de-votre-app
heroku stack:set container --app nom-de-votre-app

heroku config:set \
  TELEGRAM_BOT_TOKEN=... \
  TELEGRAM_CHAT_ID=... \
  LOCATIONS=Paris \
  CHECK_INTERVAL_MINUTES=10 \
  WEB_PASSWORD=... \
  USE_AUTH=false \
  --app nom-de-votre-app

git push heroku master
```

Ajouter `HEROKU_API_KEY` et `HEROKU_APP_NAME` dans le `.env` local pour que `--login` puisse pousser les cookies sur Heroku automatiquement.

### Renouveler les cookies sur Heroku

```bash
python main.py --login   # se connecte en local et pousse les cookies sur Heroku
heroku ps:restart --app nom-de-votre-app
```

## Structure du projet

```
main.py          – Point d'entrée CLI (--web, --login, --run)
web.py           – Application Flask, routes, boucle de polling
scraper.py       – Scraper du site CROUS
notifier.py      – Compare les annonces et envoie les alertes Telegram
state.py         – Persistance des annonces vues (state.json)
auth.py          – Connexion par cookies via Playwright
telegram_bot.py  – send_message() + bot de statut
config.py        – Configuration via variables d'environnement
cities.txt       – Plus de 200 villes françaises pour le sélecteur
```

## Variables d'environnement

| Variable | Requis | Défaut | Description |
|----------|--------|--------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Token du bot via @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | — | Votre ID Telegram |
| `LOCATIONS` | ✅ | — | Villes à surveiller (séparées par des virgules) |
| `CHECK_INTERVAL_MINUTES` | | `10` | Fréquence de vérification |
| `MAX_PRICE` | | aucun | Loyer maximum en € |
| `USE_AUTH` | | `false` | Utiliser les cookies de connexion |
| `WEB_PASSWORD` | | — | Mot de passe de l'interface web |
| `HEROKU_API_KEY` | | — | Pour pousser les cookies sur Heroku |
| `HEROKU_APP_NAME` | | — | Nom de votre app Heroku |
