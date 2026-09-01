from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Max, Min
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from accounts.decorators import admin_required, teacher_required, student_required
from accounts.models import CustomUser
from courses.models import Course, Enrollment, Department, AcademicSession
from students.models import Student
from .models import AcademicRecord
from .forms import AcademicRecordForm, AcademicRecordFilterForm


@login_required
def record_list_view(request):
    """
    Overview directory of all student examination marks & grades.
    Includes searchable filters, KPI metrics, and paginated records.
    """
    user = request.user

    # Redirect students directly to their personal transcript / report card
    if user.role == CustomUser.Role.STUDENT:
        if hasattr(user, 'student_profile'):
            return redirect('academics:student_report_card', student_pk=user.student_profile.pk)
        messages.error(request, "Student profile not found.")
        return redirect('dashboard:student_dashboard')

    records = AcademicRecord.objects.select_related(
        'student__user',
        'student__classroom',
        'course__department',
        'course__teacher__user'
    ).order_by('-date_recorded', 'course__course_code', 'student__admission_number')

    # Role-based filtering: Teachers see records for their assigned courses only
    if user.role == CustomUser.Role.TEACHER and hasattr(user, 'teacher_profile'):
        records = records.filter(course__teacher=user.teacher_profile)
        available_courses = Course.objects.filter(teacher=user.teacher_profile).order_by('course_code')
    else:
        available_courses = Course.objects.all().order_by('course_code')

    # Process search and filter query parameters
    query = request.GET.get('q', '').strip()
    course_id = request.GET.get('course', '').strip()
    exam_type = request.GET.get('exam_type', '').strip()
    grade = request.GET.get('grade', '').strip()

    if query:
        records = records.filter(
            Q(student__admission_number__icontains=query) |
            Q(student__user__first_name__icontains=query) |
            Q(student__user__last_name__icontains=query) |
            Q(student__user__username__icontains=query) |
            Q(course__course_code__icontains=query) |
            Q(course__title__icontains=query) |
            Q(exam_name__icontains=query)
        )

    if course_id:
        records = records.filter(course_id=course_id)
    if exam_type:
        records = records.filter(exam_type=exam_type)
    if grade:
        records = records.filter(grade=grade)

    # Calculate overall analytics
    total_records = records.count()
    avg_performance = records.aggregate(avg_pct=Avg('percentage'), avg_gpa=Avg('grade_point'))
    avg_percentage = round(avg_performance['avg_pct'], 2) if avg_performance['avg_pct'] is not None else 0.00
    avg_gpa = round(avg_performance['avg_gpa'], 2) if avg_performance['avg_gpa'] is not None else 0.00
    passing_count = records.exclude(grade='F').count()
    pass_rate = round((passing_count / total_records) * 100, 1) if total_records > 0 else 0.0

    # Pagination (20 records per page)
    paginator = Paginator(records, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    filter_form = AcademicRecordFilterForm(request.GET)

    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'total_records': total_records,
        'avg_percentage': avg_percentage,
        'avg_gpa': avg_gpa,
        'pass_rate': pass_rate,
        'passing_count': passing_count,
        'query': query,
        'course_id': course_id,
        'exam_type': exam_type,
        'grade': grade,
        'available_courses': available_courses,
    }
    return render(request, 'academics/record_list.html', context)


@login_required
@teacher_required
def record_create_view(request):
    """
    Enter marks for a student in an academic course.
    Teachers can only enter marks for courses they teach; Admins can enter for any course.
    """
    user = request.user
    course_id = request.GET.get('course')
    student_id = request.GET.get('student')

    if request.method == 'POST':
        form = AcademicRecordForm(request.POST, user=user)
        if form.is_valid():
            record = form.save(commit=False)

            # Security check: verify teacher teaches this course
            if user.role == CustomUser.Role.TEACHER and hasattr(user, 'teacher_profile'):
                if record.course.teacher != user.teacher_profile:
                    raise PermissionDenied("You can only enter marks for courses assigned to you.")

            record.save()
            messages.success(
                request,
                f"Marks recorded successfully: {record.student.admission_number} received {record.marks_obtained}/{record.total_marks} ({record.grade}) in '{record.exam_name}'."
            )
            return redirect('academics:record_list')
    else:
        initial_data = {}
        if student_id:
            try:
                initial_data['student'] = Student.objects.get(pk=student_id)
            except Student.DoesNotExist:
                pass
        if course_id:
            try:
                initial_data['course'] = Course.objects.get(pk=course_id)
            except Course.DoesNotExist:
                pass

        form = AcademicRecordForm(user=user, course_id=course_id, initial=initial_data)

    context = {
        'form': form,
        'title': 'Enter Examination Marks',
        'button_text': 'Save Academic Record',
    }
    return render(request, 'academics/record_form.html', context)


