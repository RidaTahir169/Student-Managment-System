from django import forms
from django.utils import timezone
from .models import Attendance
from courses.models import Course, ClassRoom
from students.models import Student


class CourseDateSelectionForm(forms.Form):
    """
    Form allowing teachers and admins to select a course and date for marking attendance.
    """
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'course_select'}),
        empty_label='-- Select Academic Course --'
    )
    date = forms.DateField(
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'attendance_date'})
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            if user.is_superuser or user.role == 'ADMIN':
                self.fields['course'].queryset = Course.objects.select_related('department', 'classroom').all()
            elif user.role == 'TEACHER' and hasattr(user, 'teacher_profile'):
                self.fields['course'].queryset = Course.objects.filter(
                    teacher=user.teacher_profile
                ).select_related('department', 'classroom')
            else:
                self.fields['course'].queryset = Course.objects.none()

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date > timezone.now().date():
            raise forms.ValidationError('Attendance date cannot be in the future.')
        return date


class AttendanceFilterForm(forms.Form):
    """
    Filter form for Attendance History & Logs.
    """
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-light',
            'placeholder': 'Search student name, admission #...'
        })
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.all().order_by('course_code'),
        required=False,
        empty_label='-- All Courses --',
        widget=forms.Select(attrs={'class': 'form-select bg-light'})
    )
    status = forms.ChoiceField(
        choices=[('', '-- All Statuses --')] + list(Attendance.Status.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select bg-light'})
    )
    classroom = forms.ModelChoiceField(
        queryset=ClassRoom.objects.all().order_by('name', 'section'),
        required=False,
        empty_label='-- All Classes --',
        widget=forms.Select(attrs={'class': 'form-select bg-light'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control bg-light', 'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control bg-light', 'type': 'date'})
    )


class AttendanceSingleUpdateForm(forms.ModelForm):
    """
    Form to edit a single attendance entry's status and remarks.
    """
    class Meta:
        model = Attendance
        fields = ('status', 'remarks', 'date')
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional remarks (e.g. Doctor note)'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        if date and date > timezone.now().date():
            self.add_error('date', 'Attendance date cannot be in the future.')

        if date and self.instance and self.instance.student and self.instance.course:
            qs = Attendance.objects.filter(
                student=self.instance.student,
                course=self.instance.course,
                date=date
            ).exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('date', 'An attendance record for this student and course already exists on this date.')

        return cleaned_data

