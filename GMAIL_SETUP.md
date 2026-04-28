# 🔐 Configuration Gmail API pour NidBuyer

Tu as presque tout ! Il ne te reste qu'une étape : **générer le REFRESH_TOKEN**.

## 📋 Checklist complète

✅ CLIENT_ID ajouté à `.env`  
✅ CLIENT_SECRET ajouté à `.env`  
⏳ REFRESH_TOKEN - À GÉNÉRER  
✅ Module `gmail_service.py` créé  
✅ Module `auth_gmail.py` créé  
✅ `alert.py` adapté  

---

## 🚀 Étape finale : Générer le REFRESH_TOKEN

### 1️⃣ Installe les dépendances
```bash
pip install -r requirements.txt
```

### 2️⃣ Lance le script d'authentification
```bash
python backend/auth_gmail.py
```

**Ce qui va se passer :**
- Une fenêtre navigateur s'ouvre
- Tu te connectes avec **projectaimmo@gmail.com**
- Google demande les permissions
- Tu acceptes ✓
- Tu obtiens un **REFRESH_TOKEN** (copie-le)

### 3️⃣ Ajoute le REFRESH_TOKEN à `.env`
Remplace cette ligne dans `.env` :
```
GMAIL_REFRESH_TOKEN=⚠️ À GÉNÉRER AVEC LE SCRIPT auth_gmail.py
```

Par :
```
GMAIL_REFRESH_TOKEN=1//0gAYW-... (ton token reçu)
```

---

## ✅ C'est bon !

Une fois fait, ton système est prêt :

- `notifier_email()` utilise **Gmail API** (OAuth2 sécurisé)
- Pas plus de SMTP fragile
- Meilleure délivrabilité
- Scalable pour la production

---

## 🧪 Test rapide

Tu peux tester avec :

```python
from backend.gmail_service import envoyer_email_gmail

envoyer_email_gmail(
    "test@example.com",
    "Test NidBuyer",
    "<h1>Ça marche ! 🚀</h1>"
)
```

---

## 🔐 Sécurité

- ✅ CLIENT_SECRET + REFRESH_TOKEN = sécurisés dans `.env`
- ✅ Jamais commité sur Git (ajoute `.env` à `.gitignore`)
- ✅ OAuth2 = pas de mot de passe stocké
- ✅ Le token se renouvelle automatiquement

---

## 💡 Prochaines étapes (optionnel)

Quand tu seras à l'aise :

- [ ] Système de queue d'emails (Redis + Celery)
- [ ] Tracking d'ouverture des emails
- [ ] Templates HTML avancés
- [ ] Rate limiting (100-200 emails/jour max par Gmail)

---

**Des questions ?** Dis-moi ! 👍
