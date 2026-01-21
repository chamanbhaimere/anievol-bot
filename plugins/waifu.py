import aiohttp
import asyncio
import logging
from typing import Union
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
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

async def show_tag_menu(client: Client, message: Message):
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
    
    menu_msg = await message.reply_text(
        "<b>🎨 Select a Tag to Generate Image:</b>",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    # Delete menu after delay if no interaction
    asyncio.create_task(auto_delete_msg(menu_msg, WAIFU_DELETE_TIME))

async def fetch_and_send_waifu(client: Client, message: Union[Message, CallbackQuery], included_tags=None, is_callback=False):
    """Helper to fetch and send image"""
    params = {"is_nsfw": "false"}
    if included_tags:
        params["included_tags"] = included_tags

    target = message if not is_callback else message.message
    
    if not is_callback:
        status_msg = await target.reply_text("<b>Generating image... 🎨</b>")
    else:
        await message.answer("Generating...")

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
                        
                        if is_callback:
                            await message.edit_message_media(
                                media=InputMediaPhoto(media=image_url, caption=caption),
                                reply_markup=buttons
                            )
                            # Schedule deletion for the edited message
                            asyncio.create_task(auto_delete_msg(message.message, WAIFU_DELETE_TIME))
                        else:
                            sent = await target.reply_photo(photo=image_url, caption=caption, reply_markup=buttons)
                            await status_msg.delete()
                            # Schedule deletion for the new photo
                            asyncio.create_task(auto_delete_msg(sent, WAIFU_DELETE_TIME))
                    else:
                        error_text = "<b>❌ No images found for those tags!</b>"
                        if is_callback: await message.answer(error_text, show_alert=True)
                        else: await status_msg.edit(error_text)
                else:
                    error_text = f"<b>❌ API Error: {response.status}</b>"
                    if is_callback: await message.answer(error_text, show_alert=True)
                    else: await status_msg.edit(error_text)
    except Exception as e:
        logging.error(f"Error fetching waifu: {e}")
        error_text = f"<b>❌ Error:</b> <code>{str(e)}</code>"
        if is_callback: await message.answer(error_text, show_alert=True)
        else: await status_msg.edit(error_text)

@Client.on_callback_query(filters.regex("^regen_waifu_"))
async def regen_waifu_specific_callback(client: Client, query: CallbackQuery):
    tag = query.data.split("_")[-1]
    included_tags = [tag] if tag != "random" else None
    await fetch_and_send_waifu(client, query, included_tags, is_callback=True)

@Client.on_callback_query(filters.regex("^tagwaifu_"))
async def tag_waifu_callback(client: Client, query: CallbackQuery):
    tag = query.data.split("_")[1]
    await fetch_and_send_waifu(client, query, [tag], is_callback=True)

@Client.on_callback_query(filters.regex("^waifu_tag_menu$"))
async def waifu_tag_menu_callback(client: Client, query: CallbackQuery):
    """Switch back to tag menu"""
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
    
    await query.edit_message_caption(
        caption="<b>🎨 Select a Tag to Generate Image:</b>",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    # Reset auto-delete for the menu
    asyncio.create_task(auto_delete_msg(query.message, WAIFU_DELETE_TIME))
