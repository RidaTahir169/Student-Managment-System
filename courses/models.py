from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Department(models.Model):
    """
    Academic Department (e.g., Computer Science, Mathematics, Physics).
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class AcademicSession(models.Model):
    """
    Academic year / term cycle (e.g., 2025-2026).
    """
    name = models.CharField(max_length=50, unique=True, help_text=_('e.g., 2025-2026'))
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(
        default=False,
        help_text=_('Mark this session as the active academic period.')
    )

    class Meta:
        verbose_name = _('Academic Session')
        verbose_name_plural = _('Academic Sessions')
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # If this session is set as current, unset any existing current session
        if self.is_current:
            AcademicSession.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class ClassRoom(models.Model):
    """
    Class or Grade level (e.g., Grade 10 - Section A).
    """
    name = models.CharField(max_length=50, help_text=_('e.g., Grade 10, Year 1, BSCS-4th'))
    section = models.CharField(max_length=20, help_text=_('e.g., Section A, Group 1'))
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classrooms'
    )

    class Meta:
        verbose_name = _('Class Room')
        verbose_name_plural = _('Class Rooms')
        unique_together = ['name', 'section']
        ordering = ['name', 'section']

    def __str__(self):
        return f"{self.name} - {self.section}"


class Course(models.Model):
    """
    Subject / Course module linked to a Department, Class, and Teacher.
    """
    course_code = models.CharField(max_length=20, unique=True, help_text=_('e.g., CS101'))
    title = models.CharField(max_length=150, help_text=_('e.g., Introduction to Computer Science'))
    credit_hours = models.PositiveIntegerField(default=3)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='courses'
    )
    teacher = models.ForeignKey(
        'teachers.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_courses'
    )
    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses'
    )
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses'
    )
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _('Course')
        verbose_name_plural = _('Courses')
        ordering = ['course_code']

    def __str__(self):
        return f"{self.course_code} - {self.title}"


class Enrollment(models.Model):
    """
    Intermediary enrollment linking a Student to an active Course.
    """
    class EnrollmentStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        DROPPED = 'DROPPED', _('Dropped')
        COMPLETED = 'COMPLETED', _('Completed')

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    enrollment_date = models.DateField(default=timezone.now)
    status = models.CharField(
        max_length=15,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ACTIVE
    )

    class Meta:
        verbose_name = _('Enrollment')
        verbose_name_plural = _('Enrollments')
        unique_together = ['student', 'course']
        ordering = ['-enrollment_date']

    def __str__(self):
        return f"{self.student} enrolled in {self.course} ({self.get_status_display()})"
