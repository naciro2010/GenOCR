# Guide de Déploiement GenOCR

Ce guide explique comment déployer GenOCR sur différentes plateformes gratuites.

## 🚀 Option 1: Hugging Face Spaces (RECOMMANDÉ)

Hugging Face Spaces offre 16GB de RAM et un déploiement Docker gratuit.

### Déploiement automatique avec GitHub Actions

1. **Créez un Space sur Hugging Face**
   - Allez sur https://huggingface.co/spaces
   - Cliquez sur "Create new Space"
   - Choisissez "Docker" comme SDK
   - Nommez votre Space (ex: `votre-username/genocr`)

2. **Configurez le secret GitHub**
   - Allez dans Settings > Secrets and variables > Actions de votre repo GitHub
   - Créez un nouveau secret `HF_TOKEN`
   - Obtenez votre token sur https://huggingface.co/settings/tokens

3. **Mettez à jour le workflow**
   - Éditez `.github/workflows/deploy.yml`
   - Remplacez `<YOUR_HF_USERNAME>/<YOUR_SPACE_NAME>` par votre username/space-name
   - Exemple: `naciro2010/genocr`

4. **Déployez**
   ```bash
   git push origin main
   ```
   Le workflow GitHub Actions déploiera automatiquement!

### Déploiement manuel

```bash
# Installez le CLI
pip install huggingface-hub

# Connectez-vous
huggingface-cli login

# Uploadez le repo
huggingface-cli upload votre-username/genocr . --repo-type=space
```

Votre app sera disponible sur: `https://huggingface.co/spaces/votre-username/genocr`

---

## 🎨 Option 2: Render.com

Render offre un free tier avec 512MB RAM (suffisant pour tester).

### Étapes

1. **Créez un compte sur Render.com**
   - Allez sur https://render.com et inscrivez-vous

2. **Créez un nouveau Web Service**
   - Cliquez sur "New +" puis "Web Service"
   - Connectez votre repo GitHub
   - Sélectionnez le repo `GenOCR`

3. **Configuration**
   - **Runtime**: Docker
   - **Plan**: Free
   - Le fichier `render.yaml` sera détecté automatiquement

4. **Déployez**
   - Cliquez sur "Create Web Service"
   - Le déploiement démarre automatiquement

Votre app sera disponible sur: `https://genocr.onrender.com`

**Note**: Le free tier de Render met l'app en veille après 15 min d'inactivité.

---

## 🚂 Option 3: Railway.app

Railway offre $5 de crédit gratuit par mois.

### Étapes

1. **Créez un compte sur Railway**
   - Allez sur https://railway.app
   - Connectez-vous avec GitHub

2. **Créez un nouveau projet**
   - Cliquez sur "New Project"
   - Sélectionnez "Deploy from GitHub repo"
   - Choisissez le repo `GenOCR`

3. **Configuration**
   Railway détecte automatiquement le Dockerfile.

   Ajoutez ces variables d'environnement:
   - `PORT`: 8080 (Railway l'injecte automatiquement)
   - `MAX_CONTENT_LENGTH`: 26214400

4. **Déployez**
   - Railway déploie automatiquement à chaque push sur main

---

## ✈️ Option 4: Fly.io

Fly.io offre un free tier généreux avec des machines partout dans le monde.

### Installation

```bash
# Installez Fly CLI
curl -L https://fly.io/install.sh | sh

# Ou avec brew sur macOS
brew install flyctl
```

### Déploiement

```bash
# Login
flyctl auth login

# Lancez l'app depuis le dossier du projet
flyctl launch

# Suivez les instructions:
# - Nom de l'app: genocr (ou autre)
# - Région: choisissez la plus proche
# - Base de données: Non
# - Deploy: Oui

# Pour les déploiements futurs
flyctl deploy
```

Configuration dans `fly.toml` (généré automatiquement):
```toml
app = "genocr"

[env]
  PORT = "8080"
  MAX_CONTENT_LENGTH = "26214400"

[[services]]
  http_checks = []
  internal_port = 8080
  processes = ["app"]
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

---

## 🐳 Option 5: Déploiement local avec Docker

Pour tester localement:

```bash
# Build
docker build -t genocr .

# Run
docker run -p 7860:7860 \
  -e MAX_CONTENT_LENGTH=26214400 \
  -e APP_ORIGIN="http://localhost:7860" \
  genocr

# Accédez à http://localhost:7860
```

---

## 🔧 Variables d'environnement

Toutes les plateformes supportent ces variables:

| Variable | Valeur par défaut | Description |
|----------|------------------|-------------|
| `PORT` | 7860 | Port d'écoute |
| `MAX_CONTENT_LENGTH` | 26214400 | Taille max upload (25MB) |
| `APP_ORIGIN` | - | Origine CORS (optionnel) |
| `USE_DEEP_TABLES` | false | Modèles ML avancés |
| `SYNC_PIPELINE` | false | Pipeline synchrone |
| `FORCE_HTTPS` | false | Redirection HTTPS |

---

## 📊 Comparaison des plateformes

| Plateforme | RAM | Stockage | Build time | Cold start | Coût |
|------------|-----|----------|------------|------------|------|
| **Hugging Face** | 16GB | 50GB | ~5min | Aucun | Gratuit |
| **Render** | 512MB | Limité | ~3min | ~30s | Gratuit |
| **Railway** | 512MB | 1GB | ~2min | Aucun | $5/mois crédit |
| **Fly.io** | 256MB | 3GB | ~2min | Rapide | Gratuit (limité) |

**Recommandation**:
- **Production**: Hugging Face Spaces (plus de ressources)
- **Test rapide**: Render.com (déploiement le plus simple)
- **Scaling**: Railway ou Fly.io (meilleur contrôle)

---

## 🐛 Dépannage

### L'app ne démarre pas

Vérifiez les logs:
- **Hugging Face**: Onglet "Logs" dans votre Space
- **Render**: Section "Logs" du dashboard
- **Railway**: Onglet "Deployments" > "View Logs"
- **Fly.io**: `flyctl logs`

### Erreur "Out of memory"

Réduisez `MAX_CONTENT_LENGTH` ou passez à une plateforme avec plus de RAM.

### Les uploads échouent

1. Vérifiez que `MAX_CONTENT_LENGTH` est configuré
2. Assurez-vous que le fichier est PDF/PNG/JPG
3. Vérifiez les logs pour les erreurs OCR

---

## 📚 Ressources

- [Documentation Hugging Face Spaces](https://huggingface.co/docs/hub/spaces)
- [Documentation Render](https://render.com/docs)
- [Documentation Railway](https://docs.railway.app)
- [Documentation Fly.io](https://fly.io/docs)

---

**Besoin d'aide?** Ouvrez une issue sur GitHub!
