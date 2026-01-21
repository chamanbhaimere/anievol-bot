import aiohttp
import asyncio
import logging
import io
from typing import Union
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import WAIFU_DELETE_TIME

# API Endpoint
WAIFU_API_URL = "https://api.waifu.im/search"

# Available SFW Tags
SFW_TAGS = [
    "maid", "waifu", "marin-kitagawa", 
    "mori-calliope", "raiden-shogun", "oppai", 
    "selfies", "uniform", "kamisato-ayaka"
]

async def auto_delete_msg(message: Message, delay: int):
    """Helper to delete a message after a delay"""
    if not message or not delay:
        return
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        logging.debug(f"Auto-delete failed: {e}")

@Client.on_message(filters.command("waifu") & filters.incoming)
async def get_waifu(client: Client, message: Message):
    args = message.text.split(maxsplit=1)
    
    if len(args) > 1 and args[1].lower() == "tags":
        return await show_tag_menu(client, message)

    included_tags = []
    if len(args) > 1:
        included_tags = [tag.strip().lower() for tag in args[1].split(",")]

    await fetch_and_send_waifu(client, message, included_tags)

async def show_tag_menu(client: Client, message: Union[Message, CallbackQuery]):
    """Show interactive tag selection menu"""
    buttons = []
    row = []
    for tag in SFW_TAGS:
        row.append(InlineKeyboardButton(tag.replace("-", " ").title(), callback_data=f"tagwaifu_{tag}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("🎲 Random Waifu", callback_data="regen_waifu_random")])
    
    text = "<b>🎨 Select a Tag to Generate Image:</b>"
    reply_markup = InlineKeyboardMarkup(buttons)

    # Always send a new message for consistency and delete the old one if it was a callback
    if isinstance(message, CallbackQuery):
        await message.answer()
        try: await message.message.delete()
        except: pass
        menu_msg = await message.message.reply_text(text, reply_markup=reply_markup)
    else:
        menu_msg = await message.reply_text(text, reply_markup=reply_markup)
    
    # Schedule auto-delete
    asyncio.create_task(auto_delete_msg(menu_msg, WAIFU_DELETE_TIME))

async def fetch_and_send_waifu(client: Client, message: Union[Message, CallbackQuery], included_tags=None):
    """Helper to fetch and send image using delete-and-resend for maximum reliability"""
    params = {"is_nsfw": "false"}
    if included_tags:
        params["included_tags"] = included_tags

    is_callback = isinstance(message, CallbackQuery)
    target = message.message if is_callback else message
    
    if is_callback:
        await message.answer("Generating...")
    else:
        status_msg = await target.reply_text("<b>Generating image... 🎨</b>")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WAIFU_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "images" in data and data["images"]:
                        image_info = data["images"][0]
                        image_url = image_info["url"]
                        source_url = image_info.get("source", "https://waifu.im")
                        tags_str = ", ".join([t['name'] for t in image_info['tags']])
                        
                        buttons = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔗 Source", url=source_url)],
                            [InlineKeyboardButton("🔄 Another", callback_data=f"regen_waifu_{included_tags[0] if included_tags else 'random'}")],
                            [InlineKeyboardButton("📂 Tag Menu", callback_data="waifu_tag_menu")]
                        ])

                        caption = f"<b>✨ Random Waifu ✨</b>\n\n<b>Tags:</b> <code>{tags_str}</code>"
                        
                        # Download image bytes
                        async with session.get(image_url) as img_resp:
                            if img_resp.status == 200:
                                img_data = await img_resp.read()
                                photo = io.BytesIO(img_data)
                                photo.name = image_url.split("/")[-1]
                                
                                # If it's a callback, delete the old message (photo or menu)
                                if is_callback:
                                    try: await target.delete()
                                    except: pass
                                
                                # Send new photo
                                sent = await target.reply_photo(photo=photo, caption=caption, reply_markup=buttons)
                                
                                # Clean up status message if it exists
                                if not is_callback:
                                    try: await status_msg.delete()
                                    except: pass
                                
                                # Schedule auto-delete for the new photo
                                asyncio.create_task(auto_delete_msg(sent, WAIFU_DELETE_TIME))
                            else:
                                err_text = f"<b>❌ Failed to download (HTTP {img_resp.status})</b>"
                                if is_callback: await message.answer(err_text, show_alert=True)
                                else: await status_msg.edit(err_text)
                    else:
                        err_text = "<b>❌ No images found for those tags!</b>"
                        if is_callback: await message.answer(err_text, show_alert=True)
                        else: await status_msg.edit(err_text)
                else:
                    err_text = f"<b>❌ API Error: {response.status}</b>"
                    if is_callback: await message.answer(err_text, show_alert=True)
                    else: await status_msg.edit(err_text)
    except Exception as e:
        logging.error(f"Error fetching waifu: {e}")
        err_text = f"<b>❌ Critical Error:</b> <code>{str(e)}</code>"
        if is_callback: await message.answer(err_text, show_alert=True)
        else:
            try: await status_msg.edit(err_text)
            except: await target.reply_text(err_text)

@Client.on_callback_query(filters.regex("^regen_waifu_"))
async def regen_waifu_specific_callback(client: Client, query: CallbackQuery):
    tag = query.data.split("_")[-1]
    included_tags = [tag] if tag != "random" else None
    await fetch_and_send_waifu(client, query, included_tags)

@Client.on_callback_query(filters.regex("^tagwaifu_"))
async def tag_waifu_callback(client: Client, query: CallbackQuery):
    tag = query.data.split("_")[1]
    await fetch_and_send_waifu(client, query, [tag])

@Client.on_callback_query(filters.regex("^waifu_tag_menu$"))
async def waifu_tag_menu_callback(client: Client, query: CallbackQuery):
    """Switch back to tag menu"""
    await show_tag_menu(client, query)