@login_required
@teacher_required
def record_update_view(request, pk):
    """
    Update an existing student academic record.
    """
    user = request.user
    record = get_object_or_404(
        AcademicRecord.objects.select_related('student__user', 'course__teacher'),
        pk=pk
    )

    # Permission check: Teachers can only edit their own course records
    if user.role == CustomUser.Role.TEACHER and hasattr(user, 'teacher_profile'):
        if record.course.teacher != user.teacher_profile:
            raise PermissionDenied("You cannot edit marks for courses you do not teach.")

    if request.method == 'POST':
        form = AcademicRecordForm(request.POST, instance=record, user=user)
        if form.is_valid():
            updated_record = form.save()
            messages.success(
                request,
                f"Academic record updated: {updated_record.student.admission_number} now has {updated_record.marks_obtained}/{updated_record.total_marks} ({updated_record.grade}) in '{updated_record.exam_name}'."
            )
            return redirect('academics:record_list')
    else:
        form = AcademicRecordForm(instance=record, user=user)

    context = {
        'form': form,
        'record': record,
        'title': f'Update Marks - {record.student.admission_number}',
        'button_text': 'Update Record',
    }
    return render(request, 'academics/record_form.html', context)


@login_required
@teacher_required
def record_delete_view(request, pk):
    """
    Delete an academic record with confirmation.
    """
    user = request.user
    record = get_object_or_404(
        AcademicRecord.objects.select_related('student__user', 'course__teacher'),
        pk=pk
    )

    # Permission check
    if user.role == CustomUser.Role.TEACHER and hasattr(user, 'teacher_profile'):
        if record.course.teacher != user.teacher_profile:
            raise PermissionDenied("You cannot delete records for courses you do not teach.")

    if request.method == 'POST':
        adm_no = record.student.admission_number
        exam = record.exam_name
        course_code = record.course.course_code
        record.delete()
        messages.success(request, f"Assessment log '{exam}' for {adm_no} in {course_code} has been deleted.")
        return redirect('academics:record_list')

    return render(request, 'academics/record_confirm_delete.html', {'record': record})


@login_required
def course_gradebook_view(request, course_pk):
    """
    Detailed Gradebook for an entire course module.
    Displays all enrolled students and their scores across all assessments held in this course.
    """
    user = request.user

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
        if not Enrollment.objects.filter(student=user.student_profile, course_id=course_pk).exists():
            raise PermissionDenied("You are not enrolled in this course.")
        course = get_object_or_404(Course.objects.select_related('department', 'classroom', 'teacher__user'), pk=course_pk)
    else:
        raise PermissionDenied("Access restricted.")

    # All records for this course
    records = AcademicRecord.objects.filter(course=course).select_related(
        'student__user', 'student__classroom'
    ).order_by('-date_recorded', 'student__admission_number')

    # Distinct assessment names
    assessment_names = records.values_list('exam_name', flat=True).distinct()

    # Course stats
    total_entries = records.count()
    avg_performance = records.aggregate(avg_pct=Avg('percentage'), avg_gpa=Avg('grade_point'))
    avg_percentage = round(avg_performance['avg_pct'], 2) if avg_performance['avg_pct'] is not None else 0.00
    avg_gpa = round(avg_performance['avg_gpa'], 2) if avg_performance['avg_gpa'] is not None else 0.00

    context = {
        'course': course,
        'records': records,
        'assessment_names': assessment_names,
        'total_entries': total_entries,
        'avg_percentage': avg_percentage,
        'avg_gpa': avg_gpa,
    }
    return render(request, 'academics/course_gradebook.html', context)


