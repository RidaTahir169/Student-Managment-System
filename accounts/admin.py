from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Customer


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin configuration for CustomUser model with role support.
    """
    model = CustomUser
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'is_staff',
        'is_active',
    )
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'gender')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')
    ordering = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        (
            'Additional Profile Info',
            {
                'fields': (
                    'role',
                    'profile_picture',
                    'phone_number',
                    'address',
                    'date_of_birth',
                    'gender',
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            'Additional Profile Info',
            {
                'fields': (
                    'role',
                    'email',
                    'first_name',
                    'last_name',
                    'profile_picture',
                    'phone_number',
                    'address',
                    'date_of_birth',
                    'gender',
                )
            },
        ),
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """
    Admin configuration for Customer model.
    """
    list_display = ('id', 'user', 'phone', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'phone', 'address')
    list_filter = ('created_at', 'updated_at')
    ordering = ('-created_at',)
