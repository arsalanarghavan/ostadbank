# main.py

import logging
from telegram import Update, constants
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from unittest.mock import Mock

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
 GETTING_NEW_NAME, GETTING_UPDATED_NAME, SELECTING_PARENT_FIELD, GETTING_UPDATED_TEXT
) = range(16)

# --- Helper Functions ---
async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    is_admin_user = db.is_admin(update.effective_user.id)
    if not is_admin_user:
        if update.callback_query:
            await update.callback_query.answer(db.get_text('not_an_admin'), show_alert=True)
        else:
            await update.message.reply_text(db.get_text('not_an_admin'))
    return is_admin_user

def format_experience(exp: Experience) -> str:
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

async def reshow_list(update: Update, context: ContextTypes.DEFAULT_TYPE, model, prefix):
    header_key = f'admin_manage_{prefix}_header'
    # Simulating a callback_query to reuse the list_items function
    mock_query = Mock(
        message=update.message,
        data=f'admin_list_{prefix}',
        from_user=update.effective_user,
        answer=lambda: None,
        # A bit of a hack to make it reply with a new message instead of editing
        edit_message_text=update.message.reply_text 
    )
    mock_update = Mock(callback_query=mock_query, effective_user=update.effective_user)
    items = db.get_all_items(model)
    text = db.get_text(header_key)
    reply_markup = kb.admin_manage_item_list(items, prefix=prefix)
    # Since we use reply_text, it will send a new message
    await update.message.reply_text(text, reply_markup=reply_markup)


# --- User Commands & Main Menu ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.add_user(update.effective_user.id, update.effective_user.first_name)
    await update.message.reply_text(db.get_text('welcome'), reply_markup=kb.main_menu())

async def my_experiences_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(db.get_text('rules'), parse_mode=constants.ParseMode.MARKDOWN)

# --- Full Submission Conversation ---
async def submission_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['experience'] = {}
    fields = db.get_all_items(Field)
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
    field_id = context.user_data['experience']['field_id']
    courses = db.get_courses_by_field(field_id)
    await query.edit_message_text(db.get_text('choose_course'), reply_markup=kb.dynamic_list_keyboard(courses, 'course'))
    return SELECTING_COURSE

async def select_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    course_id = int(query.data.split('_')[-1])
    context.user_data['experience']['course_id'] = course_id
    professors = db.get_all_items(Professor)
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
    prof_name = update.message.text
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
    for admin in db.get_all_items(Admin):
        try:
            await context.bot.send_message(chat_id=admin.user_id, text=admin_message, reply_markup=kb.admin_approval_keyboard(exp.id))
        except Exception as e:
            logger.error(f"Failed to send to admin {admin.user_id}: {e}")
    await update.message.reply_text(db.get_text('submission_success'), reply_markup=kb.main_menu())
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(db.get_text('submission_cancel'))
    context.user_data.clear()
    # Need to send a follow-up message to show the main menu again
    await context.bot.send_message(chat_id=update.effective_chat.id, text=db.get_text('welcome'), reply_markup=kb.main_menu())
    return ConversationHandler.END

# --- Full Admin Panel ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_admin(update, context):
        await update.message.reply_text(db.get_text('admin_panel_welcome'), reply_markup=kb.admin_panel_main())

async def admin_main_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_admin(update, context):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(db.get_text('admin_panel_welcome'), reply_markup=kb.admin_panel_main())

# --- List Handlers ---
async def list_items(update: Update, context: ContextTypes.DEFAULT_TYPE, model, prefix):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    header_key = f'admin_manage_{prefix}_header'
    await query.edit_message_text(db.get_text(header_key), reply_markup=kb.admin_manage_item_list(db.get_all_items(model), prefix))

# --- Add Handlers ---
async def add_simple_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    prefix = query.data.split('_')[0]
    context.user_data['prefix'] = prefix
    await query.answer()
    await query.edit_message_text(db.get_text('ask_for_new_item_name'), reply_markup=kb.back_to_list_keyboard(prefix))
    return GETTING_NEW_NAME

async def save_simple_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prefix = context.user_data.pop('prefix')
    model = {'field': Field, 'professor': Professor}[prefix]
    db.add_item(model, name=update.message.text)
    await update.message.reply_text(db.get_text('item_added_successfully'))
    await reshow_list(update, context, model, prefix)
    return ConversationHandler.END

