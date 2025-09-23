# main.py

import logging
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
from models import Field, Major, Professor, Course, Experience, BotText, Admin, ExperienceStatus, RequiredChannel, Setting
from constants import (
    States, MAX_MESSAGE_LENGTH,
    FIELD_SELECT, MAJOR_SELECT, COURSE_SELECT, PROFESSOR_SELECT, PROFESSOR_ADD_NEW,
    ATTENDANCE_CHOICE, CANCEL_SUBMISSION, ADMIN_MAIN_PANEL, ADMIN_LIST_ITEMS,
    ADMIN_LIST_TEXTS, ITEM_ADD, ADMIN_ADD, ITEM_EDIT, TEXT_EDIT, ITEM_DELETE,
    ITEM_CONFIRM_DELETE, COMPLEX_ITEM_SELECT_PARENT, EXPERIENCE_APPROVAL,
    SUBMIT_EXP_BTN_KEY, MY_EXPS_BTN_KEY, RULES_BTN_KEY, CHECK_MEMBERSHIP,
    ADMIN_MANAGE_CHANNELS, ADMIN_ADD_CHANNEL, ADMIN_DELETE_CHANNEL, ADMIN_TOGGLE_FORCE_SUB
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- مدل‌ها و پیشوندها برای مدیریت آیتم‌ها ---
MODEL_MAP = {
    'field': Field, 'major': Major, 'professor': Professor,
    'course': Course, 'admin': Admin, 'text': BotText
}
PREFIX_MAP = {
    'field': 'رشته', 'major': 'گرایش', 'professor': 'استاد',
    'course': 'درس', 'admin': 'ادمین', 'text': 'متن'
}

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

async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Checks if the user is a member of all required channels."""
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
            await context.bot.send_message(chat_id=config.OWNER_ID, text=f"Error checking channel membership for {channel.channel_id}. Is the bot an admin there?")
            break

    if not is_member_of_all:
        target = update.callback_query.message if update.callback_query else update.message
        await target.reply_text(
            db.get_text('force_subscribe_message'),
            reply_markup=kb.join_channel_keyboard()
        )
        return False
        
    return True

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

# --- User Commands & Main Menu ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.add_user(update.effective_user.id, update.effective_user.first_name)
    if not await check_channel_membership(update, context):
        return
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

# --- Full Submission Conversation ---
async def submission_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    if not await check_channel_membership(update, context): return ConversationHandler.END
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
    await update.message.reply_text(db.get_text('ask_teaching_style'))
    return States.GETTING_TEACHING

async def get_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE, next_state: States, prompt_key: str, reply_markup=None) -> States:
    user_input = update.message.text
    field_name = context.user_data.get('current_field', 'input')

    if len(user_input) > 1000:
        await update.message.reply_text(f"متن شما بیش از حد طولانی است (حداکثر ۱۰۰۰ کاراکتر). لطفا دوباره تلاش کنید:")
        return context.user_data.get('current_state', next_state)

    context.user_data['experience'][field_name] = user_input
    await update.message.reply_text(db.get_text(prompt_key), reply_markup=reply_markup)
    return next_state

async def get_teaching(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    context.user_data['current_field'] = 'teaching_style'
    return await get_text_input(update, context, States.GETTING_NOTES, 'ask_notes')

async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    context.user_data['current_field'] = 'notes'
    return await get_text_input(update, context, States.GETTING_PROJECT, 'ask_project')

async def get_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    context.user_data['current_field'] = 'project'
    return await get_text_input(update, context, States.GETTING_ATTENDANCE_CHOICE, 'ask_attendance_choice', kb.attendance_keyboard())

async def get_attendance_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    query = update.callback_query
    await query.answer()
    choice = query.data.split('_')[-1]
    context.user_data['experience']['attendance_required'] = (choice == 'yes')
    context.user_data['current_field'] = 'attendance_details'
    await query.edit_message_text(db.get_text('ask_attendance_details'))
    return States.GETTING_ATTENDANCE_DETAILS

async def get_attendance_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    context.user_data['current_field'] = 'attendance_details'
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
    
    user = update.effective_user
    exp_data['user_id'] = user.id
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    new_exp = db.add_item(Experience, **exp_data)
    exp = db.get_experience(new_exp.id)
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

# --- Admin Panel ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
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

# --- New Admin Features (Stats, Broadcast, etc.) ---
async def show_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    stats = db.get_statistics()
    await query.edit_message_text(
        db.get_text('stats_message', **stats),
        parse_mode=constants.ParseMode.MARKDOWN_V2,
        reply_markup=kb.back_to_list_keyboard("main_panel")
    )

async def broadcast_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    if not await check_admin(update, context): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(db.get_text('broadcast_prompt'))
    return States.GETTING_BROADCAST_MESSAGE

async def broadcast_receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    users = db.get_all_users()
    sent_count = 0
    failed_count = 0
    await update.message.reply_text(f"در حال ارسال پیام به {len(users)} کاربر...")
    for user in users:
        try:
            await context.bot.copy_message(
                chat_id=user.user_id,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
            sent_count += 1
        except Exception:
            failed_count += 1
    
    await update.message.reply_text(
        f"پیام همگانی با موفقیت به {sent_count} کاربر ارسال شد.\n"
        f"ارسال به {failed_count} کاربر ناموفق بود."
    )
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
            chat_id=target_user,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
        await update.message.reply_text(db.get_text('single_message_success', target_user=target_user))
    except Exception as e:
        await update.message.reply_text(db.get_text('single_message_fail', target_user=target_user, error=e))
    return ConversationHandler.END

# --- Channel Management ---
async def admin_manage_channels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("مدیریت کانال‌های عضویت اجباری:", reply_markup=kb.admin_manage_channels_keyboard())

async def admin_toggle_force_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    current_status = db.get_setting('force_subscribe', 'false')
    new_status = 'true' if current_status == 'false' else 'false'
    db.set_setting('force_subscribe', new_status)
    await query.edit_message_text("مدیریت کانال‌های عضویت اجباری:", reply_markup=kb.admin_manage_channels_keyboard())

async def admin_add_channel_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    if not await check_admin(update, context): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("لطفا آیدی عددی یا یوزرنیم (با @) کانال را وارد کنید:")
    return States.GETTING_CHANNEL_ID_TO_ADD

async def admin_add_channel_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    context.user_data['new_channel_id'] = update.message.text.strip()
    await update.message.reply_text("عالی. حالا لینک عضویت در کانال را وارد کنید (مثلا: https://t.me/yourchannel):")
    return States.GETTING_CHANNEL_LINK_TO_ADD

async def admin_add_channel_get_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    channel_id = context.user_data.pop('new_channel_id')
    channel_link = update.message.text.strip()
    
    try:
        db.add_item(RequiredChannel, channel_id=channel_id, channel_link=channel_link)
        await update.message.reply_text("کانال با موفقیت اضافه شد.")
    except Exception as e:
        await update.message.reply_text(f"خطا در افزودن کانال: {e}. (ممکن است کانال تکراری باشد)")
        
    await update.message.reply_text("مدیریت کانال‌های عضویت اجباری:", reply_markup=kb.admin_manage_channels_keyboard())
    return ConversationHandler.END
    
async def admin_delete_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    channel_db_id = int(query.data.split('_')[-1])
    db.delete_item(RequiredChannel, channel_db_id)
    await query.answer("کانال با موفقیت حذف شد.")
    await query.edit_message_text("مدیریت کانال‌های عضویت اجباری:", reply_markup=kb.admin_manage_channels_keyboard())

# --- Generic Admin CRUD Operations ---
async def admin_list_items_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    prefix = parts[2]
    page = int(parts[3])
    
    model = MODEL_MAP[prefix]
    
    if model == BotText:
        items, total_pages = db.get_paginated_texts(page=page)
        keyboard = kb.admin_manage_texts_list(items, page, total_pages)
    else:
        items, total_pages = db.get_all_items(model, page=page)
        keyboard = kb.admin_manage_item_list(items, prefix, page, total_pages)
        
    header_key = f'admin_manage_{prefix}_header'
    await query.edit_message_text(db.get_text(header_key, default=f"مدیریت {PREFIX_MAP[prefix]}"), reply_markup=keyboard)

async def item_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    prefix = parts[0]
    item_id = int(parts[2])
    page = int(parts[3])
    
    model = MODEL_MAP[prefix]
    item = db.get_item_by_id(model, item_id)
    
    item_name = item.name if hasattr(item, 'name') else f"ID: {item.user_id if hasattr(item, 'user_id') else item.id}"
    
    await query.edit_message_text(
        db.get_text('confirm_delete', item_name=item_name),
        reply_markup=kb.confirm_delete_keyboard(prefix, item_id, page)
    )

async def item_confirm_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_')
    prefix = parts[0]
    item_id = int(parts[2])
    page = int(parts[3])

    model = MODEL_MAP[prefix]
    db.delete_item(model, item_id)
    await query.answer(db.get_text('item_deleted_successfully'), show_alert=True)
    
    # Refresh list
    query.data = f"admin_list_{prefix}_{page}" # Simulate a click on the list button
    await admin_list_items_callback(update, context)


async def item_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    """Starts the process of adding a new item (Field, Major, etc.)."""
    if not await check_admin(update, context): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    prefix = parts[0]
    page = int(parts[1])
    
    context.user_data['prefix'] = prefix
    context.user_data['page'] = page
    
    if prefix in ['major', 'course']:
        fields, _ = db.get_all_items(Field, per_page=100)
        await query.edit_message_text(db.get_text('select_parent_field'), reply_markup=kb.parent_field_selection_keyboard(fields, prefix, page))
        return States.SELECTING_PARENT_FIELD
    elif prefix == 'admin':
        await query.edit_message_text("لطفا آیدی عددی ادمین جدید را وارد کنید:")
        return States.GETTING_ADMIN_ID
    else:
        await query.edit_message_text(db.get_text('ask_for_new_item_name'))
        return States.GETTING_NEW_NAME

async def item_add_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the name for the new item and saves it."""
    prefix = context.user_data.get('prefix')
    page = context.user_data.get('page')
    parent_id = context.user_data.get('parent_id')
    model = MODEL_MAP[prefix]
    
    kwargs = {'name': update.message.text.strip()}
    if parent_id:
        if prefix == 'major': kwargs['field_id'] = parent_id
        if prefix == 'course': kwargs['major_id'] = parent_id
        
    db.add_item(model, **kwargs)
    await update.message.reply_text(db.get_text('item_added_successfully'))
    
    # Refresh list
    query_data = f"admin_list_{prefix}_{page}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text="بازگشت به لیست...", reply_markup=kb.back_to_list_keyboard(prefix, page))

    context.user_data.clear()
    return ConversationHandler.END

async def item_add_select_parent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    """Handles selection of a parent item (e.g., a Field for a new Major)."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    parent_id = int(parts[2])
    context.user_data['parent_id'] = parent_id
    
    await query.edit_message_text(db.get_text('ask_for_new_item_name'))
    return States.GETTING_NEW_NAME

async def admin_add_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Adds a new admin by their user ID."""
    try:
        user_id = int(update.message.text)
        db.add_item(Admin, user_id=user_id)
        await update.message.reply_text("ادمین جدید با موفقیت اضافه شد.")
    except (ValueError, Exception) as e:
        await update.message.reply_text(f"خطا: {e}. لطفا یک آیدی عددی معتبر وارد کنید.")

    page = context.user_data.get('page', 1)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="بازگشت به لیست...", reply_markup=kb.back_to_list_keyboard('admin', page))

    context.user_data.clear()
    return ConversationHandler.END


