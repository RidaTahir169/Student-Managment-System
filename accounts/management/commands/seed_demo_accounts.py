import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import CustomUser
from teachers.models import Teacher
from students.models import Student
from courses.models import Department, AcademicSession, ClassRoom, Course, Enrollment
from attendance.models import Attendance
from academics.models import AcademicRecord


class Command(BaseCommand):
    help = "Seeds the 3 pre-configured demo accounts (Admin, Teacher, Student) for RBAC evaluation."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Seeding Target Demonstration Accounts ==="))

        with transaction.atomic():
            # 1. Academic Infrastructure
            session, _ = AcademicSession.objects.get_or_create(
                name="2025-2026",
                defaults={
                    'start_date': datetime.date(2025, 9, 1),
                    'end_date': datetime.date(2026, 6, 30),
                    'is_current': True,
                }
            )

            dept_cs, _ = Department.objects.get_or_create(
                code="CS",
                defaults={
                    'name': "Computer Science",
                    'description': "Department of Computer Science & Software Engineering"
                }
            )

            classroom, _ = ClassRoom.objects.get_or_create(
                name="BSCS Sem 1",
                section="A",
                defaults={'department': dept_cs}
            )

            # 2. ADMIN ACCOUNT (admin@school.com / Admin123!)
            admin_user, _ = CustomUser.objects.get_or_create(
                email="admin@school.com",
                defaults={
                    'username': "admin_school",
                    'first_name': "School",
                    'last_name': "Administrator",
                    'role': CustomUser.Role.ADMIN,
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True,
                }
            )
            admin_user.set_password("Admin123!")
            admin_user.role = CustomUser.Role.ADMIN
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.is_active = True
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"  [+] Admin Ready: {admin_user.email} (Username: {admin_user.username}) / Admin123!"))

            # Also update legacy 'admin' username user if present to have email admin@school.com if no clash
            if CustomUser.objects.filter(username="admin").exclude(email="admin@school.com").exists():
                u_admin = CustomUser.objects.get(username="admin")
                u_admin.set_password("Admin123!")
                u_admin.is_staff = True
                u_admin.is_superuser = True
                u_admin.save()
                self.stdout.write(self.style.SUCCESS(f"  [+] Updated legacy 'admin' user password to Admin123!"))

            # 3. TEACHER ACCOUNT (teacher@school.com / Teacher123!)
            teacher_user, _ = CustomUser.objects.get_or_create(
                email="teacher@school.com",
                defaults={
                    'username': "teacher_school",
                    'first_name': "Senior",
                    'last_name': "Professor",
                    'role': CustomUser.Role.TEACHER,
                    'is_staff': False,
                    'is_superuser': False,
                    'is_active': True,
                }
            )
            teacher_user.set_password("Teacher123!")
            teacher_user.role = CustomUser.Role.TEACHER
            teacher_user.is_active = True
            teacher_user.save()

            teacher_profile, _ = Teacher.objects.get_or_create(
                user=teacher_user,
                defaults={
                    'employee_id': "FAC-DEMO-01",
                    'department': dept_cs,
                    'designation': "Senior Professor",
                    'qualification': "Ph.D. in Computer Science",
                    'joining_date': datetime.date(2020, 1, 15),
                }
            )
            self.stdout.write(self.style.SUCCESS(f"  [+] Teacher Ready: {teacher_user.email} (Username: {teacher_user.username}) / Teacher123!"))

            # 4. COURSES FOR TEACHER
            course_pf, _ = Course.objects.get_or_create(
                course_code="CS101",
                defaults={
                    'title': "Programming Fundamentals",
                    'credit_hours': 3,
                    'department': dept_cs,
                    'teacher': teacher_profile,
                    'classroom': classroom,
                    'session': session,
                    'description': "Core introductory programming concepts in Python.",
                }
            )
            if course_pf.teacher != teacher_profile:
                course_pf.teacher = teacher_profile
                course_pf.save()

            course_oop, _ = Course.objects.get_or_create(
                course_code="CS201",
                defaults={
                    'title': "Object-Oriented Programming",
                    'credit_hours': 4,
                    'department': dept_cs,
                    'teacher': teacher_profile,
                    'classroom': classroom,
                    'session': session,
                    'description': "Advanced object-oriented programming concepts.",
                }
            )
            if course_oop.teacher != teacher_profile:
                course_oop.teacher = teacher_profile
                course_oop.save()

            # 5. STUDENT ACCOUNT (student@student.com / Student123!)
            student_user, _ = CustomUser.objects.get_or_create(
                email="student@student.com",
                defaults={
                    'username': "student_school",
                    'first_name': "Demo",
                    'last_name': "Student",
                    'role': CustomUser.Role.STUDENT,
                    'is_staff': False,
                    'is_superuser': False,
                    'is_active': True,
                }
            )
            student_user.set_password("Student123!")
            student_user.role = CustomUser.Role.STUDENT
            student_user.is_active = True
            student_user.save()

            student_profile, _ = Student.objects.get_or_create(
                user=student_user,
                defaults={
                    'admission_number': "STU-DEMO-01",
                    'classroom': classroom,
                    'roll_number': "CS-001",
                    'parent_name': "Demo Guardian",
                    'parent_phone': "+1-555-0199",
                    'blood_group': "A+",
                }
            )
            self.stdout.write(self.style.SUCCESS(f"  [+] Student Ready: {student_user.email} (Username: {student_user.username}) / Student123!"))

            # 6. ENROLLMENTS
            for crs in [course_pf, course_oop]:
                Enrollment.objects.get_or_create(
                    student=student_profile,
                    course=crs,
                    defaults={'status': Enrollment.EnrollmentStatus.ACTIVE}
                )

            # 7. SAMPLE ATTENDANCE & ACADEMIC RECORDS FOR DEMO STUDENT
            today = timezone.now().date()
            for days_ago, st in [(5, Attendance.Status.PRESENT), (4, Attendance.Status.PRESENT), (3, Attendance.Status.PRESENT), (2, Attendance.Status.PRESENT), (1, Attendance.Status.PRESENT)]:
                d = today - datetime.timedelta(days=days_ago)
                Attendance.objects.get_or_create(
                    student=student_profile,
                    course=course_pf,
                    date=d,
                    defaults={'status': st}
                )

            AcademicRecord.objects.get_or_create(
                student=student_profile,
                course=course_pf,
                exam_name="Midterm Examination",
                defaults={
                    'exam_type': AcademicRecord.ExamType.MIDTERM,
                    'marks_obtained': Decimal('88.50'),
                    'total_marks': Decimal('100.00'),
                    'date_recorded': today - datetime.timedelta(days=10),
                }
            )

        self.stdout.write(self.style.SUCCESS("=== Demo Accounts Seeding Complete! ==="))
