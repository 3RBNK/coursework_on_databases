from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import exc

from my_university.models import (
    User, Student,
    Teacher, UserType,
    StudyGroup, Department,
    Admin, TimeSlot,
    Schedule, Classroom,
    LessonType, Subject,
    Curriculum, ClassroomType
)
from my_university.forms import (LoginForm, RegistrationForm, ScheduleForm, DepartmentForm, StudyGroupForm, ClassroomForm)
from my_university.main import db_session

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('index.html')
    else:
        return redirect(url_for('main.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db_session.query(User).filter_by(hash_login=form.login.data).first()

        if user and check_password_hash(user.hash_password, form.password.data):
            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')

            return redirect(url_for('main.index'))
        else:
            flash('Неверный логин или пароль', 'danger')

    return render_template('login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('main.login'))


@bp.route('/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    form = RegistrationForm()

    form.submit.label.text = "Создать пользователя"

    groups = db_session.query(StudyGroup).all()
    form.group_id.choices = [(0, 'Не выбрано')] + [(g.group_id, g.group_name) for g in groups]

    departments = db_session.query(Department).all()
    form.department_id.choices = [(0, 'Не выбрано')] + [(d.department_id, d.department_name) for d in departments]

    if form.validate_on_submit():
        try:
            hashed_pw = generate_password_hash(form.password.data)
            user_type = db_session.query(UserType).filter_by(type_name=form.role.data).first()

            new_user = User(
                hash_login=form.login.data,
                hash_password=hashed_pw,
                user_type_id=user_type.user_type_id
            )
            db_session.add(new_user)
            db_session.flush()

            if form.role.data == 'student':
                new_student = Student(
                    user_id=new_user.user_id,
                    full_name=form.full_name.data,
                    group_id=form.group_id.data
                )
                db_session.add(new_student)

            elif form.role.data == 'teacher':
                new_teacher = Teacher(
                    user_id=new_user.user_id,
                    full_name=form.full_name.data,
                    department_id=form.department_id.data,
                    email=f"{form.login.data}@unidesk.ru"
                )
                db_session.add(new_teacher)

            elif form.role.data == 'admin':
                new_admin = Admin(
                    user_id=new_user.user_id,
                    full_name=form.full_name.data
                )
                db_session.add(new_admin)

            db_session.commit()

            flash(f'Пользователь {form.login.data} успешно создан!', 'success')
            return redirect(url_for('main.create_user'))

        except Exception as e:
            db_session.rollback()
            flash(f'Ошибка создания: {e}', 'danger')

    return render_template('create_user.html', form=form)


@bp.route('/schedule')
@login_required
def view_schedule():
    user = current_user
    query = db_session.query(Schedule)

    title = "Расписание занятий"

    if user.user_type_ref.type_name == 'student':
        query = query.filter_by(study_group_id=user.student.group_id)
        title = f"Расписание группы {user.student.study_group.group_name}"

    elif user.user_type_ref.type_name == 'teacher':
        query = query.filter_by(teacher_id=user.teacher.teacher_id)
        title = f"Расписание преподавателя {user.teacher.full_name}"

    schedules = query.order_by(Schedule.day_of_week, Schedule.time_slot_id).all()

    days = {1: 'Понедельник', 2: 'Вторник', 3: 'Среда', 4: 'Четверг', 5: 'Пятница', 6: 'Суббота', 7: 'Воскресенье'}

    return render_template('schedule_view.html', schedules=schedules, days=days, title=title)


@bp.route('/schedule/manage', methods=['GET', 'POST'])
@login_required
def manage_schedule():
    if current_user.user_type_ref.type_name != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.view_schedule'))

    form = ScheduleForm()

    form.study_group_id.choices = [(g.group_id, g.group_name) for g in db_session.query(StudyGroup).all()]
    form.teacher_id.choices = [(t.teacher_id, t.full_name) for t in db_session.query(Teacher).all()]
    form.subject_id.choices = [(s.subject_id, s.subject_name) for s in db_session.query(Subject).all()]
    form.lesson_type_id.choices = [(l.lesson_type_id, l.lesson_type_name) for l in db_session.query(LessonType).all()]
    form.classroom_id.choices = [(c.class_id, c.class_name) for c in db_session.query(Classroom).all()]

    form.time_slot_id.choices = [(t.time_slot_id, f"{t.time_slot_name} ({t.time_start.strftime('%H:%M')})") for t in
                                 db_session.query(TimeSlot).all()]

    if form.validate_on_submit():
        try:
            new_schedule = Schedule(
                study_group_id=form.study_group_id.data,
                teacher_id=form.teacher_id.data,
                subject_id=form.subject_id.data,
                lesson_type_id=form.lesson_type_id.data,
                classroom_id=form.classroom_id.data,
                time_slot_id=form.time_slot_id.data,
                day_of_week=form.day_of_week.data
            )
            db_session.add(new_schedule)
            db_session.commit()
            flash('Занятие успешно добавлено!', 'success')
            return redirect(url_for('main.manage_schedule'))

        except exc.IntegrityError:
            db_session.rollback()
            flash('Ошибка: Конфликт в расписании! (Аудитория, группа или преподаватель уже заняты в это время)',
                  'danger')
        except Exception as e:
            db_session.rollback()
            flash(f'Ошибка: {e}', 'danger')

    all_schedules = db_session.query(Schedule).order_by(Schedule.day_of_week, Schedule.time_slot_id).all()
    days = {1: 'Понедельник', 2: 'Вторник', 3: 'Среда', 4: 'Четверг', 5: 'Пятница', 6: 'Суббота', 7: 'Воскресенье'}

    return render_template('schedule_manage.html', form=form, schedules=all_schedules, days=days)


@bp.route('/departments')
@login_required
def departments_list():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    departments = db_session.query(Department).order_by(Department.department_name).all()
    return render_template('departments_list.html', departments=departments)


@bp.route('/departments/new', methods=['GET', 'POST'])
@login_required
def department_create():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    form = DepartmentForm()
    if form.validate_on_submit():
        try:
            new_dep = Department(department_name=form.department_name.data)
            db_session.add(new_dep)
            db_session.commit()
            flash('Кафедра успешно создана!', 'success')
            return redirect(url_for('main.departments_list'))
        except Exception as e:
            db_session.rollback()
            flash(f'Ошибка: {e}', 'danger')

    return render_template('department_form.html', form=form, title="Новая кафедра")


@bp.route('/departments/<int:dep_id>/edit', methods=['GET', 'POST'])
@login_required
def department_edit(dep_id):
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    dep = db_session.query(Department).get(dep_id)
    if not dep:
        abort(404)

    form = DepartmentForm(obj=dep)
    if form.validate_on_submit():
        try:
            dep.department_name = form.department_name.data
            db_session.commit()
            flash('Кафедра обновлена!', 'success')
            return redirect(url_for('main.departments_list'))
        except Exception as e:
            db_session.rollback()
            flash(f'Ошибка: {e}', 'danger')

    return render_template('department_form.html', form=form, title="Редактирование кафедры")


@bp.route('/departments/<int:dep_id>/delete', methods=['POST'])
@login_required
def department_delete(dep_id):
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    dep = db_session.query(Department).get(dep_id)
    if dep:
        try:
            db_session.delete(dep)
            db_session.commit()
            flash('Кафедра удалена.', 'success')
        except Exception as e:
            db_session.rollback()
            flash('Нельзя удалить кафедру, к которой привязаны преподаватели!', 'danger')

    return redirect(url_for('main.departments_list'))

@bp.route('/groups')
@login_required
def groups_list():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    groups = db_session.query(StudyGroup).order_by(StudyGroup.group_course, StudyGroup.group_name).all()
    return render_template('groups_list.html', groups=groups)


@bp.route('/groups/new', methods=['GET', 'POST'])
@login_required
def group_create():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    form = StudyGroupForm()
    curriculums = db_session.query(Curriculum).all()
    form.curriculum_id.choices = [(c.curriculum_id, f"{c.education_level} ({c.education_form.education_form_name})") for
                                  c in curriculums]

    if form.validate_on_submit():
        try:
            new_group = StudyGroup(
                group_name=form.group_name.data,
                group_course=form.group_course.data,
                curriculum_id=form.curriculum_id.data
            )
            db_session.add(new_group)
            db_session.commit()
            flash('Группа создана!', 'success')
            return redirect(url_for('main.groups_list'))
        except Exception as e:
            db_session.rollback()
            flash(f'Ошибка: {e}', 'danger')

    return render_template('group_form.html', form=form, title="Новая группа")


@bp.route('/groups/<int:group_id>/delete', methods=['POST'])
@login_required
def group_delete(group_id):
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    group = db_session.query(StudyGroup).get(group_id)
    if group:
        try:
            db_session.delete(group)
            db_session.commit()
            flash('Группа удалена.', 'success')
        except Exception:
            db_session.rollback()
            flash('Нельзя удалить группу, в которой есть студенты или расписание!', 'danger')

    return redirect(url_for('main.groups_list'))


@bp.route('/classrooms')
@login_required
def classrooms_list():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    # Загружаем аудитории и сортируем по названию
    classrooms = db_session.query(Classroom).order_by(Classroom.class_name).all()
    return render_template('classrooms_list.html', classrooms=classrooms)


@bp.route('/classrooms/new', methods=['GET', 'POST'])
@login_required
def classroom_create():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    form = ClassroomForm()

    # Заполняем список типов аудиторий из БД (Лекционная, Компьютерная...)
    types = db_session.query(ClassroomType).all()
    form.class_type_id.choices = [(t.classroom_id, t.classroom_name) for t in types]

    if form.validate_on_submit():
        try:
            new_classroom = Classroom(
                class_name=form.class_name.data,
                class_type_id=form.class_type_id.data
            )
            db_session.add(new_classroom)
            db_session.commit()
            flash(f'Аудитория {new_classroom.class_name} создана!', 'success')
            return redirect(url_for('main.classrooms_list'))
        except Exception as e:
            db_session.rollback()
            flash(f'Ошибка: {e}', 'danger')

    return render_template('classroom_form.html', form=form, title="Новая аудитория")


@bp.route('/classrooms/<int:cls_id>/delete', methods=['POST'])
@login_required
def classroom_delete(cls_id):
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    classroom = db_session.query(Classroom).get(cls_id)
    if classroom:
        try:
            db_session.delete(classroom)
            db_session.commit()
            flash('Аудитория удалена.', 'success')
        except Exception:
            db_session.rollback()
            flash('Нельзя удалить аудиторию, если в ней уже стоят занятия в расписании!', 'danger')

    return redirect(url_for('main.classrooms_list'))