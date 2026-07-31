import os
import logging
from datetime import datetime, timedelta
import pytz
from telegram import Update, Poll, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, PollAnswerHandler, ConversationHandler, MessageHandler, filters
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import json
import re

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== CONFIGURATION =====
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Replace with your token from BotFather
TIMEZONE = "Asia/Singapore"  # Your timezone

# Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Class schedules
MATH_CLASSES = {
    "E1": {"days": ["Tuesday", "Wednesday"], "times": {"Tuesday": "4-6pm", "Wednesday": "6-8pm"}},
    "H1": {"days": ["Tuesday", "Wednesday"], "times": {"Tuesday": "6-8pm", "Wednesday": "4-6pm"}},
    "E2": {"days": ["Saturday", "Sunday"], "times": {"Saturday": "10am-12pm", "Sunday": "3-5pm"}},
    "H2": {"days": ["Saturday", "Sunday"], "times": {"Saturday": "12:30-2:30pm", "Sunday": "12:30-2:30pm"}},
    "TT": {"days": ["Thursday", "Friday"], "times": {"Thursday": "5-8pm", "Friday": "5-8pm"}},
}

ECONS_CLASSES = {
    "L1": {"days": ["Friday"], "times": {"Friday": "4:30-6:30pm"}},
    "L2": {"days": ["Saturday"], "times": {"Saturday": "12:15-2:15pm"}},
}

# File to store user selections
SELECTIONS_FILE = "class_selections.json"

# Conversation states for adding events
ASKING_EVENT_NAME, ASKING_EVENT_DAY, ASKING_EVENT_TIME = range(3)

# ===== GOOGLE CALENDAR SETUP =====
def setup_credentials():
    """Setup credentials.json from environment variable if needed"""
    # Check if credentials.json exists
    if not os.path.exists('credentials.json'):
        # Try to get from environment variable
        creds_env = os.environ.get('credentials_json')
        if creds_env:
            with open('credentials.json', 'w') as f:
                f.write(creds_env)
            logger.info("Created credentials.json from environment variable")
        else:
            logger.error("No credentials.json file and no credentials_json environment variable!")
            return False
    return True

def get_calendar_service():
    """Authenticate and create Google Calendar service"""
    try:
        # Setup credentials if needed
        if not setup_credentials():
            logger.error("Could not setup credentials")
            return None
        
        creds = None
        
        if os.path.exists('token.json'):
            from google.auth.transport.requests import Request
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        service = build('calendar', 'v3', credentials=creds)
        return service
    
    except Exception as e:
        logger.error(f"Error setting up calendar service: {e}")
        return None

def parse_time(time_str):
    """Parse time string like '4-6pm' to (start_hour, end_hour, end_minute)"""
    time_str = time_str.strip()
    
    if '-' not in time_str:
        return None
    
    parts = time_str.split('-')
    start = parts[0].strip()
    end = parts[1].strip()
    
    # Handle 'am' and 'pm'
    if 'pm' in start.lower() or 'am' in start.lower():
        pass
    else:
        if 'pm' in end.lower():
            start += 'pm'
        elif 'am' in end.lower():
            start += 'am'
    
    # Parse start time
    start_clean = start.lower().replace('am', '').replace('pm', '').strip()
    start_period = 'pm' if 'pm' in start.lower() else 'am'
    
    # Parse end time
    end_clean = end.lower().replace('am', '').replace('pm', '').strip()
    end_period = 'pm' if 'pm' in end.lower() else 'am'
    
    try:
        start_hour = int(start_clean.split(':')[0])
        if 'pm' in start_period and start_hour != 12:
            start_hour += 12
        elif 'am' in start_period and start_hour == 12:
            start_hour = 0
        
        if ':' in end_clean:
            end_hour = int(end_clean.split(':')[0])
            end_minute = int(end_clean.split(':')[1])
        else:
            end_hour = int(end_clean)
            end_minute = 0
        
        if 'pm' in end_period and end_hour != 12:
            end_hour += 12
        elif 'am' in end_period and end_hour == 12:
            end_hour = 0
        
        return (start_hour, end_hour, end_minute)
    except:
        return None

