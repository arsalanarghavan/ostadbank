# keyboards.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
import database as db
from models import RequiredChannel

def main_menu():
    """Returns the main menu keyboard for regular users."""
    return ReplyKeyboardMarkup([
        [db.get_text('btn_submit_experience')],
        [db.get_text('btn_my_experiences'), db.get_text('btn_rules')]
    ], resize_keyboard=True)

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
    """
    Creates a paginated list of items for the admin panel (Fields, Majors, etc.).
    """
    keyboard = []
    for item in items:
        name = item.name if hasattr(item, 'name') else f"Admin ID: {item.user_id}"
        # Pass current_page to the delete callback
        delete_callback = f"{prefix}_delete_{item.id}_{current_page}"
        row = [
            InlineKeyboardButton(name, callback_data=f"none"),
            InlineKeyboardButton(db.get_text('btn_delete'), callback_data=delete_callback)
        ]
        if hasattr(item, 'name'):
            # Pass current_page to the edit callback as well
            edit_callback = f"{prefix}_edit_{item.id}_{current_page}"
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
    """Creates a paginated list of bot texts for editing."""
    keyboard = []
    for text_item in texts:
        keyboard.append([InlineKeyboardButton(f"`{text_item.key}`", callback_data=f"text_edit_{text_item.key}_{current_page}")])

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
    """Returns a confirmation keyboard for deleting an item, preserving the page number."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(db.get_text('btn_confirm_delete'), callback_data=f"{prefix}_confirmdelete_{item_id}_{page}"),
        InlineKeyboardButton(db.get_text('btn_cancel_delete'), callback_data=f"admin_list_{prefix}_{page}")
    ]])

def back_to_list_keyboard(prefix, page=1, is_main_panel=False):
    """Returns a keyboard with a single button to go back to a list or the main panel."""
    if is_main_panel:
        return InlineKeyboardMarkup([[InlineKeyboardButton(db.get_text('btn_back_to_panel'), callback_data="admin_main_panel")]])
    return InlineKeyboardMarkup([[InlineKeyboardButton(db.get_text('btn_back_to_list'), callback_data=f"admin_list_{prefix}_{page}")]])

def parent_field_selection_keyboard(fields, prefix, page=1):
    """Returns a keyboard for selecting a parent field (for Majors and Courses)."""
    keyboard = [[InlineKeyboardButton(f.name, callback_data=f"{prefix}_selectfield_{f.id}_{page}")] for f in fields]
    keyboard.append([InlineKeyboardButton(db.get_text('btn_cancel'), callback_data=f"admin_list_{prefix}_{page}")])
    return InlineKeyboardMarkup(keyboard)

def dynamic_list_keyboard(items, prefix, has_add_new=False):
    """Creates a dynamic list of items for the user submission flow."""
    keyboard = []
    for item in items:
        keyboard.append([InlineKeyboardButton(item.name, callback_data=f"{prefix}_select_{item.id}")])
    if has_add_new:
        keyboard.append([InlineKeyboardButton(db.get_text('btn_add_new_professor'), callback_data=f"{prefix}_add_new")])
    keyboard.append([InlineKeyboardButton(db.get_text('btn_cancel'), callback_data="cancel_submission")])
    return InlineKeyboardMarkup(keyboard)

def attendance_keyboard():
    """Returns a Yes/No keyboard for the attendance question."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(db.get_text('btn_attendance_yes'), callback_data="attendance_yes"),
        InlineKeyboardButton(db.get_text('btn_attendance_no'), callback_data="attendance_no")
    ], [InlineKeyboardButton(db.get_text('btn_cancel'), callback_data="cancel_submission")]])

def admin_approval_keyboard(experience_id, user):
    """Returns Approve/Reject keyboard with user info."""
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
    """Returns a keyboard with common rejection reasons for admins."""
    keyboard = [
        [InlineKeyboardButton(db.get_text('btn_reject_reason_1'), callback_data=f"exp_reason_{experience_id}_1")],
        [InlineKeyboardButton(db.get_text('btn_reject_reason_2'), callback_data=f"exp_reason_{experience_id}_2")],
        [InlineKeyboardButton(db.get_text('btn_reject_reason_3'), callback_data=f"exp_reason_{experience_id}_3")],
        [InlineKeyboardButton(db.get_text('btn_back_to_list'), callback_data=f"exp_view_{experience_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def join_channel_keyboard():
    """Returns a keyboard with links to required channels."""
    channels = db.get_all_required_channels()
    keyboard = []
    for channel in channels:
        keyboard.append([InlineKeyboardButton(f"عضویت در کانال", url=channel.channel_link)])
    keyboard.append([InlineKeyboardButton(db.get_text('btn_i_am_member'), callback_data="check_membership")])
    return InlineKeyboardMarkup(keyboard)

def admin_manage_channels_keyboard():
    """Returns a keyboard for managing required channels."""
    channels = db.get_all_required_channels()
    is_forced = db.get_setting('force_subscribe', 'false') == 'true'
    
    keyboard = []
    for channel in channels:
        # Note: The channel_id stored might start with '@' or be a numeric ID
        # For simplicity, we show the link and a delete button
        keyboard.append([
            InlineKeyboardButton(channel.channel_link, url=channel.channel_link),
            InlineKeyboardButton("🗑️ حذف", callback_data=f"admin_delete_channel_{channel.id}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ افزودن کانال جدید", callback_data="admin_add_channel")])
    
    toggle_text = "✅ غیرفعال‌سازی عضویت اجباری" if is_forced else "☑️ فعال‌سازی عضویت اجباری"
    keyboard.append([InlineKeyboardButton(toggle_text, callback_data="admin_toggle_force_sub")])
    
    keyboard.append([InlineKeyboardButton(db.get_text('btn_back_to_panel'), callback_data="admin_main_panel")])
    return InlineKeyboardMarkup(keyboard)