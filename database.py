# database.py

from sqlalchemy.orm import sessionmaker, joinedload
from contextlib import contextmanager
import math
from models import (engine, create_tables, User, Admin, BotText, Field,
                    Major, Professor, Course, Experience)
import config

Session = sessionmaker(bind=engine)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
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
    """Create database tables and populate default texts if they don't exist."""
    create_tables()
    with session_scope() as session:
        # Add owner as the first admin if not already present
        if not session.query(Admin).filter_by(user_id=config.OWNER_ID).first():
            session.add(Admin(user_id=config.OWNER_ID))

        # --- All bot texts are managed here ---
        default_texts = {
            # --- General Messages ---
            'welcome': '🤖 به ربات بانک اساتید خوش آمدید!',
            'rules': '📜 **قوانین و سوالات متداول:**\n\n۱. لطفا در بیان تجربیات خود صادق باشید.\n۲. از به کار بردن الفاظ توهین‌آمیز خودداری کنید.',
            'my_experiences_empty': 'شما هنوز تجربه‌ای ثبت نکرده‌اید.',
            'my_experiences_header': '📜 **تجربه‌های ثبت شده شما:**\n\n',
            'not_an_admin': '🚫 شما دسترسی لازم برای این کار را ندارید.',
            'operation_cancelled': 'عملیات لغو شد.',
            'item_added_successfully': '✅ آیتم جدید با موفقیت اضافه شد.',
            'item_deleted_successfully': '🗑️ آیتم با موفقیت حذف شد.',
            'item_updated_successfully': '✏️ آیتم با موفقیت ویرایش شد.',

            # --- Submission Flow ---
            'submission_start': '✅ بسیار خب! فرآیند ثبت تجربه آغاز شد.\n\nلطفا **رشته تحصیلی** خود را از لیست زیر انتخاب کنید:',
            'choose_major': '📚 عالی! حالا **گرایش** خود را انتخاب کنید:',
            'choose_course': '📝 لطفا **درس** مورد نظر را انتخاب کنید:',
            'choose_professor': '👨🏻‍🏫 لطفا **استاد** این درس را انتخاب کنید.',
            'add_new_professor_prompt': 'لطفا نام کامل استاد جدید را وارد کنید:',
            'ask_teaching_style': '✏️ لطفا درباره **سبک تدریس** استاد توضیح دهید.',
            'ask_notes': '📚 آیا استاد **جزوه** خاصی دارند یا منبع خاصی معرفی می‌کنند؟',
            'ask_project': '💻 آیا این درس **پروژه** دارد؟ در صورت وجود، درباره آن توضیح دهید.',
            'ask_attendance_choice': '🕒 آیا استاد بر روی **حضور و غیاب** حساس هستند؟',
            'ask_attendance_details': 'لطفا جزئیات **حضور و غیاب** را بنویسید (مثلا: «در هر جلسه حساس هستند» یا «فقط در انتهای ترم لیست را چک می‌کنند»).',
            'ask_exam': '⭕️ درباره **امتحان** پایان‌ترم توضیح دهید (مثلا: «سخت‌گیر هستند و از جزوه سوال می‌دهند»).',
            'ask_conclusion': '⚠️ و در آخر، به عنوان **نتیجه‌گیری**، چه توصیه‌ای برای دانشجویان دارید؟',
            'submission_success': '👌 تجربه شما با موفقیت ثبت و برای بررسی به ادمین‌ها ارسال شد. متشکریم!',
            'submission_cancel': '❌ فرآیند ثبت تجربه لغو شد.',

            # --- Admin Panel ---
            'admin_panel_welcome': '🔐 به پنل مدیریت خوش آمدید.',
            'admin_manage_field_header': 'مدیریت رشته‌ها 🎓',
            'admin_manage_major_header': 'مدیریت گرایش‌ها 📚',
            'admin_manage_professor_header': 'مدیریت اساتید 👨🏻‍🏫',
            'admin_manage_course_header': 'مدیریت دروس 📝',
            'admin_manage_texts_header': 'مدیریت متن‌های ربات ⚙️',
            'ask_for_new_item_name': 'لطفا نام جدید را وارد کنید:',
            'ask_for_update_item_name': 'لطفا نام جدید را برای "{current_name}" وارد کنید:',
            'ask_for_update_text_value': 'لطفا متن جدید را برای کلید `{key}` ارسال کنید:',
            'confirm_delete': '⚠️ آیا از حذف "{item_name}" مطمئن هستید؟ این عمل غیرقابل بازگشت است.',
            'select_parent_field': 'لطفا رشته والد را برای این آیتم انتخاب کنید:',
            'rejection_reason_prompt': 'لطفا دلیل رد این تجربه را انتخاب کنید:',

            # --- Experience Formatting ---
            'exp_format_field': '🔖 رشته',
            'exp_format_professor': '👨🏻‍🏫 استاد',
            'exp_format_course': '📝 درس',
            'exp_format_teaching': '✏️ نوع تدریس',
            'exp_format_notes': '📚 جزوه',
            'exp_format_project': '💻 پروژه',
            'exp_format_attendance': '❌ حضور و غیاب',
            'exp_format_attendance_yes': 'دارد',
            'exp_format_attendance_no': 'ندارد',
            'exp_format_exam': '⭕️ امتحان',
            'exp_format_conclusion': '⚠️ نتیجه گیری',
            'exp_format_footer': """➖➖➖➖➖➖➖➖➖➖
❗️دوستانی که مایل به معرفی استاد هستن، می‌تونند با ما در ارتباط باشن تا استادشون رو معرفی کنیم و به بقیه کمک بشه برای انتخاب واحد بهتر.

#همیار_هم_باشیم

آدرس کانال:
🆔 @Shamsi_OstadBank
ثبت تجربه شما:
🆔 @Shamsi_OstadBank_Bot
➖➖➖➖➖➖➖➖➖➖""",
            'exp_format_tags': '♊️ تگ‌ها',
            
            # --- Statuses ---
            'status_pending': '⏳ در انتظار تایید',
            'status_approved': '✅ تایید شده',
            'status_rejected': '❌ رد شده',

            # --- Admin Notifications ---
            'admin_new_experience_notification': 'یک تجربه جدید برای بررسی ثبت شد (ID: {exp_id}):\n\n',
            'admin_recheck_experience': 'بررسی مجدد تجربه ID: {exp_id}\n\n',
            'admin_approval_success': '✅ تجربه با ID {exp_id} تایید و در کانال منتشر شد.',
            'admin_rejection_success': '❌ تجربه با ID {exp_id} به دلیل «{reason}» رد شد.',
            'user_approval_notification': "✅ تجربه شما برای درس '{course_name}' تایید شد!",
            'user_rejection_notification': "❌ متاسفانه تجربه شما برای درس '{course_name}' به دلیل «{reason}» رد شد.",

            # --- BUTTON TEXTS ---
            'btn_submit_experience': '✍️ ثبت تجربه',
            'btn_my_experiences': '📖 تجربه‌های من',
            'btn_rules': '📜 قوانین',
            'btn_admin_manage_fields': '🎓 مدیریت رشته‌ها',
            'btn_admin_manage_majors': '📚 مدیریت گرایش‌ها',
            'btn_admin_manage_professors': '👨🏻‍🏫 مدیریت اساتید',
            'btn_admin_manage_courses': '📝 مدیریت دروس',
            'btn_admin_manage_texts': '⚙️ مدیریت متن‌ها',
            'btn_add_new': '➕ افزودن آیتم جدید',
            'btn_add_new_professor': '➕ استاد جدید',
            'btn_edit': '✏️ ویرایش',
            'btn_delete': '🗑️ حذف',
            'btn_back_to_panel': '🔙 بازگشت به پنل اصلی',
            'btn_back_to_list': '🔙 بازگشت به لیست',
            'btn_cancel': '❌ لغو',
            'btn_confirm_delete': '✅ بله، حذف کن',
            'btn_cancel_delete': '❌ خیر، بازگشت',
            'btn_attendance_yes': '✅ دارد',
            'btn_attendance_no': '⛔️ ندارد',
            'btn_approve_exp': '✅ تایید تجربه',
            'btn_reject_exp': '❌ رد تجربه',
            'btn_next_page': 'صفحه بعد ◀️',
            'btn_prev_page': '▶️ صفحه قبل',
            'btn_reject_reason_1': 'توهین‌آمیز',
            'btn_reject_reason_2': 'نامفهوم',
            'btn_reject_reason_3': 'اسپم',
        }

        for key, value in default_texts.items():
            if not session.query(BotText).filter_by(key=key).first():
                session.add(BotText(key=key, value=value))

