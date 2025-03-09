# gestion_tutorat/logs.py

from django.core.mail import send_mail
from django.conf import settings
from .models import Log
import datetime
import os.path
import pickle
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuration pour les emails d'alerte
ALERT_ADMIN_EMAIL = getattr(settings, 'ALERT_ADMIN_EMAIL', 'admin@example.com')
SITE_NAME = getattr(settings, 'SITE_NAME', 'Gestion Tutorat')
EMAIL_ENABLED = getattr(settings, 'ALERT_EMAILS_ENABLED', True)

from .models import Log
from django.conf import settings

import os
import uuid
import base64
import traceback
from io import BytesIO
from datetime import datetime
from PIL import Image
import tempfile


from django.utils.timezone import now
from django.conf import settings

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


# Si vous êtes dans Django
credentials_path = os.path.join(settings.BASE_DIR, 'gestion_tutorat/credentials.json')



def log_action(user, action, details="", request=None, send_alert=False, severity="info"):
    """
    Enregistre une action utilisateur dans le journal.

    Args:
        user: L'utilisateur qui effectue l'action (objet User)
        action: Description courte de l'action (str)
        details: Détails supplémentaires sur l'action (str)
        request: Objet HttpRequest pour obtenir IP et User-Agent (facultatif)
        send_alert: Si True, envoie un email d'alerte (pour les erreurs critiques)
        severity: Niveau de gravité (info, warning, error, critical)

    Returns:
        L'objet Log créé
    """
    log_entry = Log(
        user=user,
        action=action,
        details=details
    )

    # Si un objet request est fourni, récupérer IP et User-Agent
    if request:
        # Obtenir l'adresse IP réelle (prend en compte les proxys)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        log_entry.ip_address = ip
        log_entry.user_agent = request.META.get('HTTP_USER_AGENT', '')

    log_entry.save()

    # Envoyer un email d'alerte si demandé (pour erreurs critiques)
    if send_alert and EMAIL_ENABLED:
        send_alert_email(log_entry, severity)

    return log_entry


def log_login(user, request=None, success=True):
    """
    Enregistre une tentative de connexion.
    """
    action = "Connexion réussie" if success else "Échec de connexion"
    return log_action(user, action, request=request)


def log_logout(user, request=None):
    """
    Enregistre une déconnexion.
    """
    return log_action(user, "Déconnexion", request=request)


def log_user_creation(creator, new_user, request=None):
    """
    Enregistre la création d'un utilisateur.
    """
    details = f"Nouvel utilisateur créé: {new_user.email} (Rôle: {new_user.role})"
    return log_action(creator, "Création d'utilisateur", details, request)


def log_user_modification(modifier, modified_user, changes, request=None):
    """
    Enregistre la modification d'un utilisateur.

    Args:
        modifier: Utilisateur qui effectue la modification
        modified_user: Utilisateur modifié
        changes: Dictionnaire des champs modifiés {champ: nouvelle_valeur}
        request: Objet request (facultatif)
    """
    details = f"Utilisateur modifié: {modified_user.email}\nChangements:\n"
    for field, new_value in changes.items():
        details += f"- {field}: {new_value}\n"

    return log_action(modifier, "Modification d'utilisateur", details, request)


def log_permission_change(modifier, user, permission, granted, request=None):
    """
    Enregistre un changement de permission utilisateur.
    """
    action = "Attribution" if granted else "Révocation"
    details = f"{action} de la permission '{permission}' pour {user.email}"
    return log_action(modifier, f"{action} de permission", details, request)


def log_error(user, error_type, error_details, request=None):
    """
    Enregistre une erreur.
    """
    return log_action(user, f"Erreur: {error_type}", error_details, request)


def log_data_access(user, data_type, data_id, request=None):
    """
    Enregistre l'accès à des données sensibles.
    """
    details = f"Accès aux données de type {data_type}, ID: {data_id}"
    return log_action(user, "Accès aux données", details, request)


