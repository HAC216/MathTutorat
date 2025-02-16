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
from MathTutorat.views import *
from django.urls import path

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

]
