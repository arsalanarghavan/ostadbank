# keyboards.py (Final Corrected Version)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
import database as db
from models import RequiredChannel, ExperienceStatus

def main_menu():
    """Returns the main menu keyboard for regular users."""
    return ReplyKeyboardMarkup([
        [db.get_text('btn_submit_experience')],
        [db.get_text('btn_my_experiences'), db.get_text('btn_rules')]
    ], resize_keyboard=True)

def my_experiences_keyboard(experiences, current_page, total_pages):
    """Creates an inline keyboard for the user's experiences with pagination."""
    keyboard = []
    
    status_map = {
        ExperienceStatus.PENDING: '⏳',
        ExperienceStatus.APPROVED: '✅',
        ExperienceStatus.REJECTED: '❌'
    }

    for exp in experiences:
        status_emoji = status_map.get(exp['status'], '❔')
        button_text = f"{status_emoji} {exp['course_name']} - {exp['professor_name']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"exp_detail_{exp['id']}")])

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(db.get_text('btn_prev_page'), callback_data=f"my_exps_{current_page - 1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(db.get_text('btn_next_page'), callback_data=f"my_exps_{current_page + 1}"))
    
    if pagination_row:
        keyboard.append(pagination_row)

    return InlineKeyboardMarkup(keyboard)

def experience_detail_keyboard(experience_id, page=1):
    """Creates the keyboard for the experience detail view, including an edit button."""
    keyboard = [
        [InlineKeyboardButton("✏️ ویرایش یا ارسال مجدد", callback_data=f"edit_exp_{experience_id}_{page}")],
        [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data=f"my_exps_{page}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ------------------- START: NEW FUNCTION -------------------
def confirm_edit_keyboard(experience_id, page=1):
    """Asks the user to confirm the deletion and resubmission of an experience."""
    keyboard = [
        [
            InlineKeyboardButton("✅ بله، ویرایش کن", callback_data=f"confirm_edit_{experience_id}_{page}"),
            InlineKeyboardButton("❌ خیر", callback_data=f"exp_detail_{experience_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
# -------------------- END: NEW FUNCTION --------------------


def admin_panel_main():
    """Returns the main keyboard for the admin panel."""
    keyboard = [
        [InlineKeyboardButton("📊 آمار ربات", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👤 ارسال پیام به کاربر", callback_data="admin_single_message")],
        [InlineKeyboardButton("🔗 مدیریت کانال‌ها", callback_data="admin_manage_channels")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_fields'), callback_data="admin_list_field_1")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_majors'), callback_data="admin_list_major_1")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_professors'), callback_data="admin_list_professor_1")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_courses'), callback_data="admin_list_course_1")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_texts'), callback_data="admin_list_texts_1")],
        [InlineKeyboardButton("👮‍♂️ مدیریت ادمین‌ها", callback_data="admin_list_admin_1")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_manage_item_list(items, prefix, current_page, total_pages):
    keyboard = []
    for item in items:
        name = item.get('name') or f"Admin ID: {item.get('user_id')}"
        item_id = item['id']
        
        delete_callback = f"{prefix}_delete_{item_id}_{current_page}"
        row = [
            InlineKeyboardButton(name, callback_data=f"none"),
            InlineKeyboardButton(db.get_text('btn_delete'), callback_data=delete_callback)
        ]
        if 'name' in item:
            edit_callback = f"{prefix}_edit_{item_id}_{current_page}"
            row.insert(1, InlineKeyboardButton(db.get_text('btn_edit'), callback_data=edit_callback))
        keyboard.append(row)

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(db.get_text('btn_prev_page'), callback_data=f"admin_list_{prefix}_{current_page - 1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(db.get_text('btn_next_page'), callback_data=f"admin_list_{prefix}_{current_page + 1}"))

    if pagination_row:
        keyboard.append(pagination_row)

    add_button_text = db.get_text('btn_add_new') if prefix != 'admin' else '➕ افزودن ادمین جدید'
    keyboard.append([InlineKeyboardButton(add_button_text, callback_data=f"{prefix}_add_{current_page}")])
    keyboard.append([InlineKeyboardButton(db.get_text('btn_back_to_panel'), callback_data="admin_main_panel")])

    return InlineKeyboardMarkup(keyboard)

def admin_manage_texts_list(texts, current_page, total_pages):
    keyboard = []
    for text_item in texts:
        key = text_item['key']
        keyboard.append([InlineKeyboardButton(f"`{key}`", callback_data=f"text_edit_{key}_{current_page}")])

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(db.get_text('btn_prev_page'), callback_data=f"admin_list_texts_{current_page - 1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(db.get_text('btn_next_page'), callback_data=f"admin_list_texts_{current_page + 1}"))

    if pagination_row:
        keyboard.append(pagination_row)

    keyboard.append([InlineKeyboardButton(db.get_text('btn_back_to_panel'), callback_data="admin_main_panel")])
    return InlineKeyboardMarkup(keyboard)

def confirm_delete_keyboard(prefix, item_id, page):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(db.get_text('btn_confirm_delete'), callback_data=f"{prefix}_confirmdelete_{item_id}_{page}"),
        InlineKeyboardButton(db.get_text('btn_cancel_delete'), callback_data=f"admin_list_{prefix}_{page}")
    ]])

def back_to_list_keyboard(prefix, page=1, is_main_panel=False):
    if is_main_panel:
        return InlineKeyboardMarkup([[InlineKeyboardButton(db.get_text('btn_back_to_panel'), callback_data="admin_main_panel")]])
    
    list_prefix = 'texts' if prefix == 'texts' else prefix
    return InlineKeyboardMarkup([[InlineKeyboardButton(db.get_text('btn_back_to_list'), callback_data=f"admin_list_{list_prefix}_{page}")]])

def parent_field_selection_keyboard(fields, prefix, page=1):
    keyboard = [[InlineKeyboardButton(f['name'], callback_data=f"{prefix}_selectfield_{f['id']}_{page}")] for f in fields]
    keyboard.append([InlineKeyboardButton(db.get_text('btn_cancel'), callback_data=f"admin_list_{prefix}_{page}")])
    return InlineKeyboardMarkup(keyboard)

def dynamic_list_keyboard(items, prefix, has_add_new=False):
    keyboard = []
    for item in items:
        keyboard.append([InlineKeyboardButton(item['name'], callback_data=f"{prefix}_select_{item['id']}")])
    if has_add_new:
        keyboard.append([InlineKeyboardButton(db.get_text('btn_add_new_professor'), callback_data=f"{prefix}_add_new")])
    keyboard.append([InlineKeyboardButton(db.get_text('btn_cancel'), callback_data="cancel_submission")])
    return InlineKeyboardMarkup(keyboard)

def attendance_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(db.get_text('btn_attendance_yes'), callback_data="attendance_yes"),
        InlineKeyboardButton(db.get_text('btn_attendance_no'), callback_data="attendance_no")
    ], [InlineKeyboardButton(db.get_text('btn_cancel'), callback_data="cancel_submission")]])

def admin_approval_keyboard(experience_id, user):
    keyboard = [
        [
            InlineKeyboardButton(db.get_text('btn_approve_exp'), callback_data=f"exp_approve_{experience_id}"),
            InlineKeyboardButton(db.get_text('btn_reject_exp'), callback_data=f"exp_reject_{experience_id}")
        ],
        [
            InlineKeyboardButton(f"👤 {user.first_name}", url=f"tg://user?id={user.id}"),
            InlineKeyboardButton(f"ID: {user.id}", url=f"tg://user?id={user.id}")
        ]
    ]
    if user.username:
        keyboard.append([InlineKeyboardButton(f"@{user.username}", url=f"https://t.me/{user.username}")])
    
    return InlineKeyboardMarkup(keyboard)

def rejection_reasons_keyboard(experience_id):
    keyboard = [
        [InlineKeyboardButton(db.get_text('btn_reject_reason_1'), callback_data=f"exp_reason_{experience_id}_1")],
        [InlineKeyboardButton(db.get_text('btn_reject_reason_2'), callback_data=f"exp_reason_{experience_id}_2")],
        [InlineKeyboardButton(db.get_text('btn_reject_reason_3'), callback_data=f"exp_reason_{experience_id}_3")],
        [InlineKeyboardButton(db.get_text('btn_back_to_list'), callback_data=f"exp_view_{experience_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def join_channel_keyboard():
    channels = db.get_all_required_channels()
    keyboard = []
    for channel_data in channels:
        keyboard.append([InlineKeyboardButton("عضویت در کانال", url=channel_data['channel_link'])])
    keyboard.append([InlineKeyboardButton(db.get_text('btn_i_am_member'), callback_data="check_membership")])
    return InlineKeyboardMarkup(keyboard)

def admin_manage_channels_keyboard():
    channels = db.get_all_required_channels()
    is_forced = db.get_setting('force_subscribe', 'false') == 'true'
    
    keyboard = []
    for channel in channels:
        keyboard.append([
            InlineKeyboardButton(channel['channel_link'], url=channel['channel_link']),
            InlineKeyboardButton("🗑️ حذف", callback_data=f"admin_delete_channel_{channel['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ افزودن کانال جدید", callback_data="admin_add_channel")])
    
    toggle_text = "✅ غیرفعال‌سازی عضویت اجباری" if is_forced else "☑️ فعال‌سازی عضویت اجباری"
    keyboard.append([InlineKeyboardButton(toggle_text, callback_data="admin_toggle_force_sub")])
    
    keyboard.append([InlineKeyboardButton(db.get_text('btn_back_to_panel'), callback_data="admin_main_panel")])
    return InlineKeyboardMarkup(keyboard)