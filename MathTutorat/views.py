from django.core.mail import send_mail, EmailMessage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render

from MathTutorat import settings

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from django.http import HttpResponse


def robots_txt(request):
    content = (
        "User-agent: *\n"
        "Disallow:\n"
        "Sitemap: https://www.mathtutorat.com/sitemap.xml\n"
    )
    return HttpResponse(content, content_type="text/plain")


class StaticSitemap(Sitemap):
    priority = 0.5  # Priorité par défaut des pages
    changefreq = "monthly"  # Fréquence de mise à jour des pages

    def items(self):
        # Liste des noms de routes définis dans urls.py
        return [
            'index',
            'tutoratPrive',
            'tutoratSemiPrive',
            'demanderTuteur',
            'devenirTuteur',
            'about',
            'blogue',
            'apiContact',
        ]

    def location(self, item):
        return reverse(item)  # Générer automatiquement les URLs


def index(request):
    return render(request, 'index.html')


def tutoratPrive(request):
    return render(request, 'tutoratPrive.html')


def tutoratSemiPrive(request):
    return render(request, 'tutoratSemiPrive.html')


def demanderTuteur(request):
    return render(request, 'demanderTuteur.html')


def devenirTuteur(request):
    return render(request, 'devenirTuteur.html')


def about(request):
    return render(request, 'about.html')


def blogue(request):
    return render(request, 'blogue.html')


@csrf_exempt
def apiContact(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Méthode non autorisée"}, status=405)

    # Récupérer les données du formulaire
    first_name = request.POST.get("input_1", "").strip()
    last_name = request.POST.get("input_2", "").strip()
    email = request.POST.get("input_3", "").strip()
    phone = request.POST.get("input_4", "").strip()
    message = request.POST.get("input_5", "").strip()

    # Vérifie si un fichier CV a été téléchargé
    cv_file = request.FILES.get('cv')

    # Vérifier si tous les champs sont remplis
    if not all([first_name, last_name, email, phone, message]):
        return JsonResponse({"success": False, "error": "Tous les champs sont requis"}, status=400)

    subject = "Nouveau message de contact"
    body = f"""
    📩 **Nouveau message* :

    - 👤 **Nom** : {first_name} {last_name}
    - ✉ **Email** : {email}
    - 📞 **Téléphone** : {phone}
    - 📝 **Message** : 
    {message}
    """

    recipient_list = ["hassanec714@icloud.com", "mathtutorsecondaire@gmail.com"]  # Remplace par les vraies adresses

    try:

        # Crée l'email
        email_message = EmailMessage(
            subject, body, settings.EMAIL_HOST_USER, recipient_list
        )

        # Si un fichier CV est présent, l'ajoute en pièce jointe
        if cv_file:
            email_message.attach(cv_file.name, cv_file.read(), cv_file.content_type)

        # Envoie l'email
        email_message.send()

        return JsonResponse({"success": True, "message": "Email envoyé avec succès"})
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Erreur lors de l'envoi : {str(e)}"}, status=500)


# views.py - Solution avec envoi d'email
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def demande_tuteur(request):
    """Affiche le formulaire de demande de tuteur"""
    return render(request, 'demande_tuteur.html')


def envoyer_demande(request):
    """Traite l'envoi du formulaire via email"""
    if request.method == 'POST':
        # Récupération des données du formulaire
        nom = request.POST.get('nom', '')
        prenom = request.POST.get('prenom', '')
        telephone = request.POST.get('telephone', '')
        courriel = request.POST.get('courriel', '')
        adresse = request.POST.get('adresse', '')
        nom_enfant = request.POST.get('nom_enfant', '')
        prenom_enfant = request.POST.get('prenom_enfant', '')
        heures_semaine = request.POST.get('heures_semaine', '')
        mode_cours = request.POST.get('mode_cours', '')
        adresse_cours = request.POST.get('adresse_cours', '')
        message_client = request.POST.get('message', '')

        # Déterminer le mode de cours en texte
        mode_cours_texte = "En ligne" if mode_cours == "en_ligne" else "En présentiel"

        # Création du contexte pour le template d'email
        context = {
            'nom': nom,
            'prenom': prenom,
            'telephone': telephone,
            'courriel': courriel,
            'adresse': adresse,
            'nom_enfant': nom_enfant,
            'prenom_enfant': prenom_enfant,
            'heures_semaine': heures_semaine,
            'mode_cours': mode_cours_texte,
            'adresse_cours': adresse_cours,
            'message': message_client,
        }

        try:
            # Sujet de l'email
            sujet = f"Nouvelle demande de tuteur - {prenom} {nom}"

            # Email au format HTML (plus joli)
            html_message = render_to_string('email_demande_tuteur.html', context)

            # Version texte brut de l'email (pour les clients qui ne supportent pas HTML)
            texte_brut = strip_tags(html_message)

            # Email de l'expéditeur (peut être configuré dans settings.py)
            from_email = settings.DEFAULT_FROM_EMAIL

            # Liste des destinataires
            recipient_list = ["hassanec714@icloud.com","mathtutorsecondaire@gmail.com"]  # Votre adresse email pour recevoir les demandes

            # Envoi de l'email
            send_mail(
                subject=sujet,
                message=texte_brut,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False
            )

            # Message de succès
            messages.success(request,"Votre demande a été envoyée avec succès! Un tuteur vous contactera très prochainement.")

        except Exception as e:
            # En cas d'erreur
            messages.error(request,
                           "Un problème est survenu lors de l'envoi de votre demande. Veuillez réessayer plus tard.")

            # Log de l'erreur (pour débogage)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors de l'envoi de l'email: {str(e)}")

        # Redirection vers la page du formulaire
        return redirect('demande_tuteur')

    # Si la méthode n'est pas POST, rediriger vers le formulaire
    return redirect('demande_tuteur')