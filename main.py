# main.py

import logging
from telegram import Update, constants
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)

import config
import database as db
import keyboards as kb
from models import Field, Major, Professor, Course, Experience, BotText, Admin

# --- Logging Configuration ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Conversation States ---
(SELECTING_FIELD, SELECTING_MAJOR, SELECTING_COURSE, SELECTING_PROFESSOR, ADDING_PROFESSOR,
 GETTING_TEACHING, GETTING_NOTES, GETTING_PROJECT, GETTING_ATTENDANCE_CHOICE,
 GETTING_ATTENDANCE_DETAILS, GETTING_EXAM, GETTING_CONCLUSION,
 # Admin States
 GETTING_NEW_NAME, GETTING_UPDATED_NAME, SELECTING_PARENT_FIELD, GETTING_UPDATED_TEXT,
 GETTING_ADMIN_ID # State جدید برای افزودن ادمین
) = range(17)

# --- Helper Functions ---
async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Checks if the user is an admin and sends a message if not."""
    is_admin_user = db.is_admin(update.effective_user.id)
    if not is_admin_user:
        if update.callback_query:
            await update.callback_query.answer(db.get_text('not_an_admin'), show_alert=True)
        else:
            await update.message.reply_text(db.get_text('not_an_admin'))
    return is_admin_user

def format_experience(exp: Experience) -> str:
    """Formats an experience object into a readable string for sending in messages."""
    tags = f"#{exp.field.name.replace(' ', '_')} #{exp.major.name.replace(' ', '_')} #{exp.professor.name.replace(' ', '_')} #{exp.course.name.replace(' ', '_')}"

    attendance_text = db.get_text('exp_format_attendance_yes') if exp.attendance_required else db.get_text('exp_format_attendance_no')

    return f"""{db.get_text('exp_format_field')}: {exp.field.name} ({exp.major.name})

{db.get_text('exp_format_professor')}: {exp.professor.name}

{db.get_text('exp_format_course')}: {exp.course.name}

{db.get_text('exp_format_teaching')}:
{exp.teaching_style}

{db.get_text('exp_format_notes')}:
{exp.notes}

{db.get_text('exp_format_project')}:
{exp.project}

{db.get_text('exp_format_attendance')}: {attendance_text}
{exp.attendance_details}

{db.get_text('exp_format_exam')}:
{exp.exam}

{db.get_text('exp_format_conclusion')}:
{exp.conclusion}

{db.get_text('exp_format_footer')}
{db.get_text('exp_format_tags')}: {tags}"""

# --- User Commands & Main Menu ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    db.add_user(update.effective_user.id, update.effective_user.first_name)
    await update.message.reply_text(db.get_text('welcome'), reply_markup=kb.main_menu())

async def my_experiences_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'My Experiences' button."""
    exps = db.get_user_experiences(update.effective_user.id)
    if not exps:
        await update.message.reply_text(db.get_text('my_experiences_empty'))
        return
    response = db.get_text('my_experiences_header')

    status_map = {
        'pending': db.get_text('status_pending'),
        'approved': db.get_text('status_approved'),
        'rejected': db.get_text('status_rejected')
    }

    for exp in exps:
        exp_course = db.get_item_by_id(Course, exp.course_id)
        exp_prof = db.get_item_by_id(Professor, exp.professor_id)
        status_text = status_map.get(exp.status, exp.status)
        response += f"**{exp_course.name}** - **{exp_prof.name}** ({status_text})\n"

    await update.message.reply_text(response, parse_mode=constants.ParseMode.MARKDOWN)

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Rules' button."""
    await update.message.reply_text(db.get_text('rules'), parse_mode=constants.ParseMode.MARKDOWN)

# --- Full Submission Conversation ---
async def submission_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['experience'] = {}
    fields = db.get_majors_by_field(1) # Assuming field with id 1 is the default
    await update.message.reply_text(db.get_text('submission_start'), reply_markup=kb.dynamic_list_keyboard(fields, 'field'))
    return SELECTING_FIELD

async def select_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    field_id = int(query.data.split('_')[-1])
    context.user_data['experience']['field_id'] = field_id
    majors = db.get_majors_by_field(field_id)
    await query.edit_message_text(db.get_text('choose_major'), reply_markup=kb.dynamic_list_keyboard(majors, 'major'))
    return SELECTING_MAJOR