def get_text(key, **kwargs):
    """Fetch a text from the database by its key and format it."""
    with session_scope() as s:
        txt = s.query(BotText).filter_by(key=key).first()
        if not txt: 
            return f"⚠️[{key}]" # Return a noticeable error if key is not found
        return txt.value.format(**kwargs)

def get_paginated_texts(page=1, per_page=8):
    """Get a paginated list of all bot texts."""
    with session_scope() as s:
        query = s.query(BotText).order_by(BotText.key)
        total_items = query.count()
        total_pages = math.ceil(total_items / per_page)
        
        offset = (page - 1) * per_page
        items = query.limit(per_page).offset(offset).all()
        
        return items, total_pages

def is_admin(user_id):
    """Check if a user is an admin."""
    with session_scope() as s:
        return s.query(Admin).filter_by(user_id=user_id).first() is not None

def get_all_items(model):
    """Get all items from a specific model, ordered by name if possible."""
    with session_scope() as s:
        if hasattr(model, 'name'):
            return s.query(model).order_by(model.name).all()
        return s.query(model).all()

def get_item_by_id(model, item_id):
    """Get a single item by its primary key."""
    with session_scope() as s:
        return s.query(model).get(item_id)

def get_majors_by_field(field_id):
    """Get all majors belonging to a specific field."""
    with session_scope() as s:
        return s.query(Major).filter_by(field_id=field_id).order_by(Major.name).all()

