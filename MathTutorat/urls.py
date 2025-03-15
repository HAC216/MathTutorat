"""
URL configuration for MathTutorat project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib.sitemaps.views import sitemap

from MathTutorat.views import *
from django.urls import path

from gestion_tutorat.views import *

sitemaps = {
    'static': StaticSitemap(),
}


urlpatterns = [

    # index
    path('', index, name='index'),

    # tutorat Prive
    path('tutoratPrive', tutoratPrive, name='tutoratPrive'),


    # tutorat Semi Prive
    path('tutoratSemiPrive', tutoratSemiPrive, name='tutoratSemiPrive'),

    # demanderTuteur
    path('demanderTuteur', demanderTuteur, name='demanderTuteur'),

    # devenirTuteur
    path('devenirTuteur', devenirTuteur, name='devenirTuteur'),

    # about
    path('about', about, name='about'),

    # blogue
    path('blogue', blogue, name='blogue'),

    # contact
    path('apiContact', apiContact, name='apiContact'),

    # connexion
    path('connexion', connexion, name='connexion'),

    # deconnexion
    path('deconnection', deconection, name='deconnection'),

    # inscription
    path('inscription', inscription, name='inscription'),

    # dashboard admin
    path('admin_dashboard', admin_dashboard, name='admin_dashboard'),

    # dashboard superviseur
    path('superviseur_dashboard', superviseur_dashboard, name='superviseur_dashboard'),

    # dashboard professeur
    path('professeur_dashboard', professeur_dashboard, name='professeur_dashboard'),

    # dashboard client
    path('client_dashboard', client_dashboard, name='client_dashboard'),

    # URL pour signer un contrat lié à une entrevue
    path('contrat/signer/<int:entrevue_id>/', signerContrat, name='signer_contrat'),

    # URLs pour traiter la signature et l'upload de documents
    path('traiter-signature/<str:contrat_id>/', traiterSignatureContrat, name='traiter_signature'),
    path('upload-documents/<str:contrat_id>/', uploadDocumentsProfesseur, name='upload_documents'),

    # URL pour télécharger un document
    path('document/<int:document_id>/', telechargerContrat, name='telecharger_document'),

    # Génération automatique du sitemap.xml
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),

    path('robots.txt', robots_txt, name='robots_txt'),

    path('demande-tuteur/', demande_tuteur, name='demande_tuteur'),
    path('envoyer-demande/', envoyer_demande, name='envoyer_demande'),

    path('suivi-tutorat/', suivi_tutorat, name='suivi_tutorat'),
    path('envoyer-suivi/', envoyer_suivi, name='envoyer_suivi'),

]