async def select_major(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    major_id = int(query.data.split('_')[-1])
    context.user_data['experience']['major_id'] = major_id
    courses = db.get_courses_by_major(major_id)
    await query.edit_message_text(db.get_text('choose_course'), reply_markup=kb.dynamic_list_keyboard(courses, 'course'))
    return SELECTING_COURSE

async def select_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    course_id = int(query.data.split('_')[-1])
    context.user_data['experience']['course_id'] = course_id
    professors, _ = db.get_all_items(Professor, page=1, per_page=100) # Get all profs
    await query.edit_message_text(db.get_text('choose_professor'), reply_markup=kb.dynamic_list_keyboard(professors, 'professor', has_add_new=True))
    return SELECTING_PROFESSOR

async def select_professor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    prof_id = int(query.data.split('_')[-1])
    context.user_data['experience']['professor_id'] = prof_id
    await query.edit_message_text(db.get_text('ask_teaching_style'))
    return GETTING_TEACHING

async def add_new_professor_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(db.get_text('add_new_professor_prompt'))
    return ADDING_PROFESSOR

async def add_new_professor_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prof_name = update.message.text.strip()
    if not prof_name:
        await update.message.reply_text("نام استاد نمی‌تواند خالی باشد. لطفا دوباره تلاش کنید:")
        return ADDING_PROFESSOR
    new_prof = db.add_item(Professor, name=prof_name)
    context.user_data['experience']['professor_id'] = new_prof.id
    await update.message.reply_text(db.get_text('ask_teaching_style'))
    return GETTING_TEACHING

async def get_teaching(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['experience']['teaching_style'] = update.message.text
    await update.message.reply_text(db.get_text('ask_notes'))
    return GETTING_NOTES

async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['experience']['notes'] = update.message.text
    await update.message.reply_text(db.get_text('ask_project'))
    return GETTING_PROJECT

async def get_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['experience']['project'] = update.message.text
    await update.message.reply_text(db.get_text('ask_attendance_choice'), reply_markup=kb.attendance_keyboard())
    return GETTING_ATTENDANCE_CHOICE

async def get_attendance_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data.split('_')[-1]
    context.user_data['experience']['attendance_required'] = (choice == 'yes')
    await query.edit_message_text(db.get_text('ask_attendance_details'))
    return GETTING_ATTENDANCE_DETAILS

async def get_attendance_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['experience']['attendance_details'] = update.message.text
    await update.message.reply_text(db.get_text('ask_exam'))
    return GETTING_EXAM

async def get_exam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['experience']['exam'] = update.message.text
    await update.message.reply_text(db.get_text('ask_conclusion'))
    return GETTING_CONCLUSION

async def get_conclusion_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['experience']['conclusion'] = update.message.text
    exp_data = context.user_data['experience']
    exp_data['user_id'] = update.effective_user.id
    new_exp = db.add_item(Experience, **exp_data)
    exp = db.get_experience(new_exp.id)
    admin_message = db.get_text('admin_new_experience_notification', exp_id=exp.id) + format_experience(exp)
    for admin in db.get_all_admins():
        try:
            await context.bot.send_message(chat_id=admin.user_id, text=admin_message, reply_markup=kb.admin_approval_keyboard(exp.id))
        except Exception as e:
            logger.error(f"Failed to send notification to admin {admin.user_id}: {e}")
    await update.message.reply_text(db.get_text('submission_success'), reply_markup=kb.main_menu())
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(db.get_text('operation_cancelled'))
    context.user_data.clear()
    return ConversationHandler.END

# --- Full Admin Panel ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /admin command."""
    if await check_admin(update, context):
        await update.message.reply_text(db.get_text('admin_panel_welcome'), reply_markup=kb.admin_panel_main())

async def admin_main_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Back to Panel' button."""
    if await check_admin(update, context):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(db.get_text('admin_panel_welcome'), reply_markup=kb.admin_panel_main())

# --- Generic List Handler ---
async def list_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A generic handler to display paginated lists in the admin panel."""
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_') # e.g., "admin_list_field_1"
    prefix = parts[2]
    page = int(parts[3])

    model_map = {
        'field': (Field, 'admin_manage_field_header'),
        'major': (Major, 'admin_manage_major_header'),
        'professor': (Professor, 'admin_manage_professor_header'),
        'course': (Course, 'admin_manage_course_header'),
        'admin': (Admin, "👮‍♂️ مدیریت ادمین‌ها")
    }
    model, header = model_map[prefix]
    
    text = header if prefix == 'admin' else db.get_text(header)
    items, total_pages = db.get_all_items(model, page=page)
    reply_markup = kb.admin_manage_item_list(items, prefix, page, total_pages)
    
    await query.edit_message_text(text, reply_markup=reply_markup)


# --- Add Handlers ---
async def add_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    prefix = query.data.split('_')[1] # e.g., field from "field_add"
    context.user_data['prefix'] = prefix
    
    model_map = {'major': Major, 'course': Course}

    if prefix in model_map:
        fields, _ = db.get_all_items(Field, per_page=100)
        await query.answer()
        await query.edit_message_text(db.get_text('select_parent_field'), reply_markup=kb.parent_field_selection_keyboard(fields, prefix))
        return SELECTING_PARENT_FIELD
    elif prefix == 'admin':
        await query.answer()
        await query.edit_message_text("لطفا شناسه عددی (User ID) ادمین جدید را وارد کنید:", reply_markup=kb.back_to_list_keyboard(prefix))
        return GETTING_ADMIN_ID
    else: # Simple items like Field, Professor
        await query.answer()
        await query.edit_message_text(db.get_text('ask_for_new_item_name'), reply_markup=kb.back_to_list_keyboard(prefix))
        return GETTING_NEW_NAME

async def complex_item_select_parent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['parent_id'] = int(query.data.split('_')[-1])
    await query.edit_message_text(db.get_text('ask_for_new_item_name'))
    return GETTING_NEW_NAME

async def save_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prefix = context.user_data.pop('prefix')
    name = update.message.text.strip()
    
    model_map = {'field': Field, 'professor': Professor, 'major': Major, 'course': Course}
    kwargs = {'name': name}

    if prefix in ['major', 'course']:
        parent_id = context.user_data.pop('parent_id')
        parent_key = 'field_id' if prefix == 'major' else 'major_id'
        kwargs[parent_key] = parent_id

    db.add_item(model_map[prefix], **kwargs)
    await update.message.reply_text(db.get_text('item_added_successfully'))

    # Reshow list
    query_data = f"admin_list_{prefix}_1"
    update.callback_query = Update(update.update_id, callback_query={'data': query_data, 'message': update.message, 'from_user': update.effective_user}).callback_query
    await list_items(update, context)
    return ConversationHandler.END

async def save_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = int(update.message.text.strip())
        db.add_item(Admin, user_id=user_id)
        await update.message.reply_text(db.get_text('item_added_successfully'))
    except ValueError:
        await update.message.reply_text("شناسه وارد شده نامعتبر است. لطفا یک عدد وارد کنید.")
    
    # Reshow list
    query_data = "admin_list_admin_1"
    update.callback_query = Update(update.update_id, callback_query={'data': query_data, 'message': update.message, 'from_user': update.effective_user}).callback_query
    await list_items(update, context)
    return ConversationHandler.END


# --- Edit Handlers ---
async def edit_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    prefix, _, item_id_str = query.data.split('_')
    item_id = int(item_id_str)
    
    model_map = {'field': Field, 'professor': Professor, 'major': Major, 'course': Course}
    item = db.get_item_by_id(model_map[prefix], item_id)
    
    context.user_data['item_id_to_edit'] = item_id
    context.user_data['prefix'] = prefix
    
    await query.edit_message_text(db.get_text('ask_for_update_item_name', current_name=item.name), reply_markup=kb.back_to_list_keyboard(prefix))
    return GETTING_UPDATED_NAME

async def save_updated_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prefix = context.user_data.pop('prefix')
    item_id = context.user_data.pop('item_id_to_edit')
    
    model_map = {'field': Field, 'professor': Professor, 'major': Major, 'course': Course}
    db.update_item(model_map[prefix], item_id, name=update.message.text.strip())
    
    await update.message.reply_text(db.get_text('item_updated_successfully'))
    
    query_data = f"admin_list_{prefix}_1"
    update.callback_query = Update(update.update_id, callback_query={'data': query_data, 'message': update.message, 'from_user': update.effective_user}).callback_query
    await list_items(update, context)
    return ConversationHandler.END

# --- Delete Handlers ---
async def delete_item_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prefix, _, item_id_str = query.data.split('_')
    item_id = int(item_id_str)
    
    model_map = {'field': Field, 'professor': Professor, 'major': Major, 'course': Course, 'admin': Admin}
    item = db.get_item_by_id(model_map[prefix], item_id)
    
    item_name = item.name if hasattr(item, 'name') else f"Admin ID: {item.user_id}"
    await query.edit_message_text(db.get_text('confirm_delete', item_name=item_name), reply_markup=kb.confirm_delete_keyboard(prefix, item_id), parse_mode=constants.ParseMode.MARKDOWN)

async def delete_item_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    prefix, _, item_id_str = query.data.split('_')
    item_id = int(item_id_str)

    model_map = {'field': Field, 'professor': Professor, 'major': Major, 'course': Course, 'admin': Admin}
    
    # Prevent the owner from being deleted
    if prefix == 'admin':
        admin_to_delete = db.get_item_by_id(Admin, item_id)
        if admin_to_delete and admin_to_delete.user_id == config.OWNER_ID:
            await query.answer("شما نمی‌توانید ادمین اصلی را حذف کنید!", show_alert=True)
            query.data = f"admin_list_{prefix}_1"
            await list_items(update, context)
            return

    db.delete_item(model_map[prefix], item_id)
    await query.answer(db.get_text('item_deleted_successfully'), show_alert=True)
    
    query.data = f"admin_list_{prefix}_1"
    await list_items(update, context)

# --- Text Management Handlers ---
async def admin_list_texts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    page = int(query.data.split('_')[-1])
    texts, total_pages = db.get_paginated_texts(page=page)
    await query.edit_message_text(
        text=db.get_text('admin_manage_texts_header'),
        reply_markup=kb.admin_manage_texts_list(texts, page, total_pages),
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def edit_text_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    text_key = query.data.split('text_edit_')[-1]
    context.user_data['text_key_to_edit'] = text_key
    await query.edit_message_text(db.get_text('ask_for_update_text_value', key=text_key), reply_markup=kb.back_to_list_keyboard('texts_1'))
    return GETTING_UPDATED_TEXT

async def save_updated_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_value = update.message.text
    key = context.user_data.pop('text_key_to_edit')
    
    with db.session_scope() as s:
        text_item = s.query(BotText).filter_by(key=key).first()
        if text_item:
            text_item.value = new_value
    
    await update.message.reply_text(db.get_text('item_updated_successfully'))
    
    query_data = 'admin_list_texts_1'
    update.callback_query = Update(update.update_id, callback_query={'data': query_data, 'message': update.message, 'from_user': update.effective_user}).callback_query
    await admin_list_texts(update, context)
    return ConversationHandler.END

# --- General Cancel Handler for Admin Conversations ---
async def cancel_admin_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    prefix = query.data.split('_')[-2] # admin_list_{prefix}_{page}
    await list_items(update, context)
    context.user_data.clear()
    return ConversationHandler.END

# --- Experience Approval Handler ---
async def experience_approval_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    action = data[1]
    exp_id = int(data[2])

    exp = db.get_experience(exp_id)
    if not exp:
        await query.edit_message_text("این تجربه دیگر وجود ندارد.")
        return

    if action == "view":
        admin_message = db.get_text('admin_recheck_experience', exp_id=exp.id) + format_experience(exp)
        await query.edit_message_text(admin_message, reply_markup=kb.admin_approval_keyboard(exp_id))
        return

    if action == "approve":
        db.update_experience_status(exp_id, 'approved')
        await context.bot.send_message(chat_id=config.CHANNEL_ID, text=format_experience(exp), parse_mode=constants.ParseMode.MARKDOWN)
        await query.edit_message_text(db.get_text('admin_approval_success', exp_id=exp_id))
        try:
            await context.bot.send_message(chat_id=exp.user_id, text=db.get_text('user_approval_notification', course_name=exp.course.name))
        except Exception as e:
            logger.warning(f"Could not notify user {exp.user_id} about approval: {e}")

    elif action == "reject":
        await query.edit_message_text(db.get_text('rejection_reason_prompt'), reply_markup=kb.rejection_reasons_keyboard(exp_id))

    elif action == "reason":
        reason_key_num = data[3]
        reason_text = db.get_text(f'btn_reject_reason_{reason_key_num}')
        db.update_experience_status(exp_id, 'rejected')
        await query.edit_message_text(db.get_text('admin_rejection_success', exp_id=exp_id, reason=reason_text))
        try:
            await context.bot.send_message(chat_id=exp.user_id, text=db.get_text('user_rejection_notification', course_name=exp.course.name, reason=reason_text))
        except Exception as e:
            logger.warning(f"Could not notify user {exp.user_id} about rejection: {e}")


# --- Main Application Setup ---
def main():
    """Initializes the database and starts the bot."""
    db.initialize_database()
    app = Application.builder().token(config.BOT_TOKEN).build()

    # --- Conversation Handlers Definition ---
    submission_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^' + db.get_text('btn_submit_experience') + '$'), submission_start)],
        states={
            SELECTING_FIELD: [CallbackQueryHandler(select_field, pattern="^field_select_")],
            SELECTING_MAJOR: [CallbackQueryHandler(select_major, pattern="^major_select_")],
            SELECTING_COURSE: [CallbackQueryHandler(select_course, pattern="^course_select_")],
            SELECTING_PROFESSOR: [CallbackQueryHandler(select_professor, pattern="^professor_select_"), CallbackQueryHandler(add_new_professor_start, pattern="^professor_add_new$")],
            ADDING_PROFESSOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_new_professor_receive_name)],
            GETTING_TEACHING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_teaching)],
            GETTING_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_notes)],
            GETTING_PROJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_project)],
            GETTING_ATTENDANCE_CHOICE: [CallbackQueryHandler(get_attendance_choice, pattern="^attendance_")],
            GETTING_ATTENDANCE_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_attendance_details)],
            GETTING_EXAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_exam)],
            GETTING_CONCLUSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_conclusion_and_finish)],
        },
        fallbacks=[CallbackQueryHandler(cancel_submission, pattern="^cancel_submission$")]
    )

    add_item_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_item_start, pattern="^(field|major|course|professor)_add$")],
        states={
            SELECTING_PARENT_FIELD: [CallbackQueryHandler(complex_item_select_parent, pattern="^(major|course)_selectfield_")],
            GETTING_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_item)],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_conversation, pattern="^admin_list_")]
    )

    add_admin_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_item_start, pattern="^admin_add$")],
        states={GETTING_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_admin)]},
        fallbacks=[CallbackQueryHandler(cancel_admin_conversation, pattern="^admin_list_")]
    )

    edit_item_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_item_start, pattern="^(field|major|course|professor)_edit_")],
        states={GETTING_UPDATED_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_updated_item_name)]},
        fallbacks=[CallbackQueryHandler(cancel_admin_conversation, pattern="^admin_list_")]
    )

    edit_text_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_text_start, pattern="^text_edit_")],
        states={GETTING_UPDATED_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_updated_text)]},
        fallbacks=[CallbackQueryHandler(cancel_admin_conversation, pattern="^admin_list_texts_")]
    )

    # --- Registering All Handlers ---
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))

    # Conversation Handlers
    app.add_handler(submission_handler)
    app.add_handler(add_item_handler)
    app.add_handler(add_admin_handler)
    app.add_handler(edit_item_handler)
    app.add_handler(edit_text_handler)

    # CallbackQuery Handlers for Admin Panel
    app.add_handler(CallbackQueryHandler(admin_main_panel_callback, pattern="^admin_main_panel$"))
    app.add_handler(CallbackQueryHandler(list_items, pattern="^admin_list_"))
    app.add_handler(CallbackQueryHandler(admin_list_texts, pattern="^admin_list_texts_"))
    app.add_handler(CallbackQueryHandler(delete_item_confirm, pattern="^.*_delete_.*$"))
    app.add_handler(CallbackQueryHandler(delete_item_execute, pattern="^.*_confirmdelete_.*$"))
    app.add_handler(CallbackQueryHandler(experience_approval_handler, pattern="^exp_"))

    # Message Handlers for Main Menu (using Regex on texts fetched from DB)
    app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_my_experiences') + '$'), my_experiences_command))
    app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_rules') + '$'), rules_command))

    logger.info("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()