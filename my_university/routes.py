import csv
import json
import io
from flask import Blueprint, render_template, redirect, url_for, flash, abort, send_file, request, Response, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError

from my_university.models import (
    User, Student,
    Teacher, UserType,
    StudyGroup, Department,
    Admin, TimeSlot,
    Schedule, Classroom,
    LessonType, Subject,
    Curriculum, ClassroomType,
    EducationMaterial, EducationMaterialType,
    CurriculumDetail, AssessmentType,
    EducationForm,
)
from my_university.forms import (LoginForm, RegistrationForm, ScheduleForm, DepartmentForm, StudyGroupForm,
                                 ClassroomForm, MaterialUploadForm, SubjectForm, CurriculumDetailForm, CurriculumForm)
from my_university.main import db_session
from my_university.s3_client import upload_file_to_minio, get_file_content, delete_file_from_minio

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.user_type_ref.type_name in ['student', 'teacher']:
            return redirect(url_for('main.schedule_view'))

        return render_template('index.html')
    else:
        return redirect(url_for('main.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.user_type_ref.type_name in ['student', 'teacher']:
            return redirect(url_for('main.schedule_view'))
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db_session.query(User).filter_by(hash_login=form.login.data).first()

        if user and check_password_hash(user.hash_password, form.password.data):
            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)

            role = user.user_type_ref.type_name

            if role == 'student' or role == 'teacher':
                return redirect(url_for('main.schedule_view'))
            else:
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

    classrooms = db_session.query(Classroom).order_by(Classroom.class_name).all()
    return render_template('classrooms_list.html', classrooms=classrooms)


@bp.route('/classrooms/new', methods=['GET', 'POST'])
@login_required
def classroom_create():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    form = ClassroomForm()

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


@bp.route('/materials')
@login_required
def materials_list():
    query = db_session.query(EducationMaterial).join(Teacher).join(Department)

    search_text = request.args.get('search', '').strip()
    dept_id = request.args.get('department_id', type=int)
    teacher_id = request.args.get('teacher_id', type=int)

    show_mine = request.args.get('mine')

    if search_text:
        query = query.filter(EducationMaterial.education_material_name.ilike(f'%{search_text}%'))

    if dept_id:
        query = query.filter(Teacher.department_id == dept_id)

    if teacher_id:
        query = query.filter(EducationMaterial.teacher_id == teacher_id)

    if current_user.user_type_ref.type_name == 'teacher':
        if show_mine:
            query = query.filter(EducationMaterial.teacher_id == current_user.teacher.teacher_id)

    materials = query.order_by(EducationMaterial.education_material_name).all()

    all_departments = db_session.query(Department).order_by(Department.department_name).all()
    all_teachers = db_session.query(Teacher).order_by(Teacher.full_name).all()

    return render_template(
        'materials_list.html',
        materials=materials,
        all_departments=all_departments,
        all_teachers=all_teachers,
        selected_search=search_text,
        selected_dept=dept_id,
        selected_teacher=teacher_id,
        is_showing_mine=show_mine
    )


@bp.route('/materials/upload', methods=['GET', 'POST'])
@login_required
def material_upload():
    if current_user.user_type_ref.type_name != 'teacher':
        abort(403)

    form = MaterialUploadForm()
    form.subject_id.choices = [(s.subject_id, s.subject_name) for s in db_session.query(Subject).all()]
    form.type_id.choices = [(t.education_material_type_id, t.education_material_type_name) for t in
                            db_session.query(EducationMaterialType).all()]

    if form.validate_on_submit():
        if form.file.data:
            file = form.file.data
            filename = secure_filename(file.filename)
            teacher_id = current_user.teacher.teacher_id
            object_name = f"teacher_{teacher_id}/{filename}"
            upload_file_to_minio(file.stream, object_name, file.content_type)
            final_link = object_name

        elif form.link_url.data:
            final_link = form.link_url.data

        else:
            flash('Необходимо либо загрузить файл, либо указать ссылку!', 'warning')
            return render_template('material_upload.html', form=form)

        try:
            new_material = EducationMaterial(
                education_material_type_id=form.type_id.data,
                subject_id=form.subject_id.data,
                teacher_id=current_user.teacher.teacher_id,
                education_material_name=form.material_name.data,
                education_material_link=final_link
            )
            db_session.add(new_material)
            db_session.commit()
            flash('Материал сохранен!', 'success')
            return redirect(url_for('main.materials_list'))
        except Exception as e:
            db_session.rollback()
            flash(f'Ошибка: {e}', 'danger')

    return render_template('material_upload.html', form=form)


@bp.route('/materials/download/<int:material_id>')
@login_required
def material_download(material_id):
    material = db_session.query(EducationMaterial).get(material_id)
    if not material:
        abort(404)

    link = material.education_material_link

    if link.startswith('http://') or link.startswith('https://'):
        return redirect(link)

    file_stream = get_file_content(link)

    if file_stream is None:
        flash('Ошибка: Файл не найден в хранилище', 'danger')
        return redirect(url_for('main.materials_list'))

    original_filename = link.split('/')[-1]

    return send_file(
        file_stream,
        as_attachment=True,
        download_name=original_filename,
        mimetype=file_stream.headers.get('content-type')
    )


@bp.route('/materials/<int:material_id>/delete', methods=['POST'])
@login_required
def material_delete(material_id):
    material = db_session.query(EducationMaterial).get(material_id)
    if not material:
        abort(404)

    is_admin = current_user.user_type_ref.type_name == 'admin'
    is_owner = False

    if current_user.user_type_ref.type_name == 'teacher':
        if material.teacher_id == current_user.teacher.teacher_id:
            is_owner = True

    if not is_admin and not is_owner:
        abort(403)

    try:
        link = material.education_material_link
        if not (link.startswith('http://') or link.startswith('https://')):
            delete_file_from_minio(link)

        db_session.delete(material)
        db_session.commit()

        flash('Учебный материал удален.', 'success')

    except Exception as e:
        db_session.rollback()
        flash(f'Ошибка при удалении: {e}', 'danger')

    return redirect(url_for('main.materials_list'))


@bp.route('/subjects')
@login_required
def subjects_list():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    subjects = db_session.query(Subject).order_by(Subject.subject_name).all()
    return render_template('subjects_list.html', subjects=subjects)


@bp.route('/subjects/new', methods=['GET', 'POST'])
@login_required
def subject_create():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    form = SubjectForm()

    if form.validate_on_submit():
        try:
            new_subject = Subject(
                subject_name=form.subject_name.data
            )
            db_session.add(new_subject)
            db_session.commit()
            flash(f'Предмет "{new_subject.subject_name}" создан!', 'success')
            return redirect(url_for('main.subjects_list'))
        except Exception as e:
            db_session.rollback()
            flash(f'Ошибка: {e}', 'danger')

    return render_template('subject_form.html', form=form, title="Новый предмет")


@bp.route('/subjects/<int:sub_id>/delete', methods=['POST'])
@login_required
def subject_delete(sub_id):
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    subject = db_session.query(Subject).get(sub_id)
    if subject:
        try:
            db_session.delete(subject)
            db_session.commit()
            flash('Предмет удален.', 'success')
        except Exception:
            db_session.rollback()
            flash('Нельзя удалить предмет, который уже используется в расписании или материалах!', 'danger')

    return redirect(url_for('main.subjects_list'))


@bp.route('/curriculums')
@login_required
def curriculums_list():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    curriculums = db_session.query(Curriculum).order_by(Curriculum.approval_year.desc()).all()
    return render_template('curriculums_list.html', curriculums=curriculums)


@bp.route('/curriculums/new', methods=['GET', 'POST'])
@login_required
def curriculum_create():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    form = CurriculumForm()
    edu_forms = db_session.query(EducationForm).all()
    form.education_form_id.choices = [(ef.education_form_id, ef.education_form_name) for ef in edu_forms]

    if form.validate_on_submit():
        try:
            new_curr = Curriculum(
                education_level=form.education_level.data,
                education_form_id=form.education_form_id.data,
                approval_year=form.approval_year.data
            )
            db_session.add(new_curr)
            db_session.commit()
            flash('Учебный план создан! Теперь наполните его предметами.', 'success')
            return redirect(url_for('main.curriculum_view', curr_id=new_curr.curriculum_id))
        except Exception as e:
            db_session.rollback()
            flash(f'Ошибка: {e}', 'danger')

    return render_template('curriculum_form.html', form=form, title="Новый учебный план")


@bp.route('/curriculums/<int:curr_id>', methods=['GET', 'POST'])
@login_required
def curriculum_view(curr_id):
    """Страница просмотра и наполнения конкретного плана"""
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    curriculum = db_session.query(Curriculum).get(curr_id)
    if not curriculum:
        abort(404)

    form = CurriculumDetailForm()

    form.subject_id.choices = [(s.subject_id, s.subject_name) for s in
                               db_session.query(Subject).order_by(Subject.subject_name).all()]
    form.assessment_type_id.choices = [(a.assessment_type_id, a.assessment_type_name) for a in
                                       db_session.query(AssessmentType).all()]

    if form.validate_on_submit():
        try:
            detail = CurriculumDetail(
                curriculum_id=curr_id,
                subject_id=form.subject_id.data,
                assessment_type_id=form.assessment_type_id.data,
                semester=form.semester.data,
                hours_lecture=form.hours_lecture.data
            )
            db_session.add(detail)
            db_session.commit()
            flash('Предмет добавлен в план.', 'success')
            return redirect(url_for('main.curriculum_view', curr_id=curr_id))
        except Exception as e:
            db_session.rollback()

            flash(f'Ошибка: Возможно, этот предмет уже есть в этом семестре. {e}', 'danger')

    details = db_session.query(CurriculumDetail) \
        .filter_by(curriculum_id=curr_id) \
        .order_by(CurriculumDetail.semester, CurriculumDetail.subject_id).all()

    return render_template('curriculum_view.html', curriculum=curriculum, details=details, form=form)


@bp.route('/curriculums/detail/<int:detail_id>/delete', methods=['POST'])
@login_required
def curriculum_detail_delete(detail_id):
    """Удаление предмета из плана"""
    detail = db_session.query(CurriculumDetail).get(detail_id)
    if detail:
        curr_id = detail.curriculum_id
        db_session.delete(detail)
        db_session.commit()
        flash('Предмет удален из плана.', 'success')
        return redirect(url_for('main.curriculum_view', curr_id=curr_id))
    return redirect(url_for('main.curriculums_list'))


def transform_schedule_to_grid(schedule_items, time_slots):
    """
    Превращает список записей из БД в словарь:
    grid[день_недели][id_таймслота] = Занятие
    """
    grid = {day: {} for day in range(1, 7)}

    for item in schedule_items:
        grid[item.day_of_week][item.time_slot_id] = item

    return grid


@bp.route('/schedule')
@login_required
def schedule_view():
    target_group_id = None
    target_teacher_id = None

    role_name = current_user.user_type_ref.type_name

    all_groups = db_session.query(StudyGroup).order_by(StudyGroup.group_name).all()
    all_teachers = db_session.query(Teacher).order_by(Teacher.full_name).all()

    if role_name == 'admin':
        if request.args.get('group_id'):
            target_group_id = int(request.args.get('group_id'))
        elif request.args.get('teacher_id'):
            target_teacher_id = int(request.args.get('teacher_id'))

    elif role_name == 'student':
        if current_user.student:
            target_group_id = current_user.student.group_id

    elif role_name == 'teacher':
        if current_user.teacher:
            target_teacher_id = current_user.teacher.teacher_id

    query = db_session.query(Schedule)
    title = "Расписание"

    if target_group_id:
        query = query.filter_by(study_group_id=target_group_id)
        grp = db_session.query(StudyGroup).get(target_group_id)
        if grp: title = f"Расписание группы {grp.group_name}"

    elif target_teacher_id:
        query = query.filter_by(teacher_id=target_teacher_id)
        tch = db_session.query(Teacher).get(target_teacher_id)
        if tch: title = f"Расписание преподавателя {tch.full_name}"
    else:
        query = query.filter(False)

    schedule_items = query.all()
    time_slots = db_session.query(TimeSlot).order_by(TimeSlot.time_start).all()
    grid = transform_schedule_to_grid(schedule_items, time_slots)

    return render_template(
        'schedule_view.html',
        grid=grid,
        time_slots=time_slots,
        days={1: 'ПН', 2: 'ВТ', 3: 'СР', 4: 'ЧТ', 5: 'ПТ', 6: 'СБ'},
        title=title,
        all_groups=all_groups,
        all_teachers=all_teachers,
        target_group_id=target_group_id,
        target_teacher_id=target_teacher_id
    )


@bp.route('/schedule/<int:sched_id>/delete', methods=['POST'])
@login_required
def schedule_delete(sched_id):
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    item = db_session.query(Schedule).get(sched_id)
    if item:
        grp_id = item.study_group_id
        db_session.delete(item)
        db_session.commit()
        flash('Занятие отменено.', 'success')
        return redirect(url_for('main.schedule_view', group_id=grp_id))

    return redirect(url_for('main.schedule_view'))


@bp.route('/schedule/<int:sched_id>/edit', methods=['GET', 'POST'])
@login_required
def schedule_edit(sched_id):
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    schedule_item = db_session.query(Schedule).get(sched_id)
    if not schedule_item:
        abort(404)

    form = ScheduleForm(obj=schedule_item)

    form.study_group_id.choices = [(g.group_id, g.group_name) for g in
                                   db_session.query(StudyGroup).order_by(StudyGroup.group_name).all()]
    form.teacher_id.choices = [(t.teacher_id, t.full_name) for t in
                               db_session.query(Teacher).order_by(Teacher.full_name).all()]
    form.subject_id.choices = [(s.subject_id, s.subject_name) for s in
                               db_session.query(Subject).order_by(Subject.subject_name).all()]
    form.lesson_type_id.choices = [(l.lesson_type_id, l.lesson_type_name) for l in db_session.query(LessonType).all()]
    form.classroom_id.choices = [(c.class_id, f"{c.class_name} ({c.classroom_type.classroom_name})") for c in
                                 db_session.query(Classroom).order_by(Classroom.class_name).all()]
    form.time_slot_id.choices = [(ts.time_slot_id, f"{ts.time_slot_name} ({ts.time_start.strftime('%H:%M')})") for ts in
                                 db_session.query(TimeSlot).order_by(TimeSlot.time_start).all()]

    if form.validate_on_submit():
        try:
            teacher_conflict = db_session.query(Schedule).filter(
                Schedule.teacher_id == form.teacher_id.data,
                Schedule.day_of_week == form.day_of_week.data,
                Schedule.time_slot_id == form.time_slot_id.data,
                Schedule.classroom_id != form.classroom_id.data,
                Schedule.schedule_id != sched_id
            ).first()

            if teacher_conflict:
                flash(f'Преподаватель занят в ауд. {teacher_conflict.classroom.class_name}', 'danger')
                return render_template('schedule_form.html', form=form, title="Редактирование")

            room_conflict = db_session.query(Schedule).filter(
                Schedule.classroom_id == form.classroom_id.data,
                Schedule.day_of_week == form.day_of_week.data,
                Schedule.time_slot_id == form.time_slot_id.data,
                Schedule.teacher_id != form.teacher_id.data,
                Schedule.schedule_id != sched_id  # <--- ВАЖНО
            ).first()

            if room_conflict:
                flash(f'Аудитория занята преподавателем {room_conflict.teacher.full_name}', 'danger')
                return render_template('schedule_form.html', form=form, title="Редактирование")

            form.populate_obj(schedule_item)

            db_session.commit()
            flash('Занятие успешно изменено!', 'success')

            return redirect(url_for('main.schedule_view', group_id=schedule_item.study_group_id))


        except IntegrityError as e:
            db_session.rollback()
            error_text = str(e.orig)
            if '_group_time_uc' in error_text:
                flash('Ошибка: У этой ГРУППЫ уже стоит занятие в это время!', 'danger')
            else:
                flash('Ошибка: Такое занятие уже существует или нарушает правила уникальности.', 'danger')

    form.submit.label.text = "Сохранить изменения"

    return render_template('schedule_form.html', form=form, title="Редактирование занятия")


@bp.route('/schedule/new', methods=['GET', 'POST'])
@login_required
def schedule_create():
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    form = ScheduleForm()

    form.study_group_id.choices = [(g.group_id, g.group_name) for g in
                                   db_session.query(StudyGroup).order_by(StudyGroup.group_name).all()]
    form.teacher_id.choices = [(t.teacher_id, t.full_name) for t in
                               db_session.query(Teacher).order_by(Teacher.full_name).all()]
    form.subject_id.choices = [(s.subject_id, s.subject_name) for s in
                               db_session.query(Subject).order_by(Subject.subject_name).all()]
    form.lesson_type_id.choices = [(l.lesson_type_id, l.lesson_type_name) for l in db_session.query(LessonType).all()]

    form.classroom_id.choices = [(c.class_id, f"{c.class_name} ({c.classroom_type.classroom_name})") for c in
                                 db_session.query(Classroom).order_by(Classroom.class_name).all()]

    form.time_slot_id.choices = [(ts.time_slot_id, f"{ts.time_slot_name} ({ts.time_start.strftime('%H:%M')})") for ts in
                                 db_session.query(TimeSlot).order_by(TimeSlot.time_start).all()]

    if request.method == 'GET':
        req_group = request.args.get('group_id', type=int)
        req_day = request.args.get('day', type=int)
        req_slot = request.args.get('slot', type=int)

        if req_group:
            form.study_group_id.data = req_group
        if req_day:
            form.day_of_week.data = req_day
        if req_slot:
            form.time_slot_id.data = req_slot

    if form.validate_on_submit():
        try:
            teacher_conflict = db_session.query(Schedule).filter(
                Schedule.teacher_id == form.teacher_id.data,
                Schedule.day_of_week == form.day_of_week.data,
                Schedule.time_slot_id == form.time_slot_id.data,
                Schedule.classroom_id != form.classroom_id.data,
            ).first()

            if teacher_conflict:
                flash(
                    f'Ошибка: Преподаватель уже ведет пару в это время в другой аудитории ({teacher_conflict.classroom.class_name})!',
                    'danger')
                return render_template('schedule_form.html', form=form, title="Добавить занятие")

            room_conflict = db_session.query(Schedule).filter(
                Schedule.classroom_id == form.classroom_id.data,
                Schedule.day_of_week == form.day_of_week.data,
                Schedule.time_slot_id == form.time_slot_id.data,
                Schedule.teacher_id != form.teacher_id.data
            ).first()

            if room_conflict:
                flash(f'Ошибка: Аудитория занята другим преподавателем ({room_conflict.teacher.full_name})!', 'danger')
                return render_template('schedule_form.html', form=form, title="Добавить занятие")

            new_schedule = Schedule(
                study_group_id=form.study_group_id.data,
                teacher_id=form.teacher_id.data,
                subject_id=form.subject_id.data,
                lesson_type_id=form.lesson_type_id.data,
                classroom_id=form.classroom_id.data,
                day_of_week=form.day_of_week.data,
                time_slot_id=form.time_slot_id.data
            )
            db_session.add(new_schedule)
            db_session.commit()

            flash('Занятие добавлено в расписание!', 'success')

            return redirect(url_for('main.schedule_view', group_id=form.study_group_id.data))

        except IntegrityError as e:
            db_session.rollback()
            error_text = str(e.orig)
            if '_group_time_uc' in error_text:
                flash('Ошибка: У этой ГРУППЫ уже стоит занятие в это время!', 'danger')
            else:
                flash('Ошибка: Такое занятие уже существует или нарушает правила уникальности.', 'danger')

    return render_template('schedule_form.html', form=form, title="Добавить занятие")


@bp.route('/schedule/export/csv')
@login_required
def schedule_export_csv():
    group_id = request.args.get('group_id', type=int)
    teacher_id = request.args.get('teacher_id', type=int)

    if not group_id and not teacher_id:
        flash('Выберите группу или преподавателя для экспорта!', 'warning')
        return redirect(url_for('main.schedule_view'))

    query = db_session.query(Schedule).join(TimeSlot).join(Subject).join(Classroom).join(LessonType)

    filename = "schedule"
    if group_id:
        query = query.filter(Schedule.study_group_id == group_id)
        filename = f"schedule_group_{group_id}"
    elif teacher_id:
        query = query.filter(Schedule.teacher_id == teacher_id)
        filename = f"schedule_teacher_{teacher_id}"

    items = query.order_by(Schedule.day_of_week, TimeSlot.time_start).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Day', 'Time', 'Subject', 'Type', 'Room', 'Group', 'Teacher'])

    days_map = {1: 'ПН', 2: 'ВТ', 3: 'СР', 4: 'ЧТ', 5: 'ПТ', 6: 'СБ'}

    for item in items:
        writer.writerow([
            days_map.get(item.day_of_week, str(item.day_of_week)),
            f"{item.time_slot.time_start.strftime('%H:%M')} - {item.time_slot.time_end.strftime('%H:%M')}",
            item.subject.subject_name,
            item.lesson_type.lesson_type_name,
            item.classroom.class_name,
            item.study_group.group_name,
            item.teacher.full_name
        ])

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}.csv"}
    )


