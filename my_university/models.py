from sqlalchemy import (
    Column, INTEGER, String, ForeignKey, Integer, DATE, TIME, Table, UniqueConstraint
)
from sqlalchemy.orm import (
    relationship, DeclarativeBase
)
from flask_login import UserMixin


class Base(DeclarativeBase): pass


teacher_subject_association = Table('teacher_subject', Base.metadata,
                                    Column('teacher_id', Integer, ForeignKey('teacher.teacher_id'), primary_key=True),
                                    Column('subject_id', Integer, ForeignKey('subject.subject_id'), primary_key=True)
                                    )


class UserType(Base):
    __tablename__ = "user_type"

    user_type_id = Column(INTEGER, primary_key=True)
    type_name = Column(String(50), nullable=False, unique=True)

    users = relationship("User", back_populates="user_type_ref")


class User(Base, UserMixin):
    __tablename__ = "user"

    user_id = Column(INTEGER, primary_key=True)
    user_type_id = Column(INTEGER, ForeignKey("user_type.user_type_id"), nullable=False)
    hash_login = Column(String(255), nullable=False, unique=True)
    hash_password = Column(String(255), nullable=False)

    user_type_ref = relationship("UserType", back_populates="users")
    teacher = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")
    student = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    admin = relationship("Admin", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def get_id(self):
        return str(self.user_id)

class Admin(Base):
    __tablename__ = "admin"

    admin_id = Column(INTEGER, primary_key=True)
    user_id = Column(INTEGER, ForeignKey("user.user_id"), nullable=False, unique=True)
    full_name = Column(String(255), nullable=False)

    user = relationship("User", back_populates="admin")


class Student(Base):
    __tablename__ = "student"

    student_id = Column(INTEGER, primary_key=True)
    group_id = Column(INTEGER, ForeignKey("study_group.group_id"), nullable=False)
    user_id = Column(INTEGER, ForeignKey("user.user_id"), nullable=False, unique=True)
    full_name = Column(String(255), nullable=False)

    user = relationship("User", back_populates="student")
    study_group = relationship("StudyGroup", back_populates="students")


class Teacher(Base):
    __tablename__ = "teacher"

    teacher_id = Column(INTEGER, primary_key=True)
    user_id = Column(INTEGER, ForeignKey("user.user_id"), nullable=False, unique=True)
    department_id = Column(INTEGER, ForeignKey("department.department_id"), nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)

    user = relationship("User", back_populates="teacher")
    subjects = relationship("Subject", secondary=teacher_subject_association, back_populates="teachers")
    schedule = relationship("Schedule", back_populates="teacher")
    department = relationship("Department", back_populates="teachers")
    education_materials = relationship("EducationMaterial", back_populates="teacher")


class StudyGroup(Base):
    __tablename__ = "study_group"

    group_id = Column(INTEGER, primary_key=True)
    curriculum_id = Column(INTEGER, ForeignKey("curriculum.curriculum_id"), nullable=False)
    group_name = Column(String(255), nullable=False, unique=True)
    group_course = Column(Integer, nullable=False)

    students = relationship("Student", back_populates="study_group")
    schedule = relationship("Schedule", back_populates="study_group")
    curriculum = relationship("Curriculum", back_populates="study_group")


class Department(Base):
    __tablename__ = "department"

    department_id = Column(INTEGER, primary_key=True)
    department_name = Column(String(255), nullable=False, unique=True)

    teachers = relationship("Teacher", back_populates="department")


class ClassroomType(Base):
    __tablename__ = "classroom_type"

    classroom_id = Column(INTEGER, primary_key=True)
    classroom_name = Column(String(255), nullable=False, unique=True)

    classroom = relationship("Classroom", back_populates="classroom_type")


class Classroom(Base):
    __tablename__ = "classroom"

    class_id = Column(INTEGER, primary_key=True)
    class_type_id = Column(Integer, ForeignKey("classroom_type.classroom_id"), nullable=False)
    class_name = Column(String(255), nullable=False, unique=True)

    classroom_type = relationship("ClassroomType", back_populates="classroom")
    schedules = relationship("Schedule", back_populates="classroom")


class EducationForm(Base):
    __tablename__ = "education_form"

    education_form_id = Column(INTEGER, primary_key=True)
    education_form_name = Column(String(255), nullable=False, unique=True)

    curriculum = relationship("Curriculum", back_populates="education_form")


class Curriculum(Base):
    __tablename__ = "curriculum"

    curriculum_id = Column(INTEGER, primary_key=True)
    education_form_id = Column(INTEGER, ForeignKey("education_form.education_form_id"), nullable=False)
    education_level = Column(String(255), nullable=False)
    approval_year = Column(DATE, nullable=False)

    study_group = relationship("StudyGroup", back_populates="curriculum")
    curriculum_detail = relationship("CurriculumDetail", back_populates="curriculum")
    education_form = relationship("EducationForm", back_populates="curriculum")


class AssessmentType(Base):
    __tablename__ = "assessment_type"

    assessment_type_id = Column(INTEGER, primary_key=True)
    assessment_type_name = Column(String(255), nullable=False, unique=True)

    curriculum_detail = relationship("CurriculumDetail", back_populates="assessment_type")


class CurriculumDetail(Base):
    __tablename__ = "curriculum_detail"

    curriculum_detail_id = Column(INTEGER, primary_key=True)
    curriculum_id = Column(INTEGER, ForeignKey("curriculum.curriculum_id"), nullable=False)
    subject_id = Column(INTEGER, ForeignKey("subject.subject_id"), nullable=False)
    assessment_type_id = Column(INTEGER, ForeignKey("assessment_type.assessment_type_id"), nullable=False)
    semester = Column(Integer, nullable=False)
    hours_lecture = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('curriculum_id', 'subject_id', 'semester', name='_curriculum_subject_semester_uc'),
    )

    curriculum = relationship("Curriculum", back_populates="curriculum_detail")
    subject = relationship("Subject", back_populates="curriculum_detail")
    assessment_type = relationship("AssessmentType", back_populates="curriculum_detail")


