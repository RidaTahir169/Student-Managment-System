from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from accounts.decorators import admin_required, teacher_required
from accounts.models import CustomUser
from courses.models import ClassRoom, Enrollment, Course
from attendance.models import Attendance
from academics.models import AcademicRecord
from .models import Student
from .forms import StudentCreateForm, StudentProfileUpdateForm, StudentUserUpdateForm


@login_required
@teacher_required
def student_list_view(request):
    """
    Searchable, filterable, and paginated directory of students.
    Accessible to Administrators and Teachers.
    """
    query = request.GET.get('q', '').strip()
    classroom_id = request.GET.get('classroom', '').strip()

    students = Student.objects.select_related('user', 'classroom').order_by('admission_number')

    # Keyword Search (Admission #, Name, Username, Email, Roll #)
    if query:
        students = students.filter(
            Q(admission_number__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query) |
            Q(roll_number__icontains=query)
        )

    # Filter by Assigned Class Room
    if classroom_id:
        students = students.filter(classroom_id=classroom_id)

    # Pagination (10 students per page)
    paginator = Paginator(students, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    classrooms = ClassRoom.objects.all()

    context = {
        'page_obj': page_obj,
        'query': query,
        'classroom_id': classroom_id,
        'classrooms': classrooms,
        'total_count': students.count(),
    }
    return render(request, 'students/student_list.html', context)


@login_required
def student_detail_view(request, pk):
    """
    Comprehensive student profile view displaying demographic records,
    active course enrollments, attendance history, and exam results.
    """
    student = get_object_or_404(
        Student.objects.select_related('user', 'classroom'),
        pk=pk
    )

    # Access control: Admins and Teachers can view any student.
    # Students can only view their own profile.
    if request.user.role == CustomUser.Role.STUDENT:
        if not hasattr(request.user, 'student_profile') or request.user.student_profile.pk != student.pk:
            raise PermissionDenied("You are not authorized to view this student profile.")

    enrollments = Enrollment.objects.filter(student=student).select_related('course', 'course__teacher__user')
    academic_records = AcademicRecord.objects.filter(student=student).select_related('course').order_by('-date_recorded')
    
    total_attendance = Attendance.objects.filter(student=student).count()
    present_attendance = Attendance.objects.filter(student=student, status=Attendance.Status.PRESENT).count()
    attendance_rate = round((present_attendance / total_attendance) * 100, 1) if total_attendance > 0 else 0.0

    context = {
        'student': student,
        'enrollments': enrollments,
        'academic_records': academic_records,
        'total_attendance': total_attendance,
        'present_attendance': present_attendance,
        'attendance_rate': attendance_rate,
    }
    return render(request, 'students/student_detail.html', context)


@admin_required
def student_create_view(request):
    """
    Admit a new student by creating both CustomUser and Student profile records.
    """
    if request.method == 'POST':
        form = StudentCreateForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Create CustomUser instance
                    raw_password = form.cleaned_data.get('password') or 'Student@123'
                    user = CustomUser.objects.create_user(
                        username=form.cleaned_data['username'],
                        email=form.cleaned_data['email'],
                        password=raw_password,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        role=CustomUser.Role.STUDENT,
                        phone_number=form.cleaned_data.get('phone_number'),
                        gender=form.cleaned_data.get('gender') or None,
                        date_of_birth=form.cleaned_data.get('date_of_birth'),
                        address=form.cleaned_data.get('address'),
                        profile_picture=form.cleaned_data.get('profile_picture')
                    )

                    # 2. Create Student profile
                    student = Student.objects.create(
                        user=user,
                        admission_number=form.cleaned_data['admission_number'],
                        classroom=form.cleaned_data.get('classroom'),
                        roll_number=form.cleaned_data.get('roll_number', ''),
                        parent_name=form.cleaned_data.get('parent_name', ''),
                        parent_phone=form.cleaned_data.get('parent_phone', ''),
                        emergency_contact=form.cleaned_data.get('emergency_contact', ''),
                        blood_group=form.cleaned_data.get('blood_group', ''),
                        admission_date=form.cleaned_data.get('admission_date') or timezone.now().date()
                    )

                messages.success(request, f"Student {student.user.get_full_name()} ({student.admission_number}) admitted successfully!")
                return redirect('students:student_detail', pk=student.pk)

            except Exception as e:
                messages.error(request, f"An error occurred while creating student: {str(e)}")
        else:
            messages.error(request, "Please correct the form validation errors below.")
    else:
        form = StudentCreateForm()

    return render(request, 'students/student_form.html', {'form': form, 'action_title': 'Admit New Student'})


@admin_required
def student_update_view(request, pk):
    """
    Update student academic records and user account details.
    """
    student = get_object_or_404(
        Student.objects.select_related('user', 'classroom'),
        pk=pk
    )

    if request.method == 'POST':
        student_form = StudentProfileUpdateForm(request.POST, instance=student)
        user_form = StudentUserUpdateForm(request.POST, request.FILES, instance=student.user)

        if student_form.is_valid() and user_form.is_valid():
            with transaction.atomic():
                user_form.save()
                student_form.save()

            messages.success(request, f"Student record for {student.admission_number} updated successfully.")
            return redirect('students:student_detail', pk=student.pk)
        else:
            messages.error(request, "Please correct the errors in the update form.")
    else:
        student_form = StudentProfileUpdateForm(instance=student)
        user_form = StudentUserUpdateForm(instance=student.user)

    context = {
        'student': student,
        'student_form': student_form,
        'user_form': user_form,
        'is_edit': True,
        'action_title': f'Edit Student: {student.admission_number}',
    }
    return render(request, 'students/student_form.html', context)


@admin_required
def student_delete_view(request, pk):
    """
    Delete a student profile and their associated authentication account.
    """
    student = get_object_or_404(
        Student.objects.select_related('user'),
        pk=pk
    )

    if request.method == 'POST':
        student_name = student.user.get_full_name() or student.user.username
        adm_no = student.admission_number
        user = student.user
        
        with transaction.atomic():
            # Deleting CustomUser cascades to Student profile
            user.delete()

        messages.success(request, f"Student {student_name} ({adm_no}) has been permanently deleted.")
        return redirect('students:student_list')

    return render(request, 'students/student_confirm_delete.html', {'student': student})


@admin_required
def student_enroll_courses_view(request, pk):
    """
    Manage and assign course enrollments for a specific student.
    """
    student = get_object_or_404(
        Student.objects.select_related('user', 'classroom'),
        pk=pk
    )

    all_courses = Course.objects.select_related(
        'department', 'classroom', 'session', 'teacher__user'
    ).order_by('course_code')

    currently_enrolled_ids = list(student.enrollments.values_list('course_id', flat=True))

    if request.method == 'POST':
        selected_course_ids = request.POST.getlist('courses')
        selected_course_ids = [int(cid) for cid in selected_course_ids if cid.isdigit()]

        with transaction.atomic():
            # 1. Remove enrollments that were unselected
            Enrollment.objects.filter(student=student).exclude(course_id__in=selected_course_ids).delete()

            # 2. Add or keep selected course enrollments
            for cid in selected_course_ids:
                Enrollment.objects.get_or_create(
                    student=student,
                    course_id=cid,
                    defaults={'status': Enrollment.EnrollmentStatus.ACTIVE}
                )

        messages.success(
            request,
            f"Successfully updated course enrollments for {student.user.get_full_name() or student.admission_number} ({len(selected_course_ids)} courses active)."
        )
        return redirect('students:student_detail', pk=student.pk)

    context = {
        'student': student,
        'all_courses': all_courses,
        'currently_enrolled_ids': currently_enrolled_ids,
    }
    return render(request, 'students/student_enroll_courses.html', context)

