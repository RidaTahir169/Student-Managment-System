from django import forms
from django.utils import timezone
from .models import Course, ClassRoom, Department, AcademicSession, Enrollment
from teachers.models import Teacher
from students.models import Student


class CourseForm(forms.ModelForm):
    """
    Form to create or update an academic course module.
    """
    class Meta:
        model = Course
        fields = (
            'course_code',
            'title',
            'credit_hours',
            'department',
            'teacher',
            'classroom',
            'session',
            'description',
        )
        widgets = {
            'course_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CS101, MATH201'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Introduction to Computer Science'}),
            'credit_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'session': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief course description, syllabus overview, objectives...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = Teacher.objects.select_related('user').all()
        self.fields['teacher'].empty_label = '-- Unassigned (Assign Later) --'
        self.fields['classroom'].empty_label = '-- Select Target Class Room --'
        self.fields['department'].empty_label = '-- Select Department --'
        self.fields['session'].empty_label = '-- Select Academic Session --'

    def clean_course_code(self):
        course_code = self.cleaned_data.get('course_code', '').strip().upper()
        query = Course.objects.filter(course_code__iexact=course_code)
        if self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise forms.ValidationError(f"A course with code '{course_code}' already exists.")
        return course_code


class ClassRoomForm(forms.ModelForm):
    """
    Form to create or update a grade section or classroom cohort.
    """
    class Meta:
        model = ClassRoom
        fields = (
            'name',
            'section',
            'department',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Grade 10, BSCS-1st, Year 2'}),
            'section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Section A, Group 1, Morning'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].empty_label = '-- Select Department (Optional) --'

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        section = cleaned_data.get('section')

        if name and section:
            query = ClassRoom.objects.filter(name__iexact=name.strip(), section__iexact=section.strip())
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise forms.ValidationError(f"A class room with name '{name}' and section '{section}' already exists.")
        return cleaned_data


class ClassRoomAssignStudentsForm(forms.Form):
    """
    Form allowing administrators to assign or transfer students to a Class Room.
    """
    students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.select_related('user', 'classroom').all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Select the students to place in this class section.'
    )


class CourseEnrollStudentsForm(forms.Form):
    """
    Form allowing administrators or teachers to enroll students into a course.
    """
    students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.select_related('user', 'classroom').all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Select students to enroll in this course module.'
    )


class StudentCourseEnrollForm(forms.Form):
    """
    Form allowing administrators to enroll a specific student into multiple courses.
    """
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.select_related('department', 'classroom', 'session', 'teacher__user').all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Select courses to enroll this student in.'
    )


class EnrollmentCreateForm(forms.ModelForm):
    """
    Form to enroll a single student into a course with strict duplicate validation.
    """
    class Meta:
        model = Enrollment
        fields = ('student', 'course', 'enrollment_date', 'status')
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'enrollment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = Student.objects.select_related('user', 'classroom').all()
        self.fields['student'].empty_label = '-- Select Student --'
        self.fields['course'].queryset = Course.objects.select_related('department', 'classroom').all()
        self.fields['course'].empty_label = '-- Select Course --'
        if not self.instance.pk and 'enrollment_date' not in self.initial:
            self.initial['enrollment_date'] = timezone.now().date()

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        course = cleaned_data.get('course')

        if student and course:
            query = Enrollment.objects.filter(student=student, course=course)
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                student_name = student.user.get_full_name() or student.admission_number
                raise forms.ValidationError(
                    f"Student {student_name} ({student.admission_number}) is already enrolled in {course.course_code} - {course.title}."
                )
        return cleaned_data


class EnrollmentUpdateForm(forms.ModelForm):
    """
    Form to update enrollment status (Active, Dropped, Completed) or enrollment date.
    """
    class Meta:
        model = Enrollment
        fields = ('status', 'enrollment_date')
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'enrollment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
