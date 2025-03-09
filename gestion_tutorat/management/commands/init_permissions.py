# gestion_tutorat/management/commands/init_permissions.py

from django.core.management.base import BaseCommand

from gestion_tutorat.models import Permission, RolePermission


class Command(BaseCommand):
    help = 'Initialise les permissions de base du système'

    def handle(self, *args, **options):
        # Liste des permissions à créer
        permissions = [
            # Format: (code, description)
            ('manage_users', 'Peut gérer les utilisateurs'),
            ('view_admin_dashboard', 'Peut voir le tableau de bord admin'),
            ('view_superviseur_dashbord', 'Peut voir le tableau de bord des superviseurs'),
            ('view_professeur_dashbord', 'Peut voir le tableau de bord des professeur'),
            ('view_client_dashbord', 'Peut voir le tableau de bord des clients'),
            # Ajoutez d'autres permissions selon vos besoins
        ]

        # Créer les permissions
        self.stdout.write("Création des permissions...")
        for code, description in permissions:
            perm, created = Permission.objects.get_or_create(
                code=code,
                defaults={'description': description}
            )
            status = "créée" if created else "déjà existante"
            self.stdout.write(f"  - {code}: {status}")

        # Attribution des permissions aux rôles
        role_permissions = {
            'admin': [
                'manage_users', 'view_admin_dashboard'
            ],
            'superviseur': [
                'view_superviseur_dashbord'
            ],
            'professeur': [
                'view_professeur_dashbord'
            ],
            'client': [
                'view_client_dashbord'
            ]
        }

        self.stdout.write("\nAttribution des permissions aux rôles...")
        for role, perm_codes in role_permissions.items():
            self.stdout.write(f"\nRôle: {role}")
            for code in perm_codes:
                try:
                    perm = Permission.objects.get(code=code)
                    role_perm, created = RolePermission.objects.get_or_create(
                        role=role,
                        permission=perm
                    )
                    status = "attribuée" if created else "déjà attribuée"
                    self.stdout.write(f"  - {code}: {status}")
                except Permission.DoesNotExist:
                    self.stdout.write(f"  - {code}: ERREUR - permission inexistante")

        self.stdout.write(self.style.SUCCESS("\nInitialisation des permissions terminée!"))