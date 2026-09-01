from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Student(models.Model):
    """
    Student profile linked 1-to-1 with CustomUser.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    admission_number = models.CharField(
        max_length=30,
        unique=True,
        help_text=_('Unique Student Admission / Registration Number.')
    )
    classroom = models.ForeignKey(
        'courses.ClassRoom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        help_text=_('Assigned class or grade level.')
    )
    roll_number = models.CharField(
        max_length=30,
        blank=True,
        help_text=_('Class roll number / seat identifier.')
    )
    parent_name = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Parent / Guardian full name.')
    )
    parent_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Parent / Guardian contact number.')
    )
    admission_date = models.DateField(default=timezone.now)
    emergency_contact = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Emergency contact phone number.')
    )
    blood_group = models.CharField(
        max_length=5,
        blank=True,
        help_text=_('e.g., A+, O-, B+, AB+')
    )

    class Meta:
        verbose_name = _('Student')
        verbose_name_plural = _('Students')
        ordering = ['admission_number']

    def __str__(self):
        full_name = self.user.get_full_name() or self.user.username
        return f"{full_name} ({self.admission_number})"

    def clean(self):
        super().clean()
        if self.admission_number:
            self.admission_number = self.admission_number.strip().upper()
            from django.core.exceptions import ValidationError
            qs = Student.objects.filter(admission_number__iexact=self.admission_number)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({'admission_number': _('A student with this Admission Number already exists.')})

    def save(self, *args, **kwargs):
        if self.admission_number:
            self.admission_number = self.admission_number.strip().upper()
        super().save(*args, **kwargs)

