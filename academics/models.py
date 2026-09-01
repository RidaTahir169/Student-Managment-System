from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AcademicRecord(models.Model):
    """
    Academic Record storing student examination marks, percentage,
    letter grade, and grade points for a specific course assessment.
    """
    class ExamType(models.TextChoices):
        QUIZ = 'QUIZ', _('Quiz')
        ASSIGNMENT = 'ASSIGNMENT', _('Assignment')
        MIDTERM = 'MIDTERM', _('Midterm Exam')
        FINAL = 'FINAL', _('Final Exam')
        PROJECT = 'PROJECT', _('Project / Practical')

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='academic_records'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='academic_records'
    )
    exam_name = models.CharField(
        max_length=100,
        help_text=_('Assessment title (e.g., Midterm Exam 2026, Quiz 1)')
    )
    exam_type = models.CharField(
        max_length=20,
        choices=ExamType.choices,
        default=ExamType.FINAL
    )
    marks_obtained = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text=_('Marks earned by student.')
    )
    total_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('1.00'))],
        help_text=_('Maximum possible marks.')
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_('Calculated automatically on save.')
    )
    grade = models.CharField(
        max_length=5,
        blank=True,
        help_text=_('Calculated letter grade (A+, A, B, etc.).')
    )
    grade_point = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_('Grade point on a 4.00 scale.')
    )
    remarks = models.TextField(blank=True, null=True)
    date_recorded = models.DateField(default=timezone.now)

    class Meta:
        verbose_name = _('Academic Record')
        verbose_name_plural = _('Academic Records')
        unique_together = ['student', 'course', 'exam_name']
        ordering = ['-date_recorded', 'student']

    def __str__(self):
        return f"{self.student.admission_number} | {self.course.course_code} - {self.exam_name}: {self.grade} ({self.marks_obtained}/{self.total_marks})"

    def clean(self):
        from django.core.exceptions import ValidationError
        from courses.models import Enrollment

        if self.exam_name:
            self.exam_name = self.exam_name.strip()

        if self.marks_obtained is not None:
            if Decimal(str(self.marks_obtained)) < Decimal('0.00'):
                raise ValidationError({'marks_obtained': _('Marks obtained cannot be negative.')})

        if self.total_marks is not None:
            if Decimal(str(self.total_marks)) <= Decimal('0.00'):
                raise ValidationError({'total_marks': _('Total marks must be greater than 0.')})

        if self.marks_obtained is not None and self.total_marks is not None:
            if Decimal(str(self.marks_obtained)) > Decimal(str(self.total_marks)):
                raise ValidationError({'marks_obtained': _('Marks obtained cannot be greater than total marks.')})

        # Validate that student is enrolled in the course
        if hasattr(self, 'student') and hasattr(self, 'course') and self.student_id and self.course_id:
            if not Enrollment.objects.filter(student_id=self.student_id, course_id=self.course_id).exists():
                raise ValidationError({'student': _('Selected student is not enrolled in this course.')})

        # Case-insensitive duplicate assessment check
        if self.student_id and self.course_id and self.exam_name:
            qs = AcademicRecord.objects.filter(
                student_id=self.student_id,
                course_id=self.course_id,
                exam_name__iexact=self.exam_name
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({'exam_name': _('An academic record for this assessment title already exists for this student in this course.')})


    def save(self, *args, **kwargs):
        # Convert values safely to Decimal
        marks = Decimal(str(self.marks_obtained)) if self.marks_obtained is not None else Decimal('0.00')
        total = Decimal(str(self.total_marks)) if self.total_marks is not None else Decimal('100.00')

        # Auto-compute percentage
        if total > Decimal('0.00'):
            self.percentage = round((marks / total) * Decimal('100.00'), 2)
        else:
            self.percentage = Decimal('0.00')

        # Auto-compute letter grade & grade point
        pct = self.percentage
        if pct >= Decimal('90.00'):
            self.grade = 'A+'
            self.grade_point = Decimal('4.00')
        elif pct >= Decimal('80.00'):
            self.grade = 'A'
            self.grade_point = Decimal('3.75')
        elif pct >= Decimal('70.00'):
            self.grade = 'B'
            self.grade_point = Decimal('3.00')
        elif pct >= Decimal('60.00'):
            self.grade = 'C'
            self.grade_point = Decimal('2.00')
        elif pct >= Decimal('50.00'):
            self.grade = 'D'
            self.grade_point = Decimal('1.00')
        else:
            self.grade = 'F'
            self.grade_point = Decimal('0.00')

        super().save(*args, **kwargs)