@login_required
def student_report_card_view(request, student_pk):
    """
    Official Transcript and Report Card view for a single student.
    Aggregates all course assessments, calculates cumulative GPA, and displays grade distribution.
    """
    student = get_object_or_404(
        Student.objects.select_related('user', 'classroom'),
        pk=student_pk
    )

    # Permission check: Students can only view their own transcript
    if request.user.role == CustomUser.Role.STUDENT:
        if not hasattr(request.user, 'student_profile') or request.user.student_profile.pk != student.pk:
            raise PermissionDenied("You are not authorized to view another student's report card.")

    records = AcademicRecord.objects.filter(student=student).select_related(
        'course__department', 'course__teacher__user'
    ).order_by('course__course_code', '-date_recorded')

    # Group records by course
    courses_dict = {}
    for record in records:
        c = record.course
        if c.id not in courses_dict:
            courses_dict[c.id] = {
                'course': c,
                'records': [],
                'total_marks_obtained': Decimal('0.00'),
                'total_max_marks': Decimal('0.00'),
            }
        courses_dict[c.id]['records'].append(record)
        courses_dict[c.id]['total_marks_obtained'] += Decimal(str(record.marks_obtained))
        courses_dict[c.id]['total_max_marks'] += Decimal(str(record.total_marks))

    # Compute course-level summary percentages
    for c_id, data in courses_dict.items():
        if data['total_max_marks'] > Decimal('0.00'):
            data['course_avg_pct'] = round((data['total_marks_obtained'] / data['total_max_marks']) * Decimal('100.00'), 2)
        else:
            data['course_avg_pct'] = Decimal('0.00')

    # Overall Student Cumulative Metrics
    total_assessments = records.count()
    overall_avg = records.aggregate(avg_pct=Avg('percentage'), avg_gpa=Avg('grade_point'))
    cumulative_percentage = round(overall_avg['avg_pct'], 2) if overall_avg['avg_pct'] is not None else 0.00
    cumulative_gpa = round(overall_avg['avg_gpa'], 2) if overall_avg['avg_gpa'] is not None else 0.00

    # Grade distribution counts
    grade_counts = {
        'A_plus': records.filter(grade='A+').count(),
        'A': records.filter(grade='A').count(),
        'B': records.filter(grade='B').count(),
        'C': records.filter(grade='C').count(),
        'D': records.filter(grade='D').count(),
        'F': records.filter(grade='F').count(),
    }

    context = {
        'student': student,
        'records': records,
        'courses_data': courses_dict.values(),
        'total_assessments': total_assessments,
        'cumulative_percentage': cumulative_percentage,
        'cumulative_gpa': cumulative_gpa,
        'grade_counts': grade_counts,
    }
    return render(request, 'academics/student_report_card.html', context)


