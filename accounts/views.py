import uuid
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm
from .models import CustomUser
from students.models import Student
from teachers.models import Teacher


from django.core.exceptions import PermissionDenied


def register_view(request):
    """
    Public registration is disabled.
    Only system administrators can provision new accounts through this endpoint.
    Unauthenticated or unauthorized visitors are blocked and redirected to login.
    """
    if not request.user.is_authenticated:
        messages.error(
            request,
            "Public registration is disabled. Student and faculty accounts are provisioned exclusively by system administrators."
        )
        return redirect('accounts:login')

    if not (request.user.is_superuser or request.user.role == CustomUser.Role.ADMIN):
        messages.error(request, "Access denied. Only administrators have permission to register new user accounts.")
        raise PermissionDenied("Public registration is disabled. Administrator privileges required.")

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Automatically create profile record based on selected role with collision prevention
            if user.role == CustomUser.Role.STUDENT:
                base_adm = f"STU-{user.id:04d}"
                adm = base_adm
                counter = 1
                while Student.objects.filter(admission_number=adm).exists():
                    adm = f"{base_adm}-{counter}"
                    counter += 1
                Student.objects.get_or_create(
                    user=user,
                    defaults={'admission_number': adm}
                )
            elif user.role == CustomUser.Role.TEACHER:
                base_emp = f"FAC-{user.id:04d}"
                emp = base_emp
                counter = 1
                while Teacher.objects.filter(employee_id=emp).exists():
                    emp = f"{base_emp}-{counter}"
                    counter += 1
                Teacher.objects.get_or_create(
                    user=user,
                    defaults={'employee_id': emp}
                )

            messages.success(request, f"Account successfully created for {user.username}!")
            return redirect('dashboard:admin_dashboard')

        else:
            messages.error(request, "Please correct the errors below to complete registration.")
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """
    Authenticates users and performs dynamic role-based redirection.
    """
    if request.user.is_authenticated:
        return redirect('accounts:role_redirect')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")

            # Check next parameter for redirect
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)

            # Role-based redirection
            return redirect('accounts:role_redirect')
        else:
            messages.error(request, "Invalid credentials. Please check your username/email and password.")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """
    Terminates user session and redirects to login.
    """
    if request.user.is_authenticated:
        username = request.user.username
        auth_logout(request)
        messages.info(request, f"Goodbye, {username}. You have been logged out.")
    return redirect('accounts:login')


@login_required
def role_redirect_view(request):
    """
    Dispatches logged-in users to their respective role dashboards.
    """
    user = request.user
    if user.is_superuser or user.role == CustomUser.Role.ADMIN:
        return redirect('dashboard:admin_dashboard')
    elif user.role == CustomUser.Role.TEACHER:
        return redirect('dashboard:teacher_dashboard')
    elif user.role == CustomUser.Role.STUDENT:
        return redirect('dashboard:student_dashboard')
    return redirect('accounts:profile')


@login_required
def profile_view(request):
    """
    Displays and allows editing of personal profile details.
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please fix the errors below to update your profile.")
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


def permission_denied_view(request, exception=None):
    """
    Custom 403 Forbidden handler: renders user-friendly 403 error page.
    """
    return render(request, '403.html', status=403)


def page_not_found_view(request, exception=None):
    """
    Custom 404 Not Found handler: renders user-friendly 404 error page.
    """
    return render(request, '404.html', status=404)


def server_error_view(request):
    """
    Custom 500 Internal Server Error handler: renders user-friendly 500 error page.
    """
    return render(request, '500.html', status=500)

