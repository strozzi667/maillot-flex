import os
import uuid
import json
import threading
from functools import wraps

import certifi
import mysql.connector
from mysql.connector import Error

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, render_template_string
)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# ==================================================
# CONFIGURATION MAILLOT FLEX
# ==================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "cle-secrete-maillot-flex-a-changer"
)

app.config["UPLOAD_FOLDER"] = os.path.join(
    app.root_path, "static", "uploads"
)

app.config["AUDIO_FOLDER"] = os.path.join(
    app.root_path, "static", "uploads", "musiques"
)

app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["AUDIO_FOLDER"], exist_ok=True)

ADMIN_EMAIL = os.environ.get(
    "ADMIN_EMAIL",
    "Strozzingalwe23@gmail.com"
).strip().lower()

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

DB_NAME = os.environ.get("DB_NAME", "maillot_flex")
DB_HOST = os.environ.get("DB_HOST", "localhost")

DB_CONFIG = {
    "host": DB_HOST,
    "user": os.environ.get(
        "DB_USER",
        "root" if DB_HOST == "localhost" else "fsyRNaqcDJZSxtJ.root"
    ),
    "password": os.environ.get("DB_PASSWORD", ""),
    "port": int(os.environ.get(
        "DB_PORT",
        "3306" if DB_HOST == "localhost" else "4000"
    ))
}

# TLS obligatoire pour l'endpoint public TiDB Cloud
if DB_HOST != "localhost":
    DB_CONFIG.update({
        "ssl_ca": certifi.where(),
        "ssl_verify_cert": True,
        "ssl_verify_identity": True
    })

EXTENSIONS_AUTORISEES = {
    "jpg", "jpeg", "png", "webp"
}

EXTENSIONS_AUDIO = {
    "mp3", "wav", "ogg"
}


# ==================================================
# CONNEXION MYSQL / TIDB CLOUD
# ==================================================

def connexion_mysql(avec_base=True):

    config = DB_CONFIG.copy()

    if avec_base:
        config["database"] = DB_NAME

    return mysql.connector.connect(**config)


# ==================================================
# OUTILS POUR LES FICHIERS
# ==================================================

def extension_autorisee(nom_fichier, extensions):

    if not nom_fichier or "." not in nom_fichier:
        return False

    extension = nom_fichier.rsplit(".", 1)[1].lower()

    return extension in extensions


def enregistrer_fichier(fichier, dossier, extensions):

    if not fichier or not fichier.filename:
        return None

    if not extension_autorisee(fichier.filename, extensions):
        raise ValueError("Format de fichier non autorisé.")

    nom_original = secure_filename(fichier.filename)
    extension = nom_original.rsplit(".", 1)[1].lower()

    nom_unique = f"{uuid.uuid4().hex}.{extension}"

    chemin = os.path.join(dossier, nom_unique)

    fichier.save(chemin)

    return nom_unique


def supprimer_fichier(dossier, nom_fichier):

    if not nom_fichier:
        return

    if str(nom_fichier).startswith(("http://", "https://")):
        return

    nom_fichier = os.path.basename(nom_fichier)

    chemin = os.path.join(dossier, nom_fichier)

    if os.path.isfile(chemin):
        os.remove(chemin)


# ==================================================
# CATALOGUE INITIAL DES MAILLOTS
# ==================================================

