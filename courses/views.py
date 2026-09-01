from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from accounts.decorators import admin_required, teacher_required
from accounts.models import CustomUser
from teachers.models import Teacher
from students.models import Student
from .models import Course, ClassRoom, Department, AcademicSession, Enrollment
from .forms import (
    CourseForm,
    ClassRoomForm,
    ClassRoomAssignStudentsForm,
    CourseEnrollStudentsForm,
    EnrollmentCreateForm,
    EnrollmentUpdateForm,
)


# ==============================================================================
# COURSE MANAGEMENT VIEWS
# ==============================================================================

@login_required
def course_list_view(request):
    """
    Searchable, filterable, and paginated directory of academic courses.
    Accessible to Administrators, Teachers, and Students.
    """
    query = request.GET.get('q', '').strip()
    department_id = request.GET.get('department', '').strip()
    classroom_id = request.GET.get('classroom', '').strip()
    session_id = request.GET.get('session', '').strip()

    courses = Course.objects.select_related(
        'department', 'teacher__user', 'classroom', 'session'
    ).annotate(
        enrolled_students_count=Count('enrollments')
    ).order_by('course_code')

    # Keyword Search (Course Code, Title, Teacher Name, Employee ID, Department)
    if query:
        courses = courses.filter(
            Q(course_code__icontains=query) |
            Q(title__icontains=query) |
            Q(teacher__user__first_name__icontains=query) |
            Q(teacher__user__last_name__icontains=query) |
            Q(teacher__user__username__icontains=query) |
            Q(teacher__employee_id__icontains=query) |
            Q(department__name__icontains=query) |
            Q(department__code__icontains=query)
        )

    # Filters
    if department_id:
        courses = courses.filter(department_id=department_id)
    if classroom_id:
        courses = courses.filter(classroom_id=classroom_id)
    if session_id:
        courses = courses.filter(session_id=session_id)

    # Pagination (10 courses per page)
    paginator = Paginator(courses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    departments = Department.objects.all()
    classrooms = ClassRoom.objects.all()
    sessions = AcademicSession.objects.all()

    context = {
        'page_obj': page_obj,
        'query': query,
        'department_id': department_id,
        'classroom_id': classroom_id,
        'session_id': session_id,
        'departments': departments,
        'classrooms': classrooms,
        'sessions': sessions,
        'total_count': courses.count(),
    }
    return render(request, 'courses/course_list.html', context)


@login_required
def course_detail_view(request, pk):
    """
    Comprehensive course details view displaying syllabus info, assigned teacher,
    target classroom, and all enrolled students with status badges and actions.
    """
    course = get_object_or_404(
        Course.objects.select_related('department', 'teacher__user', 'classroom', 'session'),
        pk=pk
    )

    enrollments = Enrollment.objects.filter(course=course).select_related(
        'student__user', 'student__classroom'
    ).order_by('student__admission_number')

    total_enrolled = enrollments.count()
    active_enrolled = enrollments.filter(status=Enrollment.EnrollmentStatus.ACTIVE).count()
    dropped_enrolled = enrollments.filter(status=Enrollment.EnrollmentStatus.DROPPED).count()
    completed_enrolled = enrollments.filter(status=Enrollment.EnrollmentStatus.COMPLETED).count()

    context = {
        'course': course,
        'enrollments': enrollments,
        'total_enrolled': total_enrolled,
        'active_enrolled': active_enrolled,
        'dropped_enrolled': dropped_enrolled,
        'completed_enrolled': completed_enrolled,
    }
    return render(request, 'courses/course_detail.html', context)


@admin_required
def course_create_view(request):
    """
    Create a new course module and assign department, teacher, and classroom.
    """
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, f"Course '{course.course_code} - {course.title}' created successfully!")
            return redirect('courses:course_detail', pk=course.pk)
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        form = CourseForm()

    return render(request, 'courses/course_form.html', {
        'form': form,
        'action_title': 'Create New Course'
    })


@admin_required
def course_update_view(request, pk):
    """
    Update course details, instructor allocation, or classroom target.
    """
    course = get_object_or_404(Course, pk=pk)

    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            updated_course = form.save()
            messages.success(request, f"Course '{updated_course.course_code}' updated successfully!")
            return redirect('courses:course_detail', pk=updated_course.pk)
        else:
            messages.error(request, "Please correct the errors in the update form.")
    else:
        form = CourseForm(instance=course)

    context = {
        'form': form,
        'course': course,
        'is_edit': True,
        'action_title': f'Edit Course: {course.course_code}',
    }
    return render(request, 'courses/course_form.html', context)


