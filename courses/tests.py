from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from teachers.models import Teacher
from students.models import Student
from courses.models import Department, ClassRoom, AcademicSession, Course, Enrollment


class CourseAndClassManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Admin User
        self.admin_user = CustomUser.objects.create_superuser(
            username='admin_academic',
            email='admin_academic@test.com',
            password='AdminPassword123!',
            role=CustomUser.Role.ADMIN
        )

        # 2. Create Teacher
        self.teacher_user = CustomUser.objects.create_user(
            username='prof_taylor',
            email='taylor@test.com',
            password='TeacherPassword123!',
            first_name='Emma',
            last_name='Taylor',
            role=CustomUser.Role.TEACHER
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='EMP-TAY-001',
            designation='Assistant Professor'
        )

        # 3. Create Department & Academic Session
        self.department = Department.objects.create(
            name='Computer Science',
            code='CS',
            description='Department of Computer Science & Software Engineering'
        )
        self.session = AcademicSession.objects.create(
            name='2025-2026',
            start_date='2025-09-01',
            end_date='2026-06-30',
            is_current=True
        )

        # 4. Create ClassRoom
        self.classroom = ClassRoom.objects.create(
            name='Grade 10',
            section='Section A',
            department=self.department
        )

        # 5. Create Students
        self.student_user1 = CustomUser.objects.create_user(
            username='student_one',
            email='student1@test.com',
            password='StudentPassword123!',
            first_name='Alice',
            last_name='Walker',
            role=CustomUser.Role.STUDENT
        )
        self.student1 = Student.objects.create(
            user=self.student_user1,
            admission_number='STU-TEST-001',
            classroom=self.classroom,
            roll_number='101'
        )

        self.student_user2 = CustomUser.objects.create_user(
            username='student_two',
            email='student2@test.com',
            password='StudentPassword123!',
            first_name='Bob',
            last_name='Miller',
            role=CustomUser.Role.STUDENT
        )
        self.student2 = Student.objects.create(
            user=self.student_user2,
            admission_number='STU-TEST-002',
            roll_number='102'
        )

        # 6. Create Course
        self.course = Course.objects.create(
            course_code='CS101',
            title='Intro to Computer Science',
            credit_hours=3,
            department=self.department,
            teacher=self.teacher,
            classroom=self.classroom,
            session=self.session
        )

    # --------------------------------------------------------------------------
    # COURSE TESTS
    # --------------------------------------------------------------------------

    def test_course_list_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        response = self.client.get(reverse('courses:course_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CS101')
        self.assertContains(response, 'Intro to Computer Science')

    def test_course_list_search_and_filter(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        # Search by code
        response = self.client.get(reverse('courses:course_list'), {'q': 'CS101'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Intro to Computer Science')

        # Filter by department
        response = self.client.get(reverse('courses:course_list'), {'department': self.department.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CS101')

    def test_course_detail_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        response = self.client.get(reverse('courses:course_detail', kwargs={'pk': self.course.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CS101')
        self.assertContains(response, 'Emma Taylor')

    def test_course_create_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        create_data = {
            'course_code': 'MATH101',
            'title': 'Calculus & Analytical Geometry',
            'credit_hours': 4,
            'department': self.department.id,
            'teacher': self.teacher.id,
            'classroom': self.classroom.id,
            'session': self.session.id,
            'description': 'Fundamental calculus topics.'
        }
        response = self.client.post(reverse('courses:course_create'), create_data, follow=True)
        self.assertEqual(response.status_code, 200)

        new_course = Course.objects.filter(course_code='MATH101').first()
        self.assertIsNotNone(new_course)
        self.assertEqual(new_course.title, 'Calculus & Analytical Geometry')
        self.assertEqual(new_course.teacher, self.teacher)
        self.assertEqual(new_course.classroom, self.classroom)

    def test_course_update_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        update_data = {
            'course_code': 'CS101',
            'title': 'Introduction to Computer Science (Honors)',
            'credit_hours': 4,
            'department': self.department.id,
            'teacher': self.teacher.id,
            'classroom': self.classroom.id,
            'session': self.session.id,
            'description': 'Advanced programming principles.'
        }
        response = self.client.post(
            reverse('courses:course_update', kwargs={'pk': self.course.pk}),
            update_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Introduction to Computer Science (Honors)')
        self.assertEqual(self.course.credit_hours, 4)

    def test_course_delete_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        course_pk = self.course.pk

        response = self.client.post(reverse('courses:course_delete', kwargs={'pk': course_pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Course.objects.filter(pk=course_pk).exists())

    # --------------------------------------------------------------------------
    # CLASS ROOM TESTS
    # --------------------------------------------------------------------------

    def test_classroom_list_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        response = self.client.get(reverse('courses:classroom_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Grade 10')
        self.assertContains(response, 'Section A')

    def test_classroom_detail_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        response = self.client.get(reverse('courses:classroom_detail', kwargs={'pk': self.classroom.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Grade 10')
        self.assertContains(response, 'Alice Walker')

    def test_classroom_create_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        create_data = {
            'name': 'Grade 11',
            'section': 'Section B',
            'department': self.department.id,
        }
        response = self.client.post(reverse('courses:classroom_create'), create_data, follow=True)
        self.assertEqual(response.status_code, 200)

        new_class = ClassRoom.objects.filter(name='Grade 11', section='Section B').first()
        self.assertIsNotNone(new_class)
        self.assertEqual(new_class.department, self.department)

    def test_classroom_update_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        update_data = {
            'name': 'Grade 10 (Advanced)',
            'section': 'Section A1',
            'department': self.department.id,
        }
        response = self.client.post(
            reverse('courses:classroom_update', kwargs={'pk': self.classroom.pk}),
            update_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.classroom.refresh_from_db()
        self.assertEqual(self.classroom.name, 'Grade 10 (Advanced)')
        self.assertEqual(self.classroom.section, 'Section A1')

    def test_classroom_delete_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        class_pk = self.classroom.pk

        response = self.client.post(reverse('courses:classroom_delete', kwargs={'pk': class_pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ClassRoom.objects.filter(pk=class_pk).exists())

        # Verify student classroom was safely set to null
        self.student1.refresh_from_db()
        self.assertIsNone(self.student1.classroom)

    def test_classroom_assign_students_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        # Assign both student1 and student2 to classroom
        response = self.client.post(
            reverse('courses:classroom_assign_students', kwargs={'pk': self.classroom.pk}),
            {'students': [self.student1.id, self.student2.id]},
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.student1.refresh_from_db()
        self.student2.refresh_from_db()
        self.assertEqual(self.student1.classroom, self.classroom)
        self.assertEqual(self.student2.classroom, self.classroom)

    # --------------------------------------------------------------------------
    # ENROLLMENT & RELATIONSHIP CHAIN TESTS (PHASE 10)
    # --------------------------------------------------------------------------

    def test_enrollment_list_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        Enrollment.objects.create(student=self.student1, course=self.course)

        response = self.client.get(reverse('courses:enrollment_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'STU-TEST-001')
        self.assertContains(response, 'CS101')

    def test_enrollment_list_search_and_filter(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        Enrollment.objects.create(student=self.student1, course=self.course, status=Enrollment.EnrollmentStatus.ACTIVE)

        # Search by student name
        response = self.client.get(reverse('courses:enrollment_list'), {'q': 'Alice'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'STU-TEST-001')

        # Filter by status
        response = self.client.get(reverse('courses:enrollment_list'), {'status': 'ACTIVE'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CS101')

    def test_enrollment_create_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        enroll_data = {
            'student': self.student1.id,
            'course': self.course.id,
            'enrollment_date': '2026-01-10',
            'status': 'ACTIVE',
        }
        response = self.client.post(reverse('courses:enrollment_create'), enroll_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(Enrollment.objects.filter(student=self.student1, course=self.course).exists())

    def test_enrollment_duplicate_prevention(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        # Pre-existing enrollment
        Enrollment.objects.create(student=self.student1, course=self.course)

        # Attempt to enroll same student in same course again
        enroll_data = {
            'student': self.student1.id,
            'course': self.course.id,
            'enrollment_date': '2026-01-10',
            'status': 'ACTIVE',
        }
        response = self.client.post(reverse('courses:enrollment_create'), enroll_data)
        self.assertEqual(response.status_code, 200)
        # Form error message is displayed
        self.assertContains(response, 'already enrolled')
        # Only 1 enrollment exists
        self.assertEqual(Enrollment.objects.filter(student=self.student1, course=self.course).count(), 1)

    def test_enrollment_update_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        enrollment = Enrollment.objects.create(student=self.student1, course=self.course, status=Enrollment.EnrollmentStatus.ACTIVE)

        update_data = {
            'status': 'COMPLETED',
            'enrollment_date': '2026-05-20',
        }
        response = self.client.post(
            reverse('courses:enrollment_update', kwargs={'pk': enrollment.pk}),
            update_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, 'COMPLETED')

    def test_enrollment_delete_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        enrollment = Enrollment.objects.create(student=self.student1, course=self.course)
        enroll_pk = enrollment.pk

        response = self.client.post(reverse('courses:enrollment_delete', kwargs={'pk': enroll_pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Enrollment.objects.filter(pk=enroll_pk).exists())

    def test_student_enroll_courses_view(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        course2 = Course.objects.create(
            course_code='CS102',
            title='Object Oriented Programming',
            credit_hours=3,
            department=self.department
        )

        response = self.client.post(
            reverse('students:student_enroll_courses', kwargs={'pk': self.student1.pk}),
            {'courses': [self.course.id, course2.id]},
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.student1.enrollments.count(), 2)

    def test_course_enroll_students_and_sync_class(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')

        # 1. Test auto-sync class students into course
        response = self.client.post(
            reverse('courses:course_enroll_students', kwargs={'pk': self.course.pk}),
            {'action': 'enroll_classroom'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Enrollment.objects.filter(course=self.course, student=self.student1).exists())

        # 2. Test manual student enrollment update
        response = self.client.post(
            reverse('courses:course_enroll_students', kwargs={'pk': self.course.pk}),
            {'students': [self.student1.id, self.student2.id]},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Enrollment.objects.filter(course=self.course).count(), 2)

    def test_course_unenroll_student(self):
        self.client.login(username='admin_academic', password='AdminPassword123!')
        Enrollment.objects.create(student=self.student1, course=self.course)

        response = self.client.post(
            reverse('courses:course_unenroll_student', kwargs={
                'course_pk': self.course.pk,
                'student_pk': self.student1.pk
            }),
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Enrollment.objects.filter(course=self.course, student=self.student1).exists())

    def test_relationship_chain_integrity(self):
        """
        Verify the complete Teacher -> Course -> Enrollment -> Student chain.
        """
        enrollment = Enrollment.objects.create(student=self.student1, course=self.course)

        # 1. Teacher to Course
        self.assertIn(self.course, self.teacher.assigned_courses.all())
        # 2. Course to Teacher
        self.assertEqual(self.course.teacher, self.teacher)
        # 3. Course to Classroom
        self.assertEqual(self.course.classroom, self.classroom)
        # 4. Classroom to Students
        self.assertIn(self.student1, self.classroom.students.all())
        # 5. Course to Enrollments
        self.assertIn(enrollment, self.course.enrollments.all())
        # 6. Student to Enrollments
        self.assertIn(enrollment, self.student1.enrollments.all())
        # 7. Student enrolled in Course taught by Teacher
        self.assertEqual(enrollment.course.teacher.user.username, 'prof_taylor')
