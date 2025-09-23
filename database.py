# database.py

from sqlalchemy.orm import sessionmaker, joinedload
from contextlib import contextmanager
from models import (engine, create_tables, User, Admin, BotText, Field,
                    Major, Professor, Course, Experience)
import config

Session = sessionmaker(bind=engine)

@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Session rollback due to error: {e}")
        raise
    finally:
        session.close()

def initialize_database():
    create_tables()
    with session_scope() as session:
        if not session.query(Admin).filter_by(user_id=config.OWNER_ID).first():
            session.add(Admin(user_id=config.OWNER_ID))

        default_texts = {
            'welcome': '🤖 به ربات بانک اساتید خوش آمدید!',
            'rules': '📜 **قوانین و سوالات متداول:**\n\n۱. لطفا در بیان تجربیات خود صادق باشید.\n۲. از به کار بردن الفاظ توهین‌آمیز خودداری کنید.',
            'my_experiences_empty': 'شما هنوز تجربه‌ای ثبت نکرده‌اید.',
            'submission_start': '✅ بسیار خب! فرآیند ثبت تجربه آغاز شد.\n\nلطفا **رشته تحصیلی** خود را از لیست زیر انتخاب کنید:',
            'choose_major': '📚 عالی! حالا **گرایش** خود را انتخاب کنید:',
            'choose_course': '📝 لطفا **درس** مورد نظر را انتخاب کنید:',
            'choose_professor': '👨🏻‍🏫 لطفا **استاد** این درس را انتخاب کنید. اگر نام استاد در لیست نیست، گزینه "افزودن استاد جدید" را بزنید.',
            'add_new_professor_prompt': 'لطفا نام کامل استاد جدید را وارد کنید:',
            'ask_teaching_style': '✏️ لطفا درباره **سبک تدریس** استاد توضیح دهید.',
            'ask_notes': '📚 آیا استاد **جزوه** خاصی دارند یا منبع خاصی معرفی می‌کنند؟',
            'ask_project': '💻 آیا این درس **پروژه** دارد؟ در صورت وجود، درباره آن توضیح دهید.',
            'ask_attendance_choice': '
            'ask_attendance_details': 'لطفا جزئیات **حضور و غیاب** را بنویسید.',
            'ask_exam': '⭕️ درباره **امتحان** پایان‌ترم توضیح دهید.',
            'ask_conclusion': '⚠️ و در آخر، به عنوان **نتیجه‌گیری**، چه توصیه‌ای برای دانشجویان دارید؟',
            'submission_success': '👌 تجربه شما با موفقیت ثبت و برای بررسی به ادمین‌ها ارسال شد. متشکریم!',
            'submission_cancel': '❌ فرآیند ثبت تجربه لغو شد.',
            'admin_panel_welcome': '🔐 به پنل مدیریت خوش آمدید.',
            'not_an_admin': '🚫 شما دسترسی لازم برای این کار را ندارید.',
            'admin_manage_field_header': 'مدیریت رشته‌ها 🎓',
            'admin_manage_major_header': 'مدیریت گرایش‌ها 📚',
            'admin_manage_professor_header': 'مدیریت اساتید 👨🏻‍🏫',
            'admin_manage_course_header': 'مدیریت دروس 📝',
            'item_added_successfully': '✅ آیتم جدید با موفقیت اضافه شد.',
            'item_deleted_successfully': '🗑️ آیتم با موفقیت حذف شد.',
            'item_updated_successfully': '✏️ آیتم با موفقیت ویرایش شد.',
            'ask_for_new_item_name': 'لطفا نام جدید را وارد کنید:',
            'ask_for_update_item_name': 'لطفا نام جدید را برای "{current_name}" وارد کنید:',
            'confirm_delete': '⚠️ آیا از حذف "{item_name}" مطمئن هستید؟\n\n**توجه:** تمام اطلاعات وابسته نیز حذف خواهند شد. این عمل غیرقابل بازگشت است.',
            'select_parent_field': 'لطفا رشته والد را برای این آیتم انتخاب کنید:',
            'operation_cancelled': 'عملیات لغو شد.',
        }
        for key, value in default_texts.items():
            if not session.query(BotText).filter_by(key=key).first():
                session.add(BotText(key=key, value=value))

def get_text(key, **kwargs):
    with session_scope() as s:
        txt = s.query(BotText).filter_by(key=key).first()
        if not txt: return f"⚠️[{key}]"
        return txt.value.format(**kwargs)

def is_admin(user_id):
    with session_scope() as s:
        return s.query(Admin).filter_by(user_id=user_id).first() is not None

def get_all_items(model):
    with session_scope() as s:
        if hasattr(model, 'name'): return s.query(model).order_by(model.name).all()
        return s.query(model).all()

def get_item_by_id(model, item_id):
    with session_scope() as s:
        return s.query(model).get(item_id)

def get_majors_by_field(field_id):
    with session_scope() as s:
        return s.query(Major).filter_by(field_id=field_id).order_by(Major.name).all()

def get_courses_by_field(field_id):
    with session_scope() as s:
        return s.query(Course).filter_by(field_id=field_id).order_by(Course.name).all()

def get_experience(exp_id):
    with session_scope() as s:
        return s.query(Experience).options(
            joinedload(Experience.field), joinedload(Experience.major),
            joinedload(Experience.professor), joinedload(Experience.course)
        ).get(exp_id)

def get_user_experiences(user_id):
    with session_scope() as s:
        return s.query(Experience).filter_by(user_id=user_id).all()

def add_item(model, **kwargs):
    with session_scope() as s:
        new_item = model(**kwargs)
        s.add(new_item)
        s.flush()
        return new_item

def update_item(model, item_id, **kwargs):
    with session_scope() as s:
        item = s.query(model).get(item_id)
        if item:
            for key, value in kwargs.items(): setattr(item, key, value)
            return True
        return False

def update_experience_status(exp_id, status):
    with session_scope() as s:
        exp = s.query(Experience).get(exp_id)
        if exp: exp.status = status

def add_user(user_id, first_name):
    with session_scope() as s:
        if not s.query(User).filter_by(user_id=user_id).first():
            s.add(User(user_id=user_id, first_name=first_name))

def delete_item(model, item_id):
    with session_scope() as s:
        item = s.query(model).get(item_id)
        if item:
            s.delete(item)
            return True
        return False