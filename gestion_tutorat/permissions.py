# gestion_tutorat/permissions.py

from .models import Permission, RolePermission, UserPermission


def user_has_permission(user, permission_code):
    """
    Vérifie si un utilisateur a une permission spécifique.
    """
    # Si l'utilisateur n'est pas connecté, aucune permission
    if not user.is_authenticated:
        return False

    # Les administrateurs ont toutes les permissions
    if user.role == 'admin':
        return True

    try:
        # Vérifier les permissions spécifiques de l'utilisateur
        user_perm = UserPermission.objects.filter(
            user=user,
            permission__code=permission_code
        ).first()

        # Si une permission spécifique existe, utiliser sa valeur
        if user_perm is not None:
            return user_perm.granted

        # Sinon, vérifier les permissions du rôle
        permission = Permission.objects.get(code=permission_code)
        return RolePermission.objects.filter(
            role=user.role,
            permission=permission
        ).exists()

    except Exception:
        return False


# Fonctions pratiques pour les permissions courantes
def can_manage_users(user):
    return user_has_permission(user, 'manage_users')


