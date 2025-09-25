import logging
import asyncio
import datetime
import os
import re 
from telegram import Update, constants, ChatMember, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.helpers import escape_markdown
from telegram.error import TelegramError
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager

import config
import database as db
import keyboards as kb
from models import (Field, Major, Professor, Course, Experience, BotText, Admin,
                    ExperienceStatus, RequiredChannel, Setting, User)
from constants import (
    States,
    FIELD_SELECT, MAJOR_SELECT, COURSE_SELECT, PROFESSOR_SELECT, PROFESSOR_ADD_NEW,
    ATTENDANCE_CHOICE, CANCEL_SUBMISSION, ADMIN_MAIN_PANEL, ADMIN_LIST_ITEMS,
    ADMIN_LIST_TEXTS, ITEM_ADD, ADMIN_ADD, ITEM_EDIT, TEXT_EDIT, ITEM_DELETE,
    ITEM_CONFIRM_DELETE, COMPLEX_ITEM_SELECT_PARENT, EXPERIENCE_APPROVAL,
    SUBMIT_EXP_BTN_KEY, MY_EXPS_BTN_KEY, RULES_BTN_KEY, CHECK_MEMBERSHIP,
    ADMIN_MANAGE_CHANNELS, ADMIN_ADD_CHANNEL, ADMIN_DELETE_CHANNEL, ADMIN_TOGGLE_FORCE_SUB,
    ADMIN_MANAGE_EXPERIENCES, ADMIN_LIST_PENDING_EXPERIENCES, ADMIN_PENDING_EXPERIENCE_DETAIL
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

db.initialize_database()

MODEL_MAP = {
    'field': Field, 'major': Major, 'professor': Professor,
    'course': Course, 'admin': Admin, 'text': BotText
}
PREFIX_MAP = {
    'field': 'رشته', 'major': 'گرایش', 'professor': 'استاد',
    'course': 'درس', 'admin': 'ادمین', 'text': 'متن'
}

async def backup_database(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Starting scheduled database backup...")
    backup_filename = ""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"ostadbank_backup_{timestamp}.sql"
        command = (
            f"mysqldump --skip-ssl -h {config.DB_HOST} "
            f"-P {config.DB_PORT} "
            f"-u {config.DB_USER} "
            f"-p{config.DB_PASSWORD} "
            f"--single-transaction --routines --triggers "
            f"{config.DB_NAME} > {backup_filename}"
        )
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            error_message = stderr.decode().strip()
            logger.error(f"Database backup failed! Error: {error_message}")
            await context.bot.send_message(chat_id=config.OWNER_ID, text=f"🔴 DB Backup Failed: `{error_message}`")
            return
        with open(backup_filename, 'rb') as backup_file:
            await context.bot.send_document(
                chat_id=config.BACKUP_CHANNEL_ID,
                document=backup_file,
                caption=f"✅ DB Backup\n🗓 `{timestamp}`"
            )
        logger.info(f"DB backup successful: {backup_filename}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during backup: {e}")
    finally:
        if os.path.exists(backup_filename):
            os.remove(backup_filename)

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    is_admin_user = db.is_admin(update.effective_user.id)
    if not is_admin_user:
        if update.callback_query:
            await update.callback_query.answer(db.get_text('not_an_admin'), show_alert=True)
        else:
            await update.message.reply_text(db.get_text('not_an_admin'))
    return is_admin_user

async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if db.get_setting('force_subscribe', 'false') == 'false':
        return True
    user_id = update.effective_user.id
    required_channels = db.get_all_required_channels()
    if not required_channels:
        return True
    is_member_of_all = True
    for channel in required_channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel['channel_id'], user_id=user_id)
            if member.status not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
                is_member_of_all = False
                break
        except TelegramError as e:
            logger.error(f"Error checking membership for channel {channel['channel_id']}: {e}")
            is_member_of_all = False
            break
    if not is_member_of_all:
        target = update.callback_query.message if update.callback_query else update.message
        await target.reply_text(
            db.get_text('force_subscribe_message'),
            reply_markup=kb.join_channel_keyboard()
        )
    return is_member_of_all

def format_experience(exp: Experience, md_version: int = 2) -> str:
    def def_md(text):
        return escape_markdown(str(text), version=md_version)

    def remove_emojis(text):
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F700-\U0001F77F"
            "\U0001F780-\U0001F7FF"
            "\U0001F800-\U0001F8FF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F"
            "\U0001FA70-\U0001FAFF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251" 
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text).strip()

    def make_safe_tag(name: str) -> str:
        text_no_emoji = remove_emojis(name)
        return re.sub(r'[\s\-_]+', '_', text_no_emoji)

    field_name = def_md(exp.field.name)
    major_name = def_md(exp.major.name)
    professor_name = def_md(exp.professor.name)
    course_name = def_md(exp.course.name)
    teaching_style = def_md(exp.teaching_style)
    notes = def_md(exp.notes)
    project = def_md(exp.project)
    attendance_details = def_md(exp.attendance_details)
    exam = def_md(exp.exam)
    conclusion = def_md(exp.conclusion)

    tags = (f"\\#{make_safe_tag(exp.field.name)} \\#{make_safe_tag(exp.major.name)} "
            f"\\#{make_safe_tag(exp.professor.name)} \\#{make_safe_tag(exp.course.name)}")
            
    attendance_status = db.get_text('exp_format_attendance_yes') if exp.attendance_required else db.get_text('exp_format_attendance_no')
    
    return (f"*{db.get_text('exp_format_field')}*: {field_name} \\({major_name}\\)\n\n"
            f"*{db.get_text('exp_format_professor')}*: {professor_name}\n\n"
            f"*{db.get_text('exp_format_course')}*: {course_name}\n\n"
            f"*{db.get_text('exp_format_teaching')}*: {teaching_style}\n\n"
            f"*{db.get_text('exp_format_notes')}*: {notes}\n\n"
            f"*{db.get_text('exp_format_project')}*: {project}\n\n"
            f"*{db.get_text('exp_format_attendance')}*: {attendance_status} \\- {attendance_details}\n\n"
            f"*{db.get_text('exp_format_exam')}*: {exam}\n\n"
            f"*{db.get_text('exp_format_conclusion')}*: {conclusion}\n\n"
            f"{def_md(db.get_text('exp_format_footer'))}\n\n"
            f"*{db.get_text('exp_format_tags')}*: {tags}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.add_user(update.effective_user.id, update.effective_user.first_name)
    if await check_channel_membership(update, context):
        await update.message.reply_text(db.get_text('welcome'), reply_markup=kb.main_menu())

async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(db.get_text('welcome'), reply_markup=kb.main_menu())

async def membership_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await check_channel_membership(update, context):
        await query.message.delete()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=db.get_text('welcome'),
            reply_markup=kb.main_menu()
        )

