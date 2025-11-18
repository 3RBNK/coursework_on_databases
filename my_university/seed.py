from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from my_university.config import get_db_url
from my_university.db_class import (
    Base,
    ClassroomType, LessonType,
    UserType, EducationForm,
    AssessmentType, TimeSlot,
    EducationMaterialType,
)


def seed_database():
    engine = create_engine(get_db_url())
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        user_types_to_add = [
            UserType(type_name='student'),
            UserType(type_name='teacher'),
            UserType(type_name='admin')
        ]
        for utype in user_types_to_add:
            if not session.query(UserType).filter_by(type_name=utype.type_name).first():
                session.add(utype)
                print(f"  - Добавлен тип пользователя: {utype.type_name}")


        class_types_to_add = [
            ClassroomType(classroom_name="Лекционная аудитория"),
            ClassroomType(classroom_name="Класс для практических заняzтий"),
            ClassroomType(classroom_name="Компьютерный класс"),
            ClassroomType(classroom_name="Лаборатория"),
        ]

        for ctype in class_types_to_add:
            if not session.query(ClassroomType).filter_by(classroom_name=ctype.classroom_name).first():
                session.add(ctype)
                print(f"  - Добавлен тип класса: {ctype.classroom_name}")


        lesson_types_to_add = [
            LessonType(lesson_type_name="Лекция"),
            LessonType(lesson_type_name="Практика"),
            LessonType(lesson_type_name="Лабораторная работа")
        ]

        for ltype in lesson_types_to_add:
            if not session.query(LessonType).filter_by(lesson_type_name=ltype.lesson_type_name).first():
                session.add(ltype)
                print(f"  - Добавлена форма занятия: {ltype.lesson_type_name}")


        education_material_form_to_add = [
            EducationMaterialType(education_material_type_name="Учебник"),
            EducationMaterialType(education_material_type_name="Методическое пособие"),
            EducationMaterialType(education_material_type_name="Лабораторный практикум"),
            EducationMaterialType(education_material_type_name="Презентация"),
            EducationMaterialType(education_material_type_name="Ссылка на ресурс"),
        ]

        for education_material_form in education_material_form_to_add:
            if not session.query(EducationMaterialType).filter_by(education_material_type_name=education_material_form.education_material_type_name).first():
                session.add(education_material_form)
                print(f"  - Добавлен тип материала: {education_material_form.education_material_type_name}")


        edu_forms_to_add = [
            EducationForm(education_form_name='Очная'),
            EducationForm(education_form_name='Заочная'),
            EducationForm(education_form_name='Очно-заочная')
        ]
        for form in edu_forms_to_add:
            if not session.query(EducationForm).filter_by(education_form_name=form.education_form_name).first():
                session.add(form)
                print(f"  - Добавлена форма обучения: {form.education_form_name}")


        assessment_types_to_add = [
            AssessmentType(assessment_type_name='Экзамен'),
            AssessmentType(assessment_type_name='Зачет'),
            AssessmentType(assessment_type_name='Дифференцированный зачет')
        ]
        for atype in assessment_types_to_add:
            if not session.query(AssessmentType).filter_by(assessment_type_name=atype.assessment_type_name).first():
                session.add(atype)
                print(f"  - Добавлен тип аттестации: {atype.assessment_type_name}")


        time_slots_to_add = [
            TimeSlot(time_slot_name='1 пара, 1 часть', time_start='08:15', time_end='09:00'),
            TimeSlot(time_slot_name='1 пара, 2 часть', time_start='09:05', time_end='09:50'),
            TimeSlot(time_slot_name='2 пара, 1 часть', time_start='10:00', time_end='10:45'),
            TimeSlot(time_slot_name='2 пара, 2 часть', time_start='10:50', time_end='11:35'),
            TimeSlot(time_slot_name='3 пара, 1 часть', time_start='11:45', time_end='12:30'),
            TimeSlot(time_slot_name='3 пара, 2 часть', time_start='12:35', time_end='13:20'),
            TimeSlot(time_slot_name='3 пара, 3 часть', time_start='13:25', time_end='14:10'),
            TimeSlot(time_slot_name='4 пара, 1 часть', time_start='14:20', time_end='15:05'),
            TimeSlot(time_slot_name='4 пара, 2 часть', time_start='15:10', time_end='15:55'),
            TimeSlot(time_slot_name='5 пара, 1 часть', time_start='16:05', time_end='16:50'),
            TimeSlot(time_slot_name='5 пара, 2 часть', time_start='16:55', time_end='17:40'),
            TimeSlot(time_slot_name='6 пара, 1 часть', time_start='17:50', time_end='18:35'),
            TimeSlot(time_slot_name='6 пара, 2 часть', time_start='18:40', time_end='19:25'),
            TimeSlot(time_slot_name='7 пара, 1 часть', time_start='19:35', time_end='20:20'),
            TimeSlot(time_slot_name='7 пара, 2 часть', time_start='20:25', time_end='21:10')
        ]
        for slot in time_slots_to_add:
            if not session.query(TimeSlot).filter_by(time_slot_name=slot.time_slot_name).first():
                session.add(slot)
                print(f"  - Добавлен таймслот: {slot.time_slot_name}")


        session.commit()
        print("Данные успешно сохранены в БД.")

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        session.rollback()
    finally:
        session.close()
        print("Соединение с БД закрыто.")


seed_database()