def inserer_catalogue_initial(curseur):

    catalogue = [

        {
            "nom": "Maillot Real Madrid Domicile",
            "club": "Real Madrid",
            "categorie": "club",
            "image": "https://www.prosoccer.com/cdn/shop/files/adidas2026-27RealMadridMen_sAuthenticHomeSoccerJersey_Front.jpg?v=1782863888&width=1946"
        },

        {
            "nom": "Maillot FC Barcelona Domicile",
            "club": "FC Barcelona",
            "categorie": "club",
            "image": "https://www.subsidesports.com/media/catalog/product/cache/a5716ed2a1003630b9abacca1719c93b/d/7/d742752720060b9fe622b4454cf1bbe7b8af08fae676ebdae1da351ee4906422.jpeg"
        },

        {
            "nom": "Maillot PSG Domicile",
            "club": "PSG",
            "categorie": "club",
            "image": "https://thumblr.uniid.it/product/392882/c4afd57cc142.jpg?format=webp&q=75&width=1200"
        },

        {
            "nom": "Maillot Manchester United Domicile",
            "club": "Manchester United",
            "categorie": "club",
            "image": "https://cdn.media.amplience.net/i/frasersdev/37746108_o.jpg?v=20260501102933"
        },

        {
            "nom": "Maillot Inter Milan Domicile",
            "club": "Inter Milan",
            "categorie": "club",
            "image": "https://cdn.sportshop.com/catalog/product/1500/1500/3/9/394821_1.jpg?v=ac6d03ca5ceb20b1"
        },

        {
            "nom": "Maillot AC Milan Domicile",
            "club": "AC Milan",
            "categorie": "club",
            "image": "https://store.acmilan.com/cdn/shop/files/784120-A82_01.jpg?v=1779429459"
        },

        {
            "nom": "Maillot Atlético Madrid Domicile",
            "club": "Atlético Madrid",
            "categorie": "club",
            "image": "https://shop.atleticodemadrid.com/on/demandware.static/-/Sites-atm-master-catalog/default/dwd1104d16/II2740-101_DELANTERA_PARCHELIGA.jpg"
        },

        {
            "nom": "Maillot Borussia Dortmund Domicile",
            "club": "Borussia Dortmund",
            "categorie": "club",
            "image": "https://www.kickoffofficialstore.com/cdn/shop/files/94965-62da355905166_1400x.jpg?v=1778418814"
        },

        {
            "nom": "Maillot RDC Domicile",
            "club": "République démocratique du Congo",
            "categorie": "selection",
            "image": "https://umbroteam.com/cdn/shop/files/DRC_WC_HOME_JERSEY_02.jpg?v=1778267835&width=1920"
        }
    ]

    ajoutes = 0

    for article in catalogue:

        curseur.execute("""
            SELECT id
            FROM produits
            WHERE LOWER(club) = LOWER(%s)
              AND saison = %s
              AND type_maillot = %s
            LIMIT 1
        """, (
            article["club"],
            "2026/2027",
            "Domicile"
        ))

        existe = curseur.fetchone()

        if existe:
            continue

        curseur.execute("""
            INSERT INTO produits (
                nom,
                club,
                categorie,
                type_maillot,
                saison,
                prix,
                image,
                tailles,
                description
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            article["nom"],
            article["club"],
            article["categorie"],
            "Domicile",
            "2026/2027",
            12.00,
            article["image"],
            "S,M,L,XL,XXL",
            "Maillot domicile disponible chez MAILLOT FLEX."
        ))

        ajoutes += 1

    print(f"{ajoutes} nouveaux maillots ajoutés au catalogue.")


# ==================================================
# INITIALISATION DE LA BASE DE DONNÉES
# ==================================================

def initialiser_base():

    # Création automatique de la base uniquement en local.
    # Sur TiDB, on utilise la base sélectionnée dans Render.

    if DB_HOST == "localhost":

        connexion = connexion_mysql(avec_base=False)
        curseur = connexion.cursor()

        try:

            curseur.execute(
                f"CREATE DATABASE IF NOT EXISTS {DB_NAME} "
                "CHARACTER SET utf8mb4 "
                "COLLATE utf8mb4_unicode_ci"
            )

        finally:

            curseur.close()
            connexion.close()

    connexion = connexion_mysql()
    curseur = connexion.cursor()

    try:

        curseur.execute("""
            CREATE TABLE IF NOT EXISTS administrateurs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(150) NOT NULL UNIQUE,
                mot_de_passe VARCHAR(255) NOT NULL,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        curseur.execute("""
            CREATE TABLE IF NOT EXISTS produits (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nom VARCHAR(200) NOT NULL,
                club VARCHAR(150) NOT NULL,
                categorie VARCHAR(50) NOT NULL,
                type_maillot VARCHAR(80),
                saison VARCHAR(30) NOT NULL,
                prix DECIMAL(10,2) NOT NULL,
                image VARCHAR(255) NOT NULL,
                tailles VARCHAR(100),
                description TEXT,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        curseur.execute("""
            CREATE TABLE IF NOT EXISTS produit_photos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                produit_id INT NOT NULL,
                image VARCHAR(255) NOT NULL,
                ordre INT DEFAULT 0,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (produit_id)
                    REFERENCES produits(id)
                    ON DELETE CASCADE
            )
        """)

        curseur.execute("""
            CREATE TABLE IF NOT EXISTS musiques (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nom VARCHAR(200) NOT NULL,
                fichier VARCHAR(255) NOT NULL,
                active TINYINT(1) DEFAULT 1,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        curseur.execute("""
            CREATE TABLE IF NOT EXISTS commandes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nom_client VARCHAR(150),
                telephone VARCHAR(30),
                adresse TEXT,
                total DECIMAL(10,2),
                statut VARCHAR(50) DEFAULT 'En attente',
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        nouvelles_colonnes = {
            "commune": "VARCHAR(100)",
            "instructions": "TEXT",
            "details": "TEXT"
        }

        for nom_colonne, type_colonne in nouvelles_colonnes.items():

            curseur.execute(
                f"SHOW COLUMNS FROM commandes LIKE '{nom_colonne}'"
            )

            if not curseur.fetchone():

                curseur.execute(
                    f"ALTER TABLE commandes ADD COLUMN "
                    f"{nom_colonne} {type_colonne}"
                )

        curseur.execute(
            "SELECT id FROM administrateurs WHERE email = %s",
            (ADMIN_EMAIL,)
        )

        admin = curseur.fetchone()

        if not admin and ADMIN_PASSWORD:

            mot_de_passe_hash = generate_password_hash(
                ADMIN_PASSWORD
            )

            curseur.execute("""
                INSERT INTO administrateurs (
                    email,
                    mot_de_passe
                )
                VALUES (%s, %s)
            """, (
                ADMIN_EMAIL,
                mot_de_passe_hash
            ))

            print("Administrateur créé avec succès.")

        elif not admin:

            print("ATTENTION : ADMIN_PASSWORD n'est pas défini.")

        inserer_catalogue_initial(curseur)

        connexion.commit()

        print("Base MAILLOT FLEX prête.")

    except Exception:

        connexion.rollback()
        raise

    finally:

        curseur.close()
        connexion.close()


# ==================================================
# INITIALISATION AUTOMATIQUE POUR RENDER
# ==================================================

_initialisation_verrou = threading.Lock()
_base_initialisee = False


@app.before_request
def verifier_initialisation_base():

    global _base_initialisee

    if _base_initialisee:
        return

    with _initialisation_verrou:

        if _base_initialisee:
            return

        initialiser_base()
        _base_initialisee = True


# ==================================================
# PROTECTION ADMINISTRATEUR
# ==================================================

def administrateur_requis(fonction):

    @wraps(fonction)
    def verifier(*args, **kwargs):

        if "admin_id" not in session:
            return redirect(url_for("admin_login"))

        return fonction(*args, **kwargs)

    return verifier


# ==================================================
# ACCUEIL
# ==================================================

@app.route("/")
def accueil():

    connexion = connexion_mysql()

    try:

        curseur = connexion.cursor(dictionary=True)

        curseur.execute("""
            SELECT *
            FROM produits
            ORDER BY date_creation DESC
        """)

        produits = curseur.fetchall()

        return render_template(
            "index.html",
            produits=produits
        )

    finally:

        curseur.close()
        connexion.close()


# ==================================================
# BOUTIQUE
# ==================================================

@app.route("/boutique")
def boutique():

    connexion = connexion_mysql()

    try:

        curseur = connexion.cursor(dictionary=True)

        curseur.execute("""
            SELECT *
            FROM produits
            ORDER BY date_creation DESC
        """)

        produits = curseur.fetchall()

        return render_template(
            "boutique.html",
            produits=produits
        )

    finally:

        curseur.close()
        connexion.close()


# ==================================================
# DÉTAILS D'UN PRODUIT
# ==================================================

@app.route("/produit/<int:produit_id>")
def detail_produit(produit_id):

    connexion = connexion_mysql()

    try:

        curseur = connexion.cursor(dictionary=True)

        curseur.execute(
            "SELECT * FROM produits WHERE id = %s",
            (produit_id,)
        )

        produit = curseur.fetchone()

        if produit is None:

            flash("Ce maillot n'existe pas.")

            return redirect(url_for("boutique"))

        curseur.execute("""
            SELECT id, image, ordre
            FROM produit_photos
            WHERE produit_id = %s
            ORDER BY ordre ASC, id ASC
        """, (produit_id,))

        photos = curseur.fetchall()

        return render_template(
            "produit.html",
            produit=produit,
            photos=photos
        )

    finally:

        curseur.close()
        connexion.close()


# ==================================================
# PANIER
# ==================================================

@app.route("/panier")
def panier():

    return render_template("panier.html")


# ==================================================
# PAGE DE COMMANDE
# ==================================================

@app.route("/commande")
def passer_commande():

    return render_template("commande.html")


# ==================================================
# ENREGISTREMENT ET CONFIRMATION DE COMMANDE
# ==================================================

@app.route(
    "/commande/confirmation",
    methods=["GET", "POST"]
)
def confirmation_commande():

    if request.method == "GET":

        numero = request.args.get("numero", "")

        return render_template_string("""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
            <title>Commande confirmée | MAILLOT FLEX</title>
            <style>
                body {
                    background:#080a09;
                    color:white;
                    font-family:Arial,sans-serif;
                    text-align:center;
                    padding:70px 20px;
                }
                .carte {
                    max-width:500px;
                    margin:auto;
                    background:#111612;
                    padding:35px;
                    border:1px solid #303a31;
                    border-radius:10px;
                }
                h1 { color:#b7ff35; }
                p { color:#c5cbc6; line-height:1.7; }
                a {
                    display:inline-block;
                    margin-top:20px;
                    padding:15px 25px;
                    background:#b7ff35;
                    color:#080a09;
                    text-decoration:none;
                    font-weight:bold;
                    border-radius:5px;
                }
            </style>
        </head>
        <body>
            <div class="carte">
                <h1>Commande enregistrée !</h1>
                <p>Merci pour ta confiance.</p>
                <p>Ton numéro de commande :
                   <strong>#{{ numero }}</strong>
                </p>
                <p>
                    MAILLOT FLEX prendra contact avec toi
                    pour confirmer la livraison.
                </p>
                <a href="/">RETOURNER À LA BOUTIQUE</a>
            </div>
        </body>
        </html>
        """, numero=numero)

    donnees = request.get_json(silent=True)

    if not donnees:

        return jsonify({
            "success": False,
            "message": "Informations de commande manquantes."
        }), 400

    nom = str(donnees.get("nom", "")).strip()
    telephone = str(donnees.get("telephone", "")).strip()
    commune = str(donnees.get("commune", "")).strip()
    adresse = str(donnees.get("adresse", "")).strip()

    instructions = str(
        donnees.get("instructions", "")
    ).strip()

    articles = donnees.get("panier", [])

    if not nom or not telephone or not commune or not adresse:

        return jsonify({
            "success": False,
            "message": "Remplis toutes les informations obligatoires."
        }), 400

    if not isinstance(articles, list) or not articles:

        return jsonify({
            "success": False,
            "message": "Ton panier est vide."
        }), 400

    if len(articles) > 50:

        return jsonify({
            "success": False,
            "message": "Le nombre d'articles est trop élevé."
        }), 400

    total = 0

    try:

        for article in articles:

            if not isinstance(article, dict):
                raise ValueError

            prix = float(article.get("price", 0))
            quantite = int(article.get("quantity", 1))

            if prix <= 0 or quantite <= 0:
                raise ValueError

            if quantite > 100:
                raise ValueError

            total += prix * quantite

        details = json.dumps(
            articles,
            ensure_ascii=False
        )

    except (ValueError, TypeError, AttributeError):

        return jsonify({
            "success": False,
            "message": "Les informations des articles sont invalides."
        }), 400

    connexion = None
    curseur = None

    try:

        connexion = connexion_mysql()
        curseur = connexion.cursor()

        curseur.execute("""
            INSERT INTO commandes (
                nom_client,
                telephone,
                adresse,
                commune,
                instructions,
                total,
                details,
                statut
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            nom,
            telephone,
            adresse,
            commune,
            instructions,
            total,
            details,
            "En attente"
        ))

        connexion.commit()

        numero_commande = curseur.lastrowid

        return jsonify({
            "success": True,
            "numero": numero_commande,
            "message": "Commande enregistrée."
        })

    except Error as erreur:

        print("ERREUR COMMANDE :", erreur)

        return jsonify({
            "success": False,
            "message": "Erreur lors de l'enregistrement de la commande."
        }), 500

    finally:

        if curseur:
            curseur.close()

        if connexion and connexion.is_connected():
            connexion.close()


# ==================================================
# CONNEXION ADMINISTRATEUR
# ==================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":

        email = request.form.get(
            "email", ""
        ).strip().lower()

        mot_de_passe = request.form.get(
            "mot_de_passe", ""
        )

        connexion = None
        curseur = None

        try:

            connexion = connexion_mysql()

            curseur = connexion.cursor(dictionary=True)

            curseur.execute("""
                SELECT id, email, mot_de_passe
                FROM administrateurs
                WHERE LOWER(TRIM(email)) = %s
            """, (email,))

            admin = curseur.fetchone()

            if admin and check_password_hash(
                admin["mot_de_passe"],
                mot_de_passe
            ):

                session.clear()

                session["admin_id"] = admin["id"]
                session["admin_email"] = admin["email"]

                print("CONNEXION ADMINISTRATEUR RÉUSSIE")

                return redirect(url_for("admin_dashboard"))

            flash("Adresse Gmail ou mot de passe incorrect.")

        except Error as erreur:

            print("ERREUR MYSQL :", erreur)

            flash("Impossible de contacter la base de données.")

        finally:

            if curseur:
                curseur.close()

            if connexion and connexion.is_connected():
                connexion.close()

    return render_template("connexion.html")


# ==================================================
# TABLEAU DE BORD ADMINISTRATEUR
# ==================================================

@app.route("/admin")
@administrateur_requis
def admin_dashboard():

    connexion = connexion_mysql()
    curseur = None

    try:

        curseur = connexion.cursor(dictionary=True)

        curseur.execute("""
            SELECT *
            FROM produits
            ORDER BY date_creation DESC
        """)

        produits = curseur.fetchall()

        for produit in produits:

            curseur.execute("""
                SELECT id, image, ordre
                FROM produit_photos
                WHERE produit_id = %s
                ORDER BY ordre ASC, id ASC
            """, (produit["id"],))

            produit["photos"] = curseur.fetchall()

        curseur.execute("""
            SELECT *
            FROM commandes
            ORDER BY date_creation DESC
        """)

        commandes = curseur.fetchall()

        for commande in commandes:

            try:

                commande["articles"] = json.loads(
                    commande.get("details") or "[]"
                )

                if not isinstance(commande["articles"], list):
                    commande["articles"] = []

            except (json.JSONDecodeError, TypeError):

                commande["articles"] = []

        curseur.execute("""
            SELECT *
            FROM musiques
            ORDER BY date_creation DESC
        """)

        musiques = curseur.fetchall()

        nombre_commandes = len(commandes)

        return render_template(
            "admin.html",
            produits=produits,
            commandes=commandes,
            nombre_commandes=nombre_commandes,
            musiques=musiques
        )

    finally:

        if curseur:
            curseur.close()

        if connexion and connexion.is_connected():
            connexion.close()


# ==================================================
# AJOUTER UN MAILLOT
# ==================================================

@app.route("/admin/produits/ajouter", methods=["POST"])
@administrateur_requis
def ajouter_produit():

    nom = request.form.get("nom", "").strip()
    club = request.form.get("club", "").strip()

    categorie = request.form.get("categorie", "club")
    type_maillot = request.form.get("type_maillot", "")
    saison = request.form.get("saison", "").strip()
    tailles = request.form.get("tailles", "")
    description = request.form.get("description", "").strip()

    try:

        prix = float(request.form.get("prix", "12"))

        if prix <= 0:
            raise ValueError

    except ValueError:

        flash("Le prix indiqué est invalide.")

        return redirect(url_for("admin_dashboard"))

    if categorie not in {"club", "selection", "nouveau"}:

        flash("Catégorie invalide.")

        return redirect(url_for("admin_dashboard"))

    if not nom or not club or not saison:

        flash("Remplis les champs obligatoires.")

        return redirect(url_for("admin_dashboard"))

    fichier_principal = request.files.get("image")

    if not fichier_principal or not fichier_principal.filename:

        flash("Ajoute une photo principale.")

        return redirect(url_for("admin_dashboard"))

    fichiers_enregistres = []

    connexion = None
    curseur = None

    try:

        image_principale = enregistrer_fichier(
            fichier_principal,
            app.config["UPLOAD_FOLDER"],
            EXTENSIONS_AUTORISEES
        )

        fichiers_enregistres.append(image_principale)

        images_secondaires = []

        for fichier in request.files.getlist("images_secondaires"):

            if fichier and fichier.filename:

                image = enregistrer_fichier(
                    fichier,
                    app.config["UPLOAD_FOLDER"],
                    EXTENSIONS_AUTORISEES
                )

                images_secondaires.append(image)
                fichiers_enregistres.append(image)

        connexion = connexion_mysql()
        curseur = connexion.cursor()

        curseur.execute("""
            INSERT INTO produits (
                nom,
                club,
                categorie,
                type_maillot,
                saison,
                prix,
                image,
                tailles,
                description
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            nom,
            club,
            categorie,
            type_maillot,
            saison,
            prix,
            image_principale,
            tailles,
            description
        ))

        produit_id = curseur.lastrowid

        for ordre, image in enumerate(images_secondaires, start=1):

            curseur.execute("""
                INSERT INTO produit_photos (
                    produit_id,
                    image,
                    ordre
                )
                VALUES (%s, %s, %s)
            """, (
                produit_id,
                image,
                ordre
            ))

        connexion.commit()

        flash("Le maillot a été publié avec succès.")

    except (Error, ValueError) as erreur:

        if connexion and connexion.is_connected():
            connexion.rollback()

        for nom_fichier in fichiers_enregistres:

            supprimer_fichier(
                app.config["UPLOAD_FOLDER"],
                nom_fichier
            )

        print("ERREUR AJOUT PRODUIT :", erreur)

        flash(
            str(erreur) if isinstance(erreur, ValueError)
            else "Erreur lors de l'enregistrement du maillot."
        )

    finally:

        if curseur:
            curseur.close()

        if connexion and connexion.is_connected():
            connexion.close()

    return redirect(url_for("admin_dashboard"))


# ==================================================
# MODIFIER UN MAILLOT
# ==================================================

@app.route(
    "/admin/produits/modifier/<int:produit_id>",
    methods=["POST"]
)
@administrateur_requis
def modifier_produit(produit_id):

    nom = request.form.get("nom", "").strip()
    club = request.form.get("club", "").strip()
    categorie = request.form.get("categorie", "club")
    type_maillot = request.form.get("type_maillot", "")
    saison = request.form.get("saison", "").strip()
    tailles = request.form.get("tailles", "")
    description = request.form.get("description", "").strip()

    try:

        prix = float(request.form.get("prix", "12"))

        if prix <= 0:
            raise ValueError

    except ValueError:

        flash("Prix invalide.")

        return redirect(url_for("admin_dashboard"))

    if not nom or not club or not saison:

        flash("Certains champs obligatoires sont vides.")

        return redirect(url_for("admin_dashboard"))

    if categorie not in {"club", "selection", "nouveau"}:

        flash("Catégorie invalide.")

        return redirect(url_for("admin_dashboard"))

    connexion = None
    curseur = None
    nouvelle_image = None
    ancienne_image = None

    try:

        connexion = connexion_mysql()
        curseur = connexion.cursor(dictionary=True)

        curseur.execute(
            "SELECT image FROM produits WHERE id = %s",
            (produit_id,)
        )

        produit = curseur.fetchone()

        if not produit:

            flash("Maillot introuvable.")

            return redirect(url_for("admin_dashboard"))

        ancienne_image = produit["image"]

        fichier = request.files.get("image")

        if fichier and fichier.filename:

            nouvelle_image = enregistrer_fichier(
                fichier,
                app.config["UPLOAD_FOLDER"],
                EXTENSIONS_AUTORISEES
            )

        curseur.execute("""
            UPDATE produits
            SET nom = %s,
                club = %s,
                categorie = %s,
                type_maillot = %s,
                saison = %s,
                prix = %s,
                tailles = %s,
                description = %s
            WHERE id = %s
        """, (
            nom,
            club,
            categorie,
            type_maillot,
            saison,
            prix,
            tailles,
            description,
            produit_id
        ))

        if nouvelle_image:

            curseur.execute("""
                UPDATE produits
                SET image = %s
                WHERE id = %s
            """, (
                nouvelle_image,
                produit_id
            ))

        connexion.commit()

        if nouvelle_image:

            supprimer_fichier(
                app.config["UPLOAD_FOLDER"],
                ancienne_image
            )

        flash("Le maillot a été modifié.")

    except (Error, ValueError) as erreur:

        if connexion and connexion.is_connected():
            connexion.rollback()

        if nouvelle_image:

            supprimer_fichier(
                app.config["UPLOAD_FOLDER"],
                nouvelle_image
            )

        print("ERREUR MODIFICATION :", erreur)

        flash("Impossible de modifier ce maillot.")

    finally:

        if curseur:
            curseur.close()

        if connexion and connexion.is_connected():
            connexion.close()

    return redirect(url_for("admin_dashboard"))


# ==================================================
# SUPPRIMER UNE PHOTO DE LA GALERIE
# ==================================================

@app.route(
    "/admin/photos/supprimer/<int:photo_id>",
    methods=["POST"]
)
@administrateur_requis
def supprimer_photo(photo_id):

    connexion = connexion_mysql()

    try:

        curseur = connexion.cursor(dictionary=True)

        curseur.execute("""
            SELECT image
            FROM produit_photos
            WHERE id = %s
        """, (photo_id,))

        photo = curseur.fetchone()

        if photo:

            curseur.execute("""
                DELETE FROM produit_photos
                WHERE id = %s
            """, (photo_id,))

            connexion.commit()

            supprimer_fichier(
                app.config["UPLOAD_FOLDER"],
                photo["image"]
            )

            flash("Photo supprimée.")

        else:

            flash("Photo introuvable.")

    finally:

        curseur.close()
        connexion.close()

    return redirect(url_for("admin_dashboard"))


# ==================================================
# SUPPRIMER UN MAILLOT
# ==================================================

@app.route(
    "/admin/produits/supprimer/<int:produit_id>",
    methods=["POST"]
)
@administrateur_requis
def supprimer_produit(produit_id):

    connexion = connexion_mysql()
    curseur = connexion.cursor(dictionary=True)

    try:

        curseur.execute(
            "SELECT image FROM produits WHERE id = %s",
            (produit_id,)
        )

        produit = curseur.fetchone()

        if not produit:

            flash("Maillot introuvable.")

            return redirect(url_for("admin_dashboard"))

        curseur.execute("""
            SELECT image
            FROM produit_photos
            WHERE produit_id = %s
        """, (produit_id,))

        photos = curseur.fetchall()

        curseur.execute("""
            DELETE FROM produit_photos
            WHERE produit_id = %s
        """, (produit_id,))

        curseur.execute(
            "DELETE FROM produits WHERE id = %s",
            (produit_id,)
        )

        connexion.commit()

        supprimer_fichier(
            app.config["UPLOAD_FOLDER"],
            produit["image"]
        )

        for photo in photos:

            supprimer_fichier(
                app.config["UPLOAD_FOLDER"],
                photo["image"]
            )

        flash("Le maillot a été supprimé.")

    finally:

        curseur.close()
        connexion.close()

    return redirect(url_for("admin_dashboard"))


# ==================================================
# AJOUTER UNE MUSIQUE
# ==================================================

@app.route("/admin/musiques/ajouter", methods=["POST"])
@administrateur_requis
def ajouter_musique():

    fichier = request.files.get("musique")
    nom = request.form.get("nom", "").strip()

    if not fichier or not fichier.filename:

        flash("Choisis un fichier audio.")

        return redirect(url_for("admin_dashboard"))

    if not extension_autorisee(fichier.filename, EXTENSIONS_AUDIO):

        flash("Format audio non autorisé. Utilise MP3, WAV ou OGG.")

        return redirect(url_for("admin_dashboard"))

    nom_fichier = None
    connexion = None
    curseur = None

    try:

        nom_fichier = enregistrer_fichier(
            fichier,
            app.config["AUDIO_FOLDER"],
            EXTENSIONS_AUDIO
        )

        if not nom:
            nom = os.path.splitext(
                secure_filename(fichier.filename)
            )[0]

        connexion = connexion_mysql()
        curseur = connexion.cursor()

        curseur.execute("""
            INSERT INTO musiques (nom, fichier, active)
            VALUES (%s, %s, 1)
        """, (
            nom,
            nom_fichier
        ))

        connexion.commit()

        flash("Musique ajoutée avec succès.")

    except (Error, ValueError) as erreur:

        if connexion and connexion.is_connected():
            connexion.rollback()

        if nom_fichier:

            supprimer_fichier(
                app.config["AUDIO_FOLDER"],
                nom_fichier
            )

        print("ERREUR MUSIQUE :", erreur)

        flash("Impossible d'ajouter cette musique.")

    finally:

        if curseur:
            curseur.close()

        if connexion and connexion.is_connected():
            connexion.close()

    return redirect(url_for("admin_dashboard"))


# ==================================================
# ACTIVER OU DÉSACTIVER UNE MUSIQUE
# ==================================================

@app.route(
    "/admin/musiques/etat/<int:musique_id>",
    methods=["POST"]
)
@administrateur_requis
def changer_etat_musique(musique_id):

    connexion = connexion_mysql()

    try:

        curseur = connexion.cursor()

        curseur.execute("""
            UPDATE musiques
            SET active = IF(active = 1, 0, 1)
            WHERE id = %s
        """, (musique_id,))

        connexion.commit()

        flash("État de la musique modifié.")

    finally:

        curseur.close()
        connexion.close()

    return redirect(url_for("admin_dashboard"))


# ==================================================
# SUPPRIMER UNE MUSIQUE
# ==================================================

@app.route(
    "/admin/musiques/supprimer/<int:musique_id>",
    methods=["POST"]
)
@administrateur_requis
def supprimer_musique(musique_id):

    connexion = connexion_mysql()

    try:

        curseur = connexion.cursor(dictionary=True)

        curseur.execute("""
            SELECT fichier
            FROM musiques
            WHERE id = %s
        """, (musique_id,))

        musique = curseur.fetchone()

        if musique:

            curseur.execute("""
                DELETE FROM musiques
                WHERE id = %s
            """, (musique_id,))

            connexion.commit()

            supprimer_fichier(
                app.config["AUDIO_FOLDER"],
                musique["fichier"]
            )

            flash("Musique supprimée.")

        else:

            flash("Musique introuvable.")

    finally:

        curseur.close()
        connexion.close()

    return redirect(url_for("admin_dashboard"))


# ==================================================
# DÉCONNEXION ADMINISTRATEUR
# ==================================================

@app.route("/admin/deconnexion")
def admin_deconnexion():

    session.clear()

    flash("Vous êtes déconnecté.")

    return redirect(url_for("admin_login"))


# ==================================================
# ERREURS DE TÉLÉVERSEMENT
# ==================================================

@app.errorhandler(413)
def fichier_trop_lourd(erreur):

    return (
        "Le fichier est trop lourd. "
        "La limite totale est de 30 Mo.",
        413
    )


# ==================================================
# DÉMARRAGE DE L'APPLICATION
# ==================================================

if __name__ == "__main__":

    try:

        initialiser_base()
        _base_initialisee = True

        app.run(
            host="127.0.0.1",
            port=5000,
            debug=True
        )

    except Error as erreur:

        print("ERREUR MYSQL :", erreur)

        print(
            "Vérifie les paramètres de connexion à MySQL ou TiDB Cloud."
        )