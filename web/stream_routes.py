import re, math, logging, secrets, time, mimetypes
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from info import *
from web.server import multi_clients, work_loads, Webavbot
from web.server.exceptions import FIleNotFound, InvalidHash
from web.utils.custom_dl import ByteStreamer
from utils import get_readable_time
from web.utils import StartTime, __version__
from web.utils.render_template import render_page

routes = web.RouteTableDef()
class_cache = {}

@routes.get("/", allow_head=True)
async def root_route_handler(_):
    return web.json_response({
        "server_status": "running",
        "uptime": get_readable_time(time.time() - StartTime),
        "telegram_bot": "@" + BOT_USERNAME,
        "connected_bots": len(multi_clients),
        "loads": {
            "bot" + str(i + 1): load
            for i, (_, load) in enumerate(
                sorted(work_loads.items(), key=lambda x: x[1], reverse=True)
            )
        },
        "version": __version__,
    })

@routes.get(r"/watch/{id:\d+}/{filename}", allow_head=True)
async def watch_file_handler(request: web.Request):
    """Serve HTML player page for file-based URLs"""
    return await render_watch_response(request, is_embed=False)

@routes.get(r"/embed/{id:\d+}/{filename}", allow_head=True)
async def embed_file_handler(request: web.Request):
    """Serve minimalist embed player for file-based URLs"""
    return await render_watch_response(request, is_embed=True)

async def render_watch_response(request: web.Request, is_embed: bool):
    try:
        video_id = int(request.match_info["id"])
        secure_hash = request.rel_url.query.get("hash", "")
        
        # Render the player page with file info
        html_content = await render_page(video_id, secure_hash, is_embed=is_embed)
        
        # Create response with CORS headers for iframe embedding
        response = web.Response(text=html_content, content_type="text/html")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["X-Frame-Options"] = "ALLOWALL"
        
        return response
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except Exception as e:
        logging.critical(f"Error in render_watch_response: {e}")
        return web.Response(status=500, text=str(e))

@routes.get(r"/file/{id:\d+}/{filename}", allow_head=True)
async def file_stream_handler(request: web.Request):
    """Stream video file for file-based URLs with download support"""
    try:
        video_id = int(request.match_info["id"])
        filename = request.match_info["filename"]
        secure_hash = request.rel_url.query.get("hash", "")
        download = request.rel_url.query.get("download", "0") == "1"
        
        # Stream the file
        return await media_streamer(request, video_id, secure_hash, download)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except Exception as e:
        logging.critical(f"Error in file_stream_handler: {e}")
        return web.Response(status=500, text=str(e))

@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def stream_watch_handler(request: web.Request):
    return await render_stream_response(request, is_embed=False)

@routes.get(r"/embed/{path:\S+}", allow_head=True)
async def stream_embed_handler(request: web.Request):
    return await render_stream_response(request, is_embed=True)

async def render_stream_response(request: web.Request, is_embed: bool):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")
            
        html_content = await render_page(id, secure_hash, is_embed=is_embed)
        
        response = web.Response(text=html_content, content_type="text/html")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["X-Frame-Options"] = "ALLOWALL"
        
        return response
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        return web.Response(status=400, text="Bad Request")
    except Exception as e:
        logging.critical(e)
        return web.Response(status=500, text=str(e))

@routes.get(r"/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")
        return await media_streamer(request, id, secure_hash)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        return web.Response(status=400, text="Bad Request")
    except Exception as e:
        logging.critical(e)
        return web.Response(status=500, text=str(e))

async def media_streamer(request: web.Request, id: int, secure_hash: str, download: bool = False):
    range_header = request.headers.get("Range", None)

    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]

    if MULTI_CLIENT:
        logging.info(f"📡 Client {index} is now serving: {request.remote}")

    tg_connect = class_cache.get(faster_client) or ByteStreamer(faster_client)
    class_cache[faster_client] = tg_connect

    file_id = await tg_connect.get_file_properties(id)

    if file_id.unique_id[:6] != secure_hash:
        raise InvalidHash

    file_size = file_id.file_size

    if range_header:
        try:
            match = re.match(r"bytes=(\d+)-(\d*)", range_header)
            from_bytes = int(match.group(1))
            until_bytes = int(match.group(2)) if match.group(2) else file_size - 1
        except Exception:
            return web.Response(status=400, text="Invalid Range header")
    else:
        from_bytes = 0
        until_bytes = file_size - 1

    # Validate range
    if until_bytes >= file_size or from_bytes < 0 or until_bytes < from_bytes:
        return web.Response(
            status=416,
            text="416: Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"}
        )

    # Setup stream vars
    chunk_size = 1024 * 1024
    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
    req_length = until_bytes - from_bytes + 1

    # Determine MIME type with better MKV support
    mime_type = file_id.mime_type or "application/octet-stream"
    file_name = file_id.file_name or f"{secrets.token_hex(2)}.bin"
    
    # Override MIME type for MKV files
    if file_name.lower().endswith('.mkv'):
        mime_type = 'video/x-matroska'
    elif file_name.lower().endswith('.webm'):
        mime_type = 'video/webm'
    elif file_name.lower().endswith('.mp4'):
        mime_type = 'video/mp4'

    response = web.StreamResponse(
        status=206 if range_header else 200,
        reason="Partial Content" if range_header else "OK",
        headers={
            "Content-Type": mime_type,
            "Content-Length": str(req_length),
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Disposition": f'attachment; filename="{file_name}"' if download else f'inline; filename="{file_name}"',
            "Accept-Ranges": "bytes",
            # CORS headers to allow iframe embedding from React app
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type",
            # Allow iframe embedding
            "X-Frame-Options": "ALLOWALL",
        }
    )

    await response.prepare(request)

    try:
        async for chunk in tg_connect.yield_file(
            file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
        ):
            await response.write(chunk)
    except Exception as e:
        logging.exception(f"Error streaming file {file_id.file_unique_id}: {e}")
    finally:
        await response.write_eof()

    return response
