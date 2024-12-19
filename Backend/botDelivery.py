from flask import Flask, Blueprint, jsonify
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import logging
from threading import Thread

app = Flask(__name__)

bp = Blueprint("botDelievry", __name__)

# Initialize the Telegram bot with your token
TELEGRAM_TOKEN =   # Replace with your actual token
bot = Bot(token=TELEGRAM_TOKEN)
# Example chat ID - replace with your actual chat ID
CHAT_ID = '5672534941'  # Replace with the actual chat ID

## Enable logging for debugging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Command handler for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome! Payment notifications will be sent here.")

# Error handler
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f'Update "{update}" caused error "{context.error}"')

# Setup the command handler for the start command
def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_error_handler(error)

    # Start polling for updates
    application.run_polling()


# Register the blueprint
app.register_blueprint(bp)

if __name__ == '__main__':
    # Start the Flask app in a separate thread
    flask_thread = Thread(target=lambda: app.run(port=5000, debug=True))
    flask_thread.start()
    
    # Start the Telegram bot
    main()