class Subject(Base):
    __tablename__ = "subject"

    subject_id = Column(INTEGER, primary_key=True)
    subject_name = Column(String(255), nullable=False, unique=True)

    curriculum_detail = relationship("CurriculumDetail", back_populates="subject")
    teachers = relationship("Teacher", secondary=teacher_subject_association, back_populates="subjects")
    education_materials = relationship("EducationMaterial", back_populates="subject")
    schedule = relationship("Schedule", back_populates="subject")


class EducationMaterialType(Base):
    __tablename__ = "education_material_type"

    education_material_type_id = Column(INTEGER, primary_key=True)
    education_material_type_name = Column(String(255), nullable=False, unique=True)

    education_material = relationship("EducationMaterial", back_populates="education_material_type")


class EducationMaterial(Base):
    __tablename__ = "education_material"

    education_material_id = Column(INTEGER, primary_key=True)
    education_material_type_id = Column(INTEGER, ForeignKey("education_material_type.education_material_type_id"), nullable=False)
    subject_id = Column(INTEGER, ForeignKey("subject.subject_id"), nullable=False)
    teacher_id = Column(INTEGER, ForeignKey("teacher.teacher_id"), nullable=False)
    education_material_name = Column(String(255), nullable=False)
    education_material_link = Column(String(255), nullable=False)

    education_material_type = relationship("EducationMaterialType", back_populates="education_material")
    subject = relationship("Subject", back_populates="education_materials")
    teacher = relationship("Teacher", back_populates="education_materials")


class TimeSlot(Base):
    __tablename__ = "time_slot"

    time_slot_id = Column(INTEGER, primary_key=True)
    time_slot_name = Column(String(255), nullable=False, unique=True)
    time_start = Column(TIME, nullable=False)
    time_end = Column(TIME, nullable=False)

    schedule = relationship("Schedule", back_populates="time_slot")


class LessonType(Base):
    __tablename__ = "lesson_type"

    lesson_type_id = Column(INTEGER, primary_key=True)
    lesson_type_name = Column(String(255), nullable=False, unique=True)

    schedules = relationship("Schedule", back_populates="lesson_type")

class Schedule(Base):
    __tablename__ = "schedule"

    schedule_id = Column(INTEGER, primary_key=True)
    study_group_id = Column(INTEGER, ForeignKey("study_group.group_id"), nullable=False)
    teacher_id = Column(INTEGER, ForeignKey("teacher.teacher_id"), nullable=False)
    subject_id = Column(INTEGER, ForeignKey("subject.subject_id"), nullable=False)
    lesson_type_id = Column(INTEGER, ForeignKey("lesson_type.lesson_type_id"), nullable=False)
    classroom_id = Column(INTEGER, ForeignKey("classroom.class_id"), nullable=False)
    time_slot_id = Column(INTEGER, ForeignKey("time_slot.time_slot_id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('study_group_id', 'day_of_week', 'time_slot_id', name='_group_time_uc'),
    )

    study_group = relationship("StudyGroup", back_populates="schedule")
    teacher = relationship("Teacher", back_populates="schedule")
    subject = relationship("Subject", back_populates="schedule")
    time_slot = relationship("TimeSlot", back_populates="schedule")
    lesson_type = relationship("LessonType", back_populates="schedules")
    classroom = relationship("Classroom", back_populates="schedules")
