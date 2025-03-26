import random
import json
from faker import Faker
from datetime import datetime, timedelta
from models import db, Utilisateur, MedecinTraitant, ProfilMedical, Acces
from app import app

fake = Faker()

def seed_utilisateurs():
    with app.app_context():
        roles = ['Médecin', 'Radiologue', 'Laborantin', 'Patient']
        utilisateurs = []

        for role in roles:
            for _ in range(3):  # 3 utilisateurs par rôle
                utilisateurs.append(Utilisateur(
                    nom=fake.last_name(),
                    prenom=fake.first_name(),
                    email=fake.unique.email(),
                    pwd='password',  # ⚠️ Changer en prod
                    role=role
                ))

        db.session.add_all(utilisateurs)
        db.session.commit()
        print("✔️ Utilisateurs créés.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_utilisateurs()
    print("🎉 SEEDING COMPLET ! Base de données prête.")
