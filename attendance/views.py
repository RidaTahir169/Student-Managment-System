from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count, Case, When, IntegerField
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from accounts.decorators import admin_required, teacher_required, student_required
from accounts.models import CustomUser
from courses.models import Course, Enrollment, ClassRoom
from students.models import Student
from .models import Attendance
from .forms import CourseDateSelectionForm, AttendanceFilterForm, AttendanceSingleUpdateForm


@login_required
def attendance_dashboard_view(request):
    """
    Overview hub for attendance management.
    Displays quick KPI metrics, links to mark attendance, and recent activity.
    """
    user = request.user

    if user.role == CustomUser.Role.STUDENT:
        if hasattr(user, 'student_profile'):
            return redirect('attendance:student_attendance', student_pk=user.student_profile.pk)
        messages.error(request, "Student profile not found.")
        return redirect('dashboard:student_dashboard')

    # For Teachers: filter to their courses
    if user.role == CustomUser.Role.TEACHER and hasattr(user, 'teacher_profile'):
        teacher_courses = Course.objects.filter(teacher=user.teacher_profile).select_related('department', 'classroom')
        course_ids = teacher_courses.values_list('id', flat=True)
        recent_records = Attendance.objects.filter(course_id__in=course_ids).select_related(
            'student__user', 'course'
        ).order_by('-date', '-id')[:10]
        total_records = Attendance.objects.filter(course_id__in=course_ids).count()
        present_count = Attendance.objects.filter(course_id__in=course_ids, status=Attendance.Status.PRESENT).count()
        absent_count = Attendance.objects.filter(course_id__in=course_ids, status=Attendance.Status.ABSENT).count()
        late_count = Attendance.objects.filter(course_id__in=course_ids, status=Attendance.Status.LATE).count()
        excused_count = Attendance.objects.filter(course_id__in=course_ids, status=Attendance.Status.EXCUSED).count()
    else:
        # Admin view: all courses
        teacher_courses = Course.objects.select_related('department', 'teacher__user', 'classroom').all()
        recent_records = Attendance.objects.select_related(
            'student__user', 'course'
        ).order_by('-date', '-id')[:10]
        total_records = Attendance.objects.count()
        present_count = Attendance.objects.filter(status=Attendance.Status.PRESENT).count()
        absent_count = Attendance.objects.filter(status=Attendance.Status.ABSENT).count()
        late_count = Attendance.objects.filter(status=Attendance.Status.LATE).count()
        excused_count = Attendance.objects.filter(status=Attendance.Status.EXCUSED).count()

    overall_rate = round((present_count / total_records) * 100, 1) if total_records > 0 else 0.0

    context = {
        'teacher_courses': teacher_courses,
        'recent_records': recent_records,
        'total_records': total_records,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'excused_count': excused_count,
        'overall_rate': overall_rate,
    }
    return render(request, 'attendance/attendance_dashboard.html', context)


