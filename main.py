# main.py

import logging
from telegram import Update, constants
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.helpers import escape_markdown

import config
import database as db
import keyboards as kb
from models import Field, Major, Professor, Course, Experience, BotText, Admin, ExperienceStatus
from constants import (
    States, MAX_MESSAGE_LENGTH,
    FIELD_SELECT, MAJOR_SELECT, COURSE_SELECT, PROFESSOR_SELECT, PROFESSOR_ADD_NEW,
    ATTENDANCE_CHOICE, CANCEL_SUBMISSION, ADMIN_MAIN_PANEL, ADMIN_LIST_ITEMS,
    ADMIN_LIST_TEXTS, ITEM_ADD, ADMIN_ADD, ITEM_EDIT, TEXT_EDIT, ITEM_DELETE,
    ITEM_CONFIRM_DELETE, COMPLEX_ITEM_SELECT_PARENT, EXPERIENCE_APPROVAL,
    SUBMIT_EXP_BTN_KEY, MY_EXPS_BTN_KEY, RULES_BTN_KEY
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

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

def format_experience(exp: Experience, md_version: int = 2) -> str:
    """Formats an experience object into a readable string, escaping user inputs."""
    def_md(text):
        return escape_markdown(str(text), version=md_version)
    
    tags = f"#{exp.field.name.replace(' ', '_')} #{exp.major.name.replace(' ', '_')} #{exp.professor.name.replace(' ', '_')} #{exp.course.name.replace(' ', '_')}"
    attendance_text = db.get_text('exp_format_attendance_yes') if exp.attendance_required else db.get_text('exp_format_attendance_no')

    return f"""{db.get_text('exp_format_field')}: {def_md(exp.field.name)} ({def_md(exp.major.name)})
{db.get_text('exp_format_professor')}: {def_md(exp.professor.name)}
{db.get_text('exp_format_course')}: {def_md(exp.course.name)}
{db.get_text('exp_format_teaching')}:
{def_md(exp.teaching_style)}
{db.get_text('exp_format_notes')}:
{def_md(exp.notes)}
{db.get_text('exp_format_project')}:
{def_md(exp.project)}
{db.get_text('exp_format_attendance')}: {attendance_text}
{def_md(exp.attendance_details)}
{db.get_text('exp_format_exam')}:
{def_md(exp.exam)}
{db.get_text('exp_format_conclusion')}:
{def_md(exp.conclusion)}
{db.get_text('exp_format_footer')}
{db.get_text('exp_format_tags')}: {def_md(tags)}"""

async def get_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE, next_state: States, prompt_key: str) -> States:
    """Generic function to handle text inputs, validate length, and move to the next state."""
    user_input = update.message.text
    field_name = context.user_data.get('current_field', 'input')

    if len(user_input) > 1000: # Reduced for safety and better UX
        await update.message.reply_text(f"متن شما بیش از حد طولانی است (حداکثر ۱۰۰۰ کاراکتر). لطفا دوباره تلاش کنید:")
        return context.user_data['current_state']

    context.user_data['experience'][field_name] = user_input
    await update.message.reply_text(db.get_text(prompt_key))
    return next_state

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
        ExperienceStatus.PENDING: db.get_text('status_pending'),
        ExperienceStatus.APPROVED: db.get_text('status_approved'),
        ExperienceStatus.REJECTED: db.get_text('status_rejected')
    }

    for exp in exps:
        course_name = escape_markdown(exp.course.name, version=2)
        prof_name = escape_markdown(exp.professor.name, version=2)
        status_text = status_map.get(exp.status, str(exp.status))
        response += f"*{course_name}* \\- *{prof_name}* ({status_text})\n"

    await update.message.reply_text(response, parse_mode=constants.ParseMode.MARKDOWN_V2)

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(db.get_text('rules'), parse_mode=constants.ParseMode.MARKDOWN_V2)

# --- Full Submission Conversation ---
async def submission_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    context.user_data['experience'] = {}
    fields, _ = db.get_all_items(Field, page=1, per_page=100)
    await update.message.reply_text(db.get_text('submission_start'), reply_markup=kb.dynamic_list_keyboard(fields, 'field'))
    return States.SELECTING_FIELD

