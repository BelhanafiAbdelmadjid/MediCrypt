import random
from faker import Faker
from models import db, Utilisateur, MedecinTraitant, ProfilMedical, Acces
from app import app

fake = Faker()

def create_random_user(role):
    return Utilisateur(
        nom=fake.last_name(),
        prenom=fake.first_name(),
        pwd='password',  # Utilisez un mot de passe sécurisé dans un environnement réel
        email=fake.email(),
        role=role
    )

def seed_utilisateurs(count):
    with app.app_context():
        utilisateurs = [create_random_user(random.choice(['Médecin', 'Radiologue', 'Laborantin', 'Patient'])) for _ in range(count)]
        db.session.add_all(utilisateurs)
        db.session.commit()
        print(f"{count} utilisateurs créés.")

def seed_medecin_traitant(count):
    with app.app_context():
        medecins = Utilisateur.query.filter_by(role='Médecin').all()
        patients = Utilisateur.query.filter_by(role='Patient').all()

        if not medecins or not patients:
            print("Aucun médecin ou patient disponible pour créer des relations.")
            return

        relations = []
        for _ in range(count):
            medecin = random.choice(medecins)
            patient = random.choice(patients)
            relations.append(MedecinTraitant(
                medecin_ID=medecin.ID_User,
                patient_ID=patient.ID_User,
                actif=True,
                date_debut=fake.date_between(start_date='-1y', end_date='today'),
                date_fin=fake.date_between(start_date='+1y', end_date='+2y')
            ))

        db.session.add_all(relations)
        db.session.commit()
        print(f"{count} relations médecin-patient créées.")

def seed_profils_medicaux(count):
    with app.app_context():
        patients = Utilisateur.query.filter_by(role='Patient').all()

        if not patients:
            print("Aucun patient disponible pour créer des profils médicaux.")
            return

        profils = []
        for _ in range(count):
            patient = random.choice(patients)
            profils.append(ProfilMedical(
                Patient_ID=patient.ID_User,
                Dossier={
                    "historique": fake.text(),
                    "traitements": [fake.word() for _ in range(3)]
                }
            ))

        db.session.add_all(profils)
        db.session.commit()
        print(f"{count} profils médicaux créés.")

def seed_acces(count):
    with app.app_context():
        patients = Utilisateur.query.filter_by(role='Patient').all()
        professionnels = Utilisateur.query.filter(Utilisateur.role.in_(['Radiologue', 'Laborantin'])).all()

        if not patients or not professionnels:
            print("Aucun patient ou professionnel disponible pour créer des accès.")
            return

        acces = []
        for _ in range(count):
            patient = random.choice(patients)
            professionnel = random.choice(professionnels)
            acces.append(Acces(
                Utilisateur_ID=professionnel.ID_User,
                attributes={"permission": fake.word()}
            ))

        db.session.add_all(acces)
        db.session.commit()
        print(f"{count} accès créés.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # Exemple d'utilisation des fonctions de seed
    seed_utilisateurs(10)
    seed_medecin_traitant(5)
    seed_profils_medicaux(5)
    seed_acces(5)
