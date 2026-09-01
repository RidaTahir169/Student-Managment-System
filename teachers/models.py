from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Teacher(models.Model):
    """
    Teacher profile linked 1-to-1 with CustomUser.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )
    employee_id = models.CharField(
        max_length=30,
        unique=True,
        help_text=_('Unique Faculty / Employee Identification Number.')
    )
    department = models.ForeignKey(
        'courses.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teachers'
    )
    designation = models.CharField(
        max_length=100,
        default='Lecturer',
        help_text=_('e.g., Professor, Assistant Professor, Lecturer')
    )
    qualification = models.CharField(
        max_length=150,
        blank=True,
        help_text=_('e.g., Ph.D. in Computer Science, M.Sc. Mathematics')
    )
    joining_date = models.DateField(default=timezone.now)
    bio = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _('Teacher')
        verbose_name_plural = _('Teachers')
        ordering = ['employee_id']

    def __str__(self):
        full_name = self.user.get_full_name() or self.user.username
        return f"{full_name} ({self.employee_id})"

    def clean(self):
        super().clean()
        if self.employee_id:
            self.employee_id = self.employee_id.strip().upper()
            from django.core.exceptions import ValidationError
            qs = Teacher.objects.filter(employee_id__iexact=self.employee_id)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({'employee_id': _('A teacher with this Employee ID already exists.')})

    def save(self, *args, **kwargs):
        if self.employee_id:
            self.employee_id = self.employee_id.strip().upper()
        super().save(*args, **kwargs)