async def select_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    context.user_data['experience']['field_id'] = int(query.data.split('_')[-1])
    majors = db.get_majors_by_field(context.user_data['experience']['field_id'])
    await query.edit_message_text(db.get_text('choose_major'), reply_markup=kb.dynamic_list_keyboard(majors, 'major'))
    return States.SELECTING_MAJOR

async def select_major(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    context.user_data['experience']['major_id'] = int(query.data.split('_')[-1])
    courses = db.get_courses_by_major(context.user_data['experience']['major_id'])
    await query.edit_message_text(db.get_text('choose_course'), reply_markup=kb.dynamic_list_keyboard(courses, 'course'))
    return States.SELECTING_COURSE

async def select_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    context.user_data['experience']['course_id'] = int(query.data.split('_')[-1])
    professors, _ = db.get_all_items(Professor, page=1, per_page=100)
    await query.edit_message_text(db.get_text('choose_professor'), reply_markup=kb.dynamic_list_keyboard(professors, 'professor', has_add_new=True))
    return States.SELECTING_PROFESSOR

async def select_professor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    context.user_data['experience']['professor_id'] = int(query.data.split('_')[-1])
    context.user_data['current_field'] = 'teaching_style'
    context.user_data['current_state'] = States.GETTING_TEACHING
    await query.edit_message_text(db.get_text('ask_teaching_style'))
    return States.GETTING_TEACHING

async def add_new_professor_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(db.get_text('add_new_professor_prompt'))
    return States.ADDING_PROFESSOR

async def add_new_professor_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    prof_name = update.message.text.strip()
    if not prof_name or len(prof_name) > 255:
        await update.message.reply_text("نام استاد نامعتبر یا بیش از حد طولانی است. لطفا دوباره تلاش کنید:")
        return States.ADDING_PROFESSOR
    new_prof = db.add_item(Professor, name=prof_name)
    context.user_data['experience']['professor_id'] = new_prof.id
    context.user_data['current_field'] = 'teaching_style'
    context.user_data['current_state'] = States.GETTING_TEACHING
    await update.message.reply_text(db.get_text('ask_teaching_style'))
    return States.GETTING_TEACHING

async def get_teaching(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    return await get_text_input(update, context, States.GETTING_NOTES, 'ask_notes')

async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    context.user_data['current_field'] = 'notes'
    return await get_text_input(update, context, States.GETTING_PROJECT, 'ask_project')

async def get_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    context.user_data['current_field'] = 'project'
    return await get_text_input(update, context, States.GETTING_ATTENDANCE_CHOICE, 'ask_attendance_choice')

async def get_attendance_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    choice = query.data.split('_')[-1]
    context.user_data['experience']['attendance_required'] = (choice == 'yes')
    context.user_data['current_field'] = 'attendance_details'
    context.user_data['current_state'] = States.GETTING_ATTENDANCE_DETAILS
    await query.edit_message_text(db.get_text('ask_attendance_details'))
    return States.GETTING_ATTENDANCE_DETAILS

async def get_attendance_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    return await get_text_input(update, context, States.GETTING_EXAM, 'ask_exam')

async def get_exam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    context.user_data['current_field'] = 'exam'
    return await get_text_input(update, context, States.GETTING_CONCLUSION, 'ask_conclusion')

async def get_conclusion_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['current_field'] = 'conclusion'
    user_input = update.message.text
    if len(user_input) > 1000:
        await update.message.reply_text(f"متن شما بیش از حد طولانی است. لطفا دوباره تلاش کنید:")
        return States.GETTING_CONCLUSION

    context.user_data['experience']['conclusion'] = user_input
    exp_data = context.user_data['experience']
    exp_data['user_id'] = update.effective_user.id
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    new_exp = db.add_item(Experience, **exp_data)
    exp = db.get_experience(new_exp.id)
    admin_message = db.get_text('admin_new_experience_notification', exp_id=exp.id) + format_experience(exp)
    
    for admin in db.get_all_admins():
        try:
            await context.bot.send_message(
                chat_id=admin.user_id, text=admin_message,
                reply_markup=kb.admin_approval_keyboard(exp.id),
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
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

# --- Admin Panel ---
# ... (Admin panel code remains largely the same, but uses States and constants)
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

    if action == "approve":
        db.update_experience_status(exp_id, ExperienceStatus.APPROVED)
        await context.bot.send_message(chat_id=config.CHANNEL_ID, text=format_experience(exp), parse_mode=constants.ParseMode.MARKDOWN_V2)
        await query.edit_message_text(db.get_text('admin_approval_success', exp_id=exp_id))
        try:
            course_name = escape_markdown(exp.course.name, version=2)
            await context.bot.send_message(chat_id=exp.user_id, text=db.get_text('user_approval_notification', course_name=course_name), parse_mode=constants.ParseMode.MARKDOWN_V2)
        except Exception as e:
            logger.warning(f"Could not notify user {exp.user_id} about approval: {e}")

    elif action == "reject":
        await query.edit_message_text(db.get_text('rejection_reason_prompt'), reply_markup=kb.rejection_reasons_keyboard(exp_id))

    elif action == "reason":
        reason_key_num = data[3]
        reason_text = db.get_text(f'btn_reject_reason_{reason_key_num}')
        db.update_experience_status(exp_id, ExperienceStatus.REJECTED)
        await query.edit_message_text(db.get_text('admin_rejection_success', exp_id=exp_id, reason=reason_text))
        try:
            course_name = escape_markdown(exp.course.name, version=2)
            reason_text_escaped = escape_markdown(reason_text, version=2)
            await context.bot.send_message(
                chat_id=exp.user_id,
                text=db.get_text('user_rejection_notification', course_name=course_name, reason=reason_text_escaped),
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.warning(f"Could not notify user {exp.user_id} about rejection: {e}")


def main():
    db.initialize_database()
    app = Application.builder().token(config.BOT_TOKEN).build()

    submission_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^' + db.get_text(SUBMIT_EXP_BTN_KEY) + '$'), submission_start)],
        states={
            States.SELECTING_FIELD: [CallbackQueryHandler(select_field, pattern=FIELD_SELECT)],
            States.SELECTING_MAJOR: [CallbackQueryHandler(select_major, pattern=MAJOR_SELECT)],
            States.SELECTING_COURSE: [CallbackQueryHandler(select_course, pattern=COURSE_SELECT)],
            States.SELECTING_PROFESSOR: [
                CallbackQueryHandler(select_professor, pattern=PROFESSOR_SELECT),
                CallbackQueryHandler(add_new_professor_start, pattern=PROFESSOR_ADD_NEW)
            ],
            States.ADDING_PROFESSOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_new_professor_receive_name)],
            States.GETTING_TEACHING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_teaching)],
            States.GETTING_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_notes)],
            States.GETTING_PROJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_project)],
            States.GETTING_ATTENDANCE_CHOICE: [CallbackQueryHandler(get_attendance_choice, pattern=ATTENDANCE_CHOICE)],
            States.GETTING_ATTENDANCE_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_attendance_details)],
            States.GETTING_EXAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_exam)],
            States.GETTING_CONCLUSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_conclusion_and_finish)],
        },
        fallbacks=[CallbackQueryHandler(cancel_submission, pattern=CANCEL_SUBMISSION)]
    )

    # ... Other handlers (add, edit, delete) should also be updated to use States and constants ...

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(submission_handler)
    # ... Add other handlers ...
    app.add_handler(MessageHandler(filters.Regex('^' + db.get_text(MY_EXPS_BTN_KEY) + '$'), my_experiences_command))
    app.add_handler(MessageHandler(filters.Regex('^' + db.get_text(RULES_BTN_KEY) + '$'), rules_command))
    app.add_handler(CallbackQueryHandler(experience_approval_handler, pattern=EXPERIENCE_APPROVAL))

    logger.info("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()