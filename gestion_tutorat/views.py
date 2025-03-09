import random
import string

from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login
from django.urls import reverse
from django.utils import timezone
import traceback
from .decorators import permission_required
from .permissions import user_has_permission

from gestion_tutorat.models import User, Log, Entrevue, Professeur, DocumentProfesseur, Fichier
from gestion_tutorat.utils import *

from django.http import JsonResponse, HttpResponse, Http404, FileResponse
from django.views.decorators.csrf import csrf_exempt
def connexion(request):
    try:
        if request.method == 'GET':
            # Enregistrer la tentative d'accès à la page de connexion
            if request.user.is_authenticated:
                log_action(request.user, "Accès page connexion", "Utilisateur déjà connecté", request)
            return render(request, 'connexion.html')

        elif request.method == 'POST':
            email = request.POST.get('username')
            password = request.POST.get('password')

            # Validation basique des entrées
            if not email or not password:
                messages.error(request, "Veuillez remplir tous les champs.")
                log_action(None, "Tentative de connexion incomplète", f"Email fourni: {email or 'Non fourni'}", request)
                return render(request, 'connexion.html')

            user = authenticate(request, username=email, password=password)

            if user is not None:
                # Vérifier si le compte est actif
                if user.statut != 'actif':
                    messages.error(request, f"Ce compte est {user.statut}. Contactez un administrateur.")
                    log_action(user, "Tentative de connexion sur compte inactif", f"Statut du compte: {user.statut}",
                               request)
                    return render(request, 'connexion.html')

                login(request, user)

                # Mettre à jour les champs de connexion
                user.derniere_connexion = timezone.now()
                user.est_connecte = True
                user.save()

                # Enregistrer l'action de connexion
                log_login(user, request, success=True)

                if user.role == 'admin':
                    next_url = reverse('admin_dashboard')
                elif user.role == 'superviseur':
                    next_url = reverse('superviseur_dashboard')
                elif user.role == 'professeur':
                    next_url = reverse('professeur_dashboard')
                elif user.role == 'client':
                    next_url = reverse('client_dashboard')
                else:
                    next_url = request.POST.get('next', 'index')

                # Rediriger vers la page d'accueil ou une page spécifique

                return redirect(next_url)
            else:
                messages.error(request, "Email ou mot de passe incorrect.")
                # Enregistrer la tentative échouée
                log_entry = Log(
                    user=None,
                    action="Échec de connexion",
                    details=f"Tentative avec email: {email}",
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                log_entry.save()

                # Vérifier s'il y a eu plusieurs tentatives échouées récentes
                recent_failed_attempts = Log.objects.filter(
                    action="Échec de connexion",
                    details__contains=f"email: {email}",
                    timestamp__gte=timezone.now() - timezone.timedelta(minutes=10)
                ).count()

                if recent_failed_attempts >= 5:
                    # Alerte de sécurité pour tentatives multiples
                    log_security_breach(
                        None,
                        "Tentatives multiples de connexion",
                        f"5 tentatives échouées en moins de 10 minutes pour l'email: {email}",
                        request
                    )

        return render(request, 'connexion.html')

    except Exception as e:
        # Capturer et enregistrer toute erreur imprévue
        error_details = f"Exception dans la vue connexion: {str(e)}\n{traceback.format_exc()}"
        log_critical_error(
            request.user if request.user.is_authenticated else None,
            "Erreur critique connexion",
            error_details,
            request
        )
        messages.error(request, "Une erreur inattendue s'est produite. L'administrateur a été informé.")
        return render(request, 'connexion.html')


def deconection(request):
    try:
        if request.user.is_authenticated:
            # Enregistrer l'action de déconnexion
            log_logout(request.user, request)

            # Mettre à jour le statut de connexion
            request.user.est_connecte = False
            request.user.save()

            # Déconnecter l'utilisateur
            logout(request)
        else:
            # Tentative de déconnexion sans être connecté
            log_action(None, "Tentative de déconnexion", "Utilisateur non connecté", request)

        return redirect('connexion')

    except Exception as e:
        # Capturer et enregistrer toute erreur imprévue
        error_details = f"Exception dans la vue deconnection: {str(e)}\n{traceback.format_exc()}"
        log_critical_error(
            request.user if request.user.is_authenticated else None,
            "Erreur critique déconnexion",
            error_details,
            request
        )
        messages.error(request, "Une erreur inattendue s'est produite lors de la déconnexion.")
        return redirect('connexion')


def inscription(request):
    try:
        if request.method == 'GET':
            # Enregistrer l'accès à la page d'inscription
            log_action(
                request.user if request.user.is_authenticated else None,
                "Accès page inscription",
                "",
                request
            )
            return render(request, 'inscription.html')

        elif request.method == 'POST':
            # Récupérer les données du formulaire
            email = request.POST.get('email')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            nom = request.POST.get('nom')
            prenom = request.POST.get('prenom')
            sexe = request.POST.get('sexe')
            ethnie = request.POST.get('ethnie')
            adresse = request.POST.get('adresse')
            telephone = request.POST.get('telephone')
            role = request.POST.get('role')
            statut = request.POST.get('statut')

            # Vérifier l'autorisation de créer certains types d'utilisateurs
            if role in ['admin', 'superviseur'] and (not request.user.is_authenticated or request.user.role != 'admin'):
                log_security_breach(
                    request.user if request.user.is_authenticated else None,
                    "Tentative création compte privilégié",
                    f"Tentative de création d'un compte {role} sans droits administrateur",
                    request
                )
                messages.error(request, "Vous n'avez pas l'autorisation de créer ce type de compte.")
                return render(request, 'inscription.html')

            # Convertir la date de naissance si elle existe
            date_naissance = None
            if request.POST.get('date_naissance'):
                try:
                    date_naissance = request.POST.get('date_naissance')
                except ValueError:
                    messages.error(request, "Format de date de naissance incorrect.")
                    log_action(
                        request.user if request.user.is_authenticated else None,
                        "Erreur format date",
                        f"Format de date incorrect pour: {request.POST.get('date_naissance')}",
                        request
                    )
                    return render(request, 'inscription.html')

            # Validation des données
            errors = []

            # Vérifier si l'email existe déjà
            if User.objects.filter(email=email).exists():
                errors.append("Cet email est déjà utilisé.")

            # Vérifier que les mots de passe correspondent
            if password1 != password2:
                errors.append("Les mots de passe ne correspondent pas.")

            # Vérifier que le mot de passe est suffisamment fort
            if len(password1) < 8:
                errors.append("Le mot de passe doit contenir au moins 8 caractères.")

            if role not in ['admin', 'superviseur', 'professeur', 'client']:
                errors.append("Le rôle sélectionné est incorrect.")

            if statut not in ['actif', 'inactif', 'suspendu']:
                errors.append("Le statut sélectionné est incorrect.")

            # Si des erreurs existent, afficher les messages et recharger le formulaire
            if errors:
                for error in errors:
                    messages.error(request, error)

                # Logger les erreurs de validation
                log_action(
                    request.user if request.user.is_authenticated else None,
                    "Erreur validation inscription",
                    f"Email: {email}, Erreurs: {', '.join(errors)}",
                    request
                )
                return render(request, 'inscription.html')

            # Créer un nouvel utilisateur
            try:
                user = User(
                    email=email,
                    password=make_password(password1),  # Hachage du mot de passe
                    role=role,
                    nom=nom,
                    prenom=prenom,
                    sexe=sexe,
                    ethnie=ethnie,
                    adresse=adresse,
                    telephone=telephone,
                    date_naissance=date_naissance,
                    date_creation=timezone.now(),
                    statut=statut
                )
                user.save()

                # Logger la création de l'utilisateur
                if request.user.is_authenticated:
                    log_user_creation(request.user, user, request)
                else:
                    # Auto-inscription
                    log_action(user, "Auto-inscription", f"Compte créé: {email} (Rôle: {role})", request)

                messages.success(request, "Votre compte a été créé avec succès. Vous pouvez maintenant vous connecter.")
                return redirect('connexion')

            except Exception as e:
                error_details = f"Exception lors de la création du compte: {str(e)}\n{traceback.format_exc()}"
                log_critical_error(
                    request.user if request.user.is_authenticated else None,
                    "Erreur création compte",
                    error_details,
                    request
                )
                messages.error(request, f"Une erreur est survenue lors de la création du compte: {str(e)}")
                return render(request, 'inscription.html')

        # Méthode HTTP non autorisée
        log_action(
            request.user if request.user.is_authenticated else None,
            "Méthode non autorisée",
            f"Méthode {request.method} non autorisée pour l'inscription",
            request
        )
        return redirect('inscription')

    except Exception as e:
        # Capturer et enregistrer toute erreur imprévue
        error_details = f"Exception dans la vue inscription: {str(e)}\n{traceback.format_exc()}"
        log_critical_error(
            request.user if request.user.is_authenticated else None,
            "Erreur critique inscription",
            error_details,
            request
        )
        messages.error(request, "Une erreur inattendue s'est produite. L'administrateur a été informé.")
        return render(request, 'inscription.html')


@permission_required('view_admin_dashboard')
def admin_dashboard(request):
    try:

        if request.method == 'GET':

            # Statistiques
            stats = {
                'total_users': User.objects.count(),
                'total_professeurs': User.objects.filter(role='professeur', statut='actif').count(),
                'total_clients': User.objects.filter(role='client', statut='actif').count(),
                'connected_users': User.objects.filter(statut='actif', est_connecte=True).count(),
            }

            # Utilisateurs
            users = User.objects.all().order_by('-date_creation')

            # Logs d'administration (récents)
            admin_logs = Log.objects.all().order_by('-timestamp')[:7]

            # Tous les logs (pour le modal des logs)
            logs = Log.objects.all().order_by('-timestamp')

            # Liste des administrateurs (pour le filtre des logs)
            admin_users = User.objects.filter(role__in=['admin', 'superviseur'])

            context = {
                'stats': stats,
                'users': users,
                'admin_logs': admin_logs,
                'logs': logs,
                'admin_users': admin_users,
            }

            return render(request, 'admin_dashboard.html', context)

        elif request.method == 'POST' and request.POST.get('formulaire_name') == 'ajout_user':

            # Récupérer les données du formulaire
            email = request.POST.get('email')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            nom = request.POST.get('nom')
            prenom = request.POST.get('prenom')
            sexe = request.POST.get('sexe')
            ethnie = request.POST.get('ethnie')
            adresse = request.POST.get('adresse')
            telephone = request.POST.get('telephone')
            role = request.POST.get('role')
            statut = request.POST.get('statut')

            # Vérifier l'autorisation de créer certains types d'utilisateurs
            if role in ['admin', 'superviseur'] and (not request.user.is_authenticated or request.user.role != 'admin'):
                log_security_breach(
                    request.user if request.user.is_authenticated else None,
                    "Tentative création compte privilégié",
                    f"Tentative de création d'un compte {role} sans droits administrateur",
                    request
                )
                messages.error(request, "Vous n'avez pas l'autorisation de créer ce type de compte.")
                return redirect('connexion')

            # Convertir la date de naissance si elle existe
            date_naissance = None
            if request.POST.get('date_naissance'):
                try:
                    date_naissance = request.POST.get('date_naissance')
                except ValueError:
                    messages.error(request, "Format de date de naissance incorrect.")
                    log_action(
                        request.user if request.user.is_authenticated else None,
                        "Erreur format date",
                        f"Format de date incorrect pour: {request.POST.get('date_naissance')}",
                        request
                    )
                    return redirect('admin_dashboard')

            # Validation des données
            errors = []

            # Vérifier si l'email existe déjà
            if User.objects.filter(email=email).exists():
                errors.append("Cet email est déjà utilisé.")

            # Vérifier que les mots de passe correspondent
            if password1 != password2:
                errors.append("Les mots de passe ne correspondent pas.")

            if role not in ['admin', 'superviseur', 'professeur', 'client']:
                errors.append("Le rôle sélectionné est incorrect.")

            if statut not in ['actif', 'inactif', 'suspendu']:
                errors.append("Le statut sélectionné est incorrect.")

            # Si des erreurs existent, afficher les messages et recharger le formulaire
            if errors:
                for error in errors:
                    messages.error(request, error)

                # Logger les erreurs de validation
                log_action(
                    request.user if request.user.is_authenticated else None,
                    "Erreur validation inscription",
                    f"Email: {email}, Erreurs: {', '.join(errors)}",
                    request
                )
                return redirect('admin_dashboard')

            # Créer un nouvel utilisateur
            try:
                user = User(
                    email=email,
                    password=make_password(password1),  # Hachage du mot de passe
                    role=role,
                    nom=nom,
                    prenom=prenom,
                    sexe=sexe,
                    ethnie=ethnie,
                    adresse=adresse,
                    telephone=telephone,
                    date_naissance=date_naissance,
                    date_creation=timezone.now(),
                    statut=statut
                )
                user.save()

                # Logger la création de l'utilisateur
                if request.user.is_authenticated:
                    log_user_creation(request.user, user, request)
                else:
                    # Auto-inscription
                    log_action(user, "inscription", f"Compte créé: {email} (Rôle: {role})", request)

                messages.success(request, "Votre compte a été créé avec succès. Vous pouvez maintenant vous connecter.")
                return redirect('admin_dashboard')

            except Exception as e:
                error_details = f"Exception lors de la création du compte: {str(e)}\n{traceback.format_exc()}"
                log_critical_error(
                    request.user if request.user.is_authenticated else None,
                    "Erreur création compte",
                    error_details,
                    request
                )
                messages.error(request, f"Une erreur est survenue lors de la création du compte: {str(e)}")

            return redirect('admin_dashboard')

        elif request.method == 'POST' and request.POST.get('formulaire_name') == 'edit_user':

            # Récupérer l'ID de l'utilisateur à éditer
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)

            # Récupérer les données du formulaire (tous les champs commencent par "edit_")
            nom = request.POST.get('nom')
            prenom = request.POST.get('prenom')
            email = request.POST.get('email')
            role = request.POST.get('role')
            sexe = request.POST.get('sexe')
            date_naissance = request.POST.get('date_naissance') or None
            telephone = request.POST.get('telephone')
            adresse = request.POST.get('adresse')
            ethnie = request.POST.get('ethnie') or None
            statut = request.POST.get('statut')
            password = request.POST.get('password')

            # Vérifier l'autorisation de créer certains types d'utilisateurs
            if role in ['admin', 'superviseur'] and (not request.user.is_authenticated or request.user.role != 'admin'):
                log_security_breach(
                    request.user if request.user.is_authenticated else None,
                    "Tentative de modification  compte privilégié",
                    f"Tentative de création d'un compte {role} sans droits administrateur",
                    request
                )
                messages.error(request, "Vous n'avez pas l'autorisation de créer ce type de compte.")
                return render(request, 'connexion.html')

            # Convertir la date de naissance si elle existe
            date_naissance = None
            if request.POST.get('date_naissance'):
                try:
                    date_naissance = request.POST.get('date_naissance')
                except ValueError:
                    messages.error(request, "Format de date de naissance incorrect.")
                    log_action(
                        request.user if request.user.is_authenticated else None,
                        "Erreur format date",
                        f"Format de date incorrect pour: {request.POST.get('date_naissance')}",
                        request
                    )
                    return render(request, 'inscription.html')

            # Validation des données
            errors = []

            # Vérifier si l'email existe déjà
            if User.objects.filter(email=email).exclude(id=user_id).exists():
                errors.append("Cet email est déjà utilisé.")

            if role not in ['admin', 'superviseur', 'professeur', 'client']:
                errors.append("Le rôle sélectionné est incorrect.")

            if statut not in ['actif', 'inactif', 'suspendu']:
                errors.append("Le statut sélectionné est incorrect.")

            # Si des erreurs existent, afficher les messages et recharger le formulaire
            if errors:
                for error in errors:
                    messages.error(request, error)

                # Logger les erreurs de validation
                log_action(
                    request.user if request.user.is_authenticated else None,
                    "Erreur validation edition",
                    f"Email: {email}, Erreurs: {', '.join(errors)}",
                    request
                )
                return render(request, 'connexion.html')

            # Créer un nouvel utilisateur
            try:
                # Mettre à jour les informations de l'utilisateur
                user.nom = nom
                user.prenom = prenom
                user.email = email
                user.role = role
                user.sexe = sexe
                user.date_naissance = date_naissance
                user.telephone = telephone
                user.adresse = adresse
                user.ethnie = ethnie
                user.statut = statut

                # Mettre à jour le mot de passe seulement s'il est fourni et non vide
                if password and password.strip():
                    user.set_password(make_password(password))

                # Sauvegarder les modifications
                user.save()

                # Auto-inscription
                log_action(user, "modification", f"Compte modifier: {email} (Rôle: {role})", request)

                return redirect('admin_dashboard')

            except Exception as e:
                error_details = f"Exception lors de la modification du compte: {str(e)}\n{traceback.format_exc()}"
                log_critical_error(
                    request.user if request.user.is_authenticated else None,
                    "Erreur modification compte",
                    error_details,
                    request
                )
                messages.error(request, f"Une erreur est survenue lors de la modification du compte: {str(e)}")
                return redirect('admin_dashboard')

        elif request.method == 'POST' and request.POST.get('formulaire_name') == 'delete_user':
            # Récupérer l'ID de l'utilisateur à supprimer
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)

            # Stocker les informations avant suppression pour le log
            user_email = user.email
            user_role = user.role

            try:

                # On préserve l'utilisateur mais on le désactive
                user.statut = 'inactif'
                user.est_connecte = False
                user.email = f"deleted_{user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}_{user.email}"
                user.save()

                # Créer un log pour cette action
                Log.objects.create(
                    user=request.user,
                    action="Désactivation d'utilisateur",
                    details=f"Désactivation de l'utilisateur {user_email} (ID: {user_id}, Rôle: {user_role})",
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

                return redirect('admin_dashboard')

            except Exception as e:
                # Gérer les erreurs (contraintes d'intégrité, etc.)
                error_details = f"Exception lors de la suppresion du compte: {str(e)}\n{traceback.format_exc()}"
                log_critical_error(
                    request.user if request.user.is_authenticated else None,
                    "Erreur suppresion compte",
                    error_details,
                    request
                )
                messages.error(request, f"Une erreur est survenue lors de la suppresion du compte: {str(e)}")
                return redirect('admin_dashboard')

        # Si la méthode n'est pas POST, rediriger vers le dashboard
        return redirect('admin_dashboard')


    except Exception as e:
        # Capturer et enregistrer toute erreur imprévue
        error_details = f"Exception dans la vue admin_dashboard: {str(e)}\n{traceback.format_exc()}"
        log_critical_error(
            request.user if request.user.is_authenticated else None,
            "Erreur critique connexion",
            error_details,
            request
        )
        messages.error(request, "Une erreur inattendue s'est produite. L'administrateur a été informé.")
        return render(request, 'connexion.html')


@permission_required('view_superviseur_dashbord')
def superviseur_dashboard(request):
    try:
        if request.method == 'GET':
            # Statistiques
            stats = {
                'total_professeurs': User.objects.filter(role='professeur', statut='actif').count(),
                'total_clients': User.objects.filter(role='client', statut='actif').count(),
            }

            # Récupérer les entrevues selon le rôle de l'utilisateur
            user = request.user
            if user.role == 'admin':
                # Admin voit toutes les entrevues
                entrevues = Entrevue.objects.all().order_by('-date_creation')
            else:
                # Superviseur voit les entrevues qu'il a créées ou où il est interviewer
                entrevues = Entrevue.objects.filter(
                    Q(createur=user) | Q(interviewer=user)
                ).order_by('-date_creation')

            # Ajouter le nombre d'entrevues aux statistiques
            stats['total_entrevues'] = entrevues.count()

            # Utilisateurs
            users = User.objects.all().order_by('-date_creation')



            context = {
                'stats': stats,
                'users': users,
                'entrevues': entrevues
            }
            return render(request, 'superviseur_dashboard.html', context)

        elif request.method == 'POST' and request.POST.get('formulaire_name') == "ajout_entrevu":
            createur = request.user
            interviewer = User.objects.get(id=request.POST.get('interviewer_id'))
            date_entrevue = request.POST.get('date_entrevue')
            notes = request.POST.get('notes', '')


            lien_entrevue = request.POST.get('lien_entrevue')

            # Créer ou récupérer le professeur
            # Vérifier d'abord si un utilisateur avec cet email existe déjà
            email = request.POST.get('prof_email')
            try:
                user_prof = User.objects.get(email=email)
                professeur = Professeur.objects.get(user=user_prof)

            except (User.DoesNotExist, Professeur.DoesNotExist):
                # Créer un nouveau compte utilisateur pour le professeur
                password = make_password("passer123")
                user_prof = User.objects.create_user(
                    email=email,
                    password=password,
                    nom=request.POST.get('prof_nom'),
                    prenom=request.POST.get('prof_prenom'),
                    role='professeur',
                    sexe=request.POST.get('prof_sexe'),
                    telephone=request.POST.get('prof_telephone'),
                    adresse=request.POST.get('prof_adresse'),
                    date_naissance=request.POST.get('prof_date_naissance') or None,
                )

                # Créer le profil professeur
                professeur = Professeur.objects.create(
                    user=user_prof,
                    niveau=None,
                    specialites=request.POST.get('prof_specialites', ''),
                    statut_verification='en_attente'
                )

            # Créer l'entrevue
            entrevue = Entrevue.objects.create(
                createur=createur,
                interviewer=interviewer,
                professeur=professeur,
                date_entrevue=date_entrevue,
                lien_entrevue=lien_entrevue,
                statut='en_attente',
                notes=notes
            )

            # Envoyer un email au professeur avec les détails de l'entrevue
            subject = "Invitation à une entrevue - Gestion Tutorat"
            message = f"""
            Bonjour {professeur.user.prenom} {professeur.user.nom},

            Nous avons le plaisir de vous confirmer la planification d'une entrevue:

            Date et heure: {date_entrevue}
            Lien de réunion: {lien_entrevue}

            Nous vous remercions de votre participation et nous vous souhaitons une excellente entrevue.

            Cordialement,
            L'équipe Gestion Tutorat
            """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,  # Adresse expéditeur
                [professeur.user.email],  # Adresse destinataire
                fail_silently=False,
            )

            # Enregistrer l'action dans les logs
            Log.objects.create(
                user=request.user,
                action=f"Création d'une entrevue avec {professeur.user.prenom} {professeur.user.nom}",
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )


            messages.success(request, "L'entrevue a été créée avec succès.")
            return redirect('superviseur_dashboard')

        elif request.method == 'POST' and request.POST.get('formulaire_name') == "modifier_entrevu":

            entrevue_id = request.POST.get('entrevue_id')
            try:
                entrevue = Entrevue.objects.get(id=entrevue_id)

                # Vérifier les permissions
                if request.user.role == 'admin' or request.user == entrevue.createur or request.user == entrevue.interviewer:
                    # Mettre à jour l'entrevue
                    if request.POST.get('interviewer_id'):
                        entrevue.interviewer = User.objects.get(id=request.POST.get('interviewer_id'))

                    if request.POST.get('date_entrevue'):
                        entrevue.date_entrevue = request.POST.get('date_entrevue')

                    # Pour les notes, on utilise directement get avec valeur par défaut
                    entrevue.notes = request.POST.get('notes', entrevue.notes)

                    # Vérifier si le niveau a été modifié
                    nouveau_niveau = request.POST.get('prof_niveau')
                    if nouveau_niveau and entrevue.professeur.niveau != int(nouveau_niveau):
                        entrevue.professeur.niveau = nouveau_niveau
                        entrevue.professeur.save()
                        # Si le niveau a changé, passer en vérification documents
                        entrevue.statut = 'verification_document'

                        # Construire l'URL pour le téléchargement des documents
                        upload_url = f"https://www.mathtutorat.com/contrat/signer/{entrevue_id}/"

                        # Envoyer un email au professeur
                        subject = "Documents requis - Mise à jour de votre niveau"
                        message = f"""
                        Bonjour {entrevue.professeur.user.prenom} {entrevue.professeur.user.nom},

                        Nous avons le plaisir de vous informer que votre entrevue a ete aceptee

                        Pour finaliser cette mise à jour, nous avons besoin que vous soumettiez les documents suivants:

                        1. Contrat signé
                        2. Numéro d'Assurance Sociale (NAS)
                        3. Permis d'étude/travail (si applicable)
                        4. Pièce d'identité

                        Veuillez utiliser le lien ci-dessous pour télécharger ces documents:
                        {upload_url}

                        Cordialement,
                        L'équipe Gestion Tutorat
                        """

                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL, # Adresse expéditeur
                            [entrevue.professeur.user.email],  # Adresse destinataire
                            fail_silently=False,
                        )



                    else:
                        # Sinon utiliser le statut du formulaire s'il existe
                        if request.POST.get('statut'):
                            entrevue.statut = request.POST.get('statut')

                        # Mettre à jour le lien d'entrevue s'il existe
                        if request.POST.get('lien_entrevue'):
                            entrevue.lien_entrevue = request.POST.get('lien_entrevue')

                    entrevue.save()

                    # Enregistrer l'action dans les logs
                    Log.objects.create(
                        user=request.user,
                        action=f"Modification de l'entrevue #{entrevue_id} avec {entrevue.professeur.user.prenom} {entrevue.professeur.user.nom}",
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )

                    messages.success(request, "L'entrevue a été modifiée avec succès.")
                else:
                    messages.error(request, "Vous n'avez pas les droits pour modifier cette entrevue.")

                return redirect('superviseur_dashboard')

            except Entrevue.DoesNotExist:
                messages.error(request, "Cette entrevue n'existe pas.")
            except Exception as e:
                messages.error(request, f"Une erreur est survenue: {str(e)}")

            return redirect('superviseur_dashboard')


        elif request.method == 'POST' and request.POST.get('formulaire_name') == "supprimer_entrevu":

            entrevue_id = request.POST.get('entrevue_id')
            try:
                entrevue = Entrevue.objects.get(id=entrevue_id)

                # Vérifier les permissions
                if request.user.role == 'admin' or request.user == entrevue.createur:
                    # Enregistrer les informations avant suppression
                    professeur_nom = f"{entrevue.professeur.user.prenom} {entrevue.professeur.user.nom}"
                    date_entrevue = entrevue.date_entrevue.strftime('%d/%m/%Y %H:%M')

                    # Créer un log avant suppression
                    Log.objects.create(
                        user=request.user,
                        action=f"Suppression de l'entrevue #{entrevue_id} avec {professeur_nom} prévue le {date_entrevue}",
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )

                    # Supprimer les documents associés
                    documents = DocumentProfesseur.objects.filter(entrevue=entrevue)
                    for doc in documents:
                        # Supprimer le fichier associé
                        if doc.fichier:
                            doc.fichier.delete()
                        doc.delete()

                    # Supprimer l'entrevue
                    entrevue.delete()

                    messages.success(request, f"L'entrevue avec {professeur_nom} a été supprimée avec succès.")
                else:
                    messages.error(request, "Vous n'avez pas les droits pour supprimer cette entrevue.")

            except Entrevue.DoesNotExist:
                messages.error(request, "Cette entrevue n'existe pas ou a déjà été supprimée.")
            except Exception as e:
                messages.error(request, f"Une erreur est survenue: {str(e)}")


        elif request.method == 'POST' and request.POST.get('formulaire_name') == "upload_document":

            entrevue_id = request.POST.get('entrevue_id')
            type_document = request.POST.get('type_document')

            # Vérifier si l'entrevue existe
            entrevue = get_object_or_404(Entrevue, id=entrevue_id)

            # Récupérer le document correspondant
            document = get_object_or_404(
                DocumentProfesseur,
                entrevue=entrevue,
                professeur=entrevue.professeur,
                type_document=type_document
            )

            fichier = document.fichier  # Récupérer le fichier associé

            try:
                # Créer une réponse de fichier
                response = FileResponse(
                    BytesIO(fichier.contenu),
                    content_type=fichier.type_mime
                )

                # Définir l'en-tête pour l'affichage dans le navigateur
                response['Content-Disposition'] = f'inline; filename="{fichier.nom_fichier}"'

                return response

            except Exception as e:
                # Gérer les erreurs potentielles
                raise Http404("Fichier non trouvé")



        elif request.method == 'POST' and request.POST.get('formulaire_name') == "valider_documents":

            entrevue_id = request.POST.get('id')

            try:

                entrevue = Entrevue.objects.get(id=entrevue_id)

                professeur = entrevue.professeur

                user = professeur.user

                # Marquer tous les documents comme vérifiés

                documents = DocumentProfesseur.objects.filter(entrevue=entrevue)

                for doc in documents:
                    doc.statut = 'verifie'

                    doc.date_verification = timezone.now()

                    doc.verifie_par = request.user

                    doc.save()

                # Changer le statut du professeur à actif

                user.statut = 'actif'

                # Générer un mot de passe aléatoire si nécessaire

                password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

                user.set_password(password)

                user.save()

                # Changer le statut de l'entrevue à acceptée

                entrevue.statut = 'acceptee'

                entrevue.save()

                # Créer un log

                Log.objects.create(

                    user=request.user,

                    action=f"Validation de tous les documents pour l'entrevue #{entrevue_id} avec {user.prenom} {user.nom}",

                    ip_address=get_client_ip(request),

                    user_agent=request.META.get('HTTP_USER_AGENT', '')

                )

                # Envoyer un email au professeur avec ses informations de connexion

                subject = "Vos informations de connexion - Gestion Tutorat"

                message = f"""

                Bonjour {user.prenom} {user.nom},


                Félicitations ! Vos documents ont été validés et votre compte a été activé.


                Voici vos informations de connexion:

                Email: {user.email}

                Mot de passe: {password}


                Vous pouvez vous connecter sur notre plateforme à l'adresse suivante: [https://www.mathtutorat.com/connexion]


                Nous vous recommandons de changer votre mot de passe lors de votre première connexion.


                Cordialement,

                L'équipe Gestion Tutorat

                """

                send_mail(

                    subject,

                    message,

                    settings.DEFAULT_FROM_EMAIL,

                    [user.email],

                    fail_silently=False,

                )

                messages.success(request,
                                 f"Tous les documents de {user.prenom} {user.nom} ont été validés. Un email a été envoyé avec ses informations de connexion.")


            except Entrevue.DoesNotExist:

                messages.error(request, "Cette entrevue n'existe pas.")

            except Exception as e:

                error_details = f"Exception dans la vue superviseur_dashboard: {str(e)}\n{traceback.format_exc()}"
                log_critical_error(
                    request.user if request.user.is_authenticated else None,
                    "Erreur critique ",
                    error_details,
                    request
                )


            # Redirect après toute action POST
        return redirect('superviseur_dashboard')





    except Exception as e:
        # Capturer et enregistrer toute erreur imprévue
        error_details = f"Exception dans la vue superviseur_dashboard: {str(e)}\n{traceback.format_exc()}"
        log_critical_error(
            request.user if request.user.is_authenticated else None,
            "Erreur critique ",
            error_details,
            request
        )
        messages.error(request, "Une erreur inattendue s'est produite. L'administrateur a été informé.")
        return redirect('superviseur_dashboard')