# --- Main Application Setup ---
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

    broadcast_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(broadcast_start_callback, pattern=r'^admin_broadcast$')],
        states={
            States.GETTING_BROADCAST_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_receive_message)]
        },
        fallbacks=[CallbackQueryHandler(admin_panel_callback, pattern=ADMIN_MAIN_PANEL), CommandHandler('cancel', cancel_submission)],
        per_user=True, per_chat=True
    )

    single_message_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(single_message_start_callback, pattern=r'^admin_single_message$')],
        states={
            States.GETTING_SINGLE_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, single_message_get_user)],
            States.GETTING_SINGLE_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, single_message_send)]
        },
        fallbacks=[CallbackQueryHandler(admin_panel_callback, pattern=ADMIN_MAIN_PANEL), CommandHandler('cancel', cancel_submission)],
        per_user=True, per_chat=True
    )
    
    add_channel_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_channel_start_callback, pattern=ADMIN_ADD_CHANNEL)],
        states={
            States.GETTING_CHANNEL_ID_TO_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_channel_get_id)],
            States.GETTING_CHANNEL_LINK_TO_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_channel_get_link)]
        },
        fallbacks=[CallbackQueryHandler(admin_manage_channels_callback, pattern=ADMIN_MANAGE_CHANNELS), CommandHandler('cancel', cancel_submission)],
        per_user=True, per_chat=True
    )
    
    item_add_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(item_add_start, pattern=ITEM_ADD), CallbackQueryHandler(item_add_start, pattern=ADMIN_ADD)],
        states={
            States.GETTING_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_add_receive_name)],
            States.GETTING_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_get_id)],
            States.SELECTING_PARENT_FIELD: [CallbackQueryHandler(item_add_select_parent, pattern=COMPLEX_ITEM_SELECT_PARENT)]
        },
        fallbacks=[CommandHandler('cancel', cancel_submission)],
        per_user=True, per_chat=True
    )

    # --- Register Handlers ---
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))

    # User Handlers
    app.add_handler(submission_handler)
    app.add_handler(MessageHandler(filters.Regex('^' + db.get_text(MY_EXPS_BTN_KEY) + '$'), my_experiences_command))
    app.add_handler(MessageHandler(filters.Regex('^' + db.get_text(RULES_BTN_KEY) + '$'), rules_command))
    app.add_handler(CallbackQueryHandler(membership_check_callback, pattern=CHECK_MEMBERSHIP))
    
    # Admin Panel Handlers
    app.add_handler(broadcast_handler)
    app.add_handler(single_message_handler)
    app.add_handler(add_channel_handler)
    app.add_handler(item_add_handler)
    app.add_handler(CallbackQueryHandler(admin_panel_callback, pattern=ADMIN_MAIN_PANEL))
    app.add_handler(CallbackQueryHandler(show_stats_callback, pattern=r'^admin_stats$'))
    app.add_handler(CallbackQueryHandler(experience_approval_handler, pattern=EXPERIENCE_APPROVAL))
    
    # Channel Management Handlers
    app.add_handler(CallbackQueryHandler(admin_manage_channels_callback, pattern=ADMIN_MANAGE_CHANNELS))
    app.add_handler(CallbackQueryHandler(admin_toggle_force_sub_callback, pattern=ADMIN_TOGGLE_FORCE_SUB))
    app.add_handler(CallbackQueryHandler(admin_delete_channel_callback, pattern=ADMIN_DELETE_CHANNEL))
    
    # CRUD Handlers
    app.add_handler(CallbackQueryHandler(admin_list_items_callback, pattern=ADMIN_LIST_ITEMS))
    app.add_handler(CallbackQueryHandler(admin_list_items_callback, pattern=ADMIN_LIST_TEXTS))
    app.add_handler(CallbackQueryHandler(item_delete_callback, pattern=ITEM_DELETE))
    app.add_handler(CallbackQueryHandler(item_confirm_delete_callback, pattern=ITEM_CONFIRM_DELETE))


    logger.info("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()