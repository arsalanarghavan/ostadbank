# keyboards.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
import database as db

def main_menu():
    """Returns the main menu keyboard for regular users."""
    return ReplyKeyboardMarkup([
        [db.get_text('btn_submit_experience')],
        [db.get_text('btn_my_experiences'), db.get_text('btn_rules')]
    ], resize_keyboard=True)

def admin_panel_main():
    """Returns the main keyboard for the admin panel."""
    keyboard = [
        [InlineKeyboardButton(db.get_text('btn_admin_manage_fields'), callback_data="admin_list_field_1")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_majors'), callback_data="admin_list_major_1")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_professors'), callback_data="admin_list_professor_1")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_courses'), callback_data="admin_list_course_1")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_texts'), callback_data="admin_list_texts_1")],
        # دکمه جدید برای مدیریت ادمین‌ها
        [InlineKeyboardButton("👮‍♂️ مدیریت ادمین‌ها", callback_data="admin_list_admin_1")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_manage_item_list(items, prefix, current_page, total_pages):
    """
    Creates a paginated list of items for the admin panel (Fields, Majors, etc.).
    """
    keyboard = []
    for item in items:
        # برای مدل Admin، چون فیلد name ندارد، از user_id استفاده می‌کنیم
        name = item.name if hasattr(item, 'name') else f"Admin ID: {item.user_id}"
        row = [
            InlineKeyboardButton(name, callback_data=f"none"),
            InlineKeyboardButton(db.get_text('btn_delete'), callback_data=f"{prefix}_delete_{item.id}")
        ]
        # دکمه ویرایش برای ادمین‌ها وجود ندارد، چون فقط user_id دارند
        if hasattr(item, 'name'):
            row.insert(1, InlineKeyboardButton(db.get_text('btn_edit'), callback_data=f"{prefix}_edit_{item.id}"))
        keyboard.append(row)

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(db.get_text('btn_prev_page'), callback_data=f"admin_list_{prefix}_{current_page - 1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(db.get_text('btn_next_page'), callback_data=f"admin_list_{prefix}_{current_page + 1}"))

    if pagination_row:
        keyboard.append(pagination_row)

    # برای مدل Admin، دکمه افزودن متن متفاوتی دارد
    add_button_text = db.get_text('btn_add_new') if prefix != 'admin' else '➕ افزودن ادمین جدید'
    keyboard.append([InlineKeyboardButton(add_button_text, callback_data=f"{prefix}_add")])
    keyboard.append([InlineKeyboardButton(db.get_text('btn_back_to_panel'), callback_data="admin_main_panel")])

    return InlineKeyboardMarkup(keyboard)


def admin_manage_texts_list(texts, current_page, total_pages):
    """Creates a paginated list of bot texts for editing."""
    keyboard = []
    for text_item in texts:
        # نمایش کلید متن به عنوان دکمه برای ویرایش
        keyboard.append([InlineKeyboardButton(f"`{text_item.key}`", callback_data=f"text_edit_{text_item.key}")])

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(db.get_text('btn_prev_page'), callback_data=f"admin_list_texts_{current_page - 1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(db.get_text('btn_next_page'), callback_data=f"admin_list_texts_{current_page + 1}"))

    if pagination_row:
        keyboard.append(pagination_row)

    keyboard.append([InlineKeyboardButton(db.get_text('btn_back_to_panel'), callback_data="admin_main_panel")])
    return InlineKeyboardMarkup(keyboard)

def confirm_delete_keyboard(prefix, item_id):
    """Returns a confirmation keyboard for deleting an item."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(db.get_text('btn_confirm_delete'), callback_data=f"{prefix}_confirmdelete_{item_id}"),
        InlineKeyboardButton(db.get_text('btn_cancel_delete'), callback_data=f"admin_list_{prefix}_1") # بازگشت به صفحه اول لیست
    ]])

def back_to_list_keyboard(prefix, page=1):
    """Returns a keyboard with a single button to go back to a list."""
    return InlineKeyboardMarkup([[InlineKeyboardButton(db.get_text('btn_back_to_list'), callback_data=f"admin_list_{prefix}_{page}")]])

def parent_field_selection_keyboard(fields, prefix):
    """Returns a keyboard for selecting a parent field (for Majors and Courses)."""
    keyboard = [[InlineKeyboardButton(f.name, callback_data=f"{prefix}_selectfield_{f.id}")] for f in fields]
    keyboard.append([InlineKeyboardButton(db.get_text('btn_cancel'), callback_data=f"admin_list_{prefix}_1")])
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

def admin_approval_keyboard(experience_id):
    """Returns Approve/Reject keyboard for admins to review an experience."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(db.get_text('btn_approve_exp'), callback_data=f"exp_approve_{experience_id}"),
        InlineKeyboardButton(db.get_text('btn_reject_exp'), callback_data=f"exp_reject_{experience_id}")
    ]])

def rejection_reasons_keyboard(experience_id):
    """Returns a keyboard with common rejection reasons for admins."""
    keyboard = [
        [InlineKeyboardButton(db.get_text('btn_reject_reason_1'), callback_data=f"exp_reason_{experience_id}_1")],
        [InlineKeyboardButton(db.get_text('btn_reject_reason_2'), callback_data=f"exp_reason_{experience_id}_2")],
        [InlineKeyboardButton(db.get_text('btn_reject_reason_3'), callback_data=f"exp_reason_{experience_id}_3")],
        [InlineKeyboardButton(db.get_text('btn_back_to_list'), callback_data=f"exp_view_{experience_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)