@login_required
@teacher_required
def mark_attendance_view(request):
    """
    Primary attendance marking view.
    Teacher/Admin selects a course and date, views all enrolled students,
    and marks attendance statuses (Present, Absent, Late, Excused) with duplicate prevention.
    """
    user = request.user
    selected_course_id = request.GET.get('course') or request.POST.get('course')
    selected_date_str = request.GET.get('date') or request.POST.get('date')

    # Parse date (defaults to today)
    if selected_date_str:
        try:
            selected_date = timezone.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    # Form to select course & date
    selection_form = CourseDateSelectionForm(
        user=user,
        initial={'course': selected_course_id, 'date': selected_date}
    )

    selected_course = None
    enrolled_students = []
    attendance_dict = {}

    if selected_course_id:
        # Validate course permission
        if user.is_superuser or user.role == CustomUser.Role.ADMIN:
            selected_course = get_object_or_404(
                Course.objects.select_related('department', 'classroom', 'teacher__user'),
                pk=selected_course_id
            )
        else:
            selected_course = get_object_or_404(
                Course.objects.select_related('department', 'classroom', 'teacher__user'),
                pk=selected_course_id,
                teacher=user.teacher_profile
            )

        # Get active enrolled students
        enrollments = Enrollment.objects.filter(
            course=selected_course,
            status=Enrollment.EnrollmentStatus.ACTIVE
        ).select_related('student__user', 'student__classroom').order_by('student__admission_number')

        enrolled_students = [e.student for e in enrollments]

        # Fetch any existing attendance records for this (course, date) pair
        existing_records = Attendance.objects.filter(
            course=selected_course,
            date=selected_date
        )
        attendance_dict = {rec.student_id: rec for rec in existing_records}

    # Handle POST Submission to Save/Update Attendance
    if request.method == 'POST' and 'save_attendance' in request.POST:
        if not selected_course:
            messages.error(request, "Please select a valid course first.")
            return redirect('attendance:mark_attendance')

        saved_count = 0
        with transaction.atomic():
            for student in enrolled_students:
                status_field = f"status_{student.id}"
                remarks_field = f"remarks_{student.id}"

                status_val = request.POST.get(status_field, Attendance.Status.PRESENT)
                remarks_val = request.POST.get(remarks_field, '').strip()

                # Validate status value against choices
                if status_val not in dict(Attendance.Status.choices):
                    status_val = Attendance.Status.PRESENT

                # Update or create attendance entry (prevents duplicates for same student, course, date)
                Attendance.objects.update_or_create(
                    student=student,
                    course=selected_course,
                    date=selected_date,
                    defaults={
                        'status': status_val,
                        'remarks': remarks_val or None,
                    }
                )
                saved_count += 1

        formatted_date = selected_date.strftime('%b %d, %Y')
        messages.success(
            request,
            f"Attendance for {saved_count} student(s) in '{selected_course.course_code}' on {formatted_date} saved successfully!"
        )
        return redirect(f"{request.path}?course={selected_course.id}&date={selected_date.strftime('%Y-%m-%d')}")

    context = {
        'selection_form': selection_form,
        'selected_course': selected_course,
        'selected_date': selected_date,
        'enrolled_students': enrolled_students,
        'attendance_dict': attendance_dict,
        'status_choices': Attendance.Status.choices,
        'has_existing_records': bool(attendance_dict),
    }
    return render(request, 'attendance/mark_attendance.html', context)


@login_required
@teacher_required
def mark_course_attendance_view(request, course_pk):
    """
    Shortcut view allowing teacher to jump directly to attendance marking for a specific course.
    """
    user = request.user
    if user.role == CustomUser.Role.TEACHER and hasattr(user, 'teacher_profile'):
        get_object_or_404(Course, pk=course_pk, teacher=user.teacher_profile)
    else:
        get_object_or_404(Course, pk=course_pk)
    today_str = timezone.now().date().strftime('%Y-%m-%d')
    return redirect(f"/attendance/mark/?course={course_pk}&date={today_str}")



