from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from datetime import datetime
from models import db, Utilisateur, MedecinTraitant, ProfilMedical, Acces
import json

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
    # Récupérer les patients actifs avec leurs informations
    patients_actifs = db.session.query(Utilisateur).join(MedecinTraitant, Utilisateur.ID_User == MedecinTraitant.patient_ID) \
                        .filter(MedecinTraitant.medecin_ID == current_user.ID_User, MedecinTraitant.actif == True).all()

    # Récupérer les radiologues et laborantins
    radiologues = Utilisateur.query.filter_by(role="Radiologue").all()
    laborantins = Utilisateur.query.filter_by(role="Laborantin").all()

    return render_template(
        'medecin/dashboard_medecin.html',
        patients_actifs=patients_actifs,
        radiologues=radiologues,
        laborantins=laborantins
    )

@app.route('/dossier_medical/<int:patient_id>', endpoint='dossier_medical')
@login_required
def dossier_medical(patient_id):
    # Verify if the dossier exists
    dossier = ProfilMedical.query.filter_by(Patient_ID=patient_id).first()
    if not dossier:
        flash("Dossier médical introuvable.", "danger")
        return redirect(url_for('dashboard_medecin'))

    # Verify user permissions
    if current_user.role == "Médecin":
        est_medecin_du_patient = MedecinTraitant.query.filter_by(
            medecin_ID=current_user.ID_User, patient_ID=patient_id
        ).first()
        if not est_medecin_du_patient:
            flash("Vous n'avez pas accès à ce dossier.", "danger")
            return redirect(url_for('dashboard_medecin'))
        donnees_dossier = dossier.Dossier  # The doctor sees everything

    elif current_user.role in ["Radiologue", "Laborantin"]:
        acces_autorise = Acces.query.filter_by(
            Utilisateur_ID=current_user.ID_User, Patient_ID=patient_id
        ).first()
        if not acces_autorise:
            flash("Vous n'avez pas accès à ce dossier.", "danger")
            return redirect(url_for('dashboard_medecin'))

        if current_user.role == "Laborantin":
            donnees_dossier = {"analyses": dossier.Dossier.get("analyses", [])}
        elif current_user.role == "Radiologue":
            donnees_dossier = {"imagerie": dossier.Dossier.get("imagerie", [])}

    else:
        flash("Accès refusé.", "danger")
        return redirect(url_for('home'))

    donnees_dossier["Patient_ID"] = patient_id

    # 🔹 **Attach User Info to Imaging Reports & Analyses**
    for imagerie in donnees_dossier.get("imagerie", []):
        if "ajouté_par" in imagerie:
            user = Utilisateur.query.get(imagerie["ajouté_par"])
            imagerie["radiologue_nom"] = f"{user.nom} {user.prenom}" if user else "Utilisateur inconnu"
            imagerie["radiologue_id"] = user.ID_User if user else "N/A"

    for analyse in donnees_dossier.get("analyses", []):
        if "ajouté_par" in analyse:
            user = Utilisateur.query.get(analyse["ajouté_par"])
            analyse["laborantin_nom"] = f"{user.nom} {user.prenom}" if user else "Utilisateur inconnu"
            analyse["laborantin_id"] = user.ID_User if user else "N/A"

    return render_template('medecin/dossier_medical.html', dossier=donnees_dossier)


