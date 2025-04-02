from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from datetime import datetime
from models import db, Utilisateur, MedecinTraitant, ProfilMedical, Acces
import json
import base64

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ehealth.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # Remplacez par une clé secrète

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.query.get(int(user_id))

def role_required(role):
    def decorator(f):
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role != role:
                flash("Vous n'avez pas les autorisations nécessaires pour accéder à cette page.", "danger")
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role == 'Médecin':
            return redirect(url_for('dashboard_medecin'))
        # Ajoutez d'autres redirections en fonction des rôles si nécessaire
        else:
            return redirect(url_for('login'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Utilisateur.query.filter_by(email=email, pwd=password).first()
        if user:
            login_user(user)
            print(user.role)
            if user.role == 'Médecin':
                return redirect(url_for('dashboard_medecin'))
            elif user.role == 'Radiologue':
                return redirect(url_for('dashboard_radiologue'))
            elif user.role == 'Laborantin':
                return redirect(url_for('dashboard_laborantin'))
            else :
                return redirect(url_for('dashboard_patient'))
            # return redirect(url_for('dashboard_medecin'))
        else:
            flash("Invalid credentials. Please try again.", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))
# ---------------------------------------------------------------------------- #
#                                    Medecin                                   #
# ---------------------------------------------------------------------------- #
@app.route('/dashboard_medecin', endpoint='dashboard_medecin')
@role_required('Médecin')
def dashboard_medecin():
    from utils.cryptIT import encryptDossier, decryptDossier

    # Récupérer les patients actifs avec leurs informations
    patients_actifs = (
        db.session.query(Utilisateur)
        .join(MedecinTraitant, Utilisateur.ID_User == MedecinTraitant.patient_ID)
        .join(ProfilMedical, ProfilMedical.traitant_ID == MedecinTraitant.ID)
        .filter(
            MedecinTraitant.medecin_ID == current_user.ID_User,
            ProfilMedical.actif == True  # Vérifier si un dossier est actif
        )
        .distinct()  # Évite les doublons si plusieurs dossiers actifs existent
        .all()
    )
    # Récupérer les radiologues et laborantins
    radiologues = Utilisateur.query.filter_by(role="Radiologue").all()
    laborantins = Utilisateur.query.filter_by(role="Laborantin").all()

    return render_template(
        'medecin/dashboard_medecin.html',
        patients_actifs=patients_actifs,
        radiologues=radiologues,
        laborantins=laborantins
    )

@app.route('/patient/<int:patient_id>/dossiers', endpoint='liste_dossiers_patient')
@login_required
def liste_dossiers_patient(patient_id):
    # Vérifier si l'utilisateur est un médecin
    if current_user.role != "Médecin":
        flash("Accès refusé.", "danger")
        return redirect(url_for('dashboard_medecin'))

    # Vérifier si le médecin est bien le médecin traitant du patient
    traitant = MedecinTraitant.query.filter_by(
        medecin_ID=current_user.ID_User, patient_ID=patient_id
    ).first()

    if not traitant:
        flash("Vous n'avez pas accès aux dossiers de ce patient.", "danger")
        return redirect(url_for('dashboard_medecin'))

    # Récupérer le patient
    patient = Utilisateur.query.filter_by(ID_User=patient_id, role="Patient").first()
    if not patient:
        flash("Patient introuvable.", "danger")
        return redirect(url_for('dashboard_medecin'))

    # Récupérer les dossiers médicaux du patient associés à ce médecin
    dossiers = (
        ProfilMedical.query
        .join(MedecinTraitant, ProfilMedical.traitant_ID == MedecinTraitant.ID)
        .filter(
            MedecinTraitant.medecin_ID == current_user.ID_User,
            MedecinTraitant.patient_ID == patient_id
        )
        .all()
    )

    # Séparer les dossiers actifs et inactifs
    dossiers_actifs = []
    dossiers_inactifs = []

    for dossier in dossiers:
        dossier_info = {
            "id_dossier": dossier.ID_Dossier,
            "date_debut": dossier.date_debut,
            "date_fin": dossier.date_fin,
            "nom_medecin": f"{current_user.nom} {current_user.prenom}",
            "patient_info": {
                "id": patient.ID_User,
                "nom": patient.nom,
                "prenom": patient.prenom,
                "email": patient.email
            }
        }

        if dossier.actif:
            dossiers_actifs.append(dossier_info)
        else:
            dossiers_inactifs.append(dossier_info)

    return render_template(
        'medecin/liste_dossiers.html',
        dossiers_actifs=dossiers_actifs,
        dossiers_inactifs=dossiers_inactifs,
        patient=patient
    )


@app.route('/dossier_medical/<int:dossier_id>', endpoint='dossier_medical')
@login_required
def dossier_medical(dossier_id):
    from utils.cryptIT import encryptDossier, decryptDossier
    # Récupérer le dossier médical
    dossier = ProfilMedical.query.get_or_404(dossier_id)

    # Trouver le médecin traitant et le patient
    medecin_traitant = dossier.traitant
    if not medecin_traitant:
        flash("Dossier médical corrompu (pas de médecin traitant).", "danger")
        return redirect(url_for('home'))

    patient_id = medecin_traitant.patient_ID
    patient = Utilisateur.query.get(patient_id)

    try:
        print("decrypting")
        decoded_data = base64.b64decode(dossier.Dossier).decode('utf-8')
        decrypted_dossier = decryptDossier(dossier.traitant.medecin.email,decoded_data)
        print("decrypting",decrypted_dossier)
    except Exception as e:
        print(f"Erreur lors du déchiffrement du dossier: {str(e)}")
        flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
        return redirect(url_for('home'))

    # Vérification des accès
    if current_user.role == "Médecin":
        if current_user.ID_User != medecin_traitant.medecin_ID:
            flash("Vous n'êtes pas le médecin traitant de ce dossier.", "danger")
            return redirect(url_for('dashboard_medecin'))
        acces_complet = True

    elif current_user.role == "Patient":
        if current_user.ID_User != patient_id:
            flash("Vous ne pouvez accéder qu'à votre propre dossier.", "danger")
            return redirect(url_for('home'))
        acces_complet = True

    elif current_user.role == "Radiologue":
        # Vérifier si le radiologue a réalisé des imageries pour ce patient
        imageries_autorisees = [
            imagerie for imagerie in decrypted_dossier.get("imagerie", [])
            if imagerie.get("ajouté_par") == current_user.ID_User
        ]
        if not imageries_autorisees:
            flash("Vous n'avez pas d'imageries autorisées pour ce dossier.", "danger")
            return redirect(url_for('dashboard_medecin'))
        acces_complet = False

    elif current_user.role == "Laborantin":
        # Vérifier si le laborantin a réalisé des analyses pour ce patient
        analyses_autorisees = [
            analyse for analyse in decrypted_dossier.get("analyses", [])
            if analyse.get("ajouté_par") == current_user.ID_User
        ]
        if not analyses_autorisees:
            flash("Vous n'avez pas d'analyses autorisées pour ce dossier.", "danger")
            return redirect(url_for('dashboard_medecin'))
        acces_complet = False

    else:
        flash("Accès refusé.", "danger")
        return redirect(url_for('home'))

    # Construire les données à afficher
    donnees_dossier = {
        "id_dossier": dossier.ID_Dossier,
        "Patient_ID": patient_id,
        "patient_nom": patient.nom,
        "patient_prenom": patient.prenom,
    }

    if acces_complet:
        
        dossier_data = json.loads(decrypted_dossier)

        # Enrichir la section Analyses et Radiologies avec les informations de "ajouté_par"
        for analyse in dossier_data.get("analyses", []):
            utilisateur = Utilisateur.query.get(analyse.get("ajouté_par"))
            if utilisateur:
                analyse["full_name"] = utilisateur.nom + " " + utilisateur.prenom
            else:
                analyse["full_name"] = "Utilisateur inconnu"

        for imagerie in dossier_data.get("imagerie", []):
            utilisateur = Utilisateur.query.get(imagerie.get("ajouté_par"))
            if utilisateur:
                imagerie["full_name"] = utilisateur.nom + " " + utilisateur.prenom
            else:
                imagerie["full_name"] = "Utilisateur inconnu"

        # Maintenant on met à jour donnees_dossier avec les infos modifiées
        donnees_dossier.update({
            "date_debut": dossier.date_debut,
            "date_fin": dossier.date_fin,
            "actif": dossier.actif,
            **dossier_data  # On ajoute ici les données enrichies
        })

        donnees_dossier["medecin_traitant"] = {
            "id": medecin_traitant.medecin_ID,
            "nom": medecin_traitant.medecin.nom,
            "prenom": medecin_traitant.medecin.prenom,
        }
    else:
        # Accès limité pour Radiologue & Laborantin
        donnees_dossier["contenu"] = {}

        if current_user.role == "Radiologue":
            donnees_dossier["contenu"]["imagerie"] = imageries_autorisees

        if current_user.role == "Laborantin":
            donnees_dossier["contenu"]["analyses"] = analyses_autorisees

    return render_template('medecin/dossier_medical.html', dossier=donnees_dossier)

@app.route('/modifier_dossier/<int:dossier_id>', methods=['GET', 'POST'], endpoint='modifier_dossier')
@role_required('Médecin')
def modifier_dossier(dossier_id):
    from utils.cryptIT import encryptDossier, decryptDossier
    # Vérifier si le dossier médical existe
    dossier = ProfilMedical.query.filter_by(ID_Dossier=dossier_id).first()
    if not dossier:
        flash("Dossier médical introuvable.", "danger")
        return redirect(url_for('dashboard_medecin'))

    # Vérifier que le médecin connecté est bien le médecin traitant du dossier
    if not dossier.traitant or dossier.traitant.medecin_ID != current_user.ID_User:
        flash("Vous n'êtes pas autorisé à modifier ce dossier.", "danger")
        return redirect(url_for('dashboard_medecin'))

    # Correction des traitements mal formatés (si nécessaire)
    try:
        print("DECRYPTING",dossier.Dossier)
        decoded_data = base64.b64decode(dossier.Dossier).decode('utf-8')
        decrypted_dossier = decryptDossier(dossier.traitant.medecin.email,decoded_data)
        decrypted_dossier = json.loads(decrypted_dossier)
        print("DECRYPTED",decrypted_dossier)
    except Exception as e:
        flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
        return redirect(url_for('home'))
    dossier.Dossier = decrypted_dossier
    if "traitements" in decrypted_dossier:
        if isinstance(decrypted_dossier["traitements"], list):
            traitements_corriges = []
            for t in decrypted_dossier["traitements"]:
                if isinstance(t, str):  # Si c'est une chaîne mal formatée
                    try:
                        t = json.loads(t.replace("'", "\""))  # Remplacement des apostrophes simples
                    except json.JSONDecodeError:
                        print("⚠ Erreur de conversion JSON :", t)  # Debugging
                        continue  # Ignorer ce traitement mal formé
                traitements_corriges.append(t)
            decrypted_dossier["traitements"] = traitements_corriges
    
    if request.method == "GET" :
        return render_template('medecin/modifier_dossier.html', dossier=dossier)

    if request.method == 'POST':
        # Récupération des données du formulaire
        historique = request.form.get('historique')
        notes = request.form.get('notes')
        noms = request.form.getlist('traitements_nom[]')
        doses = request.form.getlist('traitements_dose[]')
        frequences = request.form.getlist('traitements_frequence[]')
       
        # dossier_data = decrypted_dossier
        print("UPDATING",decrypted_dossier)

        # Mise à jour des champs modifiables
        if historique:
            decrypted_dossier["historique"] = historique
        if notes:
            decrypted_dossier["notes"] = notes

        # Vérification des doublons et mise à jour des traitements
        traitements_uniques = set()
        traitements_list = []
        for nom, dose, freq in zip(noms, doses, frequences):
            if nom in traitements_uniques:
                flash(f"Le traitement '{nom}' est déjà ajouté. Supprimez le doublon.", "danger")
                return redirect(url_for('modifier_dossier', dossier_id=dossier_id))
            traitements_uniques.add(nom)
            traitements_list.append({"nom": nom, "dose": dose, "frequence": freq})

        decrypted_dossier["traitements"] = traitements_list  # Mise à jour des traitements sans doublons
        print("UPDATED BEFIRE ENCRYP",decrypted_dossier)
        try : 
            encrypted_dossier = encryptDossier(dossier.traitant.medecin.email,json.dumps(decrypted_dossier))
            encoded_data = base64.b64encode(encrypted_dossier.encode('utf-8')) 
        except Exception as e :
            print("Could not encrypt",e)
            flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
            return redirect(url_for('home'))

        print(f"Type of encrypted_dossier before saving: {type(encoded_data)}")
        print(f"Value of encrypted_dossier: {encoded_data}")
       
        # profile = db.session.query(ProfilMedical).filter_by(ID_Dossier=dossier_id).first()
        # if profile:
        dossier.Dossier = encoded_data  # Assign encrypted string
        db.session.commit()
        flash("Dossier médical mis à jour avec succès.", "success")
        return redirect(url_for('dossier_medical', dossier_id=dossier_id))
        # Mise à jour du dossier médical dans la base de données
        # db.session.execute(
        #     ProfilMedical.__table__.update()
        #     .where(ProfilMedical.ID_Dossier == dossier_id)
        #     .values(Dossier=str(encrypted_dossier))
        # )
        # db.session.commit()


@app.route('/associer_patient', methods=['GET', 'POST'], endpoint='associer_patient')
@role_required('Médecin')
def associer_patient():
    from utils.cryptIT import encryptDossier, decryptDossier
    if request.method == 'POST':
        patient_id = request.form['patient_id']

        # Vérifier si le patient existe réellement et a bien le rôle "Patient"
        patient = Utilisateur.query.filter_by(ID_User=patient_id, role='Patient').first()
        if not patient:
            flash("Le patient spécifié n'existe pas.", "danger")
            return redirect(url_for('associer_patient'))

        date_debut = datetime.strptime(request.form['date_debut'], '%Y-%m-%d')
        date_fin = datetime.strptime(request.form['date_fin'], '%Y-%m-%d')

        # Vérifier si le patient est déjà associé à ce médecin
        existant = MedecinTraitant.query.filter_by(medecin_ID=current_user.ID_User, patient_ID=patient_id).first()
        if existant:
            flash("Ce patient est déjà sous votre responsabilité.", "warning")
            return redirect(url_for('associer_patient'))

        # Créer l'association médecin-patient
        nouveau_traitant = MedecinTraitant(
            medecin_ID=current_user.ID_User,
            patient_ID=patient_id,
        )
        db.session.add(nouveau_traitant)
        db.session.flush() 
        # Encryption
        initial_dossier = {
            "historique": "",
            "traitements": [],
            "imagerie": [],
            "analyses": []
        }
        encrypted_dossier = encryptDossier(nouveau_traitant.medecin.email, initial_dossier)  # Encrypt using doctor's email
        encoded_data = base64.b64encode(encrypted_dossier.encode('utf-8')) 
        nouveau_dossier =  ProfilMedical(
            # Patient_ID=patient_id,
            # medecin_ID=current_user.ID_User,
            traitant_ID = nouveau_traitant.ID,
            actif=True,
            date_debut=date_debut,
            date_fin=date_fin,
            Dossier=encoded_data
        )
        db.session.add(nouveau_dossier)
        db.session.commit()
        flash("Association du patient réussie.", "success")
        return redirect(url_for('dashboard_medecin'))

    liste_patients = Utilisateur.query.filter_by(role='Patient').all()

    return render_template('medecin/associer_patient.html',liste_patients=liste_patients)

@app.route('/gerer_acces/<int:dossier_id>', methods=['GET', 'POST'], endpoint='gerer_acces')
@role_required('Médecin')
def gerer_acces(dossier_id):
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'ajouter':
            utilisateur_id = request.form['utilisateur_id']
            # patient_id = request.form['patient_id']
            # role = request.form['role']
            date_debut = datetime.strptime(request.form['date_debut'], '%Y-%m-%d')
            date_fin = datetime.strptime(request.form['date_fin'], '%Y-%m-%d')

            # Vérifier si l'utilisateur est bien un Radiologue ou un Laborantin
            professionnel = Utilisateur.query.filter_by(ID_User=utilisateur_id).first()
            if not professionnel:
                flash("L'utilisateur sélectionné n'est pas un Radiologue ou un Laborantin.", "danger")
                return redirect(url_for('gerer_acces'))

            # Vérifier si l'accès existe déjà
            acces_existant = Acces.query.filter_by(Utilisateur_ID=utilisateur_id, ID_Dossier=dossier_id).first()
            if acces_existant:
                flash("Cet utilisateur a déjà accès au dossier du patient.", "warning")
                return redirect(url_for('gerer_acces'))

            # Création d'un nouvel accès
            nouvel_acces = Acces(
                Utilisateur_ID=utilisateur_id,
                ID_Dossier=dossier_id,
                role=professionnel.role,
                date_debut=date_debut,
                date_fin=date_fin
            )
            db.session.add(nouvel_acces)
            db.session.commit()
            flash("Accès accordé avec succès.", "success")

        elif action == 'supprimer':
            acces_id = request.form['acces_id']
            acces = Acces.query.get(acces_id)
            if acces:
                db.session.delete(acces)
                db.session.commit()
                flash("Accès révoqué avec succès.", "success")
            else:
                flash("Accès introuvable.", "danger")

        return redirect(url_for('gerer_acces',dossier_id=dossier_id))

    # Récupérer les accès des patients du médecin
    acces_existants = Acces.query.join(ProfilMedical, Acces.ID_Dossier == dossier_id)\
                             .join(MedecinTraitant, ProfilMedical.traitant_ID == MedecinTraitant.ID)\
                             .filter(MedecinTraitant.medecin_ID == current_user.ID_User)\
                             .all()
    professionnels = Utilisateur.query.filter(
        Utilisateur.role.in_(['Radiologue', 'Laborantin'])
    ).all()

    return render_template('medecin/gerer_acces.html', 
                           acces_existants=acces_existants,
                           dossier={"ID_Dossier":dossier_id},
                           professionnels=professionnels)

@app.route('/historique_interactions', endpoint='historique_interactions')
@role_required('Médecin')
def historique_interactions():
    # Récupérer les accès accordés aux patients du médecin
    interactions = Acces.query.join(MedecinTraitant, Acces.Patient_ID == MedecinTraitant.patient_ID) \
                              .filter(MedecinTraitant.medecin_ID == current_user.ID_User) \
                              .all()

    return render_template('medecin/historique_interactions.html', interactions=interactions)

# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
#                                  Radiologue                                  #
# ---------------------------------------------------------------------------- #

@app.route('/dashboard_radiologue', endpoint='dashboard_radiologue')
@role_required('Radiologue')
def dashboard_radiologue():
    # Récupérer les dossiers accessibles pour ce radiologue via la table Acces
    dossiers = db.session.query(ProfilMedical, Utilisateur) \
        .join(Acces, ProfilMedical.ID_Dossier == Acces.ID_Dossier) \
        .join(MedecinTraitant, ProfilMedical.traitant_ID == MedecinTraitant.ID) \
        .join(Utilisateur, MedecinTraitant.patient_ID == Utilisateur.ID_User) \
        .filter(Acces.Utilisateur_ID == current_user.ID_User, Acces.role == 'Radiologue') \
        .all()

    return render_template('radiologue/dashboard_radiologue.html', dossiers=dossiers)

@app.route('/dossier_medical_radiologue/<int:dossier_id>', endpoint='dossier_medical_radiologue')
@role_required('Radiologue')
def dossier_medical_radiologue(dossier_id):
    from utils.cryptIT import decryptDossier
    # Vérifier si le radiologue a accès au dossier médical
    acces = Acces.query.filter_by(Utilisateur_ID=current_user.ID_User, ID_Dossier=dossier_id, role='Radiologue').first()
    if not acces:
        flash("Vous n'avez pas accès à ce dossier.", "danger")
        return redirect(url_for('dashboard_radiologue'))

    # Récupérer le dossier médical
    dossier = ProfilMedical.query.filter_by(ID_Dossier=dossier_id).first()
    
    if not dossier:
        flash("Dossier médical introuvable.", "danger")
        return redirect(url_for('dashboard_radiologue'))
    
    try:
        decoded_data = base64.b64decode(dossier.Dossier).decode('utf-8')
        decrypted_dossier = decryptDossier(dossier.traitant.medecin.email,decoded_data)
        decrypted_dossier = json.loads(decrypted_dossier)
    except Exception as e:
        flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
        return redirect(url_for('home'))

    # Le radiologue ne voit que la partie "imagerie"
    imagerie = decrypted_dossier.get("imagerie", [])

    return render_template('radiologue/dossier_medical_radiologue.html', dossier=imagerie, dossier_id=dossier_id, Utilisateur=Utilisateur)
@app.route('/ajouter_imagerie/<int:dossier_id>', methods=['GET', 'POST'], endpoint='ajouter_imagerie')
@role_required('Radiologue')
def ajouter_imagerie(dossier_id):
    from utils.cryptIT import encryptDossier, decryptDossier
    # Vérifier si l'accès est autorisé
    acces = Acces.query.filter_by(Utilisateur_ID=current_user.ID_User, ID_Dossier=dossier_id, role='Radiologue').first()
    if not acces:
        flash("Vous n'avez pas accès à ce dossier.", "danger")
        return redirect(url_for('dashboard_radiologue'))

    dossier = ProfilMedical.query.filter_by(ID_Dossier=dossier_id).first()
    if not dossier:
        flash("Dossier médical introuvable.", "danger")
        return redirect(url_for('dashboard_radiologue'))

    if request.method == 'POST':
        try:
            decoded_data = base64.b64decode(dossier.Dossier).decode('utf-8')
            decrypted_dossier = decryptDossier(dossier.traitant.medecin.email,decoded_data)
            decrypted_dossier = json.loads(decrypted_dossier)
        except Exception as e:
            flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
            return redirect(url_for('home'))
        
        type_imagerie = request.form.get('type')
        resultat = request.form.get('resultat')
        date = datetime.today().strftime('%Y-%m-%d')

        # Charger les données actuelles du dossier
        dossier_data = decrypted_dossier

        # Ajouter la section "imagerie" si elle n'existe pas
        if "imagerie" not in dossier_data:
            dossier_data["imagerie"] = []

        # Ajouter le nouveau rapport d'imagerie
        dossier_data["imagerie"].append({
            "type": type_imagerie,
            "date": date,
            "résultat": resultat,
            "ajouté_par": current_user.ID_User  
        })
        try : 
            encrypted_dossier = encryptDossier(dossier.traitant.medecin.email,json.dumps(dossier_data))
            encoded_data = base64.b64encode(encrypted_dossier.encode('utf-8')) 
        except Exception as e :
            print("Could not encrypt",e)
            flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
            return redirect(url_for('home'))
        # 🔥 **Mise à jour forcée de la colonne JSON**
        db.session.execute(
            ProfilMedical.__table__.update()
            .where(ProfilMedical.ID_Dossier == dossier_id)
            .values(Dossier=encoded_data)
        )
        db.session.commit()

        flash("Rapport d'imagerie ajouté avec succès.", "success")
        return redirect(url_for('dossier_medical_radiologue', dossier_id=dossier_id))

    return render_template('radiologue/ajouter_imagerie.html', dossier_id=dossier_id)

@app.route('/modifier_imagerie/<int:dossier_id>/<int:index>', methods=['GET', 'POST'], endpoint='modifier_imagerie')
@role_required('Radiologue')
def modifier_imagerie(dossier_id, index):
    from utils.cryptIT import encryptDossier, decryptDossier
    # Verify if the user has access to the patient's medical records
    acces = Acces.query.filter_by(Utilisateur_ID=current_user.ID_User, ID_Dossier=dossier_id, role='Radiologue').first()
    if not acces:
        flash("Vous n'avez pas accès à ce dossier.", "danger")
        return redirect(url_for('dashboard_radiologue'))

    dossier = ProfilMedical.query.filter_by(ID_Dossier=dossier_id).first()
    try:
        decoded_data = base64.b64decode(dossier.Dossier).decode('utf-8')
        decrypted_dossier = decryptDossier(dossier.traitant.medecin.email,decoded_data)
        decrypted_dossier = json.loads(decrypted_dossier)
    except Exception as e:
        flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
        return redirect(url_for('home'))
    
    if not dossier or "imagerie" not in decrypted_dossier or index >= len(decrypted_dossier["imagerie"]):
        flash("Rapport d'imagerie introuvable.", "danger")
        return redirect(url_for('dossier_medical_radiologue', dossier_id=dossier_id))

    # Get the imaging report
    rapport = decrypted_dossier["imagerie"][index]

    # 🔹 **Check if the current user is the one who added the report**
    if "ajouté_par" not in rapport or rapport["ajouté_par"] != current_user.ID_User:
        flash("Vous ne pouvez modifier ou supprimer que les rapports que vous avez ajoutés.", "danger")
        return redirect(url_for('dossier_medical_radiologue', dossier_id=dossier_id))

    if request.method == 'POST':
        if 'delete' in request.form:  # Check if the delete button was pressed
            dossier_data = decrypted_dossier
            del dossier_data["imagerie"][index]  # Remove the report

            try : 
                encrypted_dossier = encryptDossier(dossier.traitant.medecin.email,json.dumps(dossier_data))
                encoded_data = base64.b64encode(encrypted_dossier.encode('utf-8')) 
            except Exception as e :
                print("Could not encrypt",e)
                flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
                return redirect(url_for('home'))
            # 🔥 **Force updating the JSON column**
            db.session.execute(
                ProfilMedical.__table__.update()
                .where(ProfilMedical.ID_Dossier == dossier_id)
                .values(Dossier=encoded_data)
            )
            db.session.commit()

            flash("Rapport d'imagerie supprimé avec succès.", "success")
            return redirect(url_for('dossier_medical_radiologue', dossier_id=dossier_id))

        else:  # Update logic
            type_imagerie = request.form.get('type')
            resultat = request.form.get('resultat')

            # Load the current dossier data
            dossier_data = decrypted_dossier

            # Update the imaging report
            dossier_data["imagerie"][index]["type"] = type_imagerie
            dossier_data["imagerie"][index]["résultat"] = resultat
            dossier_data["imagerie"][index]["modifié_par"] = current_user.ID_User  # Store the editor ID

            try : 
                encrypted_dossier = encryptDossier(dossier.traitant.medecin.email,json.dumps(dossier_data))
                encoded_data = base64.b64encode(encrypted_dossier.encode('utf-8')) 
            except Exception as e :
                print("Could not encrypt",e)
                flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
                return redirect(url_for('home'))  
            # 🔥 **Force updating the JSON column**
            db.session.execute(
                ProfilMedical.__table__.update()
                .where(ProfilMedical.ID_Dossier == dossier_id)
                .values(Dossier=encoded_data)
            )
            db.session.commit()

            flash("Rapport d'imagerie modifié avec succès.", "success")
            return redirect(url_for('dossier_medical_radiologue', dossier_id=dossier_id))

    return render_template('radiologue/modifier_imagerie.html',
                            dossier_id=dossier_id,
                            rapport=rapport,
                            index=index)

# Laborantin 
@app.route('/dashboard_laborantin', endpoint='dashboard_laborantin')
@role_required('Laborantin')
def dashboard_laborantin():
    # Retrieve accessible patient dossiers
    
    dossiers = db.session.query(ProfilMedical, Utilisateur) \
        .join(Acces, ProfilMedical.ID_Dossier == Acces.ID_Dossier) \
        .join(MedecinTraitant, ProfilMedical.traitant_ID == MedecinTraitant.ID) \
        .join(Utilisateur, MedecinTraitant.patient_ID == Utilisateur.ID_User) \
        .filter(Acces.Utilisateur_ID == current_user.ID_User, Acces.role == 'Laborantin') \
        .all()

    return render_template('laborantin/dashboard_laborantin.html', dossiers=dossiers)

@app.route('/dossier_medical_laborantin/<int:dossier_id>', endpoint='dossier_medical_laborantin')
@role_required('Laborantin')
def dossier_medical_laborantin(dossier_id):
    from utils.cryptIT import decryptDossier
    # Check if the lab technician has access
    acces = Acces.query.filter_by(Utilisateur_ID=current_user.ID_User, ID_Dossier=dossier_id, role='Laborantin').first()
    if not acces:
        flash("Vous n'avez pas accès à ce dossier.", "danger")
        return redirect(url_for('dashboard_laborantin'))

    dossier = ProfilMedical.query.filter_by(ID_Dossier=dossier_id).first()
    if not dossier:
        flash("Dossier médical introuvable.", "danger")
        return redirect(url_for('dashboard_laborantin'))
    
    try:
        decoded_data = base64.b64decode(dossier.Dossier).decode('utf-8')
        decrypted_dossier = decryptDossier(dossier.traitant.medecin.email,decoded_data)
        decrypted_dossier = json.loads(decrypted_dossier)
    except Exception as e:
        flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
        return redirect(url_for('home'))

    # The lab technician only sees "analyses"
    analyses = decrypted_dossier.get("analyses", [])

    return render_template('laborantin/dossier_medical_laborantin.html', dossier=analyses, dossier_id=dossier_id, Utilisateur=Utilisateur)

@app.route('/ajouter_analyse/<int:dossier_id>', methods=['GET', 'POST'], endpoint='ajouter_analyse')
@role_required('Laborantin')
def ajouter_analyse(dossier_id):
    from utils.cryptIT import encryptDossier, decryptDossier
    # Verify if the lab technician has access
    acces = Acces.query.filter_by(Utilisateur_ID=current_user.ID_User, ID_Dossier=dossier_id, role='Laborantin').first()
    if not acces:
        flash("Vous n'avez pas accès à ce dossier.", "danger")
        return redirect(url_for('dashboard_laborantin'))

    dossier = ProfilMedical.query.filter_by(ID_Dossier=dossier_id).first()
    if not dossier:
        flash("Dossier médical introuvable.", "danger")
        return redirect(url_for('dashboard_laborantin'))

    if request.method == 'POST':
        try:
            decoded_data = base64.b64decode(dossier.Dossier).decode('utf-8')
            decrypted_dossier = decryptDossier(dossier.traitant.medecin.email,decoded_data)
            decrypted_dossier = json.loads(decrypted_dossier)
        except Exception as e:
            flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
            return redirect(url_for('home'))
        
        type_analyse = request.form.get('type')
        valeur = request.form.get('valeur')
        date = datetime.today().strftime('%Y-%m-%d')

        # Load current dossier data
        dossier_data = decrypted_dossier

        # Add "analyses" section if it doesn't exist
        if "analyses" not in dossier_data:
            dossier_data["analyses"] = []

        # Add the new analysis
        dossier_data["analyses"].append({
            "type": type_analyse,
            "date": date,
            "valeur": valeur,
            "ajouté_par": current_user.ID_User  
        })

        try : 
            encrypted_dossier = encryptDossier(dossier.traitant.medecin.email,json.dumps(dossier_data))
            encoded_data = base64.b64encode(encrypted_dossier.encode('utf-8')) 
        except Exception as e :
            print("Could not encrypt",e)
            flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
            return redirect(url_for('home'))

        # Force updating the JSON column
        db.session.execute(
            ProfilMedical.__table__.update()
            .where(ProfilMedical.ID_Dossier == dossier_id)
            .values(Dossier=encoded_data)
        )
        db.session.commit()

        flash("Analyse ajoutée avec succès.", "success")
        return redirect(url_for('dossier_medical_laborantin', dossier_id=dossier_id))

    return render_template('laborantin/ajouter_analyse.html', dossier_id=dossier_id)

@app.route('/modifier_analyse/<int:dossier_id>/<int:index>', methods=['GET', 'POST'], endpoint='modifier_analyse')
@role_required('Laborantin')
def modifier_analyse(dossier_id, index):
    from utils.cryptIT import encryptDossier, decryptDossier
    # Verify if the lab technician has access
    acces = Acces.query.filter_by(Utilisateur_ID=current_user.ID_User, ID_Dossier=dossier_id, role='Laborantin').first()
    if not acces:
        flash("Vous n'avez pas accès à ce dossier.", "danger")
        return redirect(url_for('dashboard_laborantin'))

    dossier = ProfilMedical.query.filter_by(ID_Dossier=dossier_id).first()
    try:
        decoded_data = base64.b64decode(dossier.Dossier).decode('utf-8')
        decrypted_dossier = decryptDossier(dossier.traitant.medecin.email,decoded_data)
        decrypted_dossier = json.loads(decrypted_dossier)
    except Exception as e:
        flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
        return redirect(url_for('home'))

    if not dossier or "analyses" not in decrypted_dossier or index >= len(decrypted_dossier["analyses"]):
        flash("Analyse introuvable.", "danger")
        return redirect(url_for('dossier_medical_laborantin', dossier_id=dossier_id))

    # Get the analysis
    analyse = decrypted_dossier["analyses"][index]

    # Only the original author can modify or delete it
    if "ajouté_par" not in analyse or analyse["ajouté_par"] != current_user.ID_User:
        flash("Vous ne pouvez modifier ou supprimer que les analyses que vous avez ajoutées.", "danger")
        return redirect(url_for('dossier_medical_laborantin', dossier_id=dossier_id))

    if request.method == 'POST':
        if 'delete' in request.form:
            dossier_data = decrypted_dossier
            del dossier_data["analyses"][index]

            try : 
                encrypted_dossier = encryptDossier(dossier.traitant.medecin.email,json.dumps(dossier_data))
                encoded_data = base64.b64encode(encrypted_dossier.encode('utf-8')) 
            except Exception as e :
                print("Could not encrypt",e)
                flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
                return redirect(url_for('home'))
            # Force updating the JSON column
            db.session.execute(
                ProfilMedical.__table__.update()
                .where(ProfilMedical.ID_Dossier == dossier_id)
                .values(Dossier=encoded_data)
            )
            db.session.commit()

            flash("Analyse supprimée avec succès.", "success")
            return redirect(url_for('dossier_medical_laborantin', dossier_id=dossier_id))

        else:  # Update analysis
            type_analyse = request.form.get('type')
            valeur = request.form.get('valeur')

            # Load current dossier data
            dossier_data = decrypted_dossier

            # Update the analysis
            dossier_data["analyses"][index]["type"] = type_analyse
            dossier_data["analyses"][index]["valeur"] = valeur
            dossier_data["analyses"][index]["modifié_par"] = current_user.ID_User

            try : 
                encrypted_dossier = encryptDossier(dossier.traitant.medecin.email,json.dumps(dossier_data))
                encoded_data = base64.b64encode(encrypted_dossier.encode('utf-8')) 
            except Exception as e :
                print("Could not encrypt",e)
                flash(f"Erreur lors du déchiffrement du dossier: {str(e)}", "danger")
                return redirect(url_for('home'))  

            # Force updating the JSON column
            db.session.execute(
                ProfilMedical.__table__.update()
                .where(ProfilMedical.ID_Dossier == dossier_id)
                .values(Dossier=encoded_data)
            )
            db.session.commit()

            flash("Analyse modifiée avec succès.", "success")
            return redirect(url_for('dossier_medical_laborantin', dossier_id=dossier_id))

    return render_template('laborantin/modifier_analyse.html', dossier_id=dossier_id, analyse=analyse)


# ---------------------------------------------------------------------------- #
#                                    Patient                                   #
# ---------------------------------------------------------------------------- #
@app.route('/dashboard_patient', endpoint='dashboard_patient')
@role_required('Patient')  
def dashboard_patient():
    # Récupérer les informations du patient
    patient = db.session.query(Utilisateur).filter(Utilisateur.ID_User == current_user.ID_User).first()

    # Récupérer les dossiers médicaux du patient
    dossiers_medical = db.session.query(ProfilMedical) \
        .join(MedecinTraitant, ProfilMedical.traitant_ID == MedecinTraitant.ID) \
        .filter(MedecinTraitant.patient_ID == current_user.ID_User) \
        .all()

    # Construire les informations des dossiers
    dossiers_info = []
    for dossier in dossiers_medical:
        medecin_traitant = db.session.query(Utilisateur.nom, Utilisateur.prenom) \
            .filter(Utilisateur.ID_User == dossier.traitant.medecin_ID) \
            .first()
        
        dossiers_info.append({
            'ID_Dossier': dossier.ID_Dossier,
            'medecin_nom': medecin_traitant.nom if medecin_traitant else "Non assigné",
            'medecin_prenom': medecin_traitant.prenom if medecin_traitant else ""
        })

    return render_template(
        'patient/dashboard.html',
        patient=patient,
        dossiers_info=dossiers_info
    )


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
