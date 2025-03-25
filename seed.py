import random
from faker import Faker
from models import db, Utilisateur, MedecinTraitant, ProfilMedical, Acces
from app import app

fake = Faker()

def create_random_user(role):
    """Crée un utilisateur avec un rôle spécifique."""
    return Utilisateur(
        nom=fake.last_name(),
        prenom=fake.first_name(),
        pwd="password",  # Mot de passe non hashé (conforme à tes modèles)
        email=fake.unique.email(),  # Évite les doublons d'email
        role=role
    )

def seed_utilisateurs(count):
    """Ajoute des utilisateurs aléatoires (médecins, radiologues, laborantins, patients)."""
    with app.app_context():
        utilisateurs = [create_random_user(random.choice(['Médecin', 'Radiologue', 'Laborantin', 'Patient'])) for _ in range(count)]
        db.session.add_all(utilisateurs)
        db.session.commit()
        print(f"{count} utilisateurs créés.")

def seed_medecin_traitant(count):
    """Associe des médecins à des patients."""
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

            # Éviter les doublons
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
        print(f"{len(relations)} relations médecin-patient créées.")

def seed_profils_medicaux(count):
    """Ajoute des profils médicaux pour les patients."""
    with app.app_context():
        patients = Utilisateur.query.filter_by(role='Patient').all()

        if not patients:
            print("Aucun patient disponible pour créer des profils médicaux.")
            return

        profils = []
        for _ in range(count):
            patient = random.choice(patients)

            # Vérifier si un profil médical existe déjà
            if ProfilMedical.query.filter_by(Patient_ID=patient.ID_User).first():
                continue

            profils.append(ProfilMedical(
                Patient_ID=patient.ID_User,
                Dossier={
                    "historique": fake.text(),
                    "traitements": [fake.word() for _ in range(3)]
                }
            ))

        db.session.add_all(profils)
        db.session.commit()
        print(f"{len(profils)} profils médicaux créés.")

def seed_acces(count):
    """Crée des accès pour les radiologues et laborantins vers des patients."""
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

            # Vérifier si l'accès existe déjà
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
        print(f"{len(acces)} accès créés.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # Exemple d'utilisation des fonctions de seed
    seed_utilisateurs(10)
    seed_medecin_traitant(5)
    seed_profils_medicaux(5)
    seed_acces(5)
