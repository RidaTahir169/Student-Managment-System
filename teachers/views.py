from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from accounts.decorators import admin_required, teacher_required
from accounts.models import CustomUser
from courses.models import Department, Course, Enrollment
from .models import Teacher
from .forms import (
    TeacherCreateForm,
    TeacherProfileUpdateForm,
    TeacherUserUpdateForm,
    TeacherCourseAssignForm,
)


@login_required
@teacher_required
def teacher_list_view(request):
    """
    Searchable, filterable, and paginated directory of faculty members.
    Accessible to Administrators and Teachers.
    """
    query = request.GET.get('q', '').strip()
    department_id = request.GET.get('department', '').strip()

    teachers = Teacher.objects.select_related('user', 'department').annotate(
        assigned_courses_count=Count('assigned_courses')
    ).order_by('employee_id')

    # Keyword Search (Employee ID, Name, Username, Email, Designation, Qualification, Department)
    if query:
        teachers = teachers.filter(
            Q(employee_id__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query) |
            Q(designation__icontains=query) |
            Q(qualification__icontains=query) |
            Q(department__name__icontains=query) |
            Q(department__code__icontains=query)
        )

    # Filter by Academic Department
    if department_id:
        teachers = teachers.filter(department_id=department_id)

    # Pagination (10 teachers per page)
    paginator = Paginator(teachers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    departments = Department.objects.all()

    context = {
        'page_obj': page_obj,
        'query': query,
        'department_id': department_id,
        'departments': departments,
        'total_count': teachers.count(),
    }
    return render(request, 'teachers/teacher_list.html', context)


@login_required
def teacher_detail_view(request, pk):
    """
    Comprehensive faculty profile view displaying demographic records,
    academic credentials, department affiliation, and assigned course load.
    """
    teacher = get_object_or_404(
        Teacher.objects.select_related('user', 'department'),
        pk=pk
    )

    # Fetch assigned courses with classroom, session, and enrolled student count
    assigned_courses = Course.objects.filter(teacher=teacher).select_related(
        'department', 'classroom', 'session'
    ).annotate(
        enrolled_students_count=Count('enrollments')
    ).order_by('course_code')

    total_courses = assigned_courses.count()
    course_ids = assigned_courses.values_list('id', flat=True)
    total_students_enrolled = Enrollment.objects.filter(
        course_id__in=course_ids,
        status='ACTIVE'
    ).count()

    context = {
        'teacher': teacher,
        'assigned_courses': assigned_courses,
        'total_courses': total_courses,
        'total_students_enrolled': total_students_enrolled,
    }
    return render(request, 'teachers/teacher_detail.html', context)


@admin_required
def teacher_create_view(request):
    """
    Onboard a new faculty member by creating both CustomUser and Teacher profile records.
    """
    if request.method == 'POST':
        form = TeacherCreateForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Create CustomUser instance with TEACHER role
                    raw_password = form.cleaned_data.get('password') or 'Teacher@123'
                    user = CustomUser.objects.create_user(
                        username=form.cleaned_data['username'],
                        email=form.cleaned_data['email'],
                        password=raw_password,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        role=CustomUser.Role.TEACHER,
                        phone_number=form.cleaned_data.get('phone_number'),
                        gender=form.cleaned_data.get('gender') or None,
                        date_of_birth=form.cleaned_data.get('date_of_birth'),
                        address=form.cleaned_data.get('address'),
                        profile_picture=form.cleaned_data.get('profile_picture')
                    )

                    # 2. Create Teacher profile
                    teacher = Teacher.objects.create(
                        user=user,
                        employee_id=form.cleaned_data['employee_id'],
                        department=form.cleaned_data.get('department'),
                        designation=form.cleaned_data.get('designation') or 'Lecturer',
                        qualification=form.cleaned_data.get('qualification', ''),
                        joining_date=form.cleaned_data.get('joining_date') or timezone.now().date(),
                        bio=form.cleaned_data.get('bio', '')
                    )

                messages.success(
                    request,
                    f"Faculty member {teacher.user.get_full_name()} ({teacher.employee_id}) onboarded successfully!"
                )
                return redirect('teachers:teacher_detail', pk=teacher.pk)

            except Exception as e:
                messages.error(request, f"An error occurred while creating teacher: {str(e)}")
        else:
            messages.error(request, "Please correct the form validation errors below.")
    else:
        form = TeacherCreateForm()

    return render(request, 'teachers/teacher_form.html', {
        'form': form,
        'action_title': 'Add New Faculty Member'
    })


@admin_required
def teacher_update_view(request, pk):
    """
    Update faculty appointment details and user account credentials.
    """
    teacher = get_object_or_404(
        Teacher.objects.select_related('user', 'department'),
        pk=pk
    )

    if request.method == 'POST':
        teacher_form = TeacherProfileUpdateForm(request.POST, instance=teacher)
        user_form = TeacherUserUpdateForm(request.POST, request.FILES, instance=teacher.user)

        if teacher_form.is_valid() and user_form.is_valid():
            with transaction.atomic():
                user_form.save()
                teacher_form.save()

            messages.success(request, f"Faculty profile for {teacher.employee_id} updated successfully.")
            return redirect('teachers:teacher_detail', pk=teacher.pk)
        else:
            messages.error(request, "Please correct the errors in the update form.")
    else:
        teacher_form = TeacherProfileUpdateForm(instance=teacher)
        user_form = TeacherUserUpdateForm(instance=teacher.user)

    context = {
        'teacher': teacher,
        'teacher_form': teacher_form,
        'user_form': user_form,
        'is_edit': True,
        'action_title': f'Edit Faculty: {teacher.employee_id}',
    }
    return render(request, 'teachers/teacher_form.html', context)


@admin_required
def teacher_delete_view(request, pk):
    """
    Delete a faculty profile and associated authentication account.
    Any assigned courses are unlinked safely without deleting the course itself.
    """
    teacher = get_object_or_404(
        Teacher.objects.select_related('user'),
        pk=pk
    )

    if request.method == 'POST':
        teacher_name = teacher.user.get_full_name() or teacher.user.username
        emp_id = teacher.employee_id
        user = teacher.user

        with transaction.atomic():
            # Safely unassign all courses assigned to this teacher
            Course.objects.filter(teacher=teacher).update(teacher=None)
            # Deleting CustomUser cascades to Teacher profile
            user.delete()

        messages.success(request, f"Faculty member {teacher_name} ({emp_id}) has been removed.")
        return redirect('teachers:teacher_list')

    return render(request, 'teachers/teacher_confirm_delete.html', {'teacher': teacher})


@admin_required
def teacher_assign_courses_view(request, pk):
    """
    Manage and assign course modules to a specific teacher.
    """
    teacher = get_object_or_404(
        Teacher.objects.select_related('user', 'department'),
        pk=pk
    )

    all_courses = Course.objects.select_related(
        'department', 'classroom', 'session', 'teacher__user'
    ).order_by('course_code')

    if request.method == 'POST':
        form = TeacherCourseAssignForm(request.POST)
        if form.is_valid():
            selected_courses = form.cleaned_data.get('courses', [])
            selected_course_ids = [c.id for c in selected_courses]

            with transaction.atomic():
                # 1. Unassign courses currently assigned to this teacher that were unchecked
                Course.objects.filter(teacher=teacher).exclude(id__in=selected_course_ids).update(teacher=None)

                # 2. Assign selected courses to this teacher
                if selected_course_ids:
                    Course.objects.filter(id__in=selected_course_ids).update(teacher=teacher)

            messages.success(
                request,
                f"Successfully assigned {len(selected_courses)} course(s) to {teacher.user.get_full_name() or teacher.employee_id}."
            )
            return redirect('teachers:teacher_detail', pk=teacher.pk)
        else:
            messages.error(request, "Invalid course selection.")
    else:
        # Pre-select courses currently assigned to this teacher
        currently_assigned = teacher.assigned_courses.all()
        form = TeacherCourseAssignForm(initial={'courses': currently_assigned})

    context = {
        'teacher': teacher,
        'form': form,
        'all_courses': all_courses,
        'currently_assigned_ids': list(teacher.assigned_courses.values_list('id', flat=True)),
    }
    return render(request, 'teachers/teacher_assign_courses.html', context)


@admin_required
def teacher_unassign_course_view(request, teacher_pk, course_pk):
    """
    Quick single-click action to detach a course from a teacher.
    """
    teacher = get_object_or_404(Teacher, pk=teacher_pk)
    course = get_object_or_404(Course, pk=course_pk, teacher=teacher)

    if request.method == 'POST':
        course_code = course.course_code
        course.teacher = None
        course.save()
        messages.success(request, f"Course {course_code} unassigned from {teacher.user.get_full_name() or teacher.employee_id}.")

    return redirect('teachers:teacher_detail', pk=teacher_pk)