@login_required
@teacher_required
def attendance_history_view(request):
    """
    Searchable, filterable, and paginated directory of past attendance logs.
    """
    user = request.user
    query = request.GET.get('q', '').strip()
    course_id = request.GET.get('course', '').strip()
    status = request.GET.get('status', '').strip()
    classroom_id = request.GET.get('classroom', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    records = Attendance.objects.select_related(
        'student__user',
        'student__classroom',
        'course__department',
        'course__teacher__user'
    ).order_by('-date', 'course__course_code', 'student__admission_number')

    # Restrict teachers to their own courses
    if user.role == CustomUser.Role.TEACHER and hasattr(user, 'teacher_profile'):
        records = records.filter(course__teacher=user.teacher_profile)
        available_courses = Course.objects.filter(teacher=user.teacher_profile).order_by('course_code')
    else:
        available_courses = Course.objects.all().order_by('course_code')

    # Keyword Search (Student Name, Admission #, Username)
    if query:
        records = records.filter(
            Q(student__admission_number__icontains=query) |
            Q(student__user__first_name__icontains=query) |
            Q(student__user__last_name__icontains=query) |
            Q(student__user__username__icontains=query) |
            Q(course__course_code__icontains=query) |
            Q(course__title__icontains=query)
        )

    # Filters
    if course_id:
        records = records.filter(course_id=course_id)
    if status:
        records = records.filter(status=status)
    if classroom_id:
        records = records.filter(student__classroom_id=classroom_id)
    if start_date:
        records = records.filter(date__gte=start_date)
    if end_date:
        records = records.filter(date__lte=end_date)

    paginator = Paginator(records, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    classrooms = ClassRoom.objects.all().order_by('name', 'section')

    context = {
        'page_obj': page_obj,
        'query': query,
        'course_id': course_id,
        'status': status,
        'classroom_id': classroom_id,
        'start_date': start_date,
        'end_date': end_date,
        'available_courses': available_courses,
        'classrooms': classrooms,
        'status_choices': Attendance.Status.choices,
        'total_count': records.count(),
    }
    return render(request, 'attendance/attendance_history.html', context)


@login_required
@teacher_required
def attendance_report_view(request):
    """
    Overview page for attendance reports and course-level summaries.
    """
    user = request.user

    if user.role == CustomUser.Role.TEACHER and hasattr(user, 'teacher_profile'):
        courses = Course.objects.filter(teacher=user.teacher_profile).select_related('department', 'classroom')
    else:
        courses = Course.objects.select_related('department', 'teacher__user', 'classroom').all()

    # Aggregate attendance stats per course
    courses_with_stats = []
    for course in courses:
        total_sessions = Attendance.objects.filter(course=course).values('date').distinct().count()
        total_logs = Attendance.objects.filter(course=course).count()
        present_logs = Attendance.objects.filter(course=course, status=Attendance.Status.PRESENT).count()
        enrolled_count = Enrollment.objects.filter(course=course, status=Enrollment.EnrollmentStatus.ACTIVE).count()
        
        rate = round((present_logs / total_logs) * 100, 1) if total_logs > 0 else 0.0

        courses_with_stats.append({
            'course': course,
            'total_sessions': total_sessions,
            'total_logs': total_logs,
            'present_logs': present_logs,
            'enrolled_count': enrolled_count,
            'rate': rate,
        })

    context = {
        'courses_with_stats': courses_with_stats,
        'total_courses': len(courses_with_stats),
    }
    return render(request, 'attendance/attendance_report.html', context)


@login_required
def course_attendance_report_view(request, course_pk):
    """
    Detailed course attendance report calculating:
    - Total Classes Held (distinct dates)
    - Per-Student breakdown: Present, Absent, Late, Excused counts
    - Per-Student Attendance Percentage = (Present Days / Total Classes) x 100
    - Attendance shortage warnings for students below 75%
    """
    user = request.user

    # Access control
    if user.role == CustomUser.Role.TEACHER and hasattr(user, 'teacher_profile'):
        course = get_object_or_404(
            Course.objects.select_related('department', 'classroom', 'teacher__user'),
            pk=course_pk,
            teacher=user.teacher_profile
        )
    elif user.is_superuser or user.role == CustomUser.Role.ADMIN:
        course = get_object_or_404(
            Course.objects.select_related('department', 'classroom', 'teacher__user'),
            pk=course_pk
        )
    elif user.role == CustomUser.Role.STUDENT and hasattr(user, 'student_profile'):
        # Verify student is enrolled in this course
        if not Enrollment.objects.filter(student=user.student_profile, course_id=course_pk).exists():
            raise PermissionDenied("You are not enrolled in this course.")
        course = get_object_or_404(Course.objects.select_related('department', 'classroom', 'teacher__user'), pk=course_pk)
    else:
        raise PermissionDenied("Access restricted.")

    # 1. Total Distinct Classes Held
    total_classes = Attendance.objects.filter(course=course).values('date').distinct().count()

    # 2. Get active enrolled students
    enrollments = Enrollment.objects.filter(
        course=course,
        status=Enrollment.EnrollmentStatus.ACTIVE
    ).select_related('student__user', 'student__classroom').order_by('student__admission_number')

    student_roster = []
    total_present_all = 0
    total_absent_all = 0
    total_late_all = 0
    total_excused_all = 0

    for enrollment in enrollments:
        student = enrollment.student
        records = Attendance.objects.filter(student=student, course=course)
        
        present_count = records.filter(status=Attendance.Status.PRESENT).count()
        absent_count = records.filter(status=Attendance.Status.ABSENT).count()
        late_count = records.filter(status=Attendance.Status.LATE).count()
        excused_count = records.filter(status=Attendance.Status.EXCUSED).count()

        total_present_all += present_count
        total_absent_all += absent_count
        total_late_all += late_count
        total_excused_all += excused_count

        # Specific formula: (Present Days / Total Classes) x 100
        if total_classes > 0:
            percentage = round((present_count / total_classes) * 100, 1)
        else:
            percentage = 0.0

        is_shortage = percentage < 75.0 if total_classes > 0 else False

        student_roster.append({
            'student': student,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'excused_count': excused_count,
            'percentage': percentage,
            'is_shortage': is_shortage,
        })

    # Overall course average
    total_logs = total_present_all + total_absent_all + total_late_all + total_excused_all
    avg_attendance = round((total_present_all / total_logs) * 100, 1) if total_logs > 0 else 0.0

    context = {
        'course': course,
        'total_classes': total_classes,
        'student_roster': student_roster,
        'total_students': len(student_roster),
        'avg_attendance': avg_attendance,
        'total_present_all': total_present_all,
        'total_absent_all': total_absent_all,
        'total_late_all': total_late_all,
        'total_excused_all': total_excused_all,
    }
    return render(request, 'attendance/course_attendance_report.html', context)


@login_required
def student_attendance_view(request, student_pk):
    """
    Detailed attendance report for an individual student across all their enrolled courses.
    Accessible to Admins, Teachers, and the student themselves.
    """
    student = get_object_or_404(
        Student.objects.select_related('user', 'classroom'),
        pk=student_pk
    )

    # Permission check for students
    if request.user.role == CustomUser.Role.STUDENT:
        if not hasattr(request.user, 'student_profile') or request.user.student_profile.pk != student.pk:
            raise PermissionDenied("You are not authorized to view another student's attendance.")

    enrollments = Enrollment.objects.filter(student=student).select_related('course', 'course__teacher__user')

    course_stats = []
    overall_total_classes = 0
    overall_present = 0

    for enrollment in enrollments:
        course = enrollment.course
        total_course_classes = Attendance.objects.filter(course=course).values('date').distinct().count()
        student_records = Attendance.objects.filter(student=student, course=course)
        
        present_count = student_records.filter(status=Attendance.Status.PRESENT).count()
        absent_count = student_records.filter(status=Attendance.Status.ABSENT).count()
        late_count = student_records.filter(status=Attendance.Status.LATE).count()
        excused_count = student_records.filter(status=Attendance.Status.EXCUSED).count()

        overall_total_classes += total_course_classes
        overall_present += present_count

        pct = round((present_count / total_course_classes) * 100, 1) if total_course_classes > 0 else 0.0

        course_stats.append({
            'course': course,
            'enrollment': enrollment,
            'total_classes': total_course_classes,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'excused_count': excused_count,
            'percentage': pct,
            'is_shortage': pct < 75.0 if total_course_classes > 0 else False,
        })

    overall_percentage = round((overall_present / overall_total_classes) * 100, 1) if overall_total_classes > 0 else 0.0

    # Recent attendance log entries for this student
    recent_logs = Attendance.objects.filter(student=student).select_related('course').order_by('-date', '-id')[:30]

    context = {
        'student': student,
        'course_stats': course_stats,
        'overall_total_classes': overall_total_classes,
        'overall_present': overall_present,
        'overall_percentage': overall_percentage,
        'recent_logs': recent_logs,
    }
    return render(request, 'attendance/student_attendance.html', context)


@admin_required
def attendance_edit_view(request, pk):
    """
    Edit a single attendance entry.
    """
    record = get_object_or_404(
        Attendance.objects.select_related('student__user', 'course'),
        pk=pk
    )

    if request.method == 'POST':
        form = AttendanceSingleUpdateForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, f"Attendance record for {record.student.admission_number} updated.")
            return redirect('attendance:attendance_history')
    else:
        form = AttendanceSingleUpdateForm(instance=record)

    context = {
        'form': form,
        'record': record,
    }
    return render(request, 'attendance/attendance_edit_form.html', context)


@admin_required
def attendance_delete_view(request, pk):
    """
    Delete a single attendance entry with confirmation.
    """
    record = get_object_or_404(
        Attendance.objects.select_related('student__user', 'course'),
        pk=pk
    )

    if request.method == 'POST':
        adm_no = record.student.admission_number
        course_code = record.course.course_code
        date_str = record.date.strftime('%b %d, %Y')
        record.delete()
        messages.success(request, f"Attendance log for {adm_no} ({course_code} on {date_str}) deleted successfully.")
        return redirect('attendance:attendance_history')

    return render(request, 'attendance/attendance_confirm_delete.html', {'record': record})
