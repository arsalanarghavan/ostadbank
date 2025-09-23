# keyboards.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

def main_menu():
    return ReplyKeyboardMarkup([["✍️ ثبت تجربه"], ["📖 تجربه‌های من", "📜 قوانین"]], resize_keyboard=True)

def admin_panel_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 مدیریت رشته‌ها", callback_data="admin_list_field")],
        [InlineKeyboardButton("📚 مدیریت گرایش‌ها", callback_data="admin_list_major")],
        [InlineKeyboardButton("👨🏻‍🏫 مدیریت اساتید", callback_data="admin_list_professor")],
        [InlineKeyboardButton("📝 مدیریت دروس", callback_data="admin_list_course")],
    ])

def admin_manage_item_list(items, prefix):
    keyboard = []
    for item in items:
        keyboard.append([
            InlineKeyboardButton(item.name, callback_data=f"none"),
            InlineKeyboardButton("✏️ ویرایش", callback_data=f"{prefix}_edit_{item.id}"),
            InlineKeyboardButton("🗑️ حذف", callback_data=f"{prefix}_delete_{item.id}")
        ])
    keyboard.append([InlineKeyboardButton(f"➕ افزودن آیتم جدید", callback_data=f"{prefix}_add")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل اصلی", callback_data="admin_main_panel")])
    return InlineKeyboardMarkup(keyboard)

def confirm_delete_keyboard(prefix, item_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"{prefix}_confirmdelete_{item_id}"),
        InlineKeyboardButton("❌ خیر، بازگشت", callback_data=f"admin_list_{prefix}")
    ]])

def back_to_list_keyboard(prefix):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به لیست", callback_data=f"admin_list_{prefix}")]])

def parent_field_selection_keyboard(fields, prefix):
    keyboard = [[InlineKeyboardButton(f.name, callback_data=f"{prefix}_selectfield_{f.id}")] for f in fields]
    keyboard.append([InlineKeyboardButton("❌ لغو", callback_data=f"admin_list_{prefix}")])
    return InlineKeyboardMarkup(keyboard)

def dynamic_list_keyboard(items, prefix, has_add_new=False, add_new_text="افزودن آیتم جدید"):
    keyboard = [[InlineKeyboardButton(item.name, callback_data=f"{prefix}_select_{item.id}")] for item in items]
    if has_add_new:
        keyboard.append([InlineKeyboardButton(f"➕ {add_new_text}", callback_data=f"{prefix}_add_new")])
    keyboard.append([InlineKeyboardButton("❌ لغو", callback_data="cancel_submission")])
    return InlineKeyboardMarkup(keyboard)

def attendance_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ دارد", callback_data="attendance_yes"),
        InlineKeyboardButton("⛔️ ندارد", callback_data="attendance_no")
    ], [InlineKeyboardButton("❌ لغو", callback_data="cancel_submission")]])

def admin_approval_keyboard(experience_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ تایید تجربه", callback_data=f"exp_approve_{experience_id}"),
        InlineKeyboardButton("❌ رد تجربه", callback_data=f"exp_reject_{experience_id}")
    ]])

def rejection_reasons_keyboard(experience_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("اطلاعات ناقص", callback_data=f"exp_reject_reason_{experience_id}_incomplete")],
        [InlineKeyboardButton("محتوای توهین‌آمیز", callback_data=f"exp_reject_reason_{experience_id}_insulting")],
        [InlineKeyboardButton("نامرتبط", callback_data=f"exp_reject_reason_{experience_id}_irrelevant")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"exp_view_{experience_id}")]
    ])