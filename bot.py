import requests
import os
import sys
import json
import time
import asyncio
import telegram
import logging
import sqlite3
import threading
import datetime
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes


load_dotenv()

#Import the token
token=os.getenv("TELEGRAM_BOT_TOKEN")

API_ENDPOINT=os.getenv('API')

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

# Connect to the database and create the subscribers table if it doesn't already exist
conn = sqlite3.connect("subscribers.db")
cursor = conn.cursor()
try:
    cursor.execute('''CREATE TABLE IF NOT EXISTS subscribers
                (chat_id INTEGER PRIMARY KEY, username TEXT)''')
    conn.commit()
except sqlite3.Error as e:
    print("Error creating subscribers table:", e)
conn.close()

# Define the start command handler
async def start(update, context):
    await context.bot.send_message(chat_id=update.message.chat_id, text="Hello! I am TbillStats Official bot. \n\nIf you'd like to receive daily updates (9AM CET) on the TBILL pools, please send the command /subscribe.\n\nIf at any time you no longer wish to receive updates, you can send the command /unsubscribe to stop receiving messages from me.")

def send_message(bot, chat_id, message):
    bot.send_message(chat_id=chat_id, text=message)

# Define the subscribe command handler
async def subscribe(update, context):
    chat_id = update.message.chat_id
    username = update.message.from_user.username

    # Connect to the database and add the new subscriber
    with sqlite3.connect("subscribers.db") as conn:
        cursor = conn.cursor()

        # Check if the user is already subscribed
        cursor.execute("SELECT * FROM subscribers WHERE chat_id=?", (chat_id,))
        result = cursor.fetchone()
        if result:
            await context.bot.send_message(chat_id=chat_id, text="You are already subscribed to TbillStats updates.")
            return

        # Add the new subscriber
        cursor.execute("INSERT INTO subscribers VALUES (?,?)", (chat_id, username))
        conn.commit()

    await context.bot.send_message(chat_id=chat_id, text="You have successfully subscribed to TbillStats updates.")

# Define the unsubscribe command handler
async def unsubscribe(update, context):
    chat_id = update.message.chat_id

    # Connect to the database
    conn = sqlite3.connect("subscribers.db")
    cursor = conn.cursor()

    # Check if the user is in the database
    cursor.execute("SELECT * FROM subscribers WHERE chat_id=?", (chat_id,))
    result = cursor.fetchone()
    if result:
        # Remove the subscriber from the database
        cursor.execute("DELETE FROM subscribers WHERE chat_id=?", (chat_id,))
        conn.commit()
        conn.close()

        await context.bot.send_message(chat_id=chat_id, text="You have successfully unsubscribed from TbillStats updates.")
    else:
        await context.bot.send_message(chat_id=chat_id, text="You are not subscribed to TbillStats updates.")
        conn.close()


data = None
def get_data():
    try:
        response = requests.get(API_ENDPOINT)
        data = json.loads(response.text)
    except:
        pass
    return data

# Command handler for the fetch command
async def get_update(update, context):
    data = get_data()
    if data:
        message = "Current status: \n"
        message += "TV Locked: ${} ({}%)\n".format(data["tvLocked"], data["tvLocked24hPct"])
        message += "TBILL Locked: {} ({}%)\n".format(data["tbillLocked"]+" TBILL", data["tbillLocked24hPct"])
        message += "TFUEL Locked: {} ({}%)\n".format(data["tfuelLocked"]+" TFUEL", data["tfuelLocked24hPct"])
        message += "GNote Locked: {} ({}%)\n".format(data["gnoteLocked"]+" gNote", data["gnoteLocked24hPct"])
        message += "TFUEL/TBILL wallets: {} ({})\n".format(data["walletCalc"], data["walletCalc24h"])
        message += "gNote/TBILL wallets: {} ({})\n".format(data["walletCalcGnote"], data["walletCalcGnote24h"])
        await context.bot.send_message(chat_id=update.message.chat_id, text=message)
    else:
        await context.bot.send_message(chat_id=update.message.chat_id, text="Data not available.")


async def send_daily_data():
    subscribers = []

    # Connect to the database and retrieve the subscribers
    conn = sqlite3.connect("subscribers.db")
    cursor = conn.cursor()  
    cursor.execute("SELECT chat_id FROM subscribers")
    subscribers = cursor.fetchall()
    conn.close()

    # Fetch the data from the API
    data = get_data()

    message = "Daily update ({}): \n".format(datetime.now().strftime("%Y-%m-%d"))
    message += "TV Locked: {} ({}%)\n".format(data["tvLocked"], data["tvLocked24hPct"])
    message += "TBILL Locked: {} ({}%)\n".format(data["tbillLocked"], data["tbillLocked24hPct"])
    message += "TFUEL Locked: {} ({}%)\n".format(data["tfuelLocked"]+" TFUEL", data["tfuelLocked24hPct"])
    message += "GNote Locked: {} ({}%)\n".format(data["gnoteLocked"]+" gNote", data["gnoteLocked24hPct"])
    message += "TFUEL/TBILL wallets: {} ({})\n".format(data["walletCalc"], data["walletCalc24h"])
    message += "gNote/TBILL wallets: {} ({})\n".format(data["walletCalcGnote"], data["walletCalcGnote24h"])

    print (subscribers)
    # Send the data to each subscriber
    for subscriber in subscribers:
        chat_id = subscriber[0]
        await app.bot.send_message(chat_id=chat_id, text=message)


async def handle_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message.text
    
    if message == "/start":
        await start(update, context)
        pass
    elif message == "/getupdate":
        await get_update(update, context)
        pass
    elif message == "/subscribe":
        await subscribe(update, context)
        pass
    elif message == "/unsubscribe":
        await unsubscribe(update, context)
        pass

try:
  action = sys.argv[1]
  if action == "listen":
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", handle_updates))
    app.add_handler(MessageHandler(filters.TEXT, handle_updates))
    app.run_polling()
    handle_updates()
    print("listening...")
  elif action == "sendUpdate":
    app = ApplicationBuilder().token(token).build()
    asyncio.run(send_daily_data())
    print("sending update...")
  else:
    print("unknown command. Exiting")
except:
  print("Missing argument ?")