async def my_experiences_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_channel_membership(update, context):
        return

    user_id = update.effective_user.id
    experiences, total_pages = db.get_user_experiences(user_id, page=1)

    if not experiences:
        await update.message.reply_text(db.get_text('my_experiences_empty'))
        return
    
    keyboard = kb.my_experiences_keyboard(experiences, 1, total_pages)
    await update.message.reply_text(db.get_text('my_experiences_header'), reply_markup=keyboard)

async def my_experiences_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    page = int(query.data.split('_')[-1])
    user_id = update.effective_user.id
    
    experiences, total_pages = db.get_user_experiences(user_id, page=page)
    
    if not experiences:
        await query.edit_message_text(db.get_text('my_experiences_empty'))
        return

    keyboard = kb.my_experiences_keyboard(experiences, page, total_pages)
    await query.edit_message_text(db.get_text('my_experiences_header'), reply_markup=keyboard)

async def experience_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    exp_id = int(parts[-1])
    page = int(parts[-2])

    with db.session_scope() as s:
        exp = db.get_experience_with_session(s, exp_id)

        if not exp:
            await query.edit_message_text("متاسفانه این تجربه پیدا نشد.")
            return
            
        keyboard = kb.experience_detail_keyboard(exp_id, page)
        await query.edit_message_text(
            format_experience(exp, md_version=2),
            parse_mode=constants.ParseMode.MARKDOWN_V2,
            reply_markup=keyboard
        )