@permission_required('view_professeur_dashbord')
def professeur_dashboard(request):
    try:
        if request.method == 'GET':

            return render(request, 'professeur_dashboard.html')


    except Exception as e:
        # Capturer et enregistrer toute erreur imprévue
        error_details = f"Exception dans la vue professeur_dashboard: {str(e)}\n{traceback.format_exc()}"
        log_critical_error(
            request.user if request.user.is_authenticated else None,
            "Erreur critique connexion",
            error_details,
            request
        )
        messages.error(request, "Une erreur inattendue s'est produite. L'administrateur a été informé.")
        return render(request, 'connexion.html')


@permission_required('view_client_dashbord')
def client_dashboard(request):
    try:

        if request.method == 'GET':
            return render(request, 'client_dashboard.html')


    except Exception as e:
        # Capturer et enregistrer toute erreur imprévue
        error_details = f"Exception dans la vue client_dashboard: {str(e)}\n{traceback.format_exc()}"
        log_critical_error(
            request.user if request.user.is_authenticated else None,
            "Erreur critique connexion",
            error_details,
            request
        )
        messages.error(request, "Une erreur inattendue s'est produite. L'administrateur a été informé.")
        return render(request, 'connexion.html')


def signerContrat(request, entrevue_id):
    if request.method == 'GET':
        try:
            # Récupérer l'entrevue avec l'ID fourni
            entrevue = get_object_or_404(Entrevue, id=entrevue_id)

            # Vérifier si un document de type 'contrat' est associé à cette entrevue
            contrat_existe = DocumentProfesseur.objects.filter(
                entrevue=entrevue,
                type_document='contrat'
            ).exists()

            if contrat_existe:
                messages.warning(request, "Un contrat existe déjà pour cette entrevue.")
                return render(request, '404.html', status=404)

            # Préparer les données pour la page de signature
            professeur = entrevue.professeur
            nom_complet = f"{professeur.user.prenom} {professeur.user.nom}"

            # Générer un identifiant unique pour ce contrat
            contrat_id = str(uuid.uuid4())

            # Chemin vers la signature Kenneth Ouedraogo
            signature_path = os.path.join(settings.MEDIA_ROOT, 'gestion_tutorat/signature', 'ken_signature.png')


            # Générer le PDF et l'encoder en base64
            pdf_data = generer_pdf_contrat(nom_complet, signature_path)
            pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')

            # Stocker les informations du contrat en session
            request.session['contrat_info'] = {
                'id': contrat_id,
                'entrevue_id': entrevue_id,
                'professeur_id': professeur.id,
                'professeur_nom': nom_complet,
                'date_creation': now().strftime("%d/%m/%Y")
            }

            # Passer le PDF encodé en base64 au template
            return render(request, 'page_signature.html', {
                'contrat_id': contrat_id,
                'professeur_nom': nom_complet,
                'date_creation': now().strftime("%d/%m/%Y"),
                'entrevue': entrevue,
                'contract_pdf_base64': pdf_base64  # Important : PDF encodé en base64
            })

        except Exception as e:
            # Capturer les erreurs
            error_details = f"Exception dans la vue signerContrat: {str(e)}\n{traceback.format_exc()}"
            log_critical_error(
                request.user if request.user.is_authenticated else None,
                "Erreur critique signature contrat",
                error_details,
                request
            )
            messages.error(request, "Une erreur inattendue s'est produite. L'administrateur a été informé.")
            return render(request, '404.html', status=404)

    return redirect('index')


