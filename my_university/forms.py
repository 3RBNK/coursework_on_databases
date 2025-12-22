from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, Optional


class LoginForm(FlaskForm):
    """Форма для входа"""
    login = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    """Форма для создания пользователя (администратором)"""
    login = StringField('Логин', validators=[DataRequired(), Length(min=4, max=25)])

    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])

    confirm_password = PasswordField('Подтверждение пароля',
                                     validators=[DataRequired(),
                                                 EqualTo('password', message='Пароли должны совпадать')])

    full_name = StringField('ФИО', validators=[DataRequired()])

    role = SelectField('Роль пользователя', choices=[
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
        ('admin', 'Администратор')
    ], validators=[DataRequired()])

    group_id = SelectField('Учебная группа', coerce=int, choices=[], validators=[Optional()])
    department_id = SelectField('Кафедра', coerce=int, choices=[], validators=[Optional()])

    submit = SubmitField('Создать пользователя')


class ScheduleForm(FlaskForm):
    """Форма для добавления занятия в расписание"""
    study_group_id = SelectField('Группа', coerce=int, validators=[DataRequired()])
    teacher_id = SelectField('Преподаватель', coerce=int, validators=[DataRequired()])
    subject_id = SelectField('Предмет', coerce=int, validators=[DataRequired()])
    lesson_type_id = SelectField('Тип занятия', coerce=int, validators=[DataRequired()])
    classroom_id = SelectField('Аудитория', coerce=int, validators=[DataRequired()])
    time_slot_id = SelectField('Время (Пара)', coerce=int, validators=[DataRequired()])

    day_of_week = SelectField('День недели', coerce=int, choices=[
        (1, 'Понедельник'),
        (2, 'Вторник'),
        (3, 'Среда'),
        (4, 'Четверг'),
        (5, 'Пятница'),
        (6, 'Суббота'),
        (7, 'Воскресенье')
    ], validators=[DataRequired()])

    submit = SubmitField('Добавить в расписание')


class DepartmentForm(FlaskForm):
    """Форма для создания/редактирования кафедры"""
    department_name = StringField('Название кафедры', validators=[DataRequired(), Length(max=255)])
    submit = SubmitField('Сохранить')


class StudyGroupForm(FlaskForm):
    """Форма для создания/редактирования группы"""
    group_name = StringField('Название группы (например, ИВТ-21)', validators=[DataRequired(), Length(max=50)])
    group_course = IntegerField('Курс', validators=[DataRequired()])

    curriculum_id = SelectField('Учебный план', coerce=int, validators=[DataRequired()])

    submit = SubmitField('Сохранить')


class ClassroomForm(FlaskForm):
    """Форма для добавления/редактирования аудитории"""
    class_name = StringField('Номер/Название аудитории', validators=[DataRequired(), Length(max=50)])

    class_type_id = SelectField('Тип аудитории', coerce=int, validators=[DataRequired()])

    submit = SubmitField('Сохранить')