def get_courses_by_field(field_id):
    """Get all courses belonging to a specific field."""
    with session_scope() as s:
        return s.query(Course).filter_by(field_id=field_id).order_by(Course.name).all()

def get_experience(exp_id):
    """Get a single experience and eagerly load related objects."""
    with session_scope() as s:
        return s.query(Experience).options(
            joinedload(Experience.field),
            joinedload(Experience.major),
            joinedload(Experience.professor),
            joinedload(Experience.course)
        ).get(exp_id)

def get_user_experiences(user_id):
    """Get all experiences submitted by a specific user."""
    with session_scope() as s:
        return s.query(Experience).filter_by(user_id=user_id).all()

def add_item(model, **kwargs):
    """Add a new item to the database."""
    with session_scope() as s:
        new_item = model(**kwargs)
        s.add(new_item)
        s.flush() # To get the ID of the new item before commit
        return new_item

def update_item(model, item_id, **kwargs):
    """Update an existing item in the database."""
    with session_scope() as s:
        item = s.query(model).get(item_id)
        if item:
            for key, value in kwargs.items():
                setattr(item, key, value)
            return True
        return False

def update_experience_status(exp_id, status):
    """Update the status of an experience (e.g., pending, approved, rejected)."""
    with session_scope() as s:
        exp = s.query(Experience).get(exp_id)
        if exp:
            exp.status = status

def add_user(user_id, first_name):
    """Add a new user if they don't already exist."""
    with session_scope() as s:
        if not s.query(User).filter_by(user_id=user_id).first():
            s.add(User(user_id=user_id, first_name=first_name))

def delete_item(model, item_id):
    """Delete an item from the database."""
    with session_scope() as s:
        item = s.query(model).get(item_id)
        if item:
            s.delete(item)
            return True
        return False