async def add_complex_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    prefix = query.data.split('_')[0]
    context.user_data['prefix'] = prefix
    await query.answer()
    await query.edit_message_text(db.get_text('select_parent_field'), reply_markup=kb.parent_field_selection_keyboard(db.get_all_items(Field), prefix))
    return SELECTING_PARENT_FIELD

async def complex_item_select_parent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['field_id'] = int(query.data.split('_')[-1])
    await query.edit_message_text(db.get_text('ask_for_new_item_name'))
    return GETTING_NEW_NAME

async def save_complex_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prefix = context.user_data.pop('prefix')
    field_id = context.user_data.pop('field_id')
    model = {'major': Major, 'course': Course}[prefix]
    db.add_item(model, name=update.message.text, field_id=field_id)
    await update.message.reply_text(db.get_text('item_added_successfully'))
    await reshow_list(update, context, model, prefix)
    return ConversationHandler.END

# --- Edit Handlers ---
async def edit_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    prefix, _, item_id_str = query.data.split('_')
    item_id = int(item_id_str)
    model = {'field': Field, 'professor': Professor, 'major': Major, 'course': Course}[prefix]
    item = db.get_item_by_id(model, item_id)
    context.user_data['item_id_to_edit'] = item_id
    context.user_data['prefix'] = prefix
    await query.edit_message_text(db.get_text('ask_for_update_item_name', current_name=item.name), reply_markup=kb.back_to_list_keyboard(prefix))
    return GETTING_UPDATED_NAME

async def save_updated_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prefix = context.user_data.pop('prefix')
    item_id = context.user_data.pop('item_id_to_edit')
    model = {'field': Field, 'professor': Professor, 'major': Major, 'course': Course}[prefix]
    db.update_item(model, item_id, name=update.message.text)
    await update.message.reply_text(db.get_text('item_updated_successfully'))
    await reshow_list(update, context, model, prefix)
    return ConversationHandler.END

# --- Delete Handlers ---
async def delete_item_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prefix, _, item_id_str = query.data.split('_')
    item_id = int(item_id_str)
    model = {'field': Field, 'professor': Professor, 'major': Major, 'course': Course}[prefix]
    item = db.get_item_by_id(model, item_id)
    await query.edit_message_text(db.get_text('confirm_delete', item_name=item.name), reply_markup=kb.confirm_delete_keyboard(prefix, item_id), parse_mode=constants.ParseMode.MARKDOWN)

async def delete_item_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer(db.get_text('item_deleted_successfully'), show_alert=True)
    prefix, _, item_id_str = query.data.split('_')
    item_id = int(item_id_str)
    model = {'field': Field, 'professor': Professor, 'major': Major, 'course': Course}[prefix]
    db.delete_item(model, item_id)
    # Re-show the list after deletion
    mock_query = Mock(message=query.message, data=f'admin_list_{prefix}', from_user=update.effective_user, answer=lambda:None, edit_message_text=query.edit_message_text)
    mock_update = Mock(callback_query=mock_query, effective_user=update.effective_user)
    await list_items(mock_update, context, model, prefix)


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
    # The primary key of BotText is 'key', so we use that instead of an 'id'
    with db.session_scope() as s:
        text_item = s.query(BotText).filter_by(key=key).first()
        if text_item:
            text_item.value = new_value
    
    await update.message.reply_text(db.get_text('item_updated_successfully'))
    
    # Simulate a callback to show the text list again
    mock_query = Mock(message=update.message, data='admin_list_texts_1', from_user=update.effective_user, answer=lambda:None, edit_message_text=update.message.reply_text)
    mock_update = Mock(callback_query=mock_query, effective_user=update.effective_user)
    await admin_list_texts(mock_update, context)
    return ConversationHandler.END


