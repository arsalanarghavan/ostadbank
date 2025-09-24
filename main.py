# main.py

import logging
import asyncio
import datetime
import os
from telegram import Update, constants, ChatMember
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.helpers import escape_markdown
from telegram.error import TelegramError

import config
import database as db
import keyboards as kb
from models import (Field, Major, Professor, Course, Experience, BotText, Admin,
                    ExperienceStatus, RequiredChannel, Setting)
from constants import (
    States,
    FIELD_SELECT, MAJOR_SELECT, COURSE_SELECT, PROFESSOR_SELECT, PROFESSOR_ADD_NEW,
    ATTENDANCE_CHOICE, CANCEL_SUBMISSION, ADMIN_MAIN_PANEL, ADMIN_LIST_ITEMS,
    ADMIN_LIST_TEXTS, ITEM_ADD, ADMIN_ADD, ITEM_EDIT, TEXT_EDIT, ITEM_DELETE,
    ITEM_CONFIRM_DELETE, COMPLEX_ITEM_SELECT_PARENT, EXPERIENCE_APPROVAL,
    SUBMIT_EXP_BTN_KEY, MY_EXPS_BTN_KEY, RULES_BTN_KEY, CHECK_MEMBERSHIP,
    ADMIN_MANAGE_CHANNELS, ADMIN_ADD_CHANNEL, ADMIN_DELETE_CHANNEL, ADMIN_TOGGLE_FORCE_SUB
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- مدل‌ها و پیشوندها ---
MODEL_MAP = {
    'field': Field, 'major': Major, 'professor': Professor,
    'course': Course, 'admin': Admin, 'text': BotText
}
PREFIX_MAP = {
    'field': 'رشته', 'major': 'گرایش', 'professor': 'استاد',
    'course': 'درس', 'admin': 'ادمین', 'text': 'متن'
}

# --- توابع اصلی برنامه ---

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
            member = await context.bot.get_chat_member(chat_id=channel.channel_id, user_id=user_id)
            if member.status not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
                is_member_of_all = False
                break
        except TelegramError as e:
            logger.error(f"Error checking membership for channel {channel.channel_id}: {e}")
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
    tags = f"#{exp.field.name.replace(' ', '_')} #{exp.major.name.replace(' ', '_')} #{exp.professor.name.replace(' ', '_')} #{exp.course.name.replace(' ', '_')}"
    attendance_text = db.get_text('exp_format_attendance_yes') if exp.attendance_required else db.get_text('exp_format_attendance_no')
    return (f"{db.get_text('exp_format_field')}: {def_md(exp.field.name)} ({def_md(exp.major.name)})\n"
            f"{db.get_text('exp_format_professor')}: {def_md(exp.professor.name)}\n"
            f"{db.get_text('exp_format_course')}: {def_md(exp.course.name)}\n"
            f"{db.get_text('exp_format_teaching')}:\n{def_md(exp.teaching_style)}\n"
            f"{db.get_text('exp_format_notes')}:\n{def_md(exp.notes)}\n"
            f"{db.get_text('exp_format_project')}:\n{def_md(exp.project)}\n"
            f"{db.get_text('exp_format_attendance')}: {attendance_text}\n{def_md(exp.attendance_details)}\n"
            f"{db.get_text('exp_format_exam')}:\n{def_md(exp.exam)}\n"
            f"{db.get_text('exp_format_conclusion')}:\n{def_md(exp.conclusion)}\n"
            f"{db.get_text('exp_format_footer')}\n{db.get_text('exp_format_tags')}: {def_md(tags)}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.add_user(update.effective_user.id, update.effective_user.first_name)
    if await check_channel_membership(update, context):
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
    if not await check_channel_membership(update, context): return
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
    if not await check_channel_membership(update, context): return
    await update.message.reply_text(db.get_text('rules'), parse_mode=constants.ParseMode.MARKDOWN_V2)

async def submission_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    if not await check_channel_membership(update, context): return ConversationHandler.END
    context.user_data['experience'] = {}
    fields, _ = db.get_all_items(Field, page=1, per_page=100)
    await update.message.reply_text(db.get_text('submission_start'), reply_markup=kb.dynamic_list_keyboard(fields, 'field'))
    return States.SELECTING_FIELD

async def select_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    field_id = int(query.data.split('_')[-1])
    context.user_data['experience']['field_id'] = field_id
    majors = db.get_majors_by_field(field_id)
    await query.edit_message_text(db.get_text('choose_major'), reply_markup=kb.dynamic_list_keyboard(majors, 'major'))
    return States.SELECTING_MAJOR

async def select_major(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    major_id = int(query.data.split('_')[-1])
    context.user_data['experience']['major_id'] = major_id
    courses = db.get_courses_by_major(major_id)
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
    new_prof_id = db.add_item(Professor, name=prof_name)
    context.user_data['experience']['professor_id'] = new_prof_id
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
    new_exp_id = db.add_item(Experience, **exp_data)
    exp = db.get_experience(new_exp_id)
    admin_message = db.get_text('admin_new_experience_notification', exp_id=exp.id) + format_experience(exp)
    for admin in db.get_all_admins():
        try:
            await context.bot.send_message(
                chat_id=admin.user_id, text=admin_message,
                reply_markup=kb.admin_approval_keyboard(exp.id, user),
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"Failed to send notification to admin {admin.user_id}: {e}")
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

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(db.get_text('admin_panel_welcome'), reply_markup=kb.admin_panel_main())

async def experience_approval_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    action, exp_id_str = data[1], data[2]
    exp_id = int(exp_id_str)
    exp = db.get_experience(exp_id)
    if not exp:
        await query.edit_message_text("این تجربه دیگر وجود ندارد.")
        return
    if action == "approve":
        db.update_experience_status(exp_id, ExperienceStatus.APPROVED)
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
        db.update_experience_status(exp_id, ExperienceStatus.REJECTED)
        await query.edit_message_text(db.get_text('admin_rejection_success', exp_id=exp_id, reason=reason_text))
        try:
            await context.bot.send_message(
                chat_id=exp.user_id,
                text=db.get_text('user_rejection_notification', course_name=exp.course.name, reason=reason_text)
            )
        except Exception as e:
            logger.warning(f"Could not notify user {exp.user_id} about rejection: {e}")

async def show_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    stats = db.get_statistics()
    await query.edit_message_text(
        db.get_text('stats_message', **stats),
        parse_mode=constants.ParseMode.MARKDOWN_V2,
        reply_markup=kb.back_to_list_keyboard("main_panel", is_main_panel=True)
    )

async def broadcast_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    if not await check_admin(update, context): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(db.get_text('broadcast_prompt'))
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
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(db.get_text('single_message_user_prompt'))
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

async def admin_manage_channels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("مدیریت کانال‌ها:", reply_markup=kb.admin_manage_channels_keyboard())

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
        items, total_pages = db.get_paginated_texts(page=page)
        keyboard = kb.admin_manage_texts_list(items, page, total_pages)
        header_key = 'admin_manage_texts_header'
    else:
        model = MODEL_MAP.get(prefix)
        if not model: return
        items, total_pages = db.get_all_items(model, page=page)
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
    item = db.get_item_by_id(model, item_id)
    item_name = item.name if hasattr(item, 'name') else f"ID: {item.user_id}"
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
        parents, _ = db.get_all_items(parent_model, per_page=100)
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
    item = db.get_item_by_id(MODEL_MAP[prefix], item_id)
    current_name = item.name if hasattr(item, 'name') else f"ID: {item.user_id}"
    await query.edit_message_text(db.get_text('ask_for_update_item_name', current_name=current_name))
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

# --- START: بخش نهایی و اصلاح‌شده برای اجرا ---

# ۱. ساخت هسته اصلی برنامه تلگرام
ptb_app = Application.builder().token(config.BOT_TOKEN).build()

# ۲. ثبت تمام کنترل‌کننده‌ها (Handlers)
conv_defaults = {'per_message': False}
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
    fallbacks=[CallbackQueryHandler(cancel_submission, pattern=CANCEL_SUBMISSION)],
    **conv_defaults
)
broadcast_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(broadcast_start_callback, pattern=r'^admin_broadcast$')],
    states={States.GETTING_BROADCAST_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_receive_message)]},
    fallbacks=[CallbackQueryHandler(admin_panel_callback, pattern=ADMIN_MAIN_PANEL)], **conv_defaults
)
single_message_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(single_message_start_callback, pattern=r'^admin_single_message$')],
    states={
        States.GETTING_SINGLE_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, single_message_get_user)],
        States.GETTING_SINGLE_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, single_message_send)]
    },
    fallbacks=[CallbackQueryHandler(admin_panel_callback, pattern=ADMIN_MAIN_PANEL)], **conv_defaults
)
add_channel_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_add_channel_start_callback, pattern=ADMIN_ADD_CHANNEL)],
    states={
        States.GETTING_CHANNEL_ID_TO_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_channel_get_id)],
        States.GETTING_CHANNEL_LINK_TO_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_channel_get_link)]
    },
    fallbacks=[CallbackQueryHandler(admin_manage_channels_callback, pattern=ADMIN_MANAGE_CHANNELS)], **conv_defaults
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
ptb_app.add_handler(CallbackQueryHandler(membership_check_callback, pattern=CHECK_MEMBERSHIP))
ptb_app.add_handler(submission_handler)
ptb_app.add_handler(broadcast_handler)
ptb_app.add_handler(single_message_handler)
ptb_app.add_handler(add_channel_handler)
ptb_app.add_handler(item_add_handler)
ptb_app.add_handler(item_edit_handler)
ptb_app.add_handler(text_edit_handler)
ptb_app.add_handler(CallbackQueryHandler(admin_panel_callback, pattern=ADMIN_MAIN_PANEL))
ptb_app.add_handler(CallbackQueryHandler(show_stats_callback, pattern=r'^admin_stats$'))
ptb_app.add_handler(CallbackQueryHandler(experience_approval_handler, pattern=EXPERIENCE_APPROVAL))
ptb_app.add_handler(CallbackQueryHandler(admin_manage_channels_callback, pattern=ADMIN_MANAGE_CHANNELS))
ptb_app.add_handler(CallbackQueryHandler(admin_toggle_force_sub_callback, pattern=ADMIN_TOGGLE_FORCE_SUB))
ptb_app.add_handler(CallbackQueryHandler(admin_delete_channel_callback, pattern=ADMIN_DELETE_CHANNEL))
ptb_app.add_handler(CallbackQueryHandler(admin_list_items_callback, pattern=ADMIN_LIST_ITEMS))
ptb_app.add_handler(CallbackQueryHandler(admin_list_items_callback, pattern=ADMIN_LIST_TEXTS))
ptb_app.add_handler(CallbackQueryHandler(item_delete_callback, pattern=ITEM_DELETE))
ptb_app.add_handler(CallbackQueryHandler(item_confirm_delete_callback, pattern=ITEM_CONFIRM_DELETE))

# ۳. تعریف توابع برای زمان شروع و پایان کار برنامه
async def on_startup(application: Application):
    """کارهایی که در زمان شروع به کار ربات باید انجام شود"""
    db.initialize_database()
    application.job_queue.run_repeating(backup_database, interval=1800, first=15)
    webhook_url = f"https://{config.DOMAIN_NAME}/{config.BOT_TOKEN}"
    await application.bot.set_webhook(
        url=webhook_url,
        allowed_updates=Update.ALL_TYPES
    )
    logger.info(f"Webhook has been set to: {webhook_url}")

async def on_shutdown(application: Application):
    """کارهایی که در زمان خاموش شدن ربات باید انجام شود"""
    logger.info("Bot is shutting down...")

# ۴. اتصال توابع شروع و پایان به برنامه
ptb_app.post_init = on_startup
ptb_app.post_shutdown = on_shutdown

# ۵. ساخت "سوئیچ استارت" نهایی برای Uvicorn
# این متغیر application همان چیزی است که Uvicorn اجرا خواهد کرد
application = ptb_app.asgi_app

# --- END: بخش نهایی ---