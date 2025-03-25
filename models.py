from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Utilisateur(db.Model, UserMixin):
    ID_User = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50))
    prenom = db.Column(db.String(50))
    pwd = db.Column(db.String(50))
    email = db.Column(db.String(50), unique=True)
    role = db.Column(db.Enum('Médecin', 'Radiologue', 'Laborantin', 'Patient', name='role_enum'))
    def get_id(self):
        return str(self.ID_User)

class MedecinTraitant(db.Model):
    ID = db.Column(db.Integer, primary_key=True)
    medecin_ID = db.Column(db.Integer, db.ForeignKey('utilisateur.ID_User'))
    patient_ID = db.Column(db.Integer, db.ForeignKey('utilisateur.ID_User'))
    actif = db.Column(db.Boolean)
    date_debut = db.Column(db.Date)
    date_fin = db.Column(db.Date)

class ProfilMedical(db.Model):
    ID_Dossier = db.Column(db.Integer, primary_key=True)
    Patient_ID = db.Column(db.Integer, db.ForeignKey('utilisateur.ID_User'))
    Dossier = db.Column(db.JSON)

class Acces(db.Model):
    ID_Acces = db.Column(db.Integer, primary_key=True)
    Utilisateur_ID = db.Column(db.Integer, db.ForeignKey('utilisateur.ID_User'))  # Radiologue ou Laborantin
    Patient_ID = db.Column(db.Integer, db.ForeignKey('utilisateur.ID_User'))  # Patient dont l'accès est accordé
    type_acces = db.Column(db.Enum('Lecture', 'Écriture', 'Modification', name='type_acces_enum'))  # Type d'accès
    date_debut = db.Column(db.Date)
    date_fin = db.Column(db.Date)