@csrf_exempt
def traiterSignatureContrat(request, contrat_id):
    """
    Traiter la signature du contrat (AJAX)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

    try:
        # Récupérer les informations du contrat depuis la session
        contrat_info = request.session.get('contrat_info')

        if not contrat_info or contrat_info.get('id') != contrat_id:
            return JsonResponse({'success': False, 'error': 'Contrat non trouvé'})

        import json
        data = json.loads(request.body)
        signature = data.get('signature')

        if not signature:
            return JsonResponse({'success': False, 'error': 'Signature manquante'})

        # Récupérer l'entrevue et le professeur
        entrevue_id = contrat_info.get('entrevue_id')
        entrevue = get_object_or_404(Entrevue, id=entrevue_id)
        professeur = entrevue.professeur

        # Chemin vers la signature Kenneth Ouedraogo
        signature_path = os.path.join(settings.MEDIA_ROOT, 'gestion_tutorat/signature', 'ken_signature.png')

        # Générer le PDF avec les deux signatures
        pdf_data = generer_pdf_contrat(contrat_info.get('professeur_nom'), signature_path, signature)

        # Créer un objet Fichier pour stocker le contrat signé
        fichier = Fichier.objects.create(
            nom_fichier=f"contrat_{contrat_id}.pdf",
            type_mime="application/pdf",
            taille=len(pdf_data),
            contenu=pdf_data
        )

        # Créer un DocumentProfesseur pour associer le contrat au professeur et à l'entrevue
        DocumentProfesseur.objects.create(
            professeur=professeur,
            entrevue=entrevue,
            type_document='contrat',
            fichier=fichier,
            statut_verification='verifie'  # Le contrat est considéré comme vérifié dès sa création
        )

        # Mettre à jour le statut de l'entrevue si nécessaire
        if entrevue.statut == 'verification_document':
            # Vérifier si tous les documents requis sont présents
            documents_requis = ['contrat', 'permis_etude', 'permis_travail', 'nas', 'piece_identite']
            documents_presents = DocumentProfesseur.objects.filter(
                professeur=professeur,
                entrevue=entrevue,
                type_document__in=documents_requis
            ).values_list('type_document', flat=True)

            # Si le professeur a tous les documents requis, passer à 'acceptee'
            if set(documents_requis).issubset(set(documents_presents)):
                entrevue.statut = 'acceptee'
                entrevue.save()

        # Encoder le PDF en base64 pour l'affichage
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')

        return JsonResponse({
            'success': True,
            'pdf_base64': pdf_base64,
            'message': 'Contrat signé avec succès'
        })

    except Exception as e:
        error_details = f"Exception dans la vue traiterSignatureContrat: {str(e)}\n{traceback.format_exc()}"
        log_critical_error(
            request.user if request.user.is_authenticated else None,
            "Erreur critique traitement signature",
            error_details,
            request
        )
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def uploadDocumentsProfesseur(request, contrat_id):
    """
    Traiter l'upload des documents du professeur
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

    try:
        # Récupérer les informations du contrat depuis la session
        contrat_info = request.session.get('contrat_info')

        if not contrat_info or contrat_info.get('id') != contrat_id:
            return JsonResponse({'success': False, 'error': 'Contrat non trouvé'})

        # Récupérer l'entrevue et le professeur
        entrevue_id = contrat_info.get('entrevue_id')
        entrevue = get_object_or_404(Entrevue, id=entrevue_id)
        professeur = entrevue.professeur

        # Mapper les noms de fichiers aux types de documents
        document_types = {
            'nas': 'nas',
            'permis': 'permis_travail',
            'identite': 'piece_identite',
            'autre': 'permis_etude'
        }

        uploaded_docs = []

        for form_field, doc_type in document_types.items():
            if form_field in request.FILES:
                uploaded_file = request.FILES[form_field]

                # Lire le contenu du fichier
                file_content = uploaded_file.read()

                # Créer un objet Fichier
                fichier = Fichier.objects.create(
                    nom_fichier=uploaded_file.name,
                    type_mime=uploaded_file.content_type or 'application/octet-stream',
                    taille=len(file_content),
                    contenu=file_content
                )

                # Créer un DocumentProfesseur
                DocumentProfesseur.objects.create(
                    professeur=professeur,
                    entrevue=entrevue,
                    type_document=doc_type,
                    fichier=fichier,
                    statut_verification='en_attente'
                )

                uploaded_docs.append(form_field)

        return JsonResponse({
            'success': True,
            'uploaded': uploaded_docs,
            'message': 'Documents téléchargés avec succès'
        })

    except Exception as e:
        error_details = f"Exception dans la vue uploadDocumentsProfesseur: {str(e)}\n{traceback.format_exc()}"
        log_critical_error(
            request.user if request.user.is_authenticated else None,
            "Erreur critique upload documents",
            error_details,
            request
        )
        return JsonResponse({'success': False, 'error': str(e)})


def telechargerContrat(request, document_id):
    """
    Télécharger un contrat ou document stocké dans la base de données
    """
    try:
        document = get_object_or_404(DocumentProfesseur, id=document_id)
        fichier = document.fichier

        response = HttpResponse(fichier.contenu, content_type=fichier.type_mime)
        response['Content-Disposition'] = f'inline; filename="{fichier.nom_fichier}"'
        return response

    except Exception as e:
        error_details = f"Exception dans la vue telechargerContrat: {str(e)}\n{traceback.format_exc()}"
        log_critical_error(
            request.user if request.user.is_authenticated else None,
            "Erreur critique téléchargement",
            error_details,
            request
        )
        messages.error(request, "Une erreur est survenue lors du téléchargement du document.")
        return redirect('index')


