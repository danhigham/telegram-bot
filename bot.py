#!/usr/bin/env python3
import os
import logging
import asyncio
import random
import google.generativeai as genai
from telethon import TelegramClient, events

# --- Configuration ---

# Set up basic logging to see errors and bot activity in the console
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- API Key Setup ---
# Use environment variables for your API keys and credentials for security.
# On your terminal, run:
# export TELEGRAM_API_ID="YOUR_API_ID"
# export TELEGRAM_API_HASH="YOUR_API_HASH"
# export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Check if the keys are available
if not all([API_ID, API_HASH, GEMINI_API_KEY]):
    raise ValueError("API_ID, API_HASH, or GEMINI_API_KEY not found. Please set them as environment variables.")

# --- Whitelist and Contact Configuration ---
# Add the Telegram User IDs of people you DO NOT want the bot to interact with.
# To find a user's ID, you can forward one of their messages to a bot like @userinfobot.
WHITELISTED_USERS = {
    129746969, # <-- Example User ID for a family member
    # 98765432, # <-- Example User ID for a friend
}
# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# --- Gemini Model and Persona ---
# Set the maximum length of the bot's reply to keep responses concise.
MAX_OUTPUT_TOKENS = 150

# Load the system persona from an external file for easy editing.
try:
    with open('persona.txt', 'r', encoding='utf-8') as f:
        SYSTEM_PERSONA = f.read().strip()
    logger.info("Successfully loaded persona from persona.txt")
except FileNotFoundError:
    logger.critical("FATAL: persona.txt not found. This file is required to define the bot's behavior. Please create it.")
    exit(1)

conversation_histories = {}
model = genai.GenerativeModel(
    'gemini-1.5-flash',
    generation_config={"max_output_tokens": MAX_OUTPUT_TOKENS}
)

# --- Telethon Client Initialization ---
# The 'userbot.session' file will store your login session so you don't have to log in every time.
# Keep this file secure!
client = TelegramClient('userbot.session', int(API_ID), API_HASH)

@client.on(events.NewMessage(incoming=True))
async def handle_new_message(event):
    """Handles any incoming private message and generates a reply using Gemini."""
    
    logger.info("Got new message.")

    # We only care about private messages, not groups or channels
    if not event.is_private:
        return

    sender = await event.get_sender()
    sender_id = sender.id
    sender_name = sender.first_name

    # --- Safety Checks ---
    # 1. Ignore messages from yourself
    if sender.is_self:
        return
        
    # 2. Ignore messages from whitelisted users
    if sender_id in WHITELISTED_USERS:
        logger.info(f"Ignoring message from whitelisted user: {sender_name} ({sender_id}).")
        return

    # If the checks pass, it's likely a message from an unknown person (potential scammer).
    user_message = event.message.text
    logger.info(f"Received new message from UNKNOWN sender: {sender_name} ({sender_id}): '{user_message}'")

    # Check if we have a conversation history for this user, if not, start one.
    if sender_id not in conversation_histories:
        logger.info(f"Starting new conversation history for user {sender_id}.")
        conversation_histories[sender_id] = model.start_chat(history=[
            {'role': 'user', 'parts': [SYSTEM_PERSONA]},
            {'role': 'model', 'parts': ["This is Dan, who is this?"]}
        ])
    
    try:
        # Mark the message as read and simulate "typing..."
        await event.mark_read()
        async with client.action(sender, 'typing'):
            
            # A random delay to make it look more natural
            typing_delay = random.uniform(20, 40)
            logger.info(f"Simulating typing for {typing_delay:.2f} seconds...")
            await asyncio.sleep(typing_delay)

            # Send the user's message to Gemini and get a response
            chat_session = conversation_histories[sender_id]
            response = await chat_session.send_message_async(user_message)
            bot_reply = response.text

        logger.info(f"Generated Gemini reply for {sender_id}: '{bot_reply}'")

        # Send the bot's reply as a new message, not a direct reply
        await client.send_message(sender, bot_reply)

    except Exception as e:
        logger.error(f"An error occurred while handling message for user {sender_id}: {e}", exc_info=True)
        # In case of an error, we won't send a message to avoid looking broken.

async def main():
    """Main function to start the userbot."""
    # Connect to Telegram
    await client.start()
    logger.info("Client started. Listening for new messages...")

    # Wait until the client is disconnected
    await client.run_until_disconnected()

if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main())
