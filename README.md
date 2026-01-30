# API de Scoring de Risque d'Insolvabilité

Une API REST complète pour l'évaluation du risque de crédit et de l'insolvabilité des clients, intégrant des modèles de Machine Learning avec explica bilité SHAP.

## 📋 Table des matières

- [Caractéristiques](#caractéristiques)
- [Technologies](#technologies)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Endpoints](#endpoints)
- [Exemples](#exemples)
- [Structure du projet](#structure-du-projet)
- [Tests](#tests)
- [Documentation](#documentation)

## 🎯 Caractéristiques

- ✅ **4 Endpoints principales** : Calcul de score, recommandation, simulation, explication
- ✅ **Authentification JWT** : Sécurisation complète des endpoints
- ✅ **Machine Learning** : Modèle Random Forest entraîné sur German Credit Data
- ✅ **Explicabilité SHAP** : Explications détaillées des prédictions
- ✅ **Documentation Swagger** : Documentation interactive via drf-yasg
- ✅ **Validation robuste** : Validation des données sensibles et cohérence
- ✅ **Audit complet** : Journalisation des opérations sensibles
- ✅ **Modèles Django riches** : Client, DemandeCredit, ScoreRisque, HistoriqueFinancier

## 🛠️ Technologies

- **Backend** : Django 4.2.27
- **API** : Django REST Framework 3.15.2
- **Authentification** : djangorestframework-simplejwt 5.3.1
- **Documentation** : drf-yasg 1.21.7
- **Machine Learning** : scikit-learn 1.5.2, pandas 2.2.3, numpy 1.26.4
- **Explicabilité** : SHAP 0.45.1
- **Base de données** : SQLite (développement) / PostgreSQL (production)
- **Versioning** : Git

## 🚀 Installation

### Prérequis

- Python 3.9+
- pip ou uv (recommandé)
- Git

### Étapes d'installation

1. **Cloner le dépôt**
```bash
git clone https://github.com/votre-username/api-scoring-risque.git
cd api-scoring-risque
```

2. **Créer l'environnement virtuel**
```bash
# Avec Python venv
python -m venv .venv

# Activer l'environnement
# Sur Windows
.\.venv\Scripts\activate
# Sur macOS/Linux
source .venv/bin/activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt

# Ou avec uv (plus rapide)
uv pip install -r requirements.txt
```

4. **Appliquer les migrations**
```bash
cd api_scoring_risque
python manage.py migrate
```

5. **Créer un utilisateur administrateur**
```bash
python manage.py createsuperuser
# Suivre les instructions pour créer le compte
```

6. **Créer les données de démonstration**
```bash
python manage.py shell
# Dans le shell Python
from donnees.generate_sample_data import generer_donnees_exemple
generer_donnees_exemple()
```

## ⚙️ Configuration

### Variables d'environnement (.env)

Créer un fichier `.env` à la racine du projet :

```env
# Django
DJANGO_SECRET_KEY=votre-clé-secrète-ici
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de données (SQLite pour développement)
# DB_ENGINE=sqlite3 (par défaut)

# Base de données PostgreSQL (pour production)
# DB_ENGINE=postgresql
# DB_NAME=scoring_risque_db
# DB_USER=postgres
# DB_PASSWORD=votre-mdp
# DB_HOST=localhost
# DB_PORT=5432

# CORS (si nécessaire)
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

### Démarrer le serveur

```bash
cd api_scoring_risque
python manage.py runserver
```

Le serveur démarre sur `http://127.0.0.1:8000/`

## 📖 Utilisation

### 1. Obtenir un token JWT

**Endpoint** : POST `/api/token/`

```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"votre-mdp"}'
```

**Réponse** :
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### 2. Utiliser le token dans les requêtes

Toutes les requêtes vers les endpoints de l'API doivent inclure le token :

```bash
curl -X GET http://localhost:8000/api/clients/ \
  -H "Authorization: Bearer votre_token_access"
```

## 🔌 Endpoints

### 1. Calcul du Score de Risque

**Endpoint** : POST `/api/evaluation-risque/calculer/`

**Description** : Calcule le score de risque pour une demande de crédit

**Paramètres** :
```json
{
  "demande_credit_id": 1,
  "force_recalcul": false,
  "inclure_explications": true
}
```

**Réponse** :
```json
{
  "message": "Score calculé avec succès",
  "score": {
    "id": 1,
    "score": 42.5,
    "categorie_risque": "modere",
    "recommandation": "revision",
    "valeurs_shap": {...}
  },
  "details_prediction": {
    "score_risque": 42.5,
    "probabilite_defaut": 0.425,
    "categorie_risque": "modere",
    "recommandation": "revision"
  }
}
```

---

### 2. Obtenir la Recommandation

**Endpoint** : GET `/api/demandes-credit/{id}/recommandation/`

**Description** : Retourne la recommandation (approbation/rejet) pour une demande

**Réponse** :
```json
{
  "demande": {
    "id": 1,
    "client": "Jean Dupont",
    "montant": 50000,
    "duree": 60,
    "statut": "en_cours"
  },
  "recommandation": "approbation",
  "recommandation_display": "Approbation",
  "justification": "Le profil du client et les conditions du crédit présentent un risque acceptable.",
  "score_details": {...}
}
```

---

### 3. Simuler des Scénarios de Crédit

**Endpoint** : POST `/api/clients/{id}/simuler/`

**Description** : Simule différents scénarios pour un client

**Paramètres** :
```json
{
  "scenarios": [
    {
      "nom": "Scénario optimiste",
      "description": "Augmentation du revenu",
      "parametres": {
        "revenu_mensuel": 7000,
        "dette_totale": 5000
      }
    },
    {
      "nom": "Scénario pessimiste",
      "description": "Réduction des revenus",
      "parametres": {
        "revenu_mensuel": 3000,
        "dette_totale": 15000
      }
    }
  ]
}
```

**Réponse** :
```json
{
  "client": {...},
  "donnees_base": {...},
  "simulations": [
    {
      "scenario_nom": "Scénario optimiste",
      "resultat": {
        "score_risque": 25.3,
        "categorie_risque": "faible",
        "recommandation": "approbation"
      }
    },
    {
      "scenario_nom": "Scénario pessimiste",
      "resultat": {
        "score_risque": 65.8,
        "categorie_risque": "eleve",
        "recommandation": "rejet"
      }
    }
  ],
  "analyse_comparative": {
    "meilleur_scenario": {...},
    "pire_scenario": {...},
    "ecart_scores": 40.5
  }
}
```

---

### 4. Expliquer les Facteurs de Risque

**Endpoint** : GET `/api/evaluation-risque/{id}/expliquer/?format=complet`

**Description** : Explique les facteurs contribuant au score avec SHAP

**Paramètres de requête** :
- `format` : 'texte', 'graphique', ou 'complet' (défaut)

**Réponse** :
```json
{
  "score": {...},
  "demande_credit": {...},
  "client": {...},
  "explications_shap": {
    "facteurs_positifs_detailles": [
      {
        "nom": "revenu_mensuel",
        "valeur": 5000,
        "impact": -15.3,
        "description": "Revenu mensuel stable"
      }
    ],
    "facteurs_negatifs_detailles": [
      {
        "nom": "defauts_paiement",
        "valeur": 2,
        "impact": 20.1,
        "description": "Antécédents de défaut"
      }
    ]
  },
  "facteurs_cles": {
    "principaux_facteurs_positifs": [...],
    "principaux_facteurs_negatifs": [...]
  }
}
```

---

## 💡 Exemples

### Exemple complet : Évaluer un client

```bash
# 1. Se connecter et obtenir le token
TOKEN=$(curl -s -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r '.access')

echo "Token: $TOKEN"

# 2. Créer un client
CLIENT=$(curl -s -X POST http://localhost:8000/api/clients/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nom": "Martin",
    "prenom": "Sophie",
    "email": "sophie.martin@example.com",
    "telephone": "+33612345678",
    "date_naissance": "1985-06-15",
    "age": 40,
    "etat_civil": "marie",
    "nombre_enfants": 2,
    "profession": "cadre",
    "anciennete_emploi": 120,
    "revenu_mensuel": 5500,
    "autres_revenus": 500
  }')

CLIENT_ID=$(echo $CLIENT | jq '.id')
echo "Client créé : $CLIENT_ID"

# 3. Créer une demande de crédit
DEMANDE=$(curl -s -X POST http://localhost:8000/api/demandes-credit/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"client\": $CLIENT_ID,
    \"type_credit\": \"immobilier\",
    \"montant_demande\": 300000,
    \"duree_mois\": 240,
    \"taux_interet\": 3.5,
    \"destination_credit\": \"Achat de bien immobilier\",
    \"avec_garantie\": true,
    \"valeur_garantie\": 350000
  }")

DEMANDE_ID=$(echo $DEMANDE | jq '.id')
echo "Demande créée : $DEMANDE_ID"

# 4. Calculer le score de risque
SCORE=$(curl -s -X POST http://localhost:8000/api/evaluation-risque/calculer/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"demande_credit_id\": $DEMANDE_ID,
    \"inclure_explications\": true
  }")

echo "Score calculé :"
echo $SCORE | jq '.score'

# 5. Obtenir la recommandation
RECOMMANDATION=$(curl -s -X GET http://localhost:8000/api/demandes-credit/$DEMANDE_ID/recommandation/ \
  -H "Authorization: Bearer $TOKEN")

echo "Recommandation :"
echo $RECOMMANDATION | jq '.recommandation'
```

## 📁 Structure du projet

```
api-scoring-risque/
├── api_scoring_risque/              # Configuration Django
│   ├── settings.py                  # Paramètres Django
│   ├── urls.py                      # URLs principales
│   ├── asgi.py                      # Configuration ASGI
│   ├── wsgi.py                      # Configuration WSGI
│   └── logging_config.py            # Configuration du logging
├── application_risque/              # Application principale
│   ├── models.py                    # Modèles Django (Client, DemandeCredit, etc.)
│   ├── serializers.py               # Serializers DRF
│   ├── api_views.py                 # Vues API
│   ├── api_urls.py                  # URLs API
│   ├── urls.py                      # URLs de l'app
│   ├── permissions.py               # Permissions personnalisées
│   ├── validators.py                # Validateurs personnalisés
│   ├── audit.py                     # Logging d'audit
│   ├── signals.py                   # Signaux Django
│   ├── migrations/                  # Migrations de base de données
│   └── tests.py                     # Tests unitaires
├── gestion_modeles/                 # Module Machine Learning
│   ├── gestionnaire_modele.py       # Gestionnaire principal du modèle
│   ├── entrainement.py              # Entraînement du modèle
│   ├── preparation_donnees.py       # Préparation des données
│   ├── modele_risque.py             # Logique du modèle
│   └── explicabilite_shap.py        # Explications SHAP
├── donnees/                         # Données et datasets
│   └── generate_sample_data.py      # Script de génération de données
├── requirements.txt                 # Dépendances Python
├── pyproject.toml                   # Configuration uv/pyproject
├── README.md                        # Ce fichier
├── .gitignore                       # Fichiers ignorés par Git
└── manage.py                        # Script de gestion Django
```

## 🧪 Tests

### Exécuter les tests unitaires

```bash
cd api_scoring_risque
python manage.py test application_risque
```

### Avec coverage

```bash
pip install coverage
coverage run --source='.' manage.py test application_risque
coverage report
coverage html  # Génère un rapport HTML
```

## 📚 Documentation

### Swagger UI

Accédez à la documentation interactive :
```
http://localhost:8000/documentation/
```

### ReDoc

Documentation alternative :
```
http://localhost:8000/redoc/
```

### API Schema

Télécharger le schéma OpenAPI :
```
GET http://localhost:8000/documentation.json
GET http://localhost:8000/documentation.yaml
```

## 🔐 Authentification

L'API utilise JWT (JSON Web Tokens) pour sécuriser les endpoints.

### Obtenir un token

```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

### Rafraîchir le token

```bash
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh":"votre_token_refresh"}'
```

## 🚀 Déploiement en production

### Avec PostgreSQL

1. Modifier `settings.py` pour utiliser PostgreSQL
2. Configurer les variables d'environnement
3. Exécuter les migrations : `python manage.py migrate`
4. Collecter les fichiers statiques : `python manage.py collectstatic`
5. Déployer avec Gunicorn/uWSGI

### Avec Docker

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "api_scoring_risque.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 📝 License

MIT License — Voir le fichier LICENSE pour plus de détails

## 👨‍💻 Auteur

Développé par PIMAGHA LONTCHI JAURES pour l'évaluation du risque d'insolvabilité

---

**Version** : 1.0.0  
**Dernière mise à jour** : janvier 2026  
**Statut** : Production Ready ✅
