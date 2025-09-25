# database.py (Final Corrected Version)

from sqlalchemy.orm import sessionmaker, joinedload
from contextlib import contextmanager
import math
from models import (engine, create_tables, User, Admin, BotText, Field,
                    Major, Professor, Course, Experience, ExperienceStatus,
                    RequiredChannel, Setting)
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
        if not session.query(Admin).filter_by(user_id=config.OWNER_ID).first():
            session.add(Admin(user_id=config.OWNER_ID))

        if not session.query(Setting).filter_by(key='force_subscribe').first():
            session.add(Setting(key='force_subscribe', value='false'))
        
        default_texts = {
            'welcome': '🤖 سلام! به ربات بانک اساتید خوش آمدید. با این ربات می‌توانید تجربه خود را از اساتید مختلف ثبت کنید و به دیگران در انتخاب واحد کمک کنید. برای شروع، یکی از گزینه‌های زیر را انتخاب کنید.',
            'rules': '📜 **قوانین و سوالات متداول:**\n\n۱. لطفا در بیان تجربیات خود صادق باشید.\n۲. از به کار بردن الفاظ توهین‌آمیز خودداری کنید.',
            'my_experiences_empty': 'شما هنوز تجربه‌ای ثبت نکرده‌اید.',
            'my_experiences_header': '📜 **تجربه‌های ثبت شده شما:**\n\n',
            'not_an_admin': '🚫 شما دسترسی لازم برای این کار را ندارید.',
            'operation_cancelled': 'عملیات لغو شد.',
            'item_added_successfully': '✅ آیتم جدید با موفقیت اضافه شد.',
            'item_deleted_successfully': '🗑️ آیتم با موفقیت حذف شد.',
            'item_updated_successfully': '✏️ آیتم با موفقیت ویرایش شد.',
            'submission_start': '✅ بسیار خب! فرآیند ثبت تجربه آغاز شد.\n\nلطفا **رشته تحصیلی** خود را از لیست زیر انتخاب کنید:',
            'choose_major': '📚 عالی! حالا **گرایش** خود را انتخاب کنید:',
            'choose_course': '📝 لطفا **درس** مورد نظر را انتخاب کنید:',
            'choose_professor': '👨🏻‍🏫 لطفا **استاد** این درس را انتخاب کنید.',
            'add_new_professor_prompt': 'لطفا نام کامل استاد جدید را وارد کنید:',
            'ask_teaching_style': '✏️ لطفا درباره **سبک تدریس** استاد توضیح دهید (حداکثر ۱۰۰۰ کاراکتر).',
            'ask_notes': '📚 آیا استاد **جزوه** خاصی دارند یا منبع خاصی معرفی می‌کنند؟ (حداکثر ۱۰۰۰ کاراکتر)',
            'ask_project': '💻 آیا این درس **پروژه** دارد؟ در صورت وجود، درباره آن توضیح دهید (حداکثر ۱۰۰۰ کاراکتر).',
            'ask_attendance_choice': '🕒 آیا استاد بر روی **حضور و غیاب** حساس هستند؟',
            'ask_attendance_details': 'لطفا جزئیات **حضور و غیاب** را بنویسید (حداکثر ۱۰۰۰ کاراکتر).',
            'ask_exam': '⭕️ درباره **امتحان** پایان‌ترم توضیح دهید (حداکثر ۱۰۰۰ کاراکتر).',
            'ask_conclusion': '⚠️ و در آخر، به عنوان **نتیجه‌گیری**، چه توصیه‌ای برای دانشجویان دارید؟ (حداکثر ۱۰۰۰ کاراکتر)',
            'submission_success': '👌 تجربه شما با موفقیت ثبت و برای بررسی به ادمین‌ها ارسال شد. متشکریم!',
            'submission_cancel': '❌ فرآیند ثبت تجربه لغو شد.',
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

            # ----------------- START: Final Corrected Text -----------------
            'exp_format_footer': """➖➖➖➖➖➖➖➖➖➖
❗️دوستانی که مایل به معرفی استاد هستن، می‌تونند با ما در ارتباط باشن تا استادشون رو معرفی کنیم و به بقیه کمک بشه برای انتخاب واحد بهتر.

#همیارهمباشیم

آدرس کانال:
🆔 @ShamsiOstadBank
ثبت تجربه شما:
🆔 @ShamsiOstadBankBot
➖➖➖➖➖➖➖➖➖➖""",
            # ----------------- END: Final Corrected Text -----------------
            
            'exp_format_tags': '♊️ تگ‌ها',
            'status_pending': '⏳ در انتظار تایید',
            'status_approved': '✅ تایید شده',
            'status_rejected': '❌ رد شده',
            'admin_new_experience_notification': 'یک تجربه جدید برای بررسی ثبت شد - ID: {exp_id}\n\n',
            'admin_recheck_experience': 'بررسی مجدد تجربه ID: {exp_id}\n\n',
            'admin_approval_success': '✅ تجربه با ID {exp_id} تایید و در کانال منتشر شد.',
            'admin_rejection_success': '❌ تجربه با ID {exp_id} به دلیل «{reason}» رد شد.',
            'user_approval_notification': "✅ تجربه شما برای درس '{course_name}' تایید شد!",
            'user_rejection_notification': "❌ متاسفانه تجربه شما برای درس '{course_name}' به دلیل «{reason}» رد شد.",
            'force_subscribe_message': 'کاربر گرامی، برای استفاده از ربات، لطفا ابتدا در کانال‌های زیر عضو شوید و سپس دکمه "عضو شدم" را فشار دهید.',
            'broadcast_prompt': 'لطفا پیامی که می‌خواهید به تمام کاربران ربات ارسال شود را وارد کنید. می‌توانید از فرمت Markdown استفاده کنید.',
            'broadcast_success': 'پیام شما برای ارسال به تمام کاربران در صف قرار گرفت. تعداد کل کاربران: {user_count}',
            'single_message_user_prompt': 'لطفا یوزرنیم (با @) یا آیدی عددی کاربری که می‌خواهید به او پیام ارسال کنید را وارد نمایید.',
            'single_message_prompt': 'لطفا پیامی که می‌خواهید برای کاربر {target_user} ارسال شود را وارد کنید.',
            'single_message_success': 'پیام شما با موفقیت برای کاربر {target_user} ارسال شد.',
            'single_message_fail': 'ارسال پیام به کاربر {target_user} ناموفق بود. خطای دریافتی: {error}',
            'stats_message': '📊 **آمار ربات:**\n\n👥 تعداد کل کاربران: {total_users}\n✍️ تعداد کل تجربیات ثبت شده: {total_experiences}\n✅ تجربیات تایید شده: {approved_experiences}\n❌ تجربیات رد شده: {rejected_experiences}\n⏳ تجربیات در انتظار تایید: {pending_experiences}',
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
            'btn_i_am_member': 'عضو شدم ✅',
        }

        for key, value in default_texts.items():
            if not session.query(BotText).filter_by(key=key).first():
                session.add(BotText(key=key, value=value))