# --- General Cancel Handler for Admin Conversations ---
async def cancel_admin_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    prefix = query.data.split('_')[-1]
    model_map = {'field': Field, 'professor': Professor, 'major': Major, 'course': Course}

    if prefix in model_map:
        await list_items(update, context, model_map[prefix], prefix)
    elif 'texts' in prefix: # Handles texts_1, texts_2 etc.
        await admin_list_texts(update, context)
    else:
        await admin_main_panel_callback(update, context)
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

    if action == "view":
        exp = db.get_experience(exp_id)
        admin_message = db.get_text('admin_recheck_experience', exp_id=exp.id) + format_experience(exp)
        await query.edit_message_text(admin_message, reply_markup=kb.admin_approval_keyboard(exp_id))
        return

    if action == "approve":
        db.update_experience_status(exp_id, 'approved')
        exp = db.get_experience(exp_id)
        await context.bot.send_message(chat_id=config.CHANNEL_ID, text=format_experience(exp), parse_mode=constants.ParseMode.MARKDOWN)
        await query.edit_message_text(db.get_text('admin_approval_success', exp_id=exp_id))
        try:
            exp_course = db.get_item_by_id(Course, exp.course_id)
            await context.bot.send_message(chat_id=exp.user_id, text=db.get_text('user_approval_notification', course_name=exp_course.name))
        except Exception as e:
            logger.warning(f"Could not notify user {exp.user_id}: {e}")

    elif action == "reject":
        await query.edit_message_text(db.get_text('rejection_reason_prompt'), reply_markup=kb.rejection_reasons_keyboard(exp_id))
    
    elif action == "reason":
        reason_key_num = data[3]
        reason_text = db.get_text(f'btn_reject_reason_{reason_key_num}')
        db.update_experience_status(exp_id, 'rejected')
        await query.edit_message_text(db.get_text('admin_rejection_success', exp_id=exp_id, reason=reason_text))
        exp = db.get_experience(exp_id)
        try:
            exp_course = db.get_item_by_id(Course, exp.course_id)
            await context.bot.send_message(chat_id=exp.user_id, text=db.get_text('user_rejection_notification', course_name=exp_course.name, reason=reason_text))
        except Exception as e:
            logger.warning(f"Could not notify user {exp.user_id}: {e}")

# --- Main Application ---
def main():
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

    add_simple_item_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_simple_item_start, pattern="^field_add$"),
            CallbackQueryHandler(add_simple_item_start, pattern="^professor_add$"),
        ],
        states={GETTING_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_simple_item)]},
        fallbacks=[CallbackQueryHandler(cancel_admin_conversation, pattern="^admin_list_")]
    )

    add_complex_item_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_complex_item_start, pattern="^major_add$"),
            CallbackQueryHandler(add_complex_item_start, pattern="^course_add$"),
        ],
        states={
            SELECTING_PARENT_FIELD: [CallbackQueryHandler(complex_item_select_parent, pattern="^(major|course)_selectfield_")],
            GETTING_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_complex_item)],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_conversation, pattern="^admin_list_")]
    )
    
    edit_item_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_item_start, pattern="^.*_edit_.*$")],
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

    app.add_handler(submission_handler)
    app.add_handler(add_simple_item_handler)
    app.add_handler(add_complex_item_handler)
    app.add_handler(edit_item_handler)
    app.add_handler(edit_text_handler)

    app.add_handler(CallbackQueryHandler(admin_main_panel_callback, pattern="^admin_main_panel$"))
    app.add_handler(CallbackQueryHandler(lambda u,c: list_items(u,c,Field,'field'), pattern="^admin_list_field$"))
    app.add_handler(CallbackQueryHandler(lambda u,c: list_items(u,c,Major,'major'), pattern="^admin_list_major$"))
    app.add_handler(CallbackQueryHandler(lambda u,c: list_items(u,c,Professor,'professor'), pattern="^admin_list_professor$"))
    app.add_handler(CallbackQueryHandler(lambda u,c: list_items(u,c,Course,'course'), pattern="^admin_list_course$"))
    app.add_handler(CallbackQueryHandler(admin_list_texts, pattern="^admin_list_texts_"))

    app.add_handler(CallbackQueryHandler(delete_item_confirm, pattern="^.*_delete_.*$"))
    app.add_handler(CallbackQueryHandler(delete_item_execute, pattern="^.*_confirmdelete_.*$"))
    
    app.add_handler(CallbackQueryHandler(experience_approval_handler, pattern="^exp_"))

    # Handlers for main menu buttons
    app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_my_experiences') + '$'), my_experiences_command))
    app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_rules') + '$'), rules_command))

    logger.info("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()