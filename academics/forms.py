from decimal import Decimal
from django import forms
from .models import AcademicRecord
from courses.models import Course, Enrollment
from students.models import Student


class AcademicRecordForm(forms.ModelForm):
    """
    Form for entering and updating student academic records (marks, exams).
    Dynamically filters courses and enrolled students based on user role and selection.
    """
    class Meta:
        model = AcademicRecord
        fields = (
            'course',
            'student',
            'exam_name',
            'exam_type',
            'marks_obtained',
            'total_marks',
            'date_recorded',
            'remarks',
        )
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select', 'id': 'id_course'}),
            'student': forms.Select(attrs={'class': 'form-select', 'id': 'id_student'}),
            'exam_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Midterm Exam 2026, Quiz 1'}),
            'exam_type': forms.Select(attrs={'class': 'form-select'}),
            'marks_obtained': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'e.g., 85.50'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '1', 'placeholder': 'e.g., 100.00'}),
            'date_recorded': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional teacher feedback or notes...'}),
        }

    def __init__(self, *args, user=None, course_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Role-based Course filtering
        if user:
            if user.is_superuser or user.role == 'ADMIN':
                self.fields['course'].queryset = Course.objects.select_related('department', 'classroom').all()
            elif user.role == 'TEACHER' and hasattr(user, 'teacher_profile'):
                self.fields['course'].queryset = Course.objects.filter(
                    teacher=user.teacher_profile
                ).select_related('department', 'classroom')
            else:
                self.fields['course'].queryset = Course.objects.none()

        # Filter students by course if provided
        selected_course = None
        if self.is_bound and self.data.get('course'):
            try:
                selected_course = Course.objects.get(pk=self.data.get('course'))
            except (Course.DoesNotExist, ValueError):
                pass
        elif course_id:
            try:
                selected_course = Course.objects.get(pk=course_id)
                self.fields['course'].initial = selected_course
            except (Course.DoesNotExist, ValueError):
                pass
        elif self.instance and self.instance.pk and self.instance.course:
            selected_course = self.instance.course

        if selected_course:
            enrolled_student_ids = Enrollment.objects.filter(
                course=selected_course,
                status=Enrollment.EnrollmentStatus.ACTIVE
            ).values_list('student_id', flat=True)
            self.fields['student'].queryset = Student.objects.filter(
                id__in=enrolled_student_ids
            ).select_related('user', 'classroom').order_by('admission_number')
        else:
            self.fields['student'].queryset = Student.objects.select_related('user', 'classroom').all().order_by('admission_number')

        self.fields['student'].label_from_instance = lambda obj: f"{obj.admission_number} - {obj.user.get_full_name() or obj.user.username}"
        self.fields['course'].label_from_instance = lambda obj: f"{obj.course_code} - {obj.title}"

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        student = cleaned_data.get('student')
        exam_name = cleaned_data.get('exam_name')
        marks = cleaned_data.get('marks_obtained')
        total = cleaned_data.get('total_marks')

        # Marks validation
        if marks is not None:
            if Decimal(str(marks)) < Decimal('0.00'):
                self.add_error('marks_obtained', 'Marks obtained cannot be negative.')

        if total is not None:
            if Decimal(str(total)) <= Decimal('0.00'):
                self.add_error('total_marks', 'Total marks must be greater than 0.')

        if marks is not None and total is not None:
            if Decimal(str(marks)) > Decimal(str(total)):
                self.add_error('marks_obtained', 'Marks obtained cannot exceed total marks.')

        # Role-based course permission check for teachers
        if self.user and self.user.role == 'TEACHER' and hasattr(self.user, 'teacher_profile') and course:
            if course.teacher != self.user.teacher_profile:
                self.add_error('course', 'You are only authorized to enter marks for courses assigned to you.')

        # Active enrollment verification
        if student and course:
            if not Enrollment.objects.filter(student=student, course=course).exists():
                self.add_error('student', f'Student {student.admission_number} is not enrolled in {course.course_code}.')

        # Duplicate assessment title check
        if student and course and exam_name:
            exam_name_clean = exam_name.strip()
            qs = AcademicRecord.objects.filter(student=student, course=course, exam_name__iexact=exam_name_clean)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('exam_name', f"An academic record for '{exam_name_clean}' already exists for this student in {course.course_code}.")

        return cleaned_data



class AcademicRecordFilterForm(forms.Form):
    """
    Filter form for searching and filtering Academic Records.
    """
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-light',
            'placeholder': 'Search student name, admission #, exam...'
        })
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.all().order_by('course_code'),
        required=False,
        empty_label='-- All Courses --',
        widget=forms.Select(attrs={'class': 'form-select bg-light'})
    )
    exam_type = forms.ChoiceField(
        choices=[('', '-- All Assessment Types --')] + list(AcademicRecord.ExamType.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select bg-light'})
    )
    grade = forms.ChoiceField(
        choices=[
            ('', '-- All Grades --'),
            ('A+', 'A+ (90-100%)'),
            ('A', 'A (80-89%)'),
            ('B', 'B (70-79%)'),
            ('C', 'C (60-69%)'),
            ('D', 'D (50-59%)'),
            ('F', 'F (Below 50%)'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select bg-light'})
    )
