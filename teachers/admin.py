from django.contrib import admin
from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'get_full_name', 'department', 'designation', 'joining_date')
    list_filter = ('department', 'designation', 'joining_date')
    search_fields = (
        'employee_id',
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
    )

    @admin.display(description='Full Name')
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
