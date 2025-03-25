from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from datetime import datetime
from models import db, Utilisateur, MedecinTraitant, ProfilMedical, Acces

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
    patients_actifs = MedecinTraitant.query.filter_by(medecin_ID=current_user.ID_User, actif=True).all()
    return render_template('medecin/dashboard_medecin.html', patients_actifs=patients_actifs)

@app.route('/dossier_medical/<int:patient_id>', endpoint='dossier_medical')
@role_required('Médecin')
def dossier_medical(patient_id):
    dossier = ProfilMedical.query.filter_by(Patient_ID=patient_id).first()
    if dossier:
        return render_template('medecin/dossier_medical.html', dossier=dossier)
    return "Dossier non trouvé", 404

@app.route('/ajouter_patient', methods=['POST'], endpoint='ajouter_patient')
@role_required('Médecin')
def ajouter_patient():
    patient_id = request.form['patient_id']
    date_debut = datetime.strptime(request.form['date_debut'], '%Y-%m-%d')
    date_fin = datetime.strptime(request.form['date_fin'], '%Y-%m-%d')

    nouveau_traitant = MedecinTraitant(
        medecin_ID=current_user.ID_User,
        patient_ID=patient_id,
        actif=True,
        date_debut=date_debut,
        date_fin=date_fin
    )
    db.session.add(nouveau_traitant)
    db.session.commit()
    return redirect(url_for('medecin/dashboard_medecin'))

@app.route('/gerer_acces', methods=['POST'], endpoint='gerer_acces')
@role_required('Médecin')
def gerer_acces():
    utilisateur_id = request.form['utilisateur_id']
    patient_id = request.form['patient_id']
    attributes = request.form['attributes']

    nouvel_acces = Acces(
        Utilisateur_ID=utilisateur_id,
        attributes=attributes
    )
    db.session.add(nouvel_acces)
    db.session.commit()
    return redirect(url_for('medecin/dashboard_medecin'))

@app.route('/historique_interactions', endpoint='historique_interactions')
@role_required('Médecin')
def historique_interactions():
    interactions = Acces.query.filter_by(Utilisateur_ID=current_user.ID_User).all()
    return render_template('medecin/historique_interactions.html', interactions=interactions)
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
#                                  Radiologue                                  #
# ---------------------------------------------------------------------------- #

@app.route('/dashboard_radiologue', endpoint='dashboard_radiologue')
@login_required
@role_required('Radiologue')
def dashboard_radiologue():
    # Récupérer les dossiers accessibles par le radiologue
    accessible_dossiers = Acces.query.filter_by(Utilisateur_ID=current_user.ID_User).all()
    dossiers = []
    for acces in accessible_dossiers:
        dossier = ProfilMedical.query.filter_by(ID_Dossier=acces.ID_Acces).first()
        if dossier:
            dossiers.append(dossier)
    return render_template('rediologue/dashboard_radiologue.html', dossiers=dossiers)

@app.route('/ajouter_rapport/<int:dossier_id>', methods=['POST'], endpoint='ajouter_rapport')
@login_required
@role_required('Radiologue')
def ajouter_rapport(dossier_id):
    # Ajouter un rapport d'imagerie à un dossier médical
    rapport = request.form.get('rapport')
    if rapport:
        dossier = ProfilMedical.query.get(dossier_id)
        if dossier:
            # Supposons que le dossier est un JSON, nous ajoutons le rapport à une clé "rapports"
            if 'rapports' not in dossier.Dossier:
                dossier.Dossier['rapports'] = []
            dossier.Dossier['rapports'].append({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'contenu': rapport
            })
            db.session.commit()
            flash("Rapport ajouté avec succès.", "success")
        else:
            flash("Dossier non trouvé.", "danger")
    else:
        flash("Aucun rapport fourni.", "warning")

    return redirect(url_for('dashboard_radiologue'))

@app.route('/laisser_note/<int:dossier_id>', methods=['POST'], endpoint='laisser_note')
@login_required
@role_required('Radiologue')
def laisser_note(dossier_id):
    # Laisser une note ou un avis sur un dossier médical
    note = request.form.get('note')
    if note:
        dossier = ProfilMedical.query.get(dossier_id)
        if dossier:
            # Supposons que le dossier est un JSON, nous ajoutons la note à une clé "notes"
            if 'notes' not in dossier.Dossier:
                dossier.Dossier['notes'] = []
            dossier.Dossier['notes'].append({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'contenu': note
            })
            db.session.commit()
            flash("Note ajoutée avec succès.", "success")
        else:
            flash("Dossier non trouvé.", "danger")
    else:
        flash("Aucune note fournie.", "warning")

    return redirect(url_for('dashboard_radiologue'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