async def edit_experience_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    exp_id = int(parts[-2])
    page = int(parts[-1])
    
    with db.session_scope() as s:
        exp = db.get_experience_with_session(s, exp_id)
        if not exp:
            await query.edit_message_text("این تجربه پیدا نشد.")
            return

        if exp.status in [ExperienceStatus.REJECTED, ExperienceStatus.APPROVED]:
            exp.status = ExperienceStatus.PENDING
            
            admins = s.query(Admin).all()
            user = s.query(User).filter_by(user_id=exp.user_id).first()
            
            notification_text = f"*تجربه برای بررسی مجدد ارسال شد*\n\n" + escape_markdown(db.get_text('admin_new_experience_notification', exp_id=exp.id), version=2)
            admin_message_text = notification_text + format_experience(exp)
            
            first_admin_message = None
            for admin in admins:
                try:
                    msg = await context.bot.send_message(
                        chat_id=admin.user_id, 
                        text=admin_message_text,
                        reply_markup=kb.admin_approval_keyboard(exp.id, user),
                        parse_mode=constants.ParseMode.MARKDOWN_V2
                    )
                    if not first_admin_message:
                        first_admin_message = msg
                except Exception as e:
                    logger.error(f"Failed to resend notification to admin {admin.user_id}: {e}")
            
            if first_admin_message:
                exp.admin_message_id = first_admin_message.message_id
                exp.admin_chat_id = first_admin_message.chat_id

            await query.edit_message_text("✅ تجربه شما با موفقیت برای بازبینی مجدد به ادمین‌ها ارسال شد.", reply_markup=kb.experience_detail_keyboard(exp_id, page))

        elif exp.status == ExperienceStatus.PENDING:
            text_part1 = "⚠️ **آیا از ویرایش این تجربه مطمئن هستید؟**\n\n"
            text_part2 = "تجربه فعلی شما حذف و فرآیند ثبت مجدد از ابتدا آغاز خواهد شد."
            final_text = text_part1 + escape_markdown(text_part2, version=2)
            await query.edit_message_text(
                text=final_text,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                reply_markup=kb.confirm_edit_keyboard(exp_id, page)
            )

async def edit_experience_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_')
    exp_id = int(parts[-2])
    
    db.delete_item(Experience, exp_id)
    
    await query.edit_message_text("تجربه قبلی حذف شد. لطفاً اطلاعات جدید را وارد کنید.")
    
    return await submission_start(query, context)

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_channel_membership(update, context): return
    await update.message.reply_text(db.get_text('rules'), parse_mode=constants.ParseMode.MARKDOWN_V2)

async def submission_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    if not await check_channel_membership(update, context): return ConversationHandler.END
    context.user_data['experience'] = {}
    fields, _ = db.get_paginated_list(Field, per_page=100)
    
    target = update.message or update.callback_query.message
    
    await target.reply_text(
        db.get_text('submission_start'),
        reply_markup=kb.dynamic_list_keyboard(fields, 'field')
    )
    return States.SELECTING_FIELD

async def select_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    field_id = int(query.data.split('_')[-1])
    context.user_data['experience']['field_id'] = field_id
    majors = db.get_all_items_by_parent(Major, 'field_id', field_id)
    await query.edit_message_text(db.get_text('choose_major'), reply_markup=kb.dynamic_list_keyboard(majors, 'major'))
    return States.SELECTING_MAJOR

async def select_major(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    major_id = int(query.data.split('_')[-1])
    context.user_data['experience']['major_id'] = major_id
    courses = db.get_all_items_by_parent(Course, 'major_id', major_id)
    await query.edit_message_text(db.get_text('choose_course'), reply_markup=kb.dynamic_list_keyboard(courses, 'course'))
    return States.SELECTING_COURSE

async def select_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    context.user_data['experience']['course_id'] = int(query.data.split('_')[-1])
    professors, _ = db.get_paginated_list(Professor, per_page=100)
    await query.edit_message_text(db.get_text('choose_professor'), reply_markup=kb.dynamic_list_keyboard(professors, 'professor', has_add_new=True))
    return States.SELECTING_PROFESSOR

async def select_professor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    professor_id = int(query.data.split('_')[-1])
    context.user_data['experience']['professor_id'] = professor_id
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
        await update.message.reply_text("نام استاد نامعتبر است. لطفا دوباره تلاش کنید:")
        return States.ADDING_PROFESSOR
    new_prof_obj = db.add_item(Professor, name=prof_name)
    context.user_data['experience']['professor_id'] = new_prof_obj.id
    await update.message.reply_text(db.get_text('ask_teaching_style'))
    return States.GETTING_TEACHING

async def get_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE, field_name: str, next_state: States, prompt_key: str, reply_markup=None) -> States:
    user_input = update.message.text
    if len(user_input) > 1000:
        await update.message.reply_text("متن شما بیش از حد طولانی است. لطفا دوباره تلاش کنید:")
        return context.current_state
    context.user_data['experience'][field_name] = user_input
    await update.message.reply_text(db.get_text(prompt_key), reply_markup=reply_markup)
    return next_state

