from decimal import Decimal
from datetime import date
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import CustomUser
from students.models import Student
from teachers.models import Teacher
from courses.models import Course, Department, ClassRoom, Enrollment, AcademicSession
from attendance.models import Attendance
from academics.models import AcademicRecord


class AcademicMarksAndGradesTests(TestCase):
    """
    Comprehensive test suite for Phase 12: Marks & Grade Management.
    Tests automatic percentage, grade scale calculation, marks entry/update flow,
    gradebook, report cards, and role-based permissions.
    """

    def setUp(self):
        self.client = Client()

        # 1. Setup Department & ClassRoom
        self.dept = Department.objects.create(
            name='Computer Science',
            code='CS',
            description='Department of Computer Science'
        )
        self.classroom = ClassRoom.objects.create(
            name='CS-101',
            section='A',
            department=self.dept
        )

        # 2. Setup Users
        # Admin
        self.admin_user = CustomUser.objects.create_superuser(
            username='admin_test',
            email='admin@sms.edu',
            password='Password123!',
            role=CustomUser.Role.ADMIN
        )

        # Teacher 1
        self.teacher_user = CustomUser.objects.create_user(
            username='prof_smith',
            email='smith@sms.edu',
            password='Password123!',
            role=CustomUser.Role.TEACHER,
            first_name='John',
            last_name='Smith'
        )
        self.teacher_profile = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='EMP-001',
            department=self.dept,
            designation='Assistant Professor'
        )

        # Teacher 2 (Other teacher)
        self.other_teacher_user = CustomUser.objects.create_user(
            username='prof_jones',
            email='jones@sms.edu',
            password='Password123!',
            role=CustomUser.Role.TEACHER,
            first_name='David',
            last_name='Jones'
        )
        self.other_teacher_profile = Teacher.objects.create(
            user=self.other_teacher_user,
            employee_id='EMP-002',
            department=self.dept,
            designation='Lecturer'
        )

        # Student 1
        self.student_user_1 = CustomUser.objects.create_user(
            username='alice_w',
            email='alice@sms.edu',
            password='Password123!',
            role=CustomUser.Role.STUDENT,
            first_name='Alice',
            last_name='Walker'
        )
        self.student_1 = Student.objects.create(
            user=self.student_user_1,
            admission_number='ADM-1001',
            classroom=self.classroom,
            roll_number='101'
        )

        # Student 2
        self.student_user_2 = CustomUser.objects.create_user(
            username='bob_t',
            email='bob@sms.edu',
            password='Password123!',
            role=CustomUser.Role.STUDENT,
            first_name='Bob',
            last_name='Taylor'
        )
        self.student_2 = Student.objects.create(
            user=self.student_user_2,
            admission_number='ADM-1002',
            classroom=self.classroom,
            roll_number='102'
        )

        # 3. Setup Courses
        self.course_1 = Course.objects.create(
            title='Data Structures & Algorithms',
            course_code='CS201',
            department=self.dept,
            teacher=self.teacher_profile,
            classroom=self.classroom,
            credit_hours=3
        )
        self.course_2 = Course.objects.create(
            title='Database Systems',
            course_code='CS202',
            department=self.dept,
            teacher=self.other_teacher_profile,
            classroom=self.classroom,
            credit_hours=3
        )

        # 4. Enroll Students
        Enrollment.objects.create(
            student=self.student_1,
            course=self.course_1,
            status=Enrollment.EnrollmentStatus.ACTIVE
        )
        Enrollment.objects.create(
            student=self.student_2,
            course=self.course_1,
            status=Enrollment.EnrollmentStatus.ACTIVE
        )

    def test_automatic_percentage_and_grade_scale_calculation(self):
        """
        Test the grading scale:
        90-100 -> A+ (4.00)
        80-89  -> A  (3.75)
        70-79  -> B  (3.00)
        60-69  -> C  (2.00)
        50-59  -> D  (1.00)
        <50    -> F  (0.00)
        """
        test_cases = [
            (Decimal('95.00'), Decimal('100.00'), Decimal('95.00'), 'A+', Decimal('4.00')),
            (Decimal('85.00'), Decimal('100.00'), Decimal('85.00'), 'A', Decimal('3.75')),
            (Decimal('72.50'), Decimal('100.00'), Decimal('72.50'), 'B', Decimal('3.00')),
            (Decimal('63.00'), Decimal('100.00'), Decimal('63.00'), 'C', Decimal('2.00')),
            (Decimal('54.00'), Decimal('100.00'), Decimal('54.00'), 'D', Decimal('1.00')),
            (Decimal('42.00'), Decimal('100.00'), Decimal('42.00'), 'F', Decimal('0.00')),
            # Test non-100 total marks: 45 / 50 -> 90.00% -> A+
            (Decimal('45.00'), Decimal('50.00'), Decimal('90.00'), 'A+', Decimal('4.00')),
            # 35 / 50 -> 70.00% -> B
            (Decimal('35.00'), Decimal('50.00'), Decimal('70.00'), 'B', Decimal('3.00')),
        ]

        for i, (marks, total, expected_pct, expected_grade, expected_gpa) in enumerate(test_cases):
            rec = AcademicRecord.objects.create(
                student=self.student_1,
                course=self.course_1,
                exam_name=f'Quiz {i+1}',
                exam_type=AcademicRecord.ExamType.QUIZ,
                marks_obtained=marks,
                total_marks=total
            )
            self.assertEqual(rec.percentage, expected_pct)
            self.assertEqual(rec.grade, expected_grade)
            self.assertEqual(rec.grade_point, expected_gpa)

    def test_validation_marks_cannot_exceed_total_marks(self):
        """Test that marks_obtained > total_marks raises a ValidationError."""
        rec = AcademicRecord(
            student=self.student_1,
            course=self.course_1,
            exam_name='Invalid Exam',
            exam_type=AcademicRecord.ExamType.MIDTERM,
            marks_obtained=Decimal('105.00'),
            total_marks=Decimal('100.00')
        )
        with self.assertRaises(ValidationError):
            rec.clean()

    def test_duplicate_assessment_entry_prevention(self):
        """Test that duplicate (student, course, exam_name) raises IntegrityError."""
        AcademicRecord.objects.create(
            student=self.student_1,
            course=self.course_1,
            exam_name='Midterm Exam 2026',
            marks_obtained=Decimal('80.00'),
            total_marks=Decimal('100.00')
        )

        with self.assertRaises(IntegrityError):
            AcademicRecord.objects.create(
                student=self.student_1,
                course=self.course_1,
                exam_name='Midterm Exam 2026',
                marks_obtained=Decimal('85.00'),
                total_marks=Decimal('100.00')
            )

    def test_teacher_marks_entry_workflow_via_post(self):
        """
        Test the Teacher marks entry workflow:
        Teacher logs in -> selects course & student -> enters marks -> record is created with auto percentage & grade.
        """
        self.client.login(username='prof_smith', password='Password123!')

        url = reverse('academics:record_create')
        post_data = {
            'course': self.course_1.id,
            'student': self.student_1.id,
            'exam_name': 'Midterm Exam 2026',
            'exam_type': AcademicRecord.ExamType.MIDTERM,
            'marks_obtained': '88.50',
            'total_marks': '100.00',
            'date_recorded': timezone.now().date().strftime('%Y-%m-%d'),
            'remarks': 'Great analytical skills shown in tree traversal question.',
        }

        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify in database
        record = AcademicRecord.objects.get(student=self.student_1, course=self.course_1, exam_name='Midterm Exam 2026')
        self.assertEqual(record.marks_obtained, Decimal('88.50'))
        self.assertEqual(record.percentage, Decimal('88.50'))
        self.assertEqual(record.grade, 'A')
        self.assertEqual(record.grade_point, Decimal('3.75'))
        self.assertEqual(record.remarks, 'Great analytical skills shown in tree traversal question.')

    def test_teacher_cannot_enter_marks_for_unassigned_course(self):
        """Test that a teacher cannot enter marks for a course taught by another teacher."""
        self.client.login(username='prof_smith', password='Password123!')

        url = reverse('academics:record_create')
        # prof_smith tries to enter marks for course_2 (taught by prof_jones)
        post_data = {
            'course': self.course_2.id,
            'student': self.student_1.id,
            'exam_name': 'DBMS Midterm',
            'exam_type': AcademicRecord.ExamType.MIDTERM,
            'marks_obtained': '90.00',
            'total_marks': '100.00',
            'date_recorded': timezone.now().date().strftime('%Y-%m-%d'),
        }

        response = self.client.post(url, post_data)
        # Form validation fails or raises PermissionDenied
        self.assertIn(response.status_code, [200, 403])
        self.assertFalse(AcademicRecord.objects.filter(course=self.course_2, exam_name='DBMS Midterm').exists())

    def test_update_marks_workflow_and_recalculation(self):
        """
        Test updating an existing academic record:
        Marks updated from 48 -> 92, percentage updates from 48.00% -> 92.00%, grade updates from F -> A+.
        """
        record = AcademicRecord.objects.create(
            student=self.student_1,
            course=self.course_1,
            exam_name='Final Project',
            exam_type=AcademicRecord.ExamType.PROJECT,
            marks_obtained=Decimal('48.00'),
            total_marks=Decimal('100.00')
        )
        self.assertEqual(record.grade, 'F')

        self.client.login(username='prof_smith', password='Password123!')
        url = reverse('academics:record_update', args=[record.pk])

        post_data = {
            'course': self.course_1.id,
            'student': self.student_1.id,
            'exam_name': 'Final Project',
            'exam_type': AcademicRecord.ExamType.PROJECT,
            'marks_obtained': '92.00',
            'total_marks': '100.00',
            'date_recorded': timezone.now().date().strftime('%Y-%m-%d'),
            'remarks': 'Re-evaluated after bug fix.',
        }

        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        record.refresh_from_db()
        self.assertEqual(record.marks_obtained, Decimal('92.00'))
        self.assertEqual(record.percentage, Decimal('92.00'))
        self.assertEqual(record.grade, 'A+')
        self.assertEqual(record.grade_point, Decimal('4.00'))

    def test_course_gradebook_view(self):
        """Test viewing course gradebook with multiple student records."""
        AcademicRecord.objects.create(
            student=self.student_1,
            course=self.course_1,
            exam_name='Final Exam',
            marks_obtained=Decimal('95.00'),
            total_marks=Decimal('100.00')
        )
        AcademicRecord.objects.create(
            student=self.student_2,
            course=self.course_1,
            exam_name='Final Exam',
            marks_obtained=Decimal('78.00'),
            total_marks=Decimal('100.00')
        )

        self.client.login(username='prof_smith', password='Password123!')
        url = reverse('academics:course_gradebook', args=[self.course_1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice Walker')
        self.assertContains(response, 'Bob Taylor')
        self.assertContains(response, '95.00')
        self.assertContains(response, '78.00')
        self.assertContains(response, 'A+')
        self.assertContains(response, 'B')

    def test_student_report_card_view_and_permission_isolation(self):
        """
        Test student transcript / report card view:
        - Alice can view her own report card.
        - Alice cannot view Bob's report card (403 Forbidden).
        """
        AcademicRecord.objects.create(
            student=self.student_1,
            course=self.course_1,
            exam_name='Midterm',
            marks_obtained=Decimal('90.00'),
            total_marks=Decimal('100.00')
        )

        # Alice logs in
        self.client.login(username='alice_w', password='Password123!')

        # Accessing academics index redirects student to own report card
        response = self.client.get(reverse('academics:record_list'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice Walker')
        self.assertContains(response, 'ADM-1001')
        self.assertContains(response, '4.00')

        # Alice attempts to view Bob's report card -> 403 Forbidden
        bob_url = reverse('academics:student_report_card', args=[self.student_2.pk])
        response = self.client.get(bob_url)
        self.assertEqual(response.status_code, 403)


class SearchFilteringAndReportsTests(TestCase):
    """
    Comprehensive test suite for Phase 15: Search, Filtering & Reports.
    Tests:
    1. Student search by Name, Student ID (admission_number), and Email.
    2. Teacher search by Name and Department.
    3. Course search by Course Code and Course Title.
    4. Attendance filtering by Student, Course, and Date range.
    5. Academic Performance Summary Reports & KPIs.
    """

    def setUp(self):
        self.client = Client()

        # 1. Departments & Session
        self.dept_cs = Department.objects.create(name='Computer Science', code='CS')
        self.dept_math = Department.objects.create(name='Mathematics', code='MATH')
        self.session = AcademicSession.objects.create(
            name='2025-2026',
            start_date='2025-09-01',
            end_date='2026-06-30',
            is_current=True
        )
        self.classroom_10 = ClassRoom.objects.create(name='Grade 10', section='A', department=self.dept_cs)
        self.classroom_11 = ClassRoom.objects.create(name='Grade 11', section='B', department=self.dept_math)

        # 2. Admin User
        self.admin_user = CustomUser.objects.create_superuser(
            username='admin_boss',
            email='admin@sms.edu',
            password='Password123!',
            role=CustomUser.Role.ADMIN
        )

        # 3. Teachers
        self.t1_user = CustomUser.objects.create_user(
            username='prof_turing',
            email='turing@sms.edu',
            password='Password123!',
            role=CustomUser.Role.TEACHER,
            first_name='Alan',
            last_name='Turing'
        )
        self.teacher_1 = Teacher.objects.create(
            user=self.t1_user,
            employee_id='FAC-101',
            department=self.dept_cs,
            designation='Professor'
        )

        self.t2_user = CustomUser.objects.create_user(
            username='prof_euler',
            email='euler@sms.edu',
            password='Password123!',
            role=CustomUser.Role.TEACHER,
            first_name='Leonhard',
            last_name='Euler'
        )
        self.teacher_2 = Teacher.objects.create(
            user=self.t2_user,
            employee_id='FAC-102',
            department=self.dept_math,
            designation='Professor'
        )

        # 4. Students
        self.s1_user = CustomUser.objects.create_user(
            username='ada_lovelace',
            email='ada@sms.edu',
            password='Password123!',
            role=CustomUser.Role.STUDENT,
            first_name='Ada',
            last_name='Lovelace'
        )
        self.student_1 = Student.objects.create(
            user=self.s1_user,
            admission_number='ADM-5001',
            classroom=self.classroom_10,
            roll_number='CS-01'
        )

        self.s2_user = CustomUser.objects.create_user(
            username='grace_hopper',
            email='grace@sms.edu',
            password='Password123!',
            role=CustomUser.Role.STUDENT,
            first_name='Grace',
            last_name='Hopper'
        )
        self.student_2 = Student.objects.create(
            user=self.s2_user,
            admission_number='ADM-5002',
            classroom=self.classroom_11,
            roll_number='MATH-01'
        )

        # 5. Courses
        self.course_cs = Course.objects.create(
            course_code='CS101',
            title='Computer Architecture',
            credit_hours=4,
            department=self.dept_cs,
            teacher=self.teacher_1,
            classroom=self.classroom_10,
            session=self.session
        )
        self.course_math = Course.objects.create(
            course_code='MATH201',
            title='Calculus II',
            credit_hours=3,
            department=self.dept_math,
            teacher=self.teacher_2,
            classroom=self.classroom_11,
            session=self.session
        )

        # Enrollments
        Enrollment.objects.create(student=self.student_1, course=self.course_cs)
        Enrollment.objects.create(student=self.student_2, course=self.course_math)

        # Attendance
        Attendance.objects.create(student=self.student_1, course=self.course_cs, date=date(2026, 3, 1), status=Attendance.Status.PRESENT)
        Attendance.objects.create(student=self.student_1, course=self.course_cs, date=date(2026, 3, 2), status=Attendance.Status.ABSENT)
        Attendance.objects.create(student=self.student_2, course=self.course_math, date=date(2026, 3, 1), status=Attendance.Status.PRESENT)

        # Academic Records
        # Ada: 95% in CS101 -> Grade A+
        self.record_ada = AcademicRecord.objects.create(
            student=self.student_1,
            course=self.course_cs,
            exam_name='Final Exam',
            marks_obtained=Decimal('95.00'),
            total_marks=Decimal('100.00')
        )
        # Grace: 40% in MATH201 -> Grade F (At-Risk)
        self.record_grace = AcademicRecord.objects.create(
            student=self.student_2,
            course=self.course_math,
            exam_name='Midterm Exam',
            marks_obtained=Decimal('40.00'),
            total_marks=Decimal('100.00')
        )

    def test_student_search_functionality(self):
        """Test searching students by Name, Student ID (admission number), and Email."""
        self.client.login(username='admin_boss', password='Password123!')

        # 1. Search by Name
        resp = self.client.get(reverse('students:student_list'), {'q': 'Ada'})
        self.assertContains(resp, 'ADM-5001')
        self.assertNotContains(resp, 'ADM-5002')

        # 2. Search by Admission Number
        resp = self.client.get(reverse('students:student_list'), {'q': 'ADM-5002'})
        self.assertContains(resp, 'Grace Hopper')
        self.assertNotContains(resp, 'Ada Lovelace')

        # 3. Search by Email
        resp = self.client.get(reverse('students:student_list'), {'q': 'grace@sms.edu'})
        self.assertContains(resp, 'ADM-5002')
        self.assertNotContains(resp, 'ADM-5001')

    def test_teacher_search_functionality(self):
        """Test searching teachers by Name and Department."""
        self.client.login(username='admin_boss', password='Password123!')

        # 1. Search by Name
        resp = self.client.get(reverse('teachers:teacher_list'), {'q': 'Turing'})
        self.assertContains(resp, 'FAC-101')
        self.assertNotContains(resp, 'FAC-102')

        # 2. Filter by Department dropdown
        resp = self.client.get(reverse('teachers:teacher_list'), {'department': self.dept_math.id})
        self.assertContains(resp, 'FAC-102')
        self.assertNotContains(resp, 'FAC-101')

        # 3. Search by Department Name in search box
        resp = self.client.get(reverse('teachers:teacher_list'), {'q': 'Mathematics'})
        self.assertContains(resp, 'FAC-102')
        self.assertNotContains(resp, 'FAC-101')

    def test_course_search_functionality(self):
        """Test searching courses by Course Code and Course Title."""
        self.client.login(username='admin_boss', password='Password123!')

        # 1. Search by Course Code
        resp = self.client.get(reverse('courses:course_list'), {'q': 'CS101'})
        self.assertContains(resp, 'Computer Architecture')
        self.assertNotContains(resp, 'Calculus II')

        # 2. Search by Course Title
        resp = self.client.get(reverse('courses:course_list'), {'q': 'Calculus'})
        self.assertContains(resp, 'MATH201')
        self.assertNotContains(resp, 'CS101')

    def test_attendance_filtering_by_student_course_and_date(self):
        """Test filtering attendance logs by Student keyword, Course ID, and Date range."""
        self.client.login(username='admin_boss', password='Password123!')

        # 1. Filter by Student query
        resp = self.client.get(reverse('attendance:attendance_history'), {'q': 'Ada'})
        self.assertEqual(resp.context['total_count'], 2)

        # 2. Filter by Course
        resp = self.client.get(reverse('attendance:attendance_history'), {'course': self.course_math.id})
        self.assertEqual(resp.context['total_count'], 1)
        self.assertContains(resp, 'ADM-5002')

        # 3. Filter by Date range
        resp = self.client.get(reverse('attendance:attendance_history'), {
            'start_date': '2026-03-02',
            'end_date': '2026-03-02'
        })
        self.assertEqual(resp.context['total_count'], 1)
        self.assertContains(resp, 'ADM-5001')

    def test_academic_reports_performance_summary_view(self):
        """Test Academic Performance Summary report aggregates benchmarks, honors, and at-risk students."""
        self.client.login(username='admin_boss', password='Password123!')
        response = self.client.get(reverse('academics:academic_reports'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'academics/academic_reports.html')

        # Check Aggregates
        self.assertEqual(response.context['total_assessments'], 2)
        # (95 + 40) / 2 = 67.50%
        self.assertEqual(response.context['avg_percentage'], 67.50)
        self.assertEqual(response.context['passing_count'], 1)
        self.assertEqual(response.context['failing_count'], 1)
        self.assertEqual(response.context['pass_rate'], 50.0)

        # Check Honor Roll (Ada >= 80%) & At-Risk (Grace < 50%)
        self.assertEqual(len(response.context['top_students']), 1)
        self.assertEqual(response.context['top_students'][0]['student'], self.student_1)
        self.assertEqual(len(response.context['at_risk_students']), 1)
        self.assertEqual(response.context['at_risk_students'][0]['student'], self.student_2)

        # Check Filter by Department
        resp_filtered = self.client.get(reverse('academics:academic_reports'), {'department': self.dept_cs.id})
        self.assertEqual(resp_filtered.context['total_assessments'], 1)
        self.assertEqual(resp_filtered.context['avg_percentage'], 95.0)
        self.assertEqual(resp_filtered.context['pass_rate'], 100.0)

