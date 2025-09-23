# keyboards.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
import database as db

def main_menu():
    return ReplyKeyboardMarkup([
        [db.get_text('btn_submit_experience')],
        [db.get_text('btn_my_experiences'), db.get_text('btn_rules')]
    ], resize_keyboard=True)

def admin_panel_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(db.get_text('btn_admin_manage_fields'), callback_data="admin_list_field")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_majors'), callback_data="admin_list_major")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_professors'), callback_data="admin_list_professor")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_courses'), callback_data="admin_list_course")],
        [InlineKeyboardButton(db.get_text('btn_admin_manage_texts'), callback_data="admin_list_texts_1")],
    ])

def admin_manage_item_list(items, prefix):
    keyboard = []
    for item in items:
        keyboard.append([
            InlineKeyboardButton(item.name, callback_data=f"none"),
            InlineKeyboardButton(db.get_text('btn_edit'), callback_data=f"{prefix}_edit_{item.id}"),
            InlineKeyboardButton(db.get_text('btn_delete'), callback_data=f"{prefix}_delete_{item.id}")
        ])
    keyboard.append([InlineKeyboardButton(db.get_text('btn_add_new'), callback_data=f"{prefix}_add")])
    keyboard.append([InlineKeyboardButton(db.get_text('btn_back_to_panel'), callback_data="admin_main_panel")])
    return InlineKeyboardMarkup(keyboard)

def admin_manage_texts_list(texts, current_page, total_pages):
    keyboard = []
    for text_item in texts:
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
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(db.get_text('btn_confirm_delete'), callback_data=f"{prefix}_confirmdelete_{item_id}"),
        InlineKeyboardButton(db.get_text('btn_cancel_delete'), callback_data=f"admin_list_{prefix}")
    ]])

def back_to_list_keyboard(prefix):
    return InlineKeyboardMarkup([[InlineKeyboardButton(db.get_text('btn_back_to_list'), callback_data=f"admin_list_{prefix}")]])

def parent_field_selection_keyboard(fields, prefix):
    keyboard = [[InlineKeyboardButton(f.name, callback_data=f"{prefix}_selectfield_{f.id}")] for f in fields]
    keyboard.append([InlineKeyboardButton(db.get_text('btn_cancel'), callback_data=f"admin_list_{prefix}")])
    return InlineKeyboardMarkup(keyboard)

def dynamic_list_keyboard(items, prefix, has_add_new=False):
    keyboard = []
    for item in items:
        keyboard.append([InlineKeyboardButton(item.name, callback_data=f"{prefix}_select_{item.id}")])
    if has_add_new:
        keyboard.append([InlineKeyboardButton(db.get_text('btn_add_new_professor'), callback_data=f"{prefix}_add_new")])
    keyboard.append([InlineKeyboardButton(db.get_text('btn_cancel'), callback_data="cancel_submission")])
    return InlineKeyboardMarkup(keyboard)

def attendance_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(db.get_text('btn_attendance_yes'), callback_data="attendance_yes"),
        InlineKeyboardButton(db.get_text('btn_attendance_no'), callback_data="attendance_no")
    ], [InlineKeyboardButton(db.get_text('btn_cancel'), callback_data="cancel_submission")]])

def admin_approval_keyboard(experience_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(db.get_text('btn_approve_exp'), callback_data=f"exp_approve_{experience_id}"),
        InlineKeyboardButton(db.get_text('btn_reject_exp'), callback_data=f"exp_reject_{experience_id}")
    ]])

def rejection_reasons_keyboard(experience_id):
    # This function creates a keyboard with common rejection reasons.
    # The reasons' texts are fetched from the database, so they are manageable by the admin.
    keyboard = [
        [InlineKeyboardButton(db.get_text('btn_reject_reason_1'), callback_data=f"exp_reject_reason_{experience_id}_1")],
        [InlineKeyboardButton(db.get_text('btn_reject_reason_2'), callback_data=f"exp_reject_reason_{experience_id}_2")],
        [InlineKeyboardButton(db.get_text('btn_reject_reason_3'), callback_data=f"exp_reject_reason_{experience_id}_3")],
        [InlineKeyboardButton(db.get_text('btn_back_to_list'), callback_data=f"exp_view_{experience_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)