async def get_teaching(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    return await get_text_input(update, context, 'teaching_style', States.GETTING_NOTES, 'ask_notes')

async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    return await get_text_input(update, context, 'notes', States.GETTING_PROJECT, 'ask_project')

async def get_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    return await get_text_input(update, context, 'project', States.GETTING_ATTENDANCE_CHOICE, 'ask_attendance_choice', kb.attendance_keyboard())

async def get_attendance_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    context.user_data['experience']['attendance_required'] = (query.data == 'attendance_yes')
    await query.edit_message_text(db.get_text('ask_attendance_details'))
    return States.GETTING_ATTENDANCE_DETAILS

async def get_attendance_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    return await get_text_input(update, context, 'attendance_details', States.GETTING_EXAM, 'ask_exam')

async def get_exam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    return await get_text_input(update, context, 'exam', States.GETTING_CONCLUSION, 'ask_conclusion')

async def get_conclusion_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text
    if len(user_input) > 1000:
        await update.message.reply_text("متن شما بیش از حد طولانی است. لطفا دوباره تلاش کنید:")
        return States.GETTING_CONCLUSION
    
    context.user_data['experience']['conclusion'] = user_input
    exp_data = context.user_data['experience']
    user = update.effective_user
    exp_data['user_id'] = user.id

    with db.session_scope() as s:
        new_exp_obj = Experience(**exp_data)
        s.add(new_exp_obj)
        s.flush()  
        s.refresh(new_exp_obj, attribute_names=['field', 'major', 'professor', 'course'])
        
        notification_text = escape_markdown(db.get_text('admin_new_experience_notification', exp_id=new_exp_obj.id), version=2)
        admin_message_text = notification_text + format_experience(new_exp_obj)
        
        first_admin_message = None
        admins = s.query(Admin).all()
        for admin in admins: 
            try:
                msg = await context.bot.send_message(
                    chat_id=admin.user_id, text=admin_message_text,
                    reply_markup=kb.admin_approval_keyboard(new_exp_obj.id, user),
                    parse_mode=constants.ParseMode.MARKDOWN_V2
                )
                if not first_admin_message:
                    first_admin_message = msg
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin.user_id}: {e}")

        if first_admin_message:
            new_exp_obj.admin_message_id = first_admin_message.message_id
            new_exp_obj.admin_chat_id = first_admin_message.chat_id

    await update.message.reply_text(db.get_text('submission_success'), reply_markup=kb.main_menu())
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(db.get_text('operation_cancelled'))
    else:
        await update.message.reply_text(db.get_text('operation_cancelled'))
    context.user_data.clear()
    return ConversationHandler.END

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_admin(update, context):
        await update.message.reply_text(db.get_text('admin_panel_welcome'), reply_markup=kb.admin_panel_main())

async def admin_panel_callback_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Since the main panel is now a reply keyboard, this just sends a text confirmation
    # and ensures the reply keyboard is visible.
    await query.message.reply_text(
        db.get_text('admin_panel_welcome'), 
        reply_markup=kb.admin_panel_main()
    )
    # We can also delete the inline message if we want a cleaner interface
    await query.message.delete()


async def show_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    stats = db.get_statistics()
    await update.message.reply_text(
        db.get_text('stats_message', **stats),
        parse_mode=constants.ParseMode.MARKDOWN_V2,
        reply_markup=kb.admin_panel_main()
    )

async def admin_list_items_command(update: Update, context: ContextTypes.DEFAULT_TYPE, prefix: str):
    if not await check_admin(update, context): return
    
    page = 1
    
    if prefix == 'texts':
        items, total_pages = db.get_paginated_list(BotText, page=page)
        keyboard = kb.admin_manage_texts_list(items, page, total_pages)
        header_key = 'admin_manage_texts_header'
    else:
        model = MODEL_MAP.get(prefix)
        if not model: return
        items, total_pages = db.get_paginated_list(model, page=page)
        keyboard = kb.admin_manage_item_list(items, prefix, page, total_pages)
        header_key = f'admin_manage_{prefix}_header'

    await update.message.reply_text(db.get_text(header_key), reply_markup=keyboard)


# START OF CHANGE - توابع جدید برای مدیریت نظرات
async def manage_experiences_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    await update.message.reply_text(
        db.get_text('admin_experiences_menu_header'),
        reply_markup=kb.admin_experience_menu()
    )

async def admin_pending_reviews_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()

    page = int(query.data.split('_')[-1])
    
    experiences, total_pages = db.get_experiences_by_status(ExperienceStatus.PENDING, page=page)
    
    if not experiences:
        await query.edit_message_text(
            db.get_text('admin_no_pending_experiences'),
            reply_markup=kb.admin_experience_menu()
        )
        return

    keyboard = kb.admin_pending_experiences_keyboard(experiences, page, total_pages)
    await query.edit_message_text(db.get_text('admin_pending_header'), reply_markup=keyboard)

