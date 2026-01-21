import aiohttp
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# API Endpoint
WAIFU_API_URL = "https://api.waifu.im/search"

@Client.on_message(filters.command("waifu") & filters.incoming)
async def get_waifu(client: Client, message: Message):
    """
    Fetch a random anime image from waifu.im
    Usage: /waifu [tag]
    """
    # Parse tags from message
    args = message.text.split(maxsplit=1)
    included_tags = []
    if len(args) > 1:
        included_tags = [tag.strip().lower() for tag in args[1].split(",")]

    params = {
        "is_nsfw": "false",  # Default to SFW
    }
    
    if included_tags:
        params["included_tags"] = included_tags

    status_msg = await message.reply_text("<b>Generating image... 🎨</b>")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WAIFU_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "images" in data and data["images"]:
                        image_info = data["images"][0]
                        image_url = image_info["url"]
                        source_url = image_info.get("source", "https://waifu.im")
                        dominant_color = image_info.get("dominant_color", "#FFFFFF")
                        
                        # Prepare buttons
                        buttons = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔗 Source", url=source_url)],
                            [InlineKeyboardButton("🔄 Another", callback_data="regen_waifu")]
                        ])

                        await message.reply_photo(
                            photo=image_url,
                            caption=f"<b>✨ Random Waifu ✨</b>\n\n<b>Tags:</b> <code>{', '.join([t['name'] for t in image_info['tags']])}</code>",
                            reply_markup=buttons
                        )
                        await status_msg.delete()
                    else:
                        await status_msg.edit("<b>❌ No images found for those tags!</b>")
                else:
                    await status_msg.edit(f"<b>❌ API Error: {response.status}</b>")
    except Exception as e:
        logging.error(f"Error fetching waifu: {e}")
        await status_msg.edit(f"<b>❌ Something went wrong:</b> <code>{str(e)}</code>")

@Client.on_callback_query(filters.regex("^regen_waifu$"))
async def regen_waifu_callback(client: Client, query):
    """Regenerate a random waifu image on button click"""
    # Simply call the same logic or send a new /waifu command
    # For simplicity, we'll just trigger the same API call
    params = {"is_nsfw": "false"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WAIFU_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "images" in data and data["images"]:
                        image_info = data["images"][0]
                        image_url = image_info["url"]
                        source_url = image_info.get("source", "https://waifu.im")
                        
                        buttons = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔗 Source", url=source_url)],
                            [InlineKeyboardButton("🔄 Another", callback_data="regen_waifu")]
                        ])

                        await query.message.edit_media(
                            media=dict(
                                type="photo",
                                media=image_url,
                                caption=f"<b>✨ Random Waifu ✨</b>\n\n<b>Tags:</b> <code>{', '.join([t['name'] for t in image_info['tags']])}</code>"
                            ),
                            reply_markup=buttons
                        )
                    else:
                        await query.answer("❌ No images found!", show_alert=True)
                else:
                    await query.answer(f"❌ API Error: {response.status}", show_alert=True)
    except Exception as e:
        logging.error(f"Error in regen_waifu_callback: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