def add_to_calendar(class_name, day_name, time_str, service):
    """Add event to Google Calendar"""
    try:
        time_info = parse_time(time_str)
        if not time_info:
            logger.error(f"Could not parse time: {time_str}")
            return False
        
        start_hour, end_hour, end_minute = time_info
        
        # Get the date for this week's day
        today = datetime.now(pytz.timezone(TIMEZONE))
        current_day = today.weekday()
        
        day_map = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
            "Friday": 4, "Saturday": 5, "Sunday": 6
        }
        
        target_day = day_map[day_name]
        days_ahead = target_day - current_day
        
        if days_ahead <= 0:  # Target day already happened this week, schedule for next week
            days_ahead += 7
        
        event_date = today + timedelta(days=days_ahead)
        
        # Create event
        start_time = event_date.replace(hour=start_hour, minute=0, second=0)
        end_time = event_date.replace(hour=end_hour, minute=end_minute, second=0)
        
        event = {
            'summary': class_name,
            'description': f'Scheduled via Calendar Bot',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': TIMEZONE,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': TIMEZONE,
            },
        }
        
        service.events().insert(calendarId='primary', body=event).execute()
        logger.info(f"Added {class_name} on {day_name} at {time_str}")
        return True
    
    except Exception as e:
        logger.error(f"Error adding to calendar: {e}")
        return False

# ===== EVENT ADDITION HANDLERS =====
async def add_event_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the add event conversation"""
    await update.message.reply_text(
        "📝 Let's add an event!\n\n"
        "What's the event name? (e.g., 'Project Deadline', 'Doctor Appointment')"
    )
    return ASKING_EVENT_NAME

async def add_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store event name and ask for day"""
    event_name = update.message.text.strip()
    
    if len(event_name) < 1:
        await update.message.reply_text("Please enter a valid event name.")
        return ASKING_EVENT_NAME
    
    context.user_data['event_name'] = event_name
    
    # Create keyboard with day options
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Today', 'Tomorrow']
    reply_keyboard = [days[i:i+3] for i in range(0, len(days), 3)]
    
    await update.message.reply_text(
        f"✅ Event: {event_name}\n\n"
        "Which day? (or type a specific date like 'Dec 25')",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return ASKING_EVENT_DAY

async def add_event_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store day and ask for time"""
    day_input = update.message.text.strip()
    
    context.user_data['event_day'] = day_input
    
    await update.message.reply_text(
        f"📅 Day: {day_input}\n\n"
        "What time? (e.g., '2pm', '3:30pm', '14:00')",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASKING_EVENT_TIME

async def add_event_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store time and create event"""
    time_input = update.message.text.strip()
    
    event_name = context.user_data['event_name']
    event_day = context.user_data['event_day']
    
    try:
        service = get_calendar_service()
        
        # Parse the day
        day_lower = event_day.lower()
        tz = pytz.timezone(TIMEZONE)
        today = datetime.now(tz).date()
        
        if day_lower == 'today':
            event_date = today
        elif day_lower == 'tomorrow':
            event_date = today + timedelta(days=1)
        else:
            # Try to parse as a weekday
            day_map = {
                "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6
            }
            
            if day_lower in day_map:
                current_day = today.weekday()
                target_day = day_map[day_lower]
                days_ahead = target_day - current_day
                
                if days_ahead <= 0:  # Day already happened this week
                    days_ahead += 7
                
                event_date = today + timedelta(days=days_ahead)
            else:
                # Try to parse as a date (e.g., "Dec 25", "25/12", "12-25")
                try:
                    # Try various date formats
                    for date_format in ["%b %d", "%d/%m", "%m-%d", "%d-%m"]:
                        try:
                            parsed = datetime.strptime(event_day, date_format)
                            event_date = today.replace(month=parsed.month, day=parsed.day)
                            if event_date < today:
                                event_date = event_date.replace(year=today.year + 1)
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError("Could not parse date")
                except:
                    await update.message.reply_text(
                        "❌ Sorry, I couldn't understand the date. Try 'Monday', 'Tomorrow', or 'Dec 25'."
                    )
                    return ASKING_EVENT_DAY
        
        # Parse the time
        time_match = re.search(r'(\d{1,2}):?(\d{0,2})\s*(am|pm)?', time_input.lower())
        if not time_match:
            await update.message.reply_text(
                "❌ I couldn't parse the time. Try '2pm', '14:00', or '3:30pm'."
            )
            return ASKING_EVENT_TIME
        
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        period = time_match.group(3)
        
        # Convert to 24-hour format
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        # Create the event
        start_time = datetime.combine(event_date, datetime.min.time(), tzinfo=tz).replace(hour=hour, minute=minute)
        end_time = start_time + timedelta(hours=1)  # Default 1-hour event
        
        event = {
            'summary': event_name,
            'description': 'Added via Telegram Calendar Bot',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': TIMEZONE,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': TIMEZONE,
            },
        }
        
        service.events().insert(calendarId='primary', body=event).execute()
        
        # Confirm to user
        await update.message.reply_text(
            f"✅ Event Added!\n\n"
            f"📌 {event_name}\n"
            f"📅 {event_date.strftime('%A, %B %d, %Y')}\n"
            f"⏰ {start_time.strftime('%I:%M %p')}\n\n"
            f"Added to your Google Calendar!"
        )
        
        logger.info(f"Added event: {event_name} on {event_date} at {hour}:{minute:02d}")
        
    except Exception as e:
        logger.error(f"Error adding event: {e}")
        await update.message.reply_text(
            f"❌ Error adding event: {str(e)}\n\n"
            "Make sure your Google credentials are set up correctly."
        )
    
    return ConversationHandler.END