async def admin_pending_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_')
    exp_id = int(parts[-1])
    page = int(parts[-2])

    with db.session_scope() as s:
        exp = db.get_experience_with_session(s, exp_id)
        if not exp:
            await query.edit_message_text("متاسفانه این تجربه پیدا نشد.")
            return
        
        user = s.query(User).filter_by(user_id=exp.user_id).first()
        if not user: # Fallback if user is not in users table
            user = update.effective_user 

        await query.edit_message_text(
            format_experience(exp, md_version=2),
            parse_mode=constants.ParseMode.MARKDOWN_V2,
            reply_markup=kb.admin_approval_keyboard(exp.id, user, from_list_page=page)
        )
# END OF CHANGE


async def experience_approval_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    action, exp_id_str = data[1], data[2]
    exp_id = int(exp_id_str)
    
    with db.session_scope() as s:
        exp = db.get_experience_with_session(s, exp_id)
        if not exp:
            await query.edit_message_text("این تجربه دیگر وجود ندارد.")
            return

        if action == "approve":
            exp.status = ExperienceStatus.APPROVED
            await context.bot.send_message(
                chat_id=config.CHANNEL_ID, text=format_experience(exp), parse_mode=constants.ParseMode.MARKDOWN_V2
            )
            await query.edit_message_text(db.get_text('admin_approval_success', exp_id=exp_id))
            try:
                await context.bot.send_message(
                    chat_id=exp.user_id, text=db.get_text('user_approval_notification', course_name=exp.course.name)
                )
            except Exception as e:
                logger.warning(f"Could not notify user {exp.user_id} about approval: {e}")

        elif action == "reject":
            await query.edit_message_text(
                db.get_text('rejection_reason_prompt'), reply_markup=kb.rejection_reasons_keyboard(exp_id)
            )

        elif action == "reason":
            reason_key = f'btn_reject_reason_{data[3]}'
            reason_text = db.get_text(reason_key)
            exp.status = ExperienceStatus.REJECTED
            await query.edit_message_text(db.get_text('admin_rejection_success', exp_id=exp_id, reason=reason_text))
            try:
                await context.bot.send_message(
                    chat_id=exp.user_id,
                    text=db.get_text('user_rejection_notification', course_name=exp.course.name, reason=reason_text)
                )
            except Exception as e:
                logger.warning(f"Could not notify user {exp.user_id} about rejection: {e}")

async def broadcast_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    if not await check_admin(update, context): return ConversationHandler.END
    await update.message.reply_text(db.get_text('broadcast_prompt'))
    return States.GETTING_BROADCAST_MESSAGE

async def broadcast_receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    users = db.get_all_users()
    sent_count, failed_count = 0, 0
    await update.message.reply_text(f"در حال ارسال پیام به {len(users)} کاربر...")
    for user in users:
        try:
            await context.bot.copy_message(
                chat_id=user.user_id, from_chat_id=update.message.chat_id, message_id=update.message.message_id
            )
            sent_count += 1
        except Exception:
            failed_count += 1
    await update.message.reply_text(f"پیام به {sent_count} کاربر ارسال شد. {failed_count} ناموفق بود.")
    return ConversationHandler.END

async def single_message_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    if not await check_admin(update, context): return ConversationHandler.END
    await update.message.reply_text(db.get_text('single_message_user_prompt'))
    return States.GETTING_SINGLE_USER_ID

async def single_message_get_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    context.user_data['target_user'] = update.message.text
    await update.message.reply_text(db.get_text('single_message_prompt', target_user=update.message.text))
    return States.GETTING_SINGLE_MESSAGE

async def single_message_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_user = context.user_data.pop('target_user')
    try:
        await context.bot.copy_message(
            chat_id=target_user, from_chat_id=update.message.chat_id, message_id=update.message.message_id
        )
        await update.message.reply_text(db.get_text('single_message_success', target_user=target_user))
    except Exception as e:
        await update.message.reply_text(db.get_text('single_message_fail', target_user=target_user, error=e))
    return ConversationHandler.END

async def admin_manage_channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    await update.message.reply_text("مدیریت کانال‌ها:", reply_markup=kb.admin_manage_channels_keyboard())

async def admin_toggle_force_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    current_status = db.get_setting('force_subscribe', 'false')
    new_status = 'true' if current_status == 'false' else 'false'
    db.set_setting('force_subscribe', new_status)
    await query.edit_message_text("مدیریت کانال‌ها:", reply_markup=kb.admin_manage_channels_keyboard())

async def admin_add_channel_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    if not await check_admin(update, context): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("آیدی عددی یا یوزرنیم کانال را وارد کنید:")
    return States.GETTING_CHANNEL_ID_TO_ADD