@login_required
def academic_reports_view(request):
    """
    Institutional & Departmental Academic Performance Summary Report.
    Aggregates metrics across courses, grade distribution, honor rolls, and at-risk students.
    Accessible to Admins and Teachers.
    """
    user = request.user
    if user.role == CustomUser.Role.STUDENT:
        if hasattr(user, 'student_profile'):
            return redirect('academics:student_report_card', student_pk=user.student_profile.pk)
        return redirect('dashboard:student_dashboard')

    department_id = request.GET.get('department', '').strip()
    session_id = request.GET.get('session', '').strip()

    records = AcademicRecord.objects.select_related(
        'student__user',
        'student__classroom',
        'course__department',
        'course__teacher__user',
        'course__session'
    )

    courses = Course.objects.select_related('department', 'teacher__user', 'classroom', 'session')

    # Role-based restriction: Teachers only see their assigned courses
    if user.role == CustomUser.Role.TEACHER and hasattr(user, 'teacher_profile'):
        records = records.filter(course__teacher=user.teacher_profile)
        courses = courses.filter(teacher=user.teacher_profile)

    # Department filter
    if department_id:
        records = records.filter(course__department_id=department_id)
        courses = courses.filter(department_id=department_id)

    # Session filter
    if session_id:
        records = records.filter(course__session_id=session_id)
        courses = courses.filter(session_id=session_id)

    # 1. Overall Aggregates
    total_assessments = records.count()
    overall_aggregates = records.aggregate(
        avg_pct=Avg('percentage'),
        avg_gpa=Avg('grade_point'),
        max_pct=Max('percentage'),
        min_pct=Min('percentage'),
    )
    avg_percentage = round(overall_aggregates['avg_pct'], 2) if overall_aggregates['avg_pct'] is not None else 0.00
    avg_gpa = round(overall_aggregates['avg_gpa'], 2) if overall_aggregates['avg_gpa'] is not None else 0.00
    highest_score = overall_aggregates['max_pct'] or Decimal('0.00')
    lowest_score = overall_aggregates['min_pct'] or Decimal('0.00')

    passing_count = records.exclude(grade='F').count()
    failing_count = records.filter(grade='F').count()
    pass_rate = round((passing_count / total_assessments) * 100, 1) if total_assessments > 0 else 0.0

    # 2. Grade Distribution
    grade_distribution = {
        'A_plus': records.filter(grade='A+').count(),
        'A': records.filter(grade='A').count(),
        'B': records.filter(grade='B').count(),
        'C': records.filter(grade='C').count(),
        'D': records.filter(grade='D').count(),
        'F': records.filter(grade='F').count(),
    }

    # 3. Course-by-Course Performance Summary
    course_performance = []
    for course in courses.order_by('course_code'):
        c_records = records.filter(course=course)
        c_total = c_records.count()
        c_enrolled = Enrollment.objects.filter(course=course, status=Enrollment.EnrollmentStatus.ACTIVE).count()
        
        if c_total > 0:
            c_agg = c_records.aggregate(
                avg_pct=Avg('percentage'),
                avg_gpa=Avg('grade_point'),
                max_pct=Max('percentage'),
                min_pct=Min('percentage')
            )
            c_avg_pct = round(c_agg['avg_pct'], 2) if c_agg['avg_pct'] is not None else 0.00
            c_avg_gpa = round(c_agg['avg_gpa'], 2) if c_agg['avg_gpa'] is not None else 0.00
            c_passed = c_records.exclude(grade='F').count()
            c_pass_rate = round((c_passed / c_total) * 100, 1)
            c_high = c_agg['max_pct']
            c_low = c_agg['min_pct']
        else:
            c_avg_pct = 0.00
            c_avg_gpa = 0.00
            c_pass_rate = 0.0
            c_high = Decimal('0.00')
            c_low = Decimal('0.00')

        course_performance.append({
            'course': course,
            'enrolled_count': c_enrolled,
            'total_assessments': c_total,
            'avg_percentage': c_avg_pct,
            'avg_gpa': c_avg_gpa,
            'pass_rate': c_pass_rate,
            'highest_score': c_high,
            'lowest_score': c_low,
        })

    # 4. Top Performing Students & At-Risk Students
    student_ids = list(records.values_list('student_id', flat=True).distinct())
    top_students = []
    at_risk_students = []

    for s_id in student_ids:
        s_records = records.filter(student_id=s_id)
        if s_records.exists():
            s_student = s_records.first().student
            s_agg = s_records.aggregate(avg_pct=Avg('percentage'), avg_gpa=Avg('grade_point'))
            s_pct = round(s_agg['avg_pct'], 2) if s_agg['avg_pct'] is not None else 0.00
            s_gpa = round(s_agg['avg_gpa'], 2) if s_agg['avg_gpa'] is not None else 0.00
            s_data = {
                'student': s_student,
                'total_exams': s_records.count(),
                'avg_percentage': s_pct,
                'avg_gpa': s_gpa,
            }
            if s_pct >= 80.0:
                top_students.append(s_data)
            elif s_pct < 50.0:
                at_risk_students.append(s_data)

    top_students.sort(key=lambda x: x['avg_percentage'], reverse=True)
    top_students = top_students[:10]

    at_risk_students.sort(key=lambda x: x['avg_percentage'])
    at_risk_students = at_risk_students[:10]

    departments = Department.objects.all().order_by('name')
    sessions = AcademicSession.objects.all().order_by('-start_date')

    context = {
        'total_assessments': total_assessments,
        'avg_percentage': avg_percentage,
        'avg_gpa': avg_gpa,
        'highest_score': highest_score,
        'lowest_score': lowest_score,
        'pass_rate': pass_rate,
        'passing_count': passing_count,
        'failing_count': failing_count,
        'grade_distribution': grade_distribution,
        'course_performance': course_performance,
        'top_students': top_students,
        'at_risk_students': at_risk_students,
        'departments': departments,
        'sessions': sessions,
        'department_id': department_id,
        'session_id': session_id,
    }
    return render(request, 'academics/academic_reports.html', context)
