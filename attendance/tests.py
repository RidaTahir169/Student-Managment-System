from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomUser
from students.models import Student
from teachers.models import Teacher
from courses.models import Course, Department, ClassRoom, Enrollment
from attendance.models import Attendance


class AttendanceModelAndWorkflowTests(TestCase):
    """
    Comprehensive tests for Phase 11: Attendance Management.
    Covers model constraints, duplicate prevention, percentage calculation,
    teacher workflow, access controls, history, and reports.
    """

    def setUp(self):
        self.client = Client()

        # 1. Create Academic Setup
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

        # 2. Create Users
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

        # 3. Create Courses
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

    def test_attendance_model_creation_and_string_representation(self):
        """Test creating an attendance record and verify __str__ format."""
        today = timezone.now().date()
        att = Attendance.objects.create(
            student=self.student_1,
            course=self.course_1,
            date=today,
            status=Attendance.Status.PRESENT,
            remarks='Present on time'
        )
        self.assertEqual(att.status, Attendance.Status.PRESENT)
        self.assertIn('ADM-1001', str(att))
        self.assertIn('CS201', str(att))
        self.assertIn('Present', str(att))

    def test_duplicate_attendance_prevention_at_model_level(self):
        """Test that duplicate attendance for the same (student, course, date) raises IntegrityError."""
        from django.db import IntegrityError
        today = timezone.now().date()

        Attendance.objects.create(
            student=self.student_1,
            course=self.course_1,
            date=today,
            status=Attendance.Status.PRESENT
        )

        with self.assertRaises(IntegrityError):
            Attendance.objects.create(
                student=self.student_1,
                course=self.course_1,
                date=today,
                status=Attendance.Status.ABSENT
            )

    def test_teacher_mark_attendance_get_and_post_workflow(self):
        """
        Test the full teacher attendance marking workflow:
        Teacher logs in -> selects course -> views students -> marks Present/Absent/Late -> saves.
        """
        self.client.login(username='prof_smith', password='Password123!')
        today_str = timezone.now().date().strftime('%Y-%m-%d')

        # GET request to load roster
        url = reverse('attendance:mark_attendance')
        response = self.client.get(f"{url}?course={self.course_1.id}&date={today_str}")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'attendance/mark_attendance.html')
        self.assertContains(response, 'Alice Walker')
        self.assertContains(response, 'Bob Taylor')
        self.assertContains(response, 'ADM-1001')

        # POST request to save attendance (Student 1: PRESENT, Student 2: LATE)
        post_data = {
            'course': self.course_1.id,
            'date': today_str,
            'save_attendance': '1',
            f'status_{self.student_1.id}': Attendance.Status.PRESENT,
            f'remarks_{self.student_1.id}': 'Attentive',
            f'status_{self.student_2.id}': Attendance.Status.LATE,
            f'remarks_{self.student_2.id}': '10 mins late',
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify records created in DB
        self.assertEqual(Attendance.objects.filter(course=self.course_1).count(), 2)
        rec_1 = Attendance.objects.get(student=self.student_1, course=self.course_1)
        self.assertEqual(rec_1.status, Attendance.Status.PRESENT)
        self.assertEqual(rec_1.remarks, 'Attentive')

        rec_2 = Attendance.objects.get(student=self.student_2, course=self.course_1)
        self.assertEqual(rec_2.status, Attendance.Status.LATE)
        self.assertEqual(rec_2.remarks, '10 mins late')

    def test_idempotent_attendance_update_prevents_duplicates(self):
        """
        Test that saving attendance again for the same course and date updates existing records
        instead of creating duplicate entries.
        """
        self.client.login(username='prof_smith', password='Password123!')
        today_str = timezone.now().date().strftime('%Y-%m-%d')
        url = reverse('attendance:mark_attendance')

        # First submission
        self.client.post(url, {
            'course': self.course_1.id,
            'date': today_str,
            'save_attendance': '1',
            f'status_{self.student_1.id}': Attendance.Status.ABSENT,
            f'status_{self.student_2.id}': Attendance.Status.ABSENT,
        })
        self.assertEqual(Attendance.objects.filter(course=self.course_1).count(), 2)
        self.assertEqual(Attendance.objects.get(student=self.student_1).status, Attendance.Status.ABSENT)

        # Second submission on same date (e.g. correcting mistake: Student 1 changed to PRESENT)
        self.client.post(url, {
            'course': self.course_1.id,
            'date': today_str,
            'save_attendance': '1',
            f'status_{self.student_1.id}': Attendance.Status.PRESENT,
            f'status_{self.student_2.id}': Attendance.Status.PRESENT,
        })

        # Count remains 2, statuses are updated
        self.assertEqual(Attendance.objects.filter(course=self.course_1).count(), 2)
        self.assertEqual(Attendance.objects.get(student=self.student_1).status, Attendance.Status.PRESENT)

    def test_teacher_cannot_mark_unassigned_course(self):
        """Test that a teacher cannot mark attendance for a course they do not teach."""
        self.client.login(username='prof_smith', password='Password123!')
        today_str = timezone.now().date().strftime('%Y-%m-%d')
        url = reverse('attendance:mark_attendance')

        # prof_smith tries to load course_2 (assigned to prof_jones) -> should return 404
        response = self.client.get(f"{url}?course={self.course_2.id}&date={today_str}")
        self.assertEqual(response.status_code, 404)

    def test_attendance_percentage_calculation_and_reports(self):
        """
        Test attendance percentage formula: (Present Days / Total Classes) * 100.
        Create 4 sessions:
        - Student 1: 3 Present, 1 Absent -> 75.0%
        - Student 2: 2 Present, 1 Late, 1 Absent -> (2 / 4) * 100 = 50.0% (Shortage)
        """
        base_date = timezone.now().date()

        for i in range(4):
            day = base_date - timedelta(days=i)
            # Student 1: 3 Present, 1 Absent on day 3
            st1_status = Attendance.Status.ABSENT if i == 3 else Attendance.Status.PRESENT
            Attendance.objects.create(
                student=self.student_1,
                course=self.course_1,
                date=day,
                status=st1_status
            )

            # Student 2: 2 Present (0, 1), 1 Late (2), 1 Absent (3)
            if i in [0, 1]:
                st2_status = Attendance.Status.PRESENT
            elif i == 2:
                st2_status = Attendance.Status.LATE
            else:
                st2_status = Attendance.Status.ABSENT

            Attendance.objects.create(
                student=self.student_2,
                course=self.course_1,
                date=day,
                status=st2_status
            )

        self.client.login(username='prof_smith', password='Password123!')

        # Course report view
        url = reverse('attendance:course_attendance_report', args=[self.course_1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '75.0%')
        self.assertContains(response, '50.0%')
        self.assertContains(response, 'Shortage')

    def test_attendance_history_and_filtering(self):
        """Test attendance history search and filtering by student and course."""
        today = timezone.now().date()
        Attendance.objects.create(
            student=self.student_1,
            course=self.course_1,
            date=today,
            status=Attendance.Status.PRESENT
        )
        Attendance.objects.create(
            student=self.student_2,
            course=self.course_1,
            date=today,
            status=Attendance.Status.ABSENT
        )

        self.client.login(username='prof_smith', password='Password123!')
        url = reverse('attendance:attendance_history')

        # Filter by status ABSENT
        response = self.client.get(f"{url}?status=ABSENT")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bob Taylor')
        self.assertNotContains(response, 'Alice Walker')

    def test_student_can_view_own_attendance_but_not_others(self):
        """Test that a logged-in student can see their own ledger but is denied access to other students."""
        today = timezone.now().date()
        Attendance.objects.create(
            student=self.student_1,
            course=self.course_1,
            date=today,
            status=Attendance.Status.PRESENT
        )

        # Alice logs in
        self.client.login(username='alice_w', password='Password123!')

        # Accessing dashboard router redirects to own attendance
        response = self.client.get(reverse('attendance:attendance_dashboard'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice Walker')

        # Alice tries to view Bob's attendance directly -> 403 Forbidden
        bob_url = reverse('attendance:student_attendance', args=[self.student_2.pk])
        response = self.client.get(bob_url)
        self.assertEqual(response.status_code, 403)