@admin_required
def course_delete_view(request, pk):
    """
    Delete a course and its associated enrollments.
    """
    course = get_object_or_404(Course, pk=pk)

    if request.method == 'POST':
        code = course.course_code
        title = course.title
        course.delete()
        messages.success(request, f"Course '{code} - {title}' has been deleted.")
        return redirect('courses:course_list')

    return render(request, 'courses/course_confirm_delete.html', {'course': course})


@admin_required
def course_enroll_students_view(request, pk):
    """
    Enroll students into a course module. Supports bulk selection or one-click enrollment
    of all students in the assigned Class Room with duplicate protection.
    """
    course = get_object_or_404(
        Course.objects.select_related('department', 'classroom', 'session', 'teacher__user'),
        pk=pk
    )

    all_students = Student.objects.select_related('user', 'classroom').order_by('admission_number')
    currently_enrolled_ids = list(course.enrollments.values_list('student_id', flat=True))

    if request.method == 'POST':
        action = request.POST.get('action')

        # One-click auto enroll all students of the assigned classroom
        if action == 'enroll_classroom' and course.classroom:
            classroom_students = Student.objects.filter(classroom=course.classroom)
            added_count = 0
            with transaction.atomic():
                for student in classroom_students:
                    _, created = Enrollment.objects.get_or_create(
                        student=student,
                        course=course,
                        defaults={'status': Enrollment.EnrollmentStatus.ACTIVE}
                    )
                    if created:
                        added_count += 1
            messages.success(
                request,
                f"Enrolled {added_count} student(s) from class '{course.classroom}' into {course.course_code}."
            )
            return redirect('courses:course_detail', pk=course.pk)

        # Standard checkbox form submission
        form = CourseEnrollStudentsForm(request.POST)
        if form.is_valid():
            selected_students = form.cleaned_data.get('students', [])
            selected_student_ids = [s.id for s in selected_students]

            with transaction.atomic():
                # 1. Remove enrollments that were unselected
                Enrollment.objects.filter(course=course).exclude(student_id__in=selected_student_ids).delete()

                # 2. Add newly selected students without duplicating
                for student in selected_students:
                    Enrollment.objects.get_or_create(
                        student=student,
                        course=course,
                        defaults={'status': Enrollment.EnrollmentStatus.ACTIVE}
                    )

            messages.success(
                request,
                f"Successfully updated enrollment roster for {course.course_code} ({len(selected_students)} total enrolled)."
            )
            return redirect('courses:course_detail', pk=course.pk)
        else:
            messages.error(request, "Invalid student enrollment selection.")
    else:
        currently_enrolled_students = Student.objects.filter(id__in=currently_enrolled_ids)
        form = CourseEnrollStudentsForm(initial={'students': currently_enrolled_students})

    context = {
        'course': course,
        'form': form,
        'all_students': all_students,
        'currently_enrolled_ids': currently_enrolled_ids,
    }
    return render(request, 'courses/course_enroll_students.html', context)


@admin_required
def course_unenroll_student_view(request, course_pk, student_pk):
    """
    Remove a single student from a course enrollment.
    """
    course = get_object_or_404(Course, pk=course_pk)
    enrollment = get_object_or_404(Enrollment, course=course, student_id=student_pk)

    if request.method == 'POST':
        student_name = enrollment.student.user.get_full_name() or enrollment.student.admission_number
        enrollment.delete()
        messages.success(request, f"Student {student_name} removed from {course.course_code}.")

    return redirect('courses:course_detail', pk=course_pk)


# ==============================================================================
# CLASS ROOM MANAGEMENT VIEWS
# ==============================================================================