async def cancel_add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel adding an event"""
    await update.message.reply_text(
        "❌ Cancelled. No event was added.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ===== TELEGRAM HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when /start is issued"""
    welcome_message = """
📚 Welcome to Class Schedule Bot!

I'll send you polls every **Sunday at 9 PM** to confirm which classes you're attending that week.

Available commands:
/start - Show this message
/help - Get help
/add_event - Add a custom event during the week
/send_polls - Send polls now (for testing)

Just wait for Sunday 9 PM and I'll send the polls! 🚀
"""
    await update.message.reply_text(welcome_message)
    
    # Save chat ID
    save_chat_id(update.effective_chat.id)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = """
📖 Help Guide:

**Weekly Class Polls:**
Every Sunday at 9 PM:
1. You'll receive a poll for Math classes
2. You'll receive a poll for Economics classes
3. Select the classes you're attending
4. They'll automatically be added to your Google Calendar!

**Add Custom Events:**
Need to add an event during the week?
- Send /add_event
- Tell me the event name, day, and time
- It'll be added to your Google Calendar!

Commands:
/start - Welcome message
/add_event - Add a custom event
/send_polls - Send polls right now (testing)
/help - This message

Examples for /add_event:
- "Project Deadline" → "Friday" → "5pm"
- "Doctor Appointment" → "Tomorrow" → "2:30pm"
- "Meeting" → "Wednesday" → "3pm"
"""
    await update.message.reply_text(help_text)

async def send_polls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send polls immediately (for testing)"""
    await send_weekly_polls(context)
    await update.message.reply_text("✅ Polls sent! Check above.")

async def send_weekly_polls(context: ContextTypes.DEFAULT_TYPE):
    """Send the weekly polls"""
    if not has_chat_id():
        logger.error("No chat ID saved")
        return
    
    chat_id = load_chat_id()
    
    # Math classes poll
    math_options = list(MATH_CLASSES.keys())
    await context.bot.send_poll(
        chat_id=chat_id,
        question="📐 Which Math classes are you attending this week?",
        options=math_options,
        is_anonymous=False,
        allows_multiple_answers=True
    )
    
    # Economics classes poll
    econs_options = list(ECONS_CLASSES.keys())
    await context.bot.send_poll(
        chat_id=chat_id,
        question="💼 Which Economics classes are you attending this week?",
        options=econs_options,
        is_anonymous=False,
        allows_multiple_answers=True
    )

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle poll answers"""
    answer = update.poll_answer
    poll_id = answer.poll_id
    
    logger.info(f"Poll answer received: {answer.option_ids}")
    
    # Store the answer
    save_selection(poll_id, answer.option_ids)

# ===== FILE OPERATIONS =====
def save_chat_id(chat_id):
    """Save chat ID to file"""
    with open('chat_id.txt', 'w') as f:
        f.write(str(chat_id))

def load_chat_id():
    """Load chat ID from file"""
    if os.path.exists('chat_id.txt'):
        with open('chat_id.txt', 'r') as f:
            return int(f.read().strip())
    return None

def has_chat_id():
    """Check if chat ID is saved"""
    return os.path.exists('chat_id.txt')

def save_selection(poll_id, selected_options):
    """Save poll selections"""
    data = {}
    if os.path.exists(SELECTIONS_FILE):
        with open(SELECTIONS_FILE, 'r') as f:
            data = json.load(f)
    
    data[poll_id] = {
        'options': selected_options,
        'timestamp': datetime.now().isoformat()
    }
    
    with open(SELECTIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ===== SCHEDULED TASKS =====
async def scheduled_weekly_polls(application):
    """Send polls at scheduled time using telegram's built-in scheduling"""
    # For now, we'll keep the send_polls command available
    # Weekly scheduling will be added via a simple job queue
    pass

# ===== MAIN FUNCTION =====
def main():
    """Start the bot"""
    # Initialize credentials
    logger.info("Initializing credentials...")
    setup_credentials()
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add event conversation handler
    add_event_handler = ConversationHandler(
        entry_points=[CommandHandler('add_event', add_event_start)],
        states={
            ASKING_EVENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_event_name)],
            ASKING_EVENT_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_event_day)],
            ASKING_EVENT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_event_time)],
        },
        fallbacks=[CommandHandler('cancel', cancel_add_event)],
    )
    
    # Register handlers
    application.add_handler(add_event_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("send_polls", send_polls_command))
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    
    # Start the Bot
    logger.info("Bot started successfully!")
    application.run_polling()

if __name__ == '__main__':
    main()
