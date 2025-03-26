import random
from faker import Faker
from datetime import datetime, timedelta
from models import db, Utilisateur, MedecinTraitant, ProfilMedical, Acces
from app import app

fake = Faker()

def create_user(role):
    return Utilisateur(
        nom=fake.last_name(),
        prenom=fake.first_name(),
        pwd="password",  # Pas de hashage pour correspondre au modèle
        email=fake.unique.email(),
        role=role
    )

def seed_utilisateurs():
    with app.app_context():
        utilisateurs = [
            create_user(random.choice(['Médecin', 'Radiologue', 'Laborantin', 'Patient']))
            for _ in range(10)
        ]
        db.session.add_all(utilisateurs)
        db.session.commit()
        print("✔️  10 utilisateurs créés.")

def seed_medecin_traitant():
    with app.app_context():
        medecins = Utilisateur.query.filter_by(role='Médecin').all()
        patients = Utilisateur.query.filter_by(role='Patient').all()

        if not medecins or not patients:
            print("❌ Aucun médecin ou patient disponible pour les associations.")
            return

        relations = []
        for _ in range(5):
            medecin = random.choice(medecins)
            patient = random.choice(patients)

            if MedecinTraitant.query.filter_by(medecin_ID=medecin.ID_User, patient_ID=patient.ID_User).first():
                continue

            relations.append(MedecinTraitant(
                medecin_ID=medecin.ID_User,
                patient_ID=patient.ID_User,
                actif=True,
                date_debut=fake.date_between(start_date='-1y', end_date='today'),
                date_fin=fake.date_between(start_date='+1y', end_date='+2y')
            ))

        db.session.add_all(relations)
        db.session.commit()
        print(f"✔️  {len(relations)} relations médecin-patient créées.")

def seed_profils_medicaux():
    with app.app_context():
        patients = Utilisateur.query.filter_by(role='Patient').all()

        if not patients:
            print("❌ Aucun patient disponible pour les profils médicaux.")
            return

        profils = []
        for patient in patients:
            if ProfilMedical.query.filter_by(Patient_ID=patient.ID_User).first():
                continue

            profils.append(ProfilMedical(
                Patient_ID=patient.ID_User,
                Dossier={
                    "historique": fake.text(),
                    "traitements": [{"nom": "Paracétamol", "dose": "500mg", "frequence": "3x/jour"}],
                    "analyses": [{"type": "Test sanguin", "date": fake.date(), "valeur": "Normal"}],
                    "imagerie": [{"type": "IRM", "date": fake.date(), "résultat": "Pas d'anomalie"}],
                    "notes": "Suivi nécessaire dans 6 mois."
                }
            ))

        db.session.add_all(profils)
        db.session.commit()
        print(f"✔️  {len(profils)} profils médicaux créés.")

def seed_acces():
    with app.app_context():
        patients = Utilisateur.query.filter_by(role='Patient').all()
        professionnels = Utilisateur.query.filter(Utilisateur.role.in_(['Radiologue', 'Laborantin'])).all()

        if not patients or not professionnels:
            print("❌ Aucun professionnel ou patient disponible pour les accès.")
            return

        acces = []
        for _ in range(5):
            patient = random.choice(patients)
            professionnel = random.choice(professionnels)

            if Acces.query.filter_by(Utilisateur_ID=professionnel.ID_User, Patient_ID=patient.ID_User).first():
                continue

            acces.append(Acces(
                Utilisateur_ID=professionnel.ID_User,
                Patient_ID=patient.ID_User,
                role=professionnel.role,
                date_debut=fake.date_between(start_date='-1y', end_date='today'),
                date_fin=fake.date_between(start_date='+1y', end_date='+2y')
            ))

        db.session.add_all(acces)
        db.session.commit()
        print(f"✔️  {len(acces)} accès créés.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    seed_utilisateurs()
    seed_medecin_traitant()
    seed_profils_medicaux()
    seed_acces()
    print("✔️  Données de test générées avec succès !")