@login_required
@teacher_required
def classroom_list_view(request):
    """
    Searchable, filterable directory of class rooms and grade sections.
    """
    query = request.GET.get('q', '').strip()
    department_id = request.GET.get('department', '').strip()

    classrooms = ClassRoom.objects.select_related('department').annotate(
        student_count=Count('students', distinct=True),
        course_count=Count('courses', distinct=True)
    ).order_by('name', 'section')

    if query:
        classrooms = classrooms.filter(
            Q(name__icontains=query) |
            Q(section__icontains=query) |
            Q(department__name__icontains=query) |
            Q(department__code__icontains=query)
        )

    if department_id:
        classrooms = classrooms.filter(department_id=department_id)

    paginator = Paginator(classrooms, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    departments = Department.objects.all()

    context = {
        'page_obj': page_obj,
        'query': query,
        'department_id': department_id,
        'departments': departments,
        'total_count': classrooms.count(),
    }
    return render(request, 'courses/classroom_list.html', context)


@login_required
@teacher_required
def classroom_detail_view(request, pk):

    """
    Class room details view displaying assigned student roster and associated course curriculum.
    """
    classroom = get_object_or_404(
        ClassRoom.objects.select_related('department'),
        pk=pk
    )

    students = classroom.students.select_related('user').order_by('admission_number')
    courses = classroom.courses.select_related(
        'department', 'teacher__user', 'session'
    ).annotate(
        student_count=Count('enrollments')
    ).order_by('course_code')

    context = {
        'classroom': classroom,
        'students': students,
        'courses': courses,
        'total_students': students.count(),
        'total_courses': courses.count(),
    }
    return render(request, 'courses/classroom_detail.html', context)


@admin_required
def classroom_create_view(request):
    """
    Create a new class room or grade section.
    """
    if request.method == 'POST':
        form = ClassRoomForm(request.POST)
        if form.is_valid():
            classroom = form.save()
            messages.success(request, f"Class Room '{classroom.name} - {classroom.section}' created successfully!")
            return redirect('courses:classroom_detail', pk=classroom.pk)
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        form = ClassRoomForm()

    return render(request, 'courses/classroom_form.html', {
        'form': form,
        'action_title': 'Create New Class Room'
    })


@admin_required
def classroom_update_view(request, pk):
    """
    Update class room details.
    """
    classroom = get_object_or_404(ClassRoom, pk=pk)

    if request.method == 'POST':
        form = ClassRoomForm(request.POST, instance=classroom)
        if form.is_valid():
            updated_classroom = form.save()
            messages.success(request, f"Class Room '{updated_classroom}' updated successfully!")
            return redirect('courses:classroom_detail', pk=updated_classroom.pk)
        else:
            messages.error(request, "Please correct the errors in the update form.")
    else:
        form = ClassRoomForm(instance=classroom)

    context = {
        'form': form,
        'classroom': classroom,
        'is_edit': True,
        'action_title': f'Edit Class Room: {classroom}',
    }
    return render(request, 'courses/classroom_form.html', context)


@admin_required
def classroom_delete_view(request, pk):
    """
    Delete a class room. Any students assigned to this class room will have classroom set to NULL safely.
    """
    classroom = get_object_or_404(ClassRoom, pk=pk)

    if request.method == 'POST':
        name = str(classroom)
        classroom.delete()
        messages.success(request, f"Class Room '{name}' has been deleted.")
        return redirect('courses:classroom_list')

    return render(request, 'courses/classroom_confirm_delete.html', {'classroom': classroom})


@admin_required
def classroom_assign_students_view(request, pk):
    """
    Assign or transfer students into this specific Class Room cohort.
    """
    classroom = get_object_or_404(
        ClassRoom.objects.select_related('department'),
        pk=pk
    )

    all_students = Student.objects.select_related('user', 'classroom').order_by('admission_number')
    currently_assigned_ids = list(classroom.students.values_list('id', flat=True))

    if request.method == 'POST':
        form = ClassRoomAssignStudentsForm(request.POST)
        if form.is_valid():
            selected_students = form.cleaned_data.get('students', [])
            selected_student_ids = [s.id for s in selected_students]

            with transaction.atomic():
                # 1. Unassign students that were previously in this class but were unchecked
                Student.objects.filter(classroom=classroom).exclude(id__in=selected_student_ids).update(classroom=None)

                # 2. Assign selected students to this class room
                if selected_student_ids:
                    Student.objects.filter(id__in=selected_student_ids).update(classroom=classroom)

            messages.success(
                request,
                f"Successfully assigned {len(selected_students)} student(s) to '{classroom}'."
            )
            return redirect('courses:classroom_detail', pk=classroom.pk)
        else:
            messages.error(request, "Invalid student assignment selection.")
    else:
        currently_assigned_students = Student.objects.filter(id__in=currently_assigned_ids)
        form = ClassRoomAssignStudentsForm(initial={'students': currently_assigned_students})

    context = {
        'classroom': classroom,
        'form': form,
        'all_students': all_students,
        'currently_assigned_ids': currently_assigned_ids,
    }
    return render(request, 'courses/classroom_assign_students.html', context)


# ==============================================================================
# ENROLLMENT MANAGEMENT VIEWS (PHASE 10)
# ==============================================================================

@login_required
@teacher_required
def enrollment_list_view(request):
    """
    Comprehensive directory of all student course enrollments across the institution.
    Searchable and filterable by course, student, classroom, department, and status.
    """
    query = request.GET.get('q', '').strip()
    course_id = request.GET.get('course', '').strip()
    status = request.GET.get('status', '').strip()
    classroom_id = request.GET.get('classroom', '').strip()
    department_id = request.GET.get('department', '').strip()

    enrollments = Enrollment.objects.select_related(
        'student__user',
        'student__classroom',
        'course__department',
        'course__teacher__user',
        'course__classroom',
        'course__session'
    ).order_by('-enrollment_date', 'student__admission_number')

    # Search keyword
    if query:
        enrollments = enrollments.filter(
            Q(student__admission_number__icontains=query) |
            Q(student__user__first_name__icontains=query) |
            Q(student__user__last_name__icontains=query) |
            Q(student__user__username__icontains=query) |
            Q(student__user__email__icontains=query) |
            Q(course__course_code__icontains=query) |
            Q(course__title__icontains=query)
        )

    # Filters
    if course_id:
        enrollments = enrollments.filter(course_id=course_id)
    if status:
        enrollments = enrollments.filter(status=status)
    if classroom_id:
        enrollments = enrollments.filter(student__classroom_id=classroom_id)
    if department_id:
        enrollments = enrollments.filter(course__department_id=department_id)

    # Role-based restriction: Teachers manage only assigned courses
    user = request.user
    if user.role == CustomUser.Role.TEACHER and hasattr(user, 'teacher_profile'):
        enrollments = enrollments.filter(course__teacher=user.teacher_profile)
        courses = Course.objects.filter(teacher=user.teacher_profile).order_by('course_code')
    else:
        courses = Course.objects.all().order_by('course_code')

    paginator = Paginator(enrollments, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    classrooms = ClassRoom.objects.all().order_by('name', 'section')
    departments = Department.objects.all().order_by('name')

    context = {
        'page_obj': page_obj,
        'query': query,
        'course_id': course_id,
        'status': status,
        'classroom_id': classroom_id,
        'department_id': department_id,
        'courses': courses,
        'classrooms': classrooms,
        'departments': departments,
        'status_choices': Enrollment.EnrollmentStatus.choices,
        'total_count': enrollments.count(),
    }
    return render(request, 'courses/enrollment_list.html', context)



@admin_required
def enrollment_create_view(request):
    """
    Enroll a single student into a specific course with duplicate prevention.
    """
    initial_data = {}
    student_id = request.GET.get('student')
    course_id = request.GET.get('course')
    if student_id:
        initial_data['student'] = student_id
    if course_id:
        initial_data['course'] = course_id

    if request.method == 'POST':
        form = EnrollmentCreateForm(request.POST)
        if form.is_valid():
            enrollment = form.save()
            messages.success(
                request,
                f"Successfully enrolled {enrollment.student.user.get_full_name() or enrollment.student.admission_number} in {enrollment.course.course_code}."
            )
            return redirect('courses:enrollment_list')
        else:
            messages.error(request, "Please correct the enrollment errors below.")
    else:
        form = EnrollmentCreateForm(initial=initial_data)

    return render(request, 'courses/enrollment_form.html', {
        'form': form,
        'action_title': 'Enroll Student in Course',
        'is_edit': False,
    })


@admin_required
def enrollment_update_view(request, pk):
    """
    Update enrollment status (Active, Dropped, Completed) or enrollment date.
    """
    enrollment = get_object_or_404(
        Enrollment.objects.select_related('student__user', 'course'),
        pk=pk
    )

    if request.method == 'POST':
        form = EnrollmentUpdateForm(request.POST, instance=enrollment)
        if form.is_valid():
            updated = form.save()
            messages.success(
                request,
                f"Enrollment status for {updated.student.admission_number} in {updated.course.course_code} updated to {updated.get_status_display()}."
            )
            return redirect('courses:enrollment_list')
        else:
            messages.error(request, "Please correct the form errors.")
    else:
        form = EnrollmentUpdateForm(instance=enrollment)

    context = {
        'form': form,
        'enrollment': enrollment,
        'action_title': f'Update Enrollment: {enrollment.student.admission_number} - {enrollment.course.course_code}',
        'is_edit': True,
    }
    return render(request, 'courses/enrollment_form.html', context)


@admin_required
def enrollment_delete_view(request, pk):
    """
    Permanently delete or drop an enrollment record.
    """
    enrollment = get_object_or_404(
        Enrollment.objects.select_related('student__user', 'course'),
        pk=pk
    )

    if request.method == 'POST':
        student_name = enrollment.student.user.get_full_name() or enrollment.student.admission_number
        course_code = enrollment.course.course_code
        enrollment.delete()
        messages.success(request, f"Enrollment of {student_name} in {course_code} has been removed.")
        return redirect('courses:enrollment_list')

    return render(request, 'courses/enrollment_confirm_delete.html', {'enrollment': enrollment})
