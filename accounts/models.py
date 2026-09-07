from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """
    Custom User model extending Django AbstractUser with role-based access
    and demographic profile fields.
    """
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrator')
        TEACHER = 'TEACHER', _('Teacher')
        STUDENT = 'STUDENT', _('Student')

    class Gender(models.TextChoices):
        MALE = 'MALE', _('Male')
        FEMALE = 'FEMALE', _('Female')
        OTHER = 'OTHER', _('Other')

    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text=_('User role determines dashboard view and access permissions.')
    )
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True,
        help_text=_('Upload a profile photo.')
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_('Contact telephone number.')
    )
    address = models.TextField(
        blank=True,
        null=True,
        help_text=_('Residential address.')
    )
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        help_text=_('Date of birth (YYYY-MM-DD).')
    )
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['username']

    def __str__(self):
        full_name = self.get_full_name()
        if full_name:
            return f"{full_name} ({self.username}) - {self.get_role_display()}"
        return f"{self.username} - {self.get_role_display()}"

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_teacher_user(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student_user(self):
        return self.role == self.Role.STUDENT

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            validate_email(self.email)
            qs = CustomUser.objects.filter(email__iexact=self.email)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({'email': _('A user with this email address already exists.')})

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Customer(models.Model):
    """
    Customer profile model linked 1-to-1 with CustomUser.
    Stored explicitly in database table 'account_customer'.
    """
    user = models.OneToOneField(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='customer_profile',
        verbose_name=_('User')
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_('Customer contact phone number.')
    )
    address = models.TextField(
        blank=True,
        null=True,
        help_text=_('Customer physical address.')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        db_table = 'account_customer'
        verbose_name = _('Customer')
        verbose_name_plural = _('Customers')
        ordering = ['-created_at']

    def __str__(self):
        full_name = self.user.get_full_name() if self.user else ''
        return f"{full_name or self.user.username} (Customer)"


