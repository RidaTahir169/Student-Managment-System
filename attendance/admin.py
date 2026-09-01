from django.contrib import admin
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'date', 'status', 'remarks')
    list_filter = ('status', 'date', 'course')
    search_fields = (
        'student__admission_number',
        'student__user__username',
        'student__user__first_name',
        'student__user__last_name',
        'course__course_code',
        'course__title',
    )
    date_hierarchy = 'date'