def send_alert_email(log_entry, severity="error"):
    """
    Envoie un email d'alerte pour une entrée de journal importante.
    """
    user_info = f"{log_entry.user}" if log_entry.user else "Utilisateur anonyme"

    subject = f"[{SITE_NAME}] ALERTE {severity.upper()}: {log_entry.action}"

    message = f"""
Une alerte a été générée dans le système {SITE_NAME}.

Détails de l'événement:
------------------------
Timestamp: {log_entry.timestamp}
Utilisateur: {user_info}
Action: {log_entry.action}
Sévérité: {severity.upper()}
IP: {log_entry.ip_address}

Détails supplémentaires:
------------------------
{log_entry.details}

---
Cet email a été généré automatiquement. Ne pas répondre.
"""

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [ALERT_ADMIN_EMAIL],
            fail_silently=False,
        )
        return True
    except Exception as e:
        # Ne pas lever d'exception pour éviter d'interrompre l'exécution
        # Log l'erreur d'envoi d'email dans la console
        print(f"Erreur lors de l'envoi de l'email d'alerte: {e}")
        return False


def log_critical_error(user, error_type, error_details, request=None):
    """
    Enregistre une erreur critique et envoie un email d'alerte.
    """
    return log_action(
        user=user,
        action=f"Erreur critique: {error_type}",
        details=error_details,
        request=request,
        send_alert=True,
        severity="critical"
    )


def log_security_breach(user, breach_type, breach_details, request=None):
    """
    Enregistre une violation de sécurité et envoie un email d'alerte.
    """
    return log_action(
        user=user,
        action=f"Violation de sécurité: {breach_type}",
        details=breach_details,
        request=request,
        send_alert=True,
        severity="critical"
    )

