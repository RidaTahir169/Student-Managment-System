from django import forms
from django.utils import timezone
from accounts.models import CustomUser
from courses.models import Department, Course
from .models import Teacher


class TeacherCreateForm(forms.Form):
    """
    Unified onboarding form to recruit / register a new faculty member,
    creating both the CustomUser authentication identity and Teacher profile.
    """
    # CustomUser Fields
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., prof_john'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g., john.doe@university.edu'})
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
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Temporary Password (default: Teacher@123)'}),
        help_text='If left blank, default password "Teacher@123" will be assigned.'
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

    # Teacher Profile Fields
    employee_id = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., EMP-2026-001'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label='-- Select Academic Department --',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    designation = forms.CharField(
        max_length=100,
        required=False,
        initial='Lecturer',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Professor, Assistant Professor, Lecturer'})
    )
    qualification = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Ph.D. in Computer Science, M.Sc. Mathematics'})
    )
    joining_date = forms.DateField(
        initial=timezone.now,
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief academic bio, research interests, etc.'})
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

    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id', '').strip().upper()
        if Teacher.objects.filter(employee_id__iexact=employee_id).exists():
            raise forms.ValidationError('A teacher with this Employee ID already exists.')
        return employee_id


class TeacherProfileUpdateForm(forms.ModelForm):
    """
    Form to update academic appointment details on an existing Teacher profile.
    """
    joining_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    class Meta:
        model = Teacher
        fields = (
            'employee_id',
            'department',
            'designation',
            'qualification',
            'joining_date',
            'bio',
        )
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id', '').strip().upper()
        qs = Teacher.objects.filter(employee_id__iexact=employee_id)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A teacher with this Employee ID already exists.')
        return employee_id


class TeacherUserUpdateForm(forms.ModelForm):
    """
    Form to update demographic and account information for a Teacher's CustomUser.
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


class TeacherCourseAssignForm(forms.Form):
    """
    Form allowing administrators to assign multiple courses to a teacher.
    """
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.select_related('department', 'classroom', 'session', 'teacher__user').all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Select the courses you want to assign to this faculty member.'
    )

