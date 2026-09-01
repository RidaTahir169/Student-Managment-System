from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Attendance(models.Model):
    """
    Daily attendance log tracking student presence for a specific course session.
    """
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', _('Present')
        ABSENT = 'ABSENT', _('Absent')
        LATE = 'LATE', _('Late')
        EXCUSED = 'EXCUSED', _('Excused')

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    date = models.DateField(
        default=timezone.now,
        help_text=_('Date of attendance.')
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PRESENT
    )
    remarks = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_('Optional notes (e.g., Medical excuse, bus delay).')
    )

    class Meta:
        verbose_name = _('Attendance Record')
        verbose_name_plural = _('Attendance Records')
        unique_together = ['student', 'course', 'date']
        ordering = ['-date', 'student']

    def __str__(self):
        return f"{self.student.admission_number} | {self.course.course_code} | {self.date} - {self.get_status_display()}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from courses.models import Enrollment

        if self.date and self.date > timezone.now().date():
            raise ValidationError({'date': _('Attendance date cannot be in the future.')})

        if hasattr(self, 'student') and hasattr(self, 'course') and self.student_id and self.course_id:
            if not Enrollment.objects.filter(student_id=self.student_id, course_id=self.course_id).exists():
                raise ValidationError({'student': _('Selected student is not enrolled in this course.')})

        if self.student_id and self.course_id and self.date:
            qs = Attendance.objects.filter(
                student_id=self.student_id,
                course_id=self.course_id,
                date=self.date
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(_('An attendance record for this student and course already exists on this date.'))

