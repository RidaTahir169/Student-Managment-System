from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from accounts.models import CustomUser
from courses.models import ClassRoom
from .models import Student


class StudentCreateForm(forms.Form):
    """
    Unified form to admit a new student, creating both the CustomUser
    authentication identity and the Student academic profile.
    """
    # CustomUser Fields
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., john_doe'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g., student@example.com'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Temporary Password (default: Student@123)'}),
        help_text='If left blank, default password "Student@123" will be assigned.'
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'})
    )
    gender = forms.ChoiceField(
        choices=[('', '-- Select Gender --')] + list(CustomUser.Gender.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Residential Address'})
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    # Student Profile Fields
    admission_number = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., STU-2026-001'})
    )
    classroom = forms.ModelChoiceField(
        queryset=ClassRoom.objects.all(),
        required=False,
        empty_label='-- Select Assigned Class Room --',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    roll_number = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 101'})
    )
    parent_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parent / Guardian Full Name'})
    )
    parent_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parent Contact Number'})
    )
    emergency_contact = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency Contact Number'})
    )
    blood_group = forms.CharField(
        max_length=5,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., A+, O+, B-'})
    )
    admission_date = forms.DateField(
        initial=timezone.now,
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email address already exists.')
        return email

    def clean_admission_number(self):
        admission_number = self.cleaned_data.get('admission_number', '').strip().upper()
        if Student.objects.filter(admission_number__iexact=admission_number).exists():
            raise forms.ValidationError('A student with this admission number already exists.')
        return admission_number


class StudentProfileUpdateForm(forms.ModelForm):
    """
    Form to update academic and parent details on an existing Student profile.
    """
    admission_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    class Meta:
        model = Student
        fields = (
            'admission_number',
            'classroom',
            'roll_number',
            'parent_name',
            'parent_phone',
            'emergency_contact',
            'blood_group',
            'admission_date',
        )
        widgets = {
            'admission_number': forms.TextInput(attrs={'class': 'form-control'}),
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'roll_number': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'blood_group': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_admission_number(self):
        admission_number = self.cleaned_data.get('admission_number', '').strip().upper()
        qs = Student.objects.filter(admission_number__iexact=admission_number)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A student with this admission number already exists.')
        return admission_number


class StudentUserUpdateForm(forms.ModelForm):
    """
    Form to update demographic and authentication info for a Student's CustomUser.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CustomUser
        fields = (
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'address',
            'date_of_birth',
            'gender',
            'profile_picture',
        )
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = CustomUser.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A user with this email address already exists.')
        return email

