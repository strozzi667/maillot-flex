import mysql.connector
from werkzeug.security import check_password_hash

connexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="maillot_flex"
)

curseur = connexion.cursor(dictionary=True)

curseur.execute("""
    SELECT email, mot_de_passe
    FROM administrateurs
    WHERE email = %s
""", ("Strozzingalwe23@gmail.com",))

admin = curseur.fetchone()

if admin:
    print("COMPTE TROUVE")
    print("EMAIL :", admin["email"])

    resultat = check_password_hash(
        admin["mot_de_passe"],
        "Strozzi2027!"
    )

    print("MOT DE PASSE CORRECT :", resultat)
else:
    print("AUCUN COMPTE TROUVE")

curseur.close()
connexion.close()