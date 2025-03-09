# gestion_tutorat/decorators.py

from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from .permissions import user_has_permission


def permission_required(permission_code):
    """
    Décorateur qui vérifie si l'utilisateur a une permission spécifique.

    Exemple d'utilisation:
    @permission_required('manage_users')
    def ma_vue(request):
        # code de la vue
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Veuillez vous connecter pour accéder à cette page.")
                return redirect('connexion')

            if user_has_permission(request.user, permission_code):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Vous n'avez pas les permissions nécessaires.")
                # Rediriger vers une page d'accès refusé ou la page d'accueil
                return redirect('index')  # ou 'access_denied' si vous créez cette vue

        return _wrapped_view

    return decorator