@app.route('/modifier_dossier/<int:patient_id>', methods=['GET', 'POST'], endpoint='modifier_dossier')
@role_required('Médecin')
def modifier_dossier(patient_id):
    # Vérifier si le dossier médical du patient existe
    dossier = ProfilMedical.query.filter_by(Patient_ID=patient_id).first()
    if not dossier:
        flash("Dossier médical introuvable.", "danger")
        return redirect(url_for('dashboard_medecin'))

    # Vérifier que le médecin a bien ce patient sous sa responsabilité
    relation = MedecinTraitant.query.filter_by(medecin_ID=current_user.ID_User, patient_ID=patient_id).first()
    if not relation:
        flash("Vous n'êtes pas autorisé à modifier ce dossier.", "danger")
        return redirect(url_for('dashboard_medecin'))
    
    if "traitements" in dossier.Dossier:
        if isinstance(dossier.Dossier["traitements"], list):
            traitements_corriges = []
            for t in dossier.Dossier["traitements"]:
                if isinstance(t, str):  # Si c'est une chaîne mal formatée
                    try:
                        t = json.loads(t.replace("'", "\""))  # Remplacer ' par "
                    except json.JSONDecodeError:
                        print("⚠ Erreur de conversion JSON :", t)  # Debugging
                        continue  # Ignorer ce traitement mal formé
                traitements_corriges.append(t)
            dossier.Dossier["traitements"] = traitements_corriges

    if request.method == 'POST':
        # Récupération des données du formulaire
        historique = request.form.get('historique')
        notes = request.form.get('notes')
        noms = request.form.getlist('traitements_nom[]')
        doses = request.form.getlist('traitements_dose[]')
        frequences = request.form.getlist('traitements_frequence[]')

        # Charger les données actuelles du dossier
        dossier_data = dossier.Dossier.copy() if dossier.Dossier else {}

        # Mise à jour des champs modifiables
        if historique:
            dossier_data["historique"] = historique
        if notes:
            dossier_data["notes"] = notes
        traitements_uniques = set()
        traitements_list = []

        for nom, dose, freq in zip(noms, doses, frequences):
            if nom in traitements_uniques:
                flash(f"Le traitement '{nom}' est déjà ajouté. Supprimez le doublon.", "danger")
                return redirect(url_for('modifier_dossier', patient_id=patient_id))
            traitements_uniques.add(nom)
            traitements_list.append({"nom": nom, "dose": dose, "frequence": freq})

        # Mise à jour des traitements sans doublons
        dossier_data["traitements"] = traitements_list



        # Forcer la mise à jour de la colonne JSON
        db.session.execute(
            ProfilMedical.__table__.update()
            .where(ProfilMedical.Patient_ID == patient_id)
            .values(Dossier=dossier_data)
        )
        db.session.commit()


        flash("Dossier médical mis à jour avec succès.", "success")
        return redirect(url_for('dossier_medical', patient_id=patient_id))

    print("Dossier to return",type(dossier.Dossier["traitements"][0]),dossier.Dossier["traitements"][0])
    return render_template('medecin/modifier_dossier.html', dossier=dossier)


@app.route('/associer_patient', methods=['GET', 'POST'], endpoint='associer_patient')
@role_required('Médecin')
def associer_patient():
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
            actif=True,
            date_debut=date_debut,
            date_fin=date_fin
        )
        db.session.add(nouveau_traitant)
        db.session.commit()
        flash("Association du patient réussie.", "success")
        return redirect(url_for('dashboard_medecin'))

    return render_template('medecin/associer_patient.html')

