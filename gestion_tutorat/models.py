from django.db import models
from django.utils import timezone

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('L\'adresse email est obligatoire')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('statut', 'actif')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    SEXE_CHOICES = (
        ('M', 'Masculin'),
        ('F', 'Féminin'),
        ('A', 'Autre'),
    )
    STATUT_CHOICES = (
        ('actif', 'Actif'),
        ('inactif', 'Inactif'),
        ('suspendu', 'Suspendu'),
    )

    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=20)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES)
    ethnie = models.CharField(max_length=100, blank=True, null=True)
    adresse = models.TextField()
    telephone = models.CharField(max_length=20)
    date_naissance = models.DateField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    derniere_connexion = models.DateTimeField(null=True, blank=True)
    est_connecte = models.BooleanField(default=False)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='inactif')

    # Champs requis pour Django Admin
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom', 'prenom']

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.role})"

    def get_full_name(self):
        return f"{self.prenom} {self.nom}"

    def get_short_name(self):
        return self.prenom


class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')

    def __str__(self):
        return f"Admin: {self.user.prenom} {self.user.nom}"


class Superviseur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='superviseur_profile')

    def __str__(self):
        return f"Superviseur: {self.user.prenom} {self.user.nom}"


class Professeur(models.Model):
    STATUT_VERIFICATION_CHOICES = (
        ('en_attente', 'En attente'),
        ('actif', 'Actif'),
        ('inactif', 'Inactif'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='professeur_profile')
    niveau = models.IntegerField(null=True, blank=True)
    statut_verification = models.CharField(max_length=20, choices=STATUT_VERIFICATION_CHOICES, default='en_attente')
    specialites = models.TextField(blank=True)

    def __str__(self):
        return f"Professeur: {self.user.prenom} {self.user.nom}"


class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')

    def __str__(self):
        return f"Client: {self.user.prenom} {self.user.nom}"


class Enfant(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='enfants')
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_naissance = models.DateField()
    classe = models.CharField(max_length=50)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.prenom} {self.nom} (Enfant de {self.client.user.prenom} {self.client.user.nom})"


class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField()

    objects = models.Manager()

    def __str__(self):
        return self.code


class RolePermission(models.Model):
    role = models.CharField(max_length=20)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    objects = models.Manager()

    class Meta:
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role} - {self.permission.code}"


class UserPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted = models.BooleanField(default=True)

    objects = models.Manager()

    class Meta:
        unique_together = ('user', 'permission')

    def __str__(self):
        action = "accordée" if self.granted else "retirée"
        return f"Permission {self.permission.code} {action} à {self.user.prenom} {self.user.nom}"


class Log(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"


class Fichier(models.Model):
    nom_fichier = models.CharField(max_length=255)
    type_mime = models.CharField(max_length=100)
    taille = models.IntegerField()  # Taille en octets
    contenu = models.BinaryField()  # Équivalent à BYTEA en PostgreSQL
    date_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nom_fichier} ({self.type_mime})"


class Entrevue(models.Model):
    STATUT_CHOICES = (
        ('en_attente', 'En attente'),
        ('terminee', 'Terminée'),
        ('verification_document', 'Vérification des documents'),
        ('acceptee', 'Acceptée'),
    )

    createur = models.ForeignKey(
        'User',  # Référence au modèle User existant
        on_delete=models.CASCADE,
        related_name='entrevues_creees'
    )
    interviewer = models.ForeignKey(
        'User',  # Référence au modèle User existant
        on_delete=models.CASCADE,
        related_name='entrevues_conduites'
    )
    professeur = models.ForeignKey(
        'Professeur',  # Référence au modèle Professeur existant
        on_delete=models.CASCADE,
        related_name='entrevues'
    )
    date_entrevue = models.DateTimeField()
    lien_entrevue = models.URLField(max_length=255)
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES, default='en_attente')
    notes = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Entrevue avec {self.professeur.user.get_full_name()} le {self.date_entrevue}"


class DocumentProfesseur(models.Model):
    TYPE_DOCUMENT_CHOICES = (
        ('contrat', 'Contrat'),
        ('permis_etude', 'Permis d\'étude'),
        ('permis_travail', 'Permis de travail'),
        ('nas', 'Numéro d\'assurance sociale'),
        ('piece_identite', 'Pièce d\'identité'),
    )

    STATUT_VERIFICATION_CHOICES = (
        ('en_attente', 'En attente'),
        ('verifie', 'Vérifié'),
        ('rejete', 'Rejeté'),
    )

    professeur = models.ForeignKey(
        'Professeur',  # Référence au modèle Professeur existant
        on_delete=models.CASCADE,
        related_name='documents'
    )
    entrevue = models.ForeignKey(
        Entrevue,
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True  # Permet que le document soit ajouté indépendamment d'une entrevue
    )
    type_document = models.CharField(max_length=30, choices=TYPE_DOCUMENT_CHOICES)
    fichier = models.ForeignKey(
        Fichier,
        on_delete=models.CASCADE,
        related_name='documents_professeur'
    )
    date_upload = models.DateTimeField(auto_now_add=True)
    statut_verification = models.CharField(
        max_length=20,
        choices=STATUT_VERIFICATION_CHOICES,
        default='en_attente'
    )

    def __str__(self):
        return f"{self.get_type_document_display()} de {self.professeur.user.get_full_name()}"

