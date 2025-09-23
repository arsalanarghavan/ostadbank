# constants.py

from enum import Enum, auto

# --- Telegram API Limits ---
MAX_MESSAGE_LENGTH = 4096
MAX_CALLBACK_DATA_LENGTH = 64
MAX_CAPTION_LENGTH = 1024

# --- Conversation States using Enum for robustness ---
class States(Enum):
    # Submission Flow
    SELECTING_FIELD = auto()
    SELECTING_MAJOR = auto()
    SELECTING_COURSE = auto()
    SELECTING_PROFESSOR = auto()
    ADDING_PROFESSOR = auto()
    GETTING_TEACHING = auto()
    GETTING_NOTES = auto()
    GETTING_PROJECT = auto()
    GETTING_ATTENDANCE_CHOICE = auto()
    GETTING_ATTENDANCE_DETAILS = auto()
    GETTING_EXAM = auto()
    GETTING_CONCLUSION = auto()
    
    # Admin Panel Flow
    GETTING_NEW_NAME = auto()
    GETTING_UPDATED_NAME = auto()
    SELECTING_PARENT_FIELD = auto()
    GETTING_UPDATED_TEXT = auto()
    GETTING_ADMIN_ID = auto()
    
    # New Admin Features
    GETTING_BROADCAST_MESSAGE = auto()
    GETTING_SINGLE_USER_ID = auto()
    GETTING_SINGLE_MESSAGE = auto()
    GETTING_CHANNEL_ID_TO_ADD = auto()
    GETTING_CHANNEL_LINK_TO_ADD = auto()


# --- Callback Data Patterns ---
# User flow patterns
FIELD_SELECT = r"^field_select_"
MAJOR_SELECT = r"^major_select_"
COURSE_SELECT = r"^course_select_"
PROFESSOR_SELECT = r"^professor_select_"
PROFESSOR_ADD_NEW = r"^professor_add_new$"
ATTENDANCE_CHOICE = r"^attendance_"
CANCEL_SUBMISSION = r"^cancel_submission$"
CHECK_MEMBERSHIP = r"^check_membership$"


# Admin panel patterns
ADMIN_MAIN_PANEL = r"^admin_main_panel$"
ADMIN_LIST_ITEMS = r"^admin_list_(field|major|course|professor|admin)_\d+$" # Corrected pattern
ADMIN_LIST_TEXTS = r"^admin_list_texts_\d+$"
ADMIN_MANAGE_CHANNELS = r"^admin_manage_channels$"
ADMIN_ADD_CHANNEL = r"^admin_add_channel$"
ADMIN_DELETE_CHANNEL = r"^admin_delete_channel_"
ADMIN_TOGGLE_FORCE_SUB = r"^admin_toggle_force_sub$"


# CRUD patterns (Create, Read, Update, Delete)
ITEM_ADD = r"^(field|major|course|professor)_add_\d+$"
ADMIN_ADD = r"^(admin)_add_\d+$" # Corrected pattern
ITEM_EDIT = r"^(field|major|course|professor)_edit_\d+_\d+$"
TEXT_EDIT = r"^text_edit_.*_\d+$"
ITEM_DELETE = r"^.*_delete_.*$"
ITEM_CONFIRM_DELETE = r"^.*_confirmdelete_.*$"

# Parent selection for complex items
COMPLEX_ITEM_SELECT_PARENT = r"^(major|course)_selectfield_"

# Experience approval patterns
EXPERIENCE_APPROVAL = r"^exp_"

# --- Bot Text Keys (for database) ---
# A few examples to show how you can use them
WELCOME_TEXT_KEY = 'welcome'
RULES_TEXT_KEY = 'rules'
SUBMIT_EXP_BTN_KEY = 'btn_submit_experience'
MY_EXPS_BTN_KEY = 'btn_my_experiences'
RULES_BTN_KEY = 'btn_rules'