@app.route('/gerer_acces', methods=['GET', 'POST'], endpoint='gerer_acces')
@role_required('Médecin')
def gerer_acces():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'ajouter':
            utilisateur_id = request.form['utilisateur_id']
            patient_id = request.form['patient_id']
            role = request.form['role']
            date_debut = datetime.strptime(request.form['date_debut'], '%Y-%m-%d')
            date_fin = datetime.strptime(request.form['date_fin'], '%Y-%m-%d')

            # Vérifier si l'utilisateur est bien un Radiologue ou un Laborantin
            professionnel = Utilisateur.query.filter_by(ID_User=utilisateur_id, role=role).first()
            if not professionnel:
                flash("L'utilisateur sélectionné n'est pas un Radiologue ou un Laborantin.", "danger")
                return redirect(url_for('gerer_acces'))

            # Vérifier si l'accès existe déjà
            acces_existant = Acces.query.filter_by(Utilisateur_ID=utilisateur_id, Patient_ID=patient_id).first()
            if acces_existant:
                flash("Cet utilisateur a déjà accès au dossier du patient.", "warning")
                return redirect(url_for('gerer_acces'))

            # Création d'un nouvel accès
            nouvel_acces = Acces(
                Utilisateur_ID=utilisateur_id,
                Patient_ID=patient_id,
                role=role,
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

        return redirect(url_for('gerer_acces'))

    # Récupérer les accès des patients du médecin
    acces_existants = Acces.query.join(MedecinTraitant, Acces.Patient_ID == MedecinTraitant.patient_ID)\
                                 .filter(MedecinTraitant.medecin_ID == current_user.ID_User)\
                                 .all()

    return render_template('medecin/gerer_acces.html', acces_existants=acces_existants)

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
        .join(Utilisateur, ProfilMedical.Patient_ID == Utilisateur.ID_User) \
        .join(Acces, ProfilMedical.Patient_ID == Acces.Patient_ID) \
        .filter(Acces.Utilisateur_ID == current_user.ID_User, Acces.role == 'Radiologue') \
        .all()

    return render_template('radiologue/dashboard_radiologue.html', dossiers=dossiers)
@app.route('/dossier_medical_radiologue/<int:patient_id>', endpoint='dossier_medical_radiologue')
@role_required('Radiologue')
def dossier_medical_radiologue(patient_id):
    # Check if the radiologist has access
    acces = Acces.query.filter_by(Utilisateur_ID=current_user.ID_User, Patient_ID=patient_id, role='Radiologue').first()
    if not acces:
        flash("Vous n'avez pas accès à ce dossier.", "danger")
        return redirect(url_for('dashboard_radiologue'))

    dossier = ProfilMedical.query.filter_by(Patient_ID=patient_id).first()
    if not dossier:
        flash("Dossier médical introuvable.", "danger")
        return redirect(url_for('dashboard_radiologue'))

    # The radiologist only sees "imagerie"
    imagerie = dossier.Dossier.get("imagerie", [])

    return render_template('radiologue/dossier_medical_radiologue.html', dossier=imagerie, patient_id=patient_id, Utilisateur=Utilisateur)
@app.route('/ajouter_imagerie/<int:patient_id>', methods=['GET', 'POST'], endpoint='ajouter_imagerie')
@role_required('Radiologue')
def ajouter_imagerie(patient_id):
    # Vérifier si l'accès est autorisé
    acces = Acces.query.filter_by(Utilisateur_ID=current_user.ID_User, Patient_ID=patient_id, role='Radiologue').first()
    if not acces:
        flash("Vous n'avez pas accès à ce dossier.", "danger")
        return redirect(url_for('dashboard_radiologue'))

    dossier = ProfilMedical.query.filter_by(Patient_ID=patient_id).first()
    if not dossier:
        flash("Dossier médical introuvable.", "danger")
        return redirect(url_for('dashboard_radiologue'))

    if request.method == 'POST':
        type_imagerie = request.form.get('type')
        resultat = request.form.get('resultat')
        date = datetime.today().strftime('%Y-%m-%d')

        # Charger les données actuelles du dossier
        dossier_data = dossier.Dossier.copy() if dossier.Dossier else {}

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

        # 🔥 **Mise à jour forcée de la colonne JSON**
        db.session.execute(
            ProfilMedical.__table__.update()
            .where(ProfilMedical.Patient_ID == patient_id)
            .values(Dossier=dossier_data)
        )
        db.session.commit()

        flash("Rapport d'imagerie ajouté avec succès.", "success")
        return redirect(url_for('dossier_medical_radiologue', patient_id=patient_id))

    return render_template('radiologue/ajouter_imagerie.html', patient_id=patient_id)

@app.route('/modifier_imagerie/<int:patient_id>/<int:index>', methods=['GET', 'POST'], endpoint='modifier_imagerie')
@role_required('Radiologue')
def modifier_imagerie(patient_id, index):
    # Verify if the user has access to the patient's medical records
    acces = Acces.query.filter_by(Utilisateur_ID=current_user.ID_User, Patient_ID=patient_id, role='Radiologue').first()
    if not acces:
        flash("Vous n'avez pas accès à ce dossier.", "danger")
        return redirect(url_for('dashboard_radiologue'))

    dossier = ProfilMedical.query.filter_by(Patient_ID=patient_id).first()
    if not dossier or "imagerie" not in dossier.Dossier or index >= len(dossier.Dossier["imagerie"]):
        flash("Rapport d'imagerie introuvable.", "danger")
        return redirect(url_for('dossier_medical_radiologue', patient_id=patient_id))

    # Get the imaging report
    rapport = dossier.Dossier["imagerie"][index]

    # 🔹 **Check if the current user is the one who added the report**
    if "ajouté_par" not in rapport or rapport["ajouté_par"] != current_user.ID_User:
        flash("Vous ne pouvez modifier ou supprimer que les rapports que vous avez ajoutés.", "danger")
        return redirect(url_for('dossier_medical_radiologue', patient_id=patient_id))

    if request.method == 'POST':
        if 'delete' in request.form:  # Check if the delete button was pressed
            dossier_data = dossier.Dossier.copy()
            del dossier_data["imagerie"][index]  # Remove the report

            # 🔥 **Force updating the JSON column**
            db.session.execute(
                ProfilMedical.__table__.update()
                .where(ProfilMedical.Patient_ID == patient_id)
                .values(Dossier=dossier_data)
            )
            db.session.commit()

            flash("Rapport d'imagerie supprimé avec succès.", "success")
            return redirect(url_for('dossier_medical_radiologue', patient_id=patient_id))

        else:  # Update logic
            type_imagerie = request.form.get('type')
            resultat = request.form.get('resultat')

            # Load the current dossier data
            dossier_data = dossier.Dossier.copy()

            # Update the imaging report
            dossier_data["imagerie"][index]["type"] = type_imagerie
            dossier_data["imagerie"][index]["résultat"] = resultat
            dossier_data["imagerie"][index]["modifié_par"] = current_user.ID_User  # Store the editor ID

            # 🔥 **Force updating the JSON column**
            db.session.execute(
                ProfilMedical.__table__.update()
                .where(ProfilMedical.Patient_ID == patient_id)
                .values(Dossier=dossier_data)
            )
            db.session.commit()

            flash("Rapport d'imagerie modifié avec succès.", "success")
            return redirect(url_for('dossier_medical_radiologue', patient_id=patient_id))

    return render_template('radiologue/modifier_imagerie.html', patient_id=patient_id, rapport=rapport)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
