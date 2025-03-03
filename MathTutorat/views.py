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
