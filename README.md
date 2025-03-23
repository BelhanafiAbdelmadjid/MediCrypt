# MediCrypt
MediCrypt - A secure eHealth platform built with Flask. It manages patient records, doctor interactions, and medical data while ensuring privacy through encryption🔒💉

# Backend de la plateforme eHealth

Bienvenue dans le backend de la plateforme eHealth. Ce document vous guidera à travers les étapes nécessaires pour exécuter l'application localement, alimenter la base de données pour les tests, utiliser Jinja pour le rendu des données, et interagir avec les endpoints.

---

## 🚀 1. Exécution de l'application localement

### 📌 Prérequis

- Python 3.x
- pip (gestionnaire de paquets Python)

### 🛠️ Installation

1. **Cloner le dépôt** :
   ```bash
   git clone <URL_DU_DEPOT>
   cd ehealth-platform
   ```

2. **Créer un environnement virtuel** :
   ```bash
   python -m venv venv
   ```

3. **Activer l'environnement virtuel** :

   - Sur **Windows** :
     ```bash
     venv\Scripts\activate
     ```
   - Sur **macOS/Linux** :
     ```bash
     source venv/bin/activate
     ```

4. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

5. **Exécuter l'application** :
   ```bash
   python run.py
   ```
   L'application sera accessible à l'adresse **[http://127.0.0.1:5000/](http://127.0.0.1:5000/)**.

---

## 📂 2. Alimenter la base de données pour les tests

Pour remplir la base de données avec des données de test, utilisez le script **seed.py** fourni.

Exécuter le script de seed :

```bash
python app/scripts/init_app.py
```

Ce script remplit la base de données avec des données fictives pour les tests. Vous pouvez spécifier le nombre d'enregistrements à créer en modifiant les appels de fonctions dans le script.

---

## 🖥️ 3. Utilisation de Jinja pour le rendu des données

Les templates HTML utilisent **Jinja** pour le rendu des données. Voici un exemple de base :

```jinja2
{% for item in data %}
  <p>{{ item.name }}: {{ item.value }}</p>
{% endfor %}
```

Pour plus d'informations sur l'utilisation de Jinja, consultez la [documentation officielle](https://jinja.palletsprojects.com/).

---

## 🔗 4. Interagir avec les endpoints

### 📌 Requêtes GET
Utilisées pour récupérer des données depuis le serveur.

```bash
curl -X GET http://127.0.0.1:5000/api/data
```

Ou en JavaScript avec `fetch` :

```javascript
fetch('/api/data', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => {
  console.log(data);
})
.catch(error => {
  console.error('Erreur:', error);
});
```

### 📌 Requêtes POST (avec formulaire)
Voici un exemple d'envoi de données à un endpoint Flask via un formulaire HTML :

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Formulaire d'Envoi</title>
</head>
<body>
    <h2>Formulaire d'Envoi</h2>
    <form id="dataForm">
        <label for="dataField">Donnée :</label>
        <input type="text" id="dataField" name="dataField" required><br>
        <button type="submit">Envoyer</button>
    </form>

    <script>
        document.getElementById('dataForm').addEventListener('submit', function(event) {
            event.preventDefault();
            const data = new FormData(this);

            fetch('/api/submit', {
                method: 'POST',
                body: JSON.stringify({ data: data.get('dataField') }),
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(result => {
                console.log('Success:', result);
            })
            .catch(error => {
                console.error('Erreur:', error);
            });
        });
    </script>
</body>
</html>
```

### 📌 Autres types de requêtes HTTP
- **PUT/PATCH** : Mise à jour des données existantes.
- **DELETE** : Suppression d'un enregistrement.

Exemple de requête **POST** en JavaScript :

```javascript
const data = {
  key1: 'value1',
  key2: 'value2'
};

fetch('/api/endpoint', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
})
.then(response => response.json())
.then(result => {
  console.log('Success:', result);
})
.catch(error => {
  console.error('Erreur:', error);
});
```

---

## 📌 Conclusion

Ce README vous a fourni les instructions nécessaires pour :
- Exécuter l'application localement.
- Alimenter la base de données pour les tests.
- Utiliser Jinja pour le rendu des données.
- Interagir avec les endpoints.

Pour toute question ou assistance supplémentaire, n'hésitez pas à contacter l'équipe backend. 🚀