def get_client_ip(request):
    """
    Extraire l'adresse IP réelle du client, même derrière un proxy.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def create_meet_link(datetime_str, duration_minutes=60, meeting_title="Réunion programmée"):
    """
    Crée un lien Google Meet pour une date et heure spécifiques et retourne le lien
    Compatible avec un champ datetime de formulaire Django

    Args:
        datetime_str (str): Date et heure au format 'YYYY-MM-DD HH:MM' ou 'YYYY-MM-DDTHH:MM'
        duration_minutes (int): Durée de la réunion en minutes
        meeting_title (str): Titre de la réunion

    Returns:
        str: Lien Google Meet
    """
    # Définir les scopes d'autorisation Google
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    # Obtenir les identifiants OAuth 2.0
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES , redirect_uri='http://127.0.0.1:8080')
            creds = flow.run_local_server(port=8080)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Construire le service Google Calendar
    service = build('calendar', 'v3', credentials=creds)

    try:
        # Gérer différents formats possibles de datetime_str
        if 'T' in datetime_str:
            # Format 'YYYY-MM-DDT HH:MM'
            datetime_str = datetime_str.replace('T', ' ')

        # Convertir la chaîne en objet datetime
        start_time = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')

        # Calculer la fin en fonction de la durée
        end_time = start_time + timedelta(minutes=duration_minutes)

        # Convertir en format ISO 8601 pour l'API
        start_iso = start_time.isoformat() + 'Z'  # 'Z' indique UTC
        end_iso = end_time.isoformat() + 'Z'

    except ValueError as e:
        return f"Erreur: Format de date ou heure invalide: {e}"

    # Créer l'événement avec la conférence Google Meet
    event = {
        'summary': meeting_title,
        'start': {
            'dateTime': start_iso,
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_iso,
            'timeZone': 'UTC',
        },
        'conferenceData': {
            'createRequest': {
                'requestId': f'meet_{int(datetime.now().timestamp())}'
            }
        },
    }

    try:
        # Insérer l'événement et créer la conférence Meet
        event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1
        ).execute()

        # Extraire le lien Meet
        meet_link = event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', None)

        return meet_link

    except HttpError as error:
        return f"Erreur: {error}"





# Fonction pour générer le PDF du contrat
def generer_pdf_contrat(professeur_nom, signature_partie_1_path=None, signature_partie_2_data=None):
    """
    Génère un PDF de contrat et retourne les données en bytes
    """
    # Création du PDF en mémoire
    pdf_buffer = BytesIO()
    can = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter

    # Titre et en-tête
    can.setFont("Helvetica-Bold", 18)
    can.drawCentredString(width / 2, height - 50, "CONTRAT DE COLLABORATION")

    # Introduction
    y = height - 80
    can.setFont("Helvetica", 12)
    can.drawString(50, y, "Entre Math Tutor, représenté par Kenneth Ouedraogo,")
    y -= 20
    can.drawString(50, y, f"Et {professeur_nom}, Travailleur Autonome,")
    y -= 20
    can.drawString(50, y, "Il est convenu ce qui suit :")
    y -= 30

    # Clauses du contrat
    clauses = [
        {
            "titre": "1. Engagement minimum",
            "points": [
                "Le professeur s'engage à une collaboration de 1 an renouvelable."
            ]
        },
        {
            "titre": "2. Engagements de Math Tutor",
            "points": [
                "Proposer des opportunités d'enseignement dans le cadre de ses services de tutorat.",
                "Rémunérer le professeur 20 $/heure pour les cours individuels et 28 $/heure pour les cours en groupe.",
                "Payer les honoraires dans les 7 jours suivant la fin de chaque mois."
            ]
        },
        {
            "titre": "3. Engagements du professeur",
            "points": [
                "Effectuer les cours avec professionnalisme et respecter les attentes pédagogiques de Math Tutor.",
                "Préserver la confidentialité des informations liées à Math Tutor et à ses clients.",
                "Rédiger un rapport d'évolution de chaque élève toutes les deux semaines et le présenter aux parents avec Math Tutor.",
                "Prévenir les parents au moins 24 heures à l'avance en cas d'annulation ou modification d'un cours."
            ]
        },
        {
            "titre": "4. Responsabilité fiscale et administrative",
            "points": [
                "Le professeur est travailleur autonome et reconnaît être seul responsable du paiement de ses impôts et charges sociales.",
                "Le professeur s'engage à fournir le total du nombre d'heures effectuées dans le mois avant le paiement de ses honoraires."
            ]
        },
        {
            "titre": "5. Résiliation",
            "points": [
                "Math Tutor peut mettre fin au contrat sans préavis en cas de manquement grave (absence répétée, non-respect des engagements).",
                "Le professeur peut mettre fin à la collaboration avec un préavis de 15 jours."
            ]
        },
        {
            "titre": "6. Interdiction de traiter directement l'argent avec les parents",
            "points": [
                "Toute transaction financière doit obligatoirement passer par Math Tutor.",
                "Le professeur ne peut en aucun cas recevoir un paiement direct des parents.",
                "Il peut uniquement discuter avec eux de l'évolution pédagogique de l'élève, mais toute question financière doit être redirigée vers Math Tutor."
            ]
        },
        {
            "titre": "7. Droit applicable et litiges",
            "points": [
                "Ce contrat est régi par le droit québécois.",
                "Tout litige sera soumis aux tribunaux de Montréal, Québec."
            ]
        },
        {
            "titre": "8. Responsabilité du professeur",
            "points": [
                "Le professeur est entièrement responsable de ses actes dans le cadre de son activité et de son interaction avec les élèves et les parents.",
                "Math Tutor ne pourra en aucun cas être tenu responsable des comportements, paroles ou actions du professeur, y compris en cas de faute professionnelle, négligence ou tout autre acte répréhensible.",
                "En cas de comportement inapproprié, abusif, violent ou illégal, le professeur en assumera seul l'entière responsabilité civile et pénale.",
                "Math Tutor se réserve le droit de mettre fin immédiatement au contrat en cas de faute grave et de transmettre toute information nécessaire aux autorités compétentes si requis."
            ]
        }
    ]

    for clause in clauses:
        # Titre de la section
        can.setFont("Helvetica-Bold", 14)
        can.drawString(50, y, clause["titre"])
        y -= 20

        # Points de la clause
        for point in clause["points"]:
            can.setFont("Helvetica", 12)

            # Gestion du texte long avec saut de ligne
            words = point.split()
            line = "• "
            x_pos = 60
            for word in words:
                test_line = line + " " + word if line != "• " else line + word
                if can.stringWidth(test_line, "Helvetica", 12) < width - 100:
                    line = test_line
                else:
                    can.drawString(x_pos, y, line)
                    y -= 15
                    line = word
                    x_pos = 70  # Indentation pour les lignes suivantes

            if line:
                can.drawString(x_pos, y, line)

            y -= 20

            # Si la page est presque pleine, créer une nouvelle page
            if y < 100:
                can.showPage()
                y = height - 50
                can.setFont("Helvetica-Bold", 14)
                can.drawString(50, y, "CONTRAT DE COLLABORATION (suite)")
                y -= 30

    # Conclusion et date
    date_actuelle = now().strftime("%d/%m/%Y")
    can.drawString(50, y, f"Fait à Montréal, le {date_actuelle}")
    y -= 40

    # Signature partie 1 (Kenneth Ouedraogo)
    can.drawString(50, y, "Signature Math Tutor:")
    y -= 15

    try:
        if signature_partie_1_path and os.path.exists(signature_partie_1_path):
            signature_img = Image.open(signature_partie_1_path)
            width_img, height_img = signature_img.size
            aspect = width_img / height_img
            new_width = min(200, width_img)
            new_height = new_width / aspect

            can.drawImage(signature_partie_1_path, 50, y - new_height, width=new_width, height=new_height)
            y -= new_height + 30
        else:
            y -= 30
    except Exception as e:
        print(f"Erreur avec la signature 1: {e}")
        y -= 30

    # Signature partie 2 (Professeur)
    can.drawString(300, y, "Signature Professeur:")
    y -= 15

    if signature_partie_2_data:
        try:
            # Nettoyer la chaîne base64 si nécessaire
            if ',' in signature_partie_2_data:
                signature_partie_2_data = signature_partie_2_data.split(',')[1]

            # Créer un fichier temporaire pour la signature partie 2
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_signature_path = temp_file.name

            try:
                # Décodage de l'image base64
                signature_data = base64.b64decode(signature_partie_2_data)

                # Ouvrir l'image avec PIL
                img_signature = Image.open(BytesIO(signature_data))

                # Convertir en mode RGBA pour traiter la transparence
                if img_signature.mode != 'RGBA':
                    img_signature = img_signature.convert('RGBA')

                # Créer une nouvelle image avec fond blanc
                white_image = Image.new('RGB', img_signature.size, (255, 255, 255))
                pixels = white_image.load()

                # Parcourir chaque pixel
                for i in range(img_signature.width):
                    for j in range(img_signature.height):
                        r, g, b, a = img_signature.getpixel((i, j))
                        if a > 0:  # Si le pixel n'est pas transparent
                            pixels[i, j] = (r, g, b)

                # Sauvegarder l'image modifiée temporairement
                white_image.save(temp_signature_path, 'PNG')

                # Obtenir les dimensions de l'image
                width_img, height_img = white_image.size
                aspect = width_img / height_img
                new_width = min(200, width_img)
                new_height = new_width / aspect

                # Dessiner l'image sur le PDF
                can.drawImage(temp_signature_path, 300, y - new_height, width=new_width, height=new_height)

            finally:
                # Nettoyer le fichier temporaire
                if os.path.exists(temp_signature_path):
                    os.unlink(temp_signature_path)

        except Exception as e:
            print(f"Erreur avec la signature 2: {e}")

    # Finaliser le PDF
    can.save()

    # Retourner les données binaires du PDF
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


