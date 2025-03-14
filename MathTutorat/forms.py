# forms.py
from django import forms
from django.utils import timezone

class TutorForm(forms.Form):
    tutor_name = forms.CharField(
        label="Nom",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'required': 'required'})
    )
    tutor_firstname = forms.CharField(
        label="Prénom",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'required': 'required'})
    )
    tutor_phone = forms.CharField(
        label="Téléphone",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'required': 'required'})
    )
    tutor_email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={'required': 'required'})
    )
    tutor_address = forms.CharField(
        label="Adresse",
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'required': 'required'})
    )
    tutor_birth_date = forms.DateField(
        label="Date de naissance",
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'required': 'required'})
    )
    tutor_gender = forms.ChoiceField(
        label="Sexe",
        choices=[('M', 'Masculin'), ('F', 'Féminin')],
        required=True
    )

class ClientForm(forms.Form):
    client_name = forms.CharField(
        label="Nom",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'required': 'required'})
    )
    client_firstname = forms.CharField(
        label="Prénom",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'required': 'required'})
    )
    client_phone = forms.CharField(
        label="Téléphone",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'required': 'required'})
    )
    client_email = forms.EmailField(
        label="Email",
        required=False
    )
    client_address = forms.CharField(
        label="Adresse",
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'required': 'required'})
    )

class ChildForm(forms.Form):
    child_name = forms.CharField(
        label="Nom",
        max_length=100,
        required=False  # Pas obligatoire dans le formulaire
    )
    child_firstname = forms.CharField(
        label="Prénom",
        max_length=100,
        required=False  # Pas obligatoire dans le formulaire
    )
    hours_per_week = forms.DecimalField(
        label="Heures par semaine",
        min_value=0.5,
        max_value=40,
        initial=1,
        required=True
    )
    tutoring_mode = forms.ChoiceField(
        label="Mode de tutorat",
        choices=[('online', 'En ligne'), ('in_person', 'En présentiel')],
        required=True
    )
    course_address = forms.CharField(
        label="Adresse du cours",
        max_length=200,
        required=False
    )
    client_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True
    )

class MessageForm(forms.Form):
    message = forms.CharField(
        label="Message",
        required=False,
        widget=forms.Textarea(attrs={'rows': 4})
    )