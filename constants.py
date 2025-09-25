# constants.py (Final Corrected Version)

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

    # START OF CHANGE - حالت جدید برای جستجو
    GETTING_PROFESSOR_SEARCH_QUERY = auto()
    # END OF CHANGE


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
ADMIN_MAIN_PANEL = r"^admin_main_panel_inline$"
ADMIN_LIST_ITEMS = r"^admin_list_(field|major|course|professor|admin)_\d+$"
ADMIN_LIST_TEXTS = r"^admin_list_texts_\d+$"
ADMIN_MANAGE_CHANNELS = r"^admin_manage_channels_inline$"
ADMIN_ADD_CHANNEL = r"^admin_add_channel$"
ADMIN_DELETE_CHANNEL = r"^admin_delete_channel_"
ADMIN_TOGGLE_FORCE_SUB = r"^admin_toggle_force_sub$"

# Experience Management Patterns
ADMIN_MANAGE_EXPERIENCES = r"^admin_manage_experiences$"
ADMIN_LIST_PENDING_EXPERIENCES = r"^admin_pending_exps_"
ADMIN_PENDING_EXPERIENCE_DETAIL = r"^admin_pending_detail_"

# START OF CHANGE - الگوهای جدید برای جستجو
ADMIN_SEARCH_EXPERIENCES = r"^admin_search_exps$"
ADMIN_SEARCH_RESULTS_PAGE = r"^admin_search_page_"
ADMIN_SEARCH_DETAIL = r"^admin_search_detail_"
# END OF CHANGE


# CRUD patterns (Create, Read, Update, Delete)
ITEM_ADD = r"^(field|major|course|professor)_add_\d+$"
ADMIN_ADD = r"^(admin)_add_\d+$"
ITEM_EDIT = r"^(field|major|course|professor)_edit_\d+_\d+$"
TEXT_EDIT = r"^text_edit_.+_\d+$"
ITEM_DELETE = r"^(field|major|course|professor|admin)_delete_\d+_\d+$"
ITEM_CONFIRM_DELETE = r"^(field|major|course|professor|admin)_confirmdelete_\d+_\d+$"


# Parent selection for complex items
COMPLEX_ITEM_SELECT_PARENT = r"^(major|course)_selectfield_"

# Experience approval patterns
EXPERIENCE_APPROVAL = r"^exp_(approve|reject|reason)_"


# --- Bot Text Keys (for database) ---
WELCOME_TEXT_KEY = 'welcome'
RULES_TEXT_KEY = 'rules'
SUBMIT_EXP_BTN_KEY = 'btn_submit_experience'
MY_EXPS_BTN_KEY = 'btn_my_experiences'
RULES_BTN_KEY = 'btn_rules'