def get_text(key, **kwargs):
    """Fetch a text from the database by its key and format it."""
    with session_scope() as s:
        txt = s.query(BotText).filter_by(key=key).first()
        if not txt:
            return f"⚠️[{key}]"
        return txt.value.format(**kwargs)

def get_paginated_list(model, page=1, per_page=8):
    """Get a paginated list of items and return them as a list of dicts."""
    with session_scope() as s:
        query = s.query(model)
        
        if hasattr(model, 'key'):
            query = query.order_by(model.key)
        elif hasattr(model, 'name'):
            query = query.order_by(model.name)
        elif hasattr(model, 'user_id'):
            query = query.order_by(model.user_id)
        
        total_items = query.count()
        total_pages = math.ceil(total_items / per_page)
        offset = (page - 1) * per_page
        items = query.limit(per_page).offset(offset).all()

        results = []
        for item in items:
            item_dict = {}
            if hasattr(item, 'id'): item_dict['id'] = item.id
            if hasattr(item, 'name'): item_dict['name'] = item.name
            if hasattr(item, 'user_id'): item_dict['user_id'] = item.user_id
            if hasattr(item, 'key'): item_dict['key'] = item.key
            if hasattr(item, 'channel_id'): item_dict['channel_id'] = item.channel_id
            if hasattr(item, 'channel_link'): item_dict['channel_link'] = item.channel_link
            results.append(item_dict)
            
        return results, total_pages

def is_admin(user_id):
    """Check if a user is an admin."""
    with session_scope() as s:
        return s.query(Admin).filter_by(user_id=user_id).first() is not None

def get_all_items_by_parent(model, parent_id_field, parent_id):
    """Get all items belonging to a parent and return as a list of dicts."""
    with session_scope() as s:
        items = s.query(model).filter(getattr(model, parent_id_field) == parent_id).order_by(model.name).all()
        return [{'id': item.id, 'name': item.name} for item in items]

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
        exps = s.query(Experience).options(
            joinedload(Experience.course),
            joinedload(Experience.professor)
        ).filter_by(user_id=user_id).all()
        return exps

def add_item(model, **kwargs):
    """Add a new item to the database."""
    with session_scope() as s:
        new_item = model(**kwargs)
        s.add(new_item)
        s.flush()
        return new_item.id

def update_item(model, item_id, **kwargs):
    """Update an existing item in the database."""
    with session_scope() as s:
        item = s.query(model).get(item_id)
        if item:
            for key, value in kwargs.items():
                setattr(item, key, value)
            return True
        return False

def update_experience_status(exp_id: int, status: ExperienceStatus):
    """Update the status of an experience using the ExperienceStatus enum."""
    with session_scope() as s:
        exp = s.query(Experience).get(exp_id)
        if exp:
            exp.status = status
            return True
        return False

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

def get_item_name(model, item_id):
    """Get the name of a single item by its ID."""
    with session_scope() as s:
        item = s.query(model).get(item_id)
        if not item:
            return None
        if hasattr(item, 'name'):
            return item.name
        if hasattr(item, 'user_id'):
            return f"ID: {item.user_id}"
        return f"ID: {item.id}"

def get_all_users():
    """Get all users from the database."""
    with session_scope() as s:
        return s.query(User).all()

def get_statistics():
    """Get various statistics from the database."""
    with session_scope() as s:
        stats = {
            'total_users': s.query(User).count(),
            'total_experiences': s.query(Experience).count(),
            'approved_experiences': s.query(Experience).filter_by(status=ExperienceStatus.APPROVED).count(),
            'rejected_experiences': s.query(Experience).filter_by(status=ExperienceStatus.REJECTED).count(),
            'pending_experiences': s.query(Experience).filter_by(status=ExperienceStatus.PENDING).count(),
        }
        return stats

def get_setting(key, default=None):
    """Get a setting value by its key."""
    with session_scope() as s:
        setting = s.query(Setting).filter_by(key=key).first()
        return setting.value if setting else default

def set_setting(key, value):
    """Set a setting value."""
    with session_scope() as s:
        setting = s.query(Setting).filter_by(key=key).first()
        if setting:
            setting.value = str(value)
        else:
            s.add(Setting(key=key, value=str(value)))

def get_all_required_channels():
    """Get all required channels from the database as dicts."""
    with session_scope() as s:
        channels = s.query(RequiredChannel).all()
        return [{'id': c.id, 'channel_id': c.channel_id, 'channel_link': c.channel_link} for c in channels]