from django.contrib import admin
from .models import AcademicRecord


@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'course',
        'exam_name',
        'exam_type',
        'marks_obtained',
        'total_marks',
        'percentage',
        'grade',
        'grade_point',
        'date_recorded',
    )
    list_filter = ('exam_type', 'grade', 'course', 'date_recorded')
    search_fields = (
        'student__admission_number',
        'student__user__username',
        'student__user__first_name',
        'student__user__last_name',
        'course__course_code',
        'course__title',
        'exam_name',
    )
    readonly_fields = ('percentage', 'grade', 'grade_point')
