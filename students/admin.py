from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('admission_number', 'get_full_name', 'classroom', 'roll_number', 'admission_date')
    list_filter = ('classroom', 'admission_date', 'blood_group')
    search_fields = (
        'admission_number',
        'roll_number',
        'user__username',
        'user__first_name',
        'user__last_name',
        'parent_name',
    )

    @admin.display(description='Full Name')
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
