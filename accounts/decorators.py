from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def role_required(allowed_roles=None):
    """
    Decorator for views that checks whether the logged-in user has one of the allowed roles.
    Superusers bypass role checks and always have full administrative access.
    """
    if allowed_roles is None:
        allowed_roles = []

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Please log in to access this page.")
                return redirect('accounts:login')

            if request.user.is_superuser or request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, "Access denied: You do not have permission to view this page.")
            raise PermissionDenied

        return _wrapped_view
    return decorator


def admin_required(view_func):
    """
    Restricts access strictly to Administrators and Superusers.
    """
    return role_required(['ADMIN'])(view_func)


def teacher_required(view_func):
    """
    Restricts access to Teachers and Administrators.
    """
    return role_required(['TEACHER', 'ADMIN'])(view_func)


def student_required(view_func):
    """
    Restricts access to Students and Administrators.
    """
    return role_required(['STUDENT', 'ADMIN'])(view_func)