@bp.route('/schedule/export/json')
@login_required
def schedule_export_json():
    group_id = request.args.get('group_id', type=int)
    teacher_id = request.args.get('teacher_id', type=int)

    if not group_id and not teacher_id:
        flash('Выберите группу или преподавателя!', 'warning')
        return redirect(url_for('main.schedule_view'))

    query = db_session.query(Schedule).join(TimeSlot).join(Subject)

    filename = "schedule"
    if group_id:
        query = query.filter(Schedule.study_group_id == group_id)
        filename = f"schedule_group_{group_id}"
    elif teacher_id:
        query = query.filter(Schedule.teacher_id == teacher_id)
        filename = f"schedule_teacher_{teacher_id}"

    items = query.order_by(Schedule.day_of_week, TimeSlot.time_start).all()

    data = []
    days_map = {1: 'Понедельник', 2: 'Вторник', 3: 'Среда', 4: 'Четверг', 5: 'Пятница', 6: 'Суббота'}

    for item in items:
        data.append({
            'day_of_week': days_map.get(item.day_of_week),
            'time_start': item.time_slot.time_start.strftime('%H:%M'),
            'time_end': item.time_slot.time_end.strftime('%H:%M'),
            'subject': item.subject.subject_name,
            'type': item.lesson_type.lesson_type_name,
            'classroom': item.classroom.class_name,
            'group': item.study_group.group_name,
            'teacher': item.teacher.full_name
        })

    response = make_response(json.dumps(data, ensure_ascii=False, indent=4))
    response.headers["Content-Disposition"] = f"attachment; filename={filename}.json"
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


@bp.route('/curriculums/<int:curr_id>/export/csv')
@login_required
def curriculum_export_csv(curr_id):
    if current_user.user_type_ref.type_name != 'admin':
        abort(403)

    curriculum = db_session.query(Curriculum).get(curr_id)
    if not curriculum:
        abort(404)

    details = db_session.query(CurriculumDetail) \
        .filter_by(curriculum_id=curr_id) \
        .order_by(CurriculumDetail.semester, CurriculumDetail.subject_id).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Учебный план:', curriculum.education_level])
    writer.writerow(['Форма обучения:', curriculum.education_form.education_form_name])
    writer.writerow(['Год утверждения:', curriculum.approval_year])
    writer.writerow([])  # Пустая строка

    writer.writerow(['Семестр', 'Предмет', 'Часы', 'Тип аттестации'])

    for det in details:
        writer.writerow([
            det.semester,
            det.subject.subject_name,
            det.hours_lecture,
            det.assessment_type.assessment_type_name
        ])

    filename = f"curriculum_{curr_id}"

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}.csv"}
    )