async def admin_add_channel_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    context.user_data['new_channel_id'] = update.message.text.strip()
    await update.message.reply_text("لینک عضویت کانال را وارد کنید:")
    return States.GETTING_CHANNEL_LINK_TO_ADD

async def admin_add_channel_get_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    channel_id = context.user_data.pop('new_channel_id')
    channel_link = update.message.text.strip()
    try:
        db.add_item(RequiredChannel, channel_id=channel_id, channel_link=channel_link)
        await update.message.reply_text("کانال اضافه شد.")
    except Exception as e:
        await update.message.reply_text(f"خطا: {e}")
    await update.message.reply_text("مدیریت کانال‌ها:", reply_markup=kb.admin_manage_channels_keyboard())
    return ConversationHandler.END

async def admin_delete_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    channel_db_id = int(query.data.split('_')[-1])
    db.delete_item(RequiredChannel, channel_db_id)
    await query.answer("کانال حذف شد.")
    await query.edit_message_text("مدیریت کانال‌ها:", reply_markup=kb.admin_manage_channels_keyboard())

async def admin_list_items_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    prefix, page = parts[2], int(parts[3])
    if prefix == 'texts':
        items, total_pages = db.get_paginated_list(BotText, page=page)
        keyboard = kb.admin_manage_texts_list(items, page, total_pages)
        header_key = 'admin_manage_texts_header'
    else:
        model = MODEL_MAP.get(prefix)
        if not model: return
        items, total_pages = db.get_paginated_list(model, page=page)
        keyboard = kb.admin_manage_item_list(items, prefix, page, total_pages)
        header_key = f'admin_manage_{prefix}_header'
    await query.edit_message_text(db.get_text(header_key), reply_markup=keyboard)

async def item_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    prefix, item_id, page = parts[0], int(parts[2]), int(parts[3])
    model = MODEL_MAP[prefix]
    item_name = db.get_item_name(model, item_id)
    await query.edit_message_text(
        db.get_text('confirm_delete', item_name=item_name),
        reply_markup=kb.confirm_delete_keyboard(prefix, item_id, page)
    )

async def item_confirm_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    prefix, item_id, page = parts[0], int(parts[2]), int(parts[3])
    db.delete_item(MODEL_MAP[prefix], item_id)
    await query.edit_message_text(db.get_text('item_deleted_successfully'), reply_markup=kb.back_to_list_keyboard(prefix, page))

async def item_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    if not await check_admin(update, context): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    prefix, page = parts[0], int(parts[2])
    context.user_data.update({'prefix': prefix, 'page': page})
    if prefix in ['major', 'course']:
        parent_model = Field if prefix == 'major' else Major
        parents, _ = db.get_paginated_list(parent_model, per_page=100)
        await query.edit_message_text(db.get_text('select_parent_field'), reply_markup=kb.parent_field_selection_keyboard(parents, prefix, page))
        return States.SELECTING_PARENT_FIELD
    elif prefix == 'admin':
        await query.edit_message_text("آیدی عددی ادمین جدید را وارد کنید:")
        return States.GETTING_ADMIN_ID
    else:
        await query.edit_message_text(db.get_text('ask_for_new_item_name'))
        return States.GETTING_NEW_NAME

async def item_add_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prefix, page, parent_id = context.user_data['prefix'], context.user_data['page'], context.user_data.get('parent_id')
    model = MODEL_MAP[prefix]
    kwargs = {'name': update.message.text.strip()}
    if parent_id:
        kwargs['field_id' if prefix == 'major' else 'major_id'] = parent_id
    db.add_item(model, **kwargs)
    await update.message.reply_text(db.get_text('item_added_successfully'), reply_markup=kb.back_to_list_keyboard(prefix, page))
    context.user_data.clear()
    return ConversationHandler.END

async def item_add_select_parent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    context.user_data['parent_id'] = int(query.data.split('_')[2])
    await query.edit_message_text(db.get_text('ask_for_new_item_name'))
    return States.GETTING_NEW_NAME

async def admin_add_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    page = context.user_data.get('page', 1)
    try:
        db.add_item(Admin, user_id=int(update.message.text))
        await update.message.reply_text("ادمین اضافه شد.", reply_markup=kb.back_to_list_keyboard('admin', page))
    except Exception as e:
        await update.message.reply_text(f"خطا: {e}", reply_markup=kb.back_to_list_keyboard('admin', page))
    context.user_data.clear()
    return ConversationHandler.END

