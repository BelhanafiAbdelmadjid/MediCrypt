from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Utilisateur(db.Model, UserMixin):
    ID_User = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50))
    prenom = db.Column(db.String(50))
    pwd = db.Column(db.String(50))
    email = db.Column(db.String(50), unique=True)
    role = db.Column(db.Enum('Médecin', 'Radiologue', 'Laborantin', 'Patient', 'Admin', name='role_enum'))
    def get_id(self):
        return str(self.ID_User)

class MedecinTraitant(db.Model):
    __tablename__ = "medecintraitant"
    ID = db.Column(db.Integer, primary_key=True)
    medecin_ID = db.Column(db.Integer, db.ForeignKey('utilisateur.ID_User'))
    patient_ID = db.Column(db.Integer, db.ForeignKey('utilisateur.ID_User'))

    medecin = db.relationship("Utilisateur", foreign_keys=[medecin_ID])
    patient = db.relationship("Utilisateur", foreign_keys=[patient_ID])
    

class ProfilMedical(db.Model):
    __tablename__ = "profilmedical"
    ID_Dossier = db.Column(db.Integer, primary_key=True)
    traitant_ID = db.Column(db.Integer,db.ForeignKey('medecintraitant.ID'))
    # Dossier = db.Column(db.JSON)
    Dossier = db.Column(db.LargeBinary)  
    actif = db.Column(db.Boolean)
    date_debut = db.Column(db.Date)
    date_fin = db.Column(db.Date)

    traitant = db.relationship("MedecinTraitant", backref="dossiers")

class Acces(db.Model):
    ID_Acces = db.Column(db.Integer, primary_key=True)
    Utilisateur_ID = db.Column(db.Integer, db.ForeignKey('utilisateur.ID_User'))  # Radiologue ou Laborantin
    ID_Dossier = db.Column(db.Integer, db.ForeignKey('profilmedical.ID_Dossier'))  # Patient concerné
    role = db.Column(db.Enum('Radiologue', 'Laborantin', name='role_enum'))  # Type de professionnel ayant accès
    date_debut = db.Column(db.Date)
    date_fin = db.Column(db.Date)
