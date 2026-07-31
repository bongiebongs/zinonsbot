# 📚 Class Schedule Telegram Bot

A Telegram bot that sends you weekly polls to select your classes, then automatically adds them to your Google Calendar!

## Features

✅ **Weekly Polls** - Every Sunday 9 PM, get polls for Math & Economics classes  
✅ **Multiple Selection** - Click the classes you're attending  
✅ **Auto Sync** - Selected classes automatically add to Google Calendar  
✅ **Add Custom Events** - Add events that come up during the week  
✅ **24/7 Running** - Deployed on Render, always online  

## Setup Instructions

### Step 1: Get Your Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow the prompts and get your **BOT TOKEN**
4. Save it somewhere safe (you'll need it later)

### Step 2: Download Google Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (name it "Calendar Bot")
3. Search for "Google Calendar API" and **Enable** it
4. Click **Create Credentials** → **OAuth 2.0 Desktop Application**
5. Download the JSON file and save as `credentials.json`

### Step 3: Set Up Locally (Testing)

```bash
# Clone your repository
git clone https://github.com/YOUR-USERNAME/telegram-calendar-bot.git
cd telegram-calendar-bot

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add credentials.json to the project folder

# Edit bot.py and replace:
# BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN" with your actual token

# Run the bot
python bot.py
```

On first run, you'll see a Google login link. Click it to authorize the bot.

### Step 4: Test the Bot

In Telegram:
- Send `/start` to your bot
- Send `/send_polls` to test the polls immediately
- Click on the classes you want to add

Check your Google Calendar - the classes should be added! ✅

### Step 5: Push to GitHub

```bash
# Add all files
git add .

# Commit
git commit -m "Add Telegram calendar bot with class schedule"

# Push
git push origin main
```

### Step 6: Deploy on Render

1. Go to [render.com](https://render.com)
2. Sign up for free
3. Click **New +** → **Web Service**
4. Connect your GitHub account and select `telegram-calendar-bot`
5. Configure:
   - **Name:** `telegram-calendar-bot`
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python bot.py`

6. Add Environment Variables (click **Environment**):
   - Add `BOT_TOKEN` with your Telegram token value

7. Add Secrets (click **Secrets**):
   - Create a `credentials.json` secret:
     - Go to your local `credentials.json`
     - Copy the entire contents
     - In Render, add secret with key `credentials_json` and paste the contents
   
   - Add this to `bot.py` after imports:
   ```python
   import json
   import os
   
   # Handle Render's environment variable for credentials
   if 'credentials_json' in os.environ:
       creds_data = os.environ.get('credentials_json')
       with open('credentials.json', 'w') as f:
           f.write(creds_data)
   ```

8. Click **Deploy**
9. Wait ~2 minutes for deployment to complete
10. Your bot is now running 24/7! 🚀

## How It Works

### Weekly Class Polls
- **Every Sunday at 9 PM (Singapore time)**, the bot sends you two polls:
  1. Math classes poll (E1, H1, E2, H2, TT)
  2. Economics classes poll (L1, L2)

- **Click the classes** you're attending that week
- **Automatically added** to your Google Calendar with correct times

### Add Custom Events
- Send `/add_event` anytime during the week
- Tell the bot:
  1. **Event name** (e.g., "Project Deadline", "Doctor Appointment")
  2. **Day** (e.g., "Monday", "Tomorrow", "Dec 25")
  3. **Time** (e.g., "2pm", "3:30pm", "14:00")
- **Automatically added** to your Google Calendar!

**Example:**
```
You: /add_event
Bot: What's the event name?
You: Project Submission
Bot: Which day?
You: Friday
Bot: What time?
You: 5pm
Bot: ✅ Event Added!
```

## Files Explained

- **bot.py** - Main bot code
- **requirements.txt** - Python dependencies
- **.gitignore** - Files to not push to GitHub (credentials, tokens)
- **README.md** - This file

## Customizing Your Classes

To change your class schedule:

1. Open `bot.py`
2. Find the `MATH_CLASSES` and `ECONS_CLASSES` sections
3. Edit the class names, days, and times
4. Example:
   ```python
   MATH_CLASSES = {
       "E1": {"days": ["Tuesday", "Wednesday"], "times": {"Tuesday": "4-6pm", "Wednesday": "6-8pm"}},
       # Add more classes or modify existing ones
   }
   ```
5. Push changes to GitHub and Render will auto-redeploy

## Customizing Event Duration

By default, custom events are set to 1 hour. To change this:

1. Open `bot.py`
2. Find this line: `end_time = start_time + timedelta(hours=1)`
3. Change `hours=1` to however long you want (e.g., `hours=2` for 2 hours)
4. Save and redeploy

## Troubleshooting

**Bot doesn't send polls?**
- Check Render logs to see if there are errors
- Make sure BOT_TOKEN is correctly set
- Make sure you sent `/start` to save your chat ID

**Classes not added to calendar?**
- Make sure `credentials.json` is properly set up on Render
- Check Render logs for Google API errors

**Wrong times on calendar?**
- Check the time format in your class schedule
- Times should be like: "4-6pm", "12:30-2:30pm", "10am-12pm"

## Support

If something doesn't work:
1. Check Render logs (Dashboard → Your App → Logs)
2. Test locally first (`python bot.py`)
3. Make sure all credentials are correct

## Future Enhancements

You can easily add:
- Skip/cancel a class for the week
- Add notes to classes
- Get reminders before class starts
- View calendar directly in Telegram
- More subjects/classes

Just modify `bot.py` and redeploy! 😊