async def item_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    if not await check_admin(update, context): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    prefix, item_id, page = parts[0], int(parts[2]), int(parts[3])
    context.user_data.update({'prefix': prefix, 'item_id': item_id, 'page': page})
    item_name = db.get_item_name(MODEL_MAP[prefix], item_id)
    await query.edit_message_text(db.get_text('ask_for_update_item_name', current_name=item_name))
    return States.GETTING_UPDATED_NAME

async def item_edit_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prefix, item_id, page = context.user_data['prefix'], context.user_data['item_id'], context.user_data['page']
    db.update_item(MODEL_MAP[prefix], item_id, name=update.message.text.strip())
    await update.message.reply_text(db.get_text('item_updated_successfully'), reply_markup=kb.back_to_list_keyboard(prefix, page))
    context.user_data.clear()
    return ConversationHandler.END

async def text_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    if not await check_admin(update, context): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    key, page = "_".join(parts[2:-1]), int(parts[-1])
    context.user_data.update({'item_key': key, 'page': page})
    await query.edit_message_text(db.get_text('ask_for_update_text_value', key=key))
    return States.GETTING_UPDATED_TEXT

async def text_edit_receive_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    key, page = context.user_data['item_key'], context.user_data['page']
    with db.session_scope() as s:
        text_item = s.query(BotText).filter_by(key=key).first()
        if text_item:
            text_item.value = update.message.text
    await update.message.reply_text(db.get_text('item_updated_successfully'), reply_markup=kb.back_to_list_keyboard('texts', page))
    context.user_data.clear()
    return ConversationHandler.END

ptb_app = Application.builder().token(config.BOT_TOKEN).build()

conv_defaults = {'per_message': False}
submission_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex('^' + db.get_text(SUBMIT_EXP_BTN_KEY) + '$'), submission_start),
        CallbackQueryHandler(edit_experience_confirm_callback, pattern=r"^confirm_edit_")
    ],
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
    fallbacks=[CallbackQueryHandler(cancel_submission, pattern=CANCEL_SUBMISSION)],
    **conv_defaults
)
broadcast_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^' + db.get_text('btn_admin_broadcast') + '$'), broadcast_start_callback)],
    states={States.GETTING_BROADCAST_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_receive_message)]},
    fallbacks=[CommandHandler('admin', admin_command)], **conv_defaults
)
single_message_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^' + db.get_text('btn_admin_single_message') + '$'), single_message_start_callback)],
    states={
        States.GETTING_SINGLE_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, single_message_get_user)],
        States.GETTING_SINGLE_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, single_message_send)]
    },
    fallbacks=[CommandHandler('admin', admin_command)], **conv_defaults
)
add_channel_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_add_channel_start_callback, pattern=ADMIN_ADD_CHANNEL)],
    states={
        States.GETTING_CHANNEL_ID_TO_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_channel_get_id)],
        States.GETTING_CHANNEL_LINK_TO_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_channel_get_link)]
    },
    fallbacks=[CallbackQueryHandler(admin_manage_channels_command, pattern=ADMIN_MANAGE_CHANNELS)], **conv_defaults
)
item_add_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(item_add_start, pattern=ITEM_ADD), CallbackQueryHandler(item_add_start, pattern=ADMIN_ADD)],
    states={
        States.GETTING_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_add_receive_name)],
        States.GETTING_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_get_id)],
        States.SELECTING_PARENT_FIELD: [CallbackQueryHandler(item_add_select_parent, pattern=COMPLEX_ITEM_SELECT_PARENT)]
    },
    fallbacks=[CallbackQueryHandler(cancel_submission, pattern=CANCEL_SUBMISSION)], **conv_defaults
)
item_edit_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(item_edit_start, pattern=ITEM_EDIT)],
    states={States.GETTING_UPDATED_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_edit_receive_name)]},
    fallbacks=[CallbackQueryHandler(cancel_submission, pattern=CANCEL_SUBMISSION)], **conv_defaults
)
text_edit_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(text_edit_start, pattern=TEXT_EDIT)],
    states={States.GETTING_UPDATED_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_edit_receive_value)]},
    fallbacks=[CallbackQueryHandler(cancel_submission, pattern=CANCEL_SUBMISSION)], **conv_defaults
)

ptb_app.add_handler(CommandHandler("start", start_command))
ptb_app.add_handler(CommandHandler("admin", admin_command))
ptb_app.add_handler(MessageHandler(filters.Regex('^' + db.get_text(MY_EXPS_BTN_KEY) + '$'), my_experiences_command))
ptb_app.add_handler(MessageHandler(filters.Regex('^' + db.get_text(RULES_BTN_KEY) + '$'), rules_command))
ptb_app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_main_menu') + '$'), back_to_main_menu))

