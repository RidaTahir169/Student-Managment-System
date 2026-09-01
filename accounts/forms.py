from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser


class UserRegistrationForm(UserCreationForm):
    """
    Form for registering new users with role selection and demographic fields.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'})
    )
    first_name = forms.CharField(
        required=True,
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        required=True,
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    role = forms.ChoiceField(
        choices=CustomUser.Role.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'})
    )
    gender = forms.ChoiceField(
        choices=[('', '-- Select Gender --')] + list(CustomUser.Gender.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'phone_number',
            'gender',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['role', 'gender']:
                field.widget.attrs.setdefault('class', 'form-control')

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


class UserLoginForm(AuthenticationForm):
    """
    Styled authentication form supporting username or email login with Bootstrap 5.
    """
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True,
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password',
        })
    )

    error_messages = {
        'invalid_login': "Invalid credentials. Please check your username/email and password.",
        'inactive': "This account is inactive. Please contact your system administrator.",
    }


class UserProfileForm(forms.ModelForm):
    """
    Form for authenticated users to update their personal profile info.
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
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
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

