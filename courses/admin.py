from django.contrib import admin
from .models import Department, AcademicSession, ClassRoom, Course, Enrollment


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current',)
    search_fields = ('name',)


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'section', 'department')
    list_filter = ('department', 'name')
    search_fields = ('name', 'section')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'title', 'department', 'teacher', 'classroom', 'credit_hours', 'session')
    list_filter = ('department', 'session', 'classroom')
    search_fields = ('course_code', 'title')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrollment_date', 'status')
    list_filter = ('status', 'enrollment_date', 'course')
    search_fields = ('student__admission_number', 'student__user__username', 'course__course_code', 'course__title')