# Admin panel command handlers (ReplyKeyboard)
ptb_app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_admin_stats') + '$'), show_stats_command))
ptb_app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_admin_manage_channels') + '$'), admin_manage_channels_command))
ptb_app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_admin_manage_experiences') + '$'), manage_experiences_command))
ptb_app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_admin_manage_fields') + '$'), lambda u, c: admin_list_items_command(u, c, 'field')))
ptb_app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_admin_manage_majors') + '$'), lambda u, c: admin_list_items_command(u, c, 'major')))
ptb_app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_admin_manage_professors') + '$'), lambda u, c: admin_list_items_command(u, c, 'professor')))
ptb_app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_admin_manage_courses') + '$'), lambda u, c: admin_list_items_command(u, c, 'course')))
ptb_app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_admin_manage_texts') + '$'), lambda u, c: admin_list_items_command(u, c, 'texts')))
ptb_app.add_handler(MessageHandler(filters.Regex('^' + db.get_text('btn_admin_manage_admins') + '$'), lambda u, c: admin_list_items_command(u, c, 'admin')))

ptb_app.add_handler(CallbackQueryHandler(membership_check_callback, pattern=CHECK_MEMBERSHIP))
ptb_app.add_handler(submission_handler)
ptb_app.add_handler(broadcast_handler)
ptb_app.add_handler(single_message_handler)
ptb_app.add_handler(add_channel_handler)
ptb_app.add_handler(item_add_handler)
ptb_app.add_handler(item_edit_handler)
ptb_app.add_handler(text_edit_handler)

ptb_app.add_handler(CallbackQueryHandler(admin_panel_callback_inline, pattern="^admin_main_panel_inline$"))
ptb_app.add_handler(CallbackQueryHandler(experience_approval_handler, pattern=EXPERIENCE_APPROVAL))
ptb_app.add_handler(CallbackQueryHandler(admin_toggle_force_sub_callback, pattern=ADMIN_TOGGLE_FORCE_SUB))
ptb_app.add_handler(CallbackQueryHandler(admin_delete_channel_callback, pattern=ADMIN_DELETE_CHANNEL))
ptb_app.add_handler(CallbackQueryHandler(admin_list_items_callback, pattern=ADMIN_LIST_ITEMS))
ptb_app.add_handler(CallbackQueryHandler(admin_list_items_callback, pattern=ADMIN_LIST_TEXTS))
ptb_app.add_handler(CallbackQueryHandler(item_delete_callback, pattern=ITEM_DELETE))
ptb_app.add_handler(CallbackQueryHandler(item_confirm_delete_callback, pattern=ITEM_CONFIRM_DELETE))
ptb_app.add_handler(CallbackQueryHandler(my_experiences_page_callback, pattern=r"^my_exps_"))
ptb_app.add_handler(CallbackQueryHandler(experience_detail_callback, pattern=r"^exp_detail_"))
ptb_app.add_handler(CallbackQueryHandler(edit_experience_callback, pattern=r"^edit_exp_"))

# START OF CHANGE - هندلرهای جدید برای مدیریت نظرات
ptb_app.add_handler(CallbackQueryHandler(manage_experiences_command, pattern=ADMIN_MANAGE_EXPERIENCES))
ptb_app.add_handler(CallbackQueryHandler(admin_pending_reviews_callback, pattern=ADMIN_LIST_PENDING_EXPERIENCES))
ptb_app.add_handler(CallbackQueryHandler(admin_pending_detail_callback, pattern=ADMIN_PENDING_EXPERIENCE_DETAIL))
# END OF CHANGE

async def on_startup(application: Application):
    application.job_queue.run_repeating(backup_database, interval=1800, first=15)
    webhook_url = f"https://{config.DOMAIN_NAME}/{config.BOT_TOKEN}"
    logger.info(f"The bot is running and listening for webhooks at: {webhook_url}")

async def on_shutdown(application: Application):
    logger.info("Bot is shutting down...")

ptb_app.post_init = on_startup
ptb_app.post_shutdown = on_shutdown

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application starting...")
    await ptb_app.initialize()
    await ptb_app.start()
    yield
    print("Application shutting down...")
    await ptb_app.updater.stop()
    await ptb_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post(f"/{config.BOT_TOKEN}")
async def webhook_handler(request: Request):
    update_data = await request.json()
    update = Update.de_json(update_data, ptb_app.bot)
    asyncio.create_task(ptb_app.process_update(update))
    return Response(content="OK", status_code=200)

if __name__ == "__main__":
    asyncio.run(ptb_app.run_polling())