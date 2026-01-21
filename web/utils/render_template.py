import jinja2
import aiofiles
import os
import urllib.parse
import logging
import aiohttp
from web.utils.Template import avbotz_template
from info import *
from web.server import Webavbot
from utils import get_size
from web.utils.file_properties import get_file_ids
from web.server.exceptions import InvalidHash

# Dont Remove My Credit @AV_BOTz_UPDATE 
# This Repo Is By @BOT_OWNER26 
# For Any Kind Of Error Ask Us In Support Group @AV_SUPPORT_GROUP

async def render_page(id: str, secure_hash: str, src: str = None, is_embed: bool = False) -> str:
    # Step 1: Fetch Telegram file and metadata
    try:
        file = await Webavbot.get_messages(int(BIN_CHANNEL), int(id))
        file_data = await get_file_ids(Webavbot, int(BIN_CHANNEL), int(id))
    except Exception as e:
        logging.error(f"Error fetching file info: {e}")
        raise

    # Step 2: Validate secure_hash
    if file_data.unique_id[:6] != secure_hash:
        logging.debug(f"link hash: {secure_hash} - {file_data.unique_id[:6]}")
        logging.debug(f"Invalid hash for message with - ID {id}")
        raise InvalidHash

    # Step 3: Construct file URL
    if not URL.endswith("/"):
        url_base = URL + "/"
    else:
        url_base = URL

    src = urllib.parse.urljoin(url_base, f"{id}?hash={secure_hash}")

    # Step 4: Determine file tag and get size
    tag = file_data.mime_type.split("/")[0].strip()
    file_size = get_size(file_data.file_size)

    if is_embed:
        template_file = os.path.join("web", "template", "embed.html")
    elif tag in ["video", "audio"]:
        template_file = os.path.join("web", "template", "webav.html")
    else:
        template_file = os.path.join("web", "template", "dl.html")
        # Recalculate file size from URL header if downloadable file
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(src) as u:
                    if u.status == 200:
                        content_length = u.headers.get("Content-Length")
                        file_size = get_size(int(content_length)) if content_length else "Unknown"
                    else:
                        logging.warning(f"Failed to fetch size: Status {u.status}")
                        file_size = "Unknown"
        except Exception as e:
            logging.error(f"Failed to fetch file size from URL: {e}")
            file_size = "Unknown"

    # Step 5: Read the template file asynchronously
    try:
        async with aiofiles.open(template_file, mode='r') as f:
            content = await f.read()
        template = jinja2.Template(content)
    except Exception as e:
        logging.error(f"Error reading template: {e}")
        return "Template Error"

    # Step 6: Prepare file name safely
    file_name = file_data.file_name.replace("_", " ") if file_data.file_name else f"AV_File_{id}.mkv"

    # Step 7: Render template with values
    return template.render(
        file_name=file_name,
        file_url=src,
        file_size=file_size,
        file_extension=file_data.file_name.split(".")[-1].lower() if file_data.file_name else "mkv",
        file_unique_id=file_data.unique_id,
        template_ne=avbotz_template.NAME,
        disclaimer=avbotz_template.DISCLAIMER,
        report_link=avbotz_template.REPORT_LINK,
        colours=avbotz_template.COLOURS,
                                    )
# Dont Remove My Credit @AV_BOTz_UPDATE 
# This Repo Is By @BOT_OWNER26 
# For Any Kind Of Error Ask Us In Support Group @AV_SUPPORT_GROUP
