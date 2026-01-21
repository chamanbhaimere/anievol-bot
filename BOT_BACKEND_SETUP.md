# Bot Backend Setup Guide

This guide explains how to configure your Telegram bot backend (`anievol-bot.onrender.com`) to serve MKV video files compatibly with the React frontend.

---

## Current Issue

Your backend serves URLs like:
```
https://anievol-bot.onrender.com/watch/114/AV_File_1768847733.mkv?hash=AgADvy
```

The React frontend loads this URL in an iframe, which should display a player selection page.

---

## Backend Requirements

### 1. Route Configuration

Your backend needs **two routes**:

#### Route 1: `/watch/<id>/<filename>` - Player Page (HTML)
Returns an HTML page with player selection options.

#### Route 2: `/file/<id>/<filename>` or `/stream/<id>/<filename>` - Video File
Returns the actual video file for streaming/downloading.

---

## Example Implementation (Python/Flask)

```python
from flask import Flask, render_template_string, send_file, request, make_response
import os

app = Flask(__name__)

# HTML Template for Player Page
PLAYER_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AV BOTz - Video Player</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a1a;
            color: #fff;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            text-align: center;
        }
        video {
            width: 100%;
            max-width: 100%;
            border-radius: 8px;
            background: #000;
            margin-bottom: 20px;
        }
        .buttons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }
        .btn {
            padding: 15px 20px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.2s;
        }
        .btn:hover { transform: translateY(-2px); opacity: 0.9; }
        .btn-primary { background: #667eea; color: white; }
        .btn-success { background: #48bb78; color: white; }
        .btn-warning { background: #ed8936; color: white; }
        .btn-info { background: #4299e1; color: white; }
        .file-info {
            background: #2d3748;
            padding: 20px;
            border-radius: 8px;
        }
        .file-info h3 { margin-bottom: 10px; }
        .file-info p { color: #a0aec0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AV BOTz</h1>
        </div>
        
        <!-- Video Player -->
        <video controls crossorigin="anonymous">
            <source src="/file/{{ video_id }}/{{ filename }}?hash={{ hash }}" type="video/mp4">
            Your browser doesn't support video playback.
        </video>
        
        <!-- Player Selection Buttons -->
        <div class="buttons">
            <a href="intent://{{ video_id }}/{{ filename }}#Intent;package=com.mxtech.videoplayer.ad;end" 
               class="btn btn-primary">
                ▶ MX Player
            </a>
            <a href="vlc://{{ video_id }}/{{ filename }}" 
               class="btn btn-success">
                ▶ VLC Player
            </a>
            <a href="/file/{{ video_id }}/{{ filename }}?hash={{ hash }}" 
               class="btn btn-warning">
                ▶ Play It
            </a>
            <a href="/file/{{ video_id }}/{{ filename }}?hash={{ hash }}&download=1" 
               download 
               class="btn btn-info">
                ⬇ Download
            </a>
        </div>
        
        <!-- File Information -->
        <div class="file-info">
            <h3>📄 File Information</h3>
            <p><strong>Name:</strong> {{ filename }}</p>
            <p><strong>Size:</strong> {{ file_size }}</p>
        </div>
    </div>
</body>
</html>
'''

@app.route('/watch/<int:video_id>/<filename>')
def watch_video(video_id, filename):
    """Serve the HTML player page"""
    hash_param = request.args.get('hash', '')
    file_path = get_video_path(video_id, filename)
    
    # Get file size
    file_size = "Unknown"
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        file_size = f"{size_bytes / (1024*1024):.2f} MB"
    
    return render_template_string(
        PLAYER_HTML,
        video_id=video_id,
        filename=filename,
        hash=hash_param,
        file_size=file_size
    )

@app.route('/file/<int:video_id>/<filename>')
def stream_file(video_id, filename):
    """Stream the actual video file"""
    hash_param = request.args.get('hash', '')
    download = request.args.get('download', '0') == '1'
    
    # TODO: Verify hash/authentication here
    # if not verify_hash(video_id, filename, hash_param):
    #     return "Unauthorized", 401
    
    # Get file path from your storage
    file_path = get_video_path(video_id, filename)
    
    if not os.path.exists(file_path):
        return "File not found", 404
    
    # Determine MIME type
    mime_type = 'video/mp4'
    if filename.endswith('.mkv'):
        mime_type = 'video/x-matroska'
    elif filename.endswith('.webm'):
        mime_type = 'video/webm'
    
    # Create response with proper headers
    response = make_response(send_file(
        file_path,
        mimetype=mime_type,
        as_attachment=download,
        download_name=filename if download else None,
        conditional=True  # Enable range requests for seeking
    ))
    
    # CRITICAL: Add CORS headers to allow React app to load in iframe
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Range, Content-Type'
    response.headers['Accept-Ranges'] = 'bytes'
    
    # Allow iframe embedding
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    # Or specifically allow your domain:
    # response.headers['X-Frame-Options'] = 'ALLOW-FROM https://anievol.app'
    
    return response

def get_video_path(video_id, filename):
    """Get the file path for a video"""
    # TODO: Implement your logic to find the file
    # Example:
    base_path = os.getenv('VIDEO_STORAGE_PATH', '/app/videos')
    return os.path.join(base_path, str(video_id), filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

## Critical Configuration Points

### 1. CORS Headers (REQUIRED)

Your bot **must** send these headers to allow iframe embedding:

```python
response.headers['Access-Control-Allow-Origin'] = '*'
response.headers['X-Frame-Options'] = 'ALLOWALL'
```

**Without these headers**, the React app cannot load your player page in an iframe.

### 2. Content-Type Header

Set the correct MIME type for videos:

```python
# For MKV files
'video/x-matroska'

# For MP4 files
'video/mp4'

# For WebM files
'video/webm'
```

### 3. Range Requests (for seeking)

Enable range requests so users can seek in the video:

```python
response.headers['Accept-Ranges'] = 'bytes'
# Use send_file(..., conditional=True) in Flask
```

---

## Testing Your Backend

### 1. Test Player Page

Open in browser:
```
https://anievol-bot.onrender.com/watch/114/test.mkv?hash=AgADvy
```

**Expected**: Should see an HTML page with player buttons (MX Player, VLC, Download, etc.)

### 2. Test Video Streaming

Open in browser:
```
https://anievol-bot.onrender.com/file/114/test.mkv
```

**Expected**: Should start downloading or playing the video file

### 3. Test CORS Headers

Run in browser console on `anievol.app`:
```javascript
fetch('https://anievol-bot.onrender.com/watch/114/test.mkv')
  .then(r => console.log('CORS OK:', r.headers))
  .catch(e => console.error('CORS FAILED:', e));
```

**Expected**: Should not see CORS errors

---

## Integration with React Frontend

Your frontend already has the correct setup:

1. **Firestore `embedId`**:
   ```
   https://anievol-bot.onrender.com/watch/114/AV_File_1768847733.mkv?hash=AgADvy
   ```

2. **React loads it in iframe**:
   ```jsx
   <iframe src={embedId} ... />
   ```

3. **Backend serves player page**:
   - Shows video player
   - Provides download/external player options
   - Streams video on demand

---

## Deployment Checklist

### Pre-Deployment
- [ ] Two routes implemented: `/watch/` and `/file/`
- [ ] CORS headers configured
- [ ] X-Frame-Options allows iframe
- [ ] Range requests enabled
- [ ] Hash verification working (if used)

### Post-Deployment
- [ ] Test `/watch/` route returns HTML page
- [ ] Test `/file/` route streams video
- [ ] Test from React app at `anievol.app`
- [ ] Verify no CORS errors in console
- [ ] Check video plays in iframe

---

## Common Issues & Solutions

### Issue 1: "Refused to display in a frame"
**Cause**: Missing or incorrect `X-Frame-Options` header
**Fix**: Add `X-Frame-Options: ALLOWALL` header

### Issue 2: CORS errors in console
**Cause**: Missing CORS headers
**Fix**: Add `Access-Control-Allow-Origin: *` header

### Issue 3: Video won't seek/skip
**Cause**: Range requests not enabled
**Fix**: Add `Accept-Ranges: bytes` header and use `conditional=True`

### Issue 4: "File not found" errors
**Cause**: Incorrect file path resolution
**Fix**: Check `get_video_path()` logic, verify file exists

---

## Environment Variables

Set these in your Render.com deployment:

```bash
VIDEO_STORAGE_PATH=/app/videos  # Where video files are stored
CORS_ORIGIN=*                    # Or specific domain: https://anievol.app
SECRET_KEY=your-secret-key       # For hash verification
```

---

## Example Telegram Bot Integration

If using Pyrogram or python-telegram-bot:

```python
from telegram import Bot
import os

# When user requests a video
@app.on_message(filters.command("watch"))
async def send_video_link(client, message):
    video_id = 114
    filename = "AV_File_1768847733.mkv"
    hash_value = generate_hash(video_id, filename)  # Your hash logic
    
    # Generate watch URL
    watch_url = f"https://anievol-bot.onrender.com/watch/{video_id}/{filename}?hash={hash_value}"
    
    # Send to user or save to Firestore
    await message.reply_text(f"Watch here: {watch_url}")
```

---

## Next Steps

1. **Implement the routes** in your bot backend
2. **Add CORS headers** to responses
3. **Deploy to Render**
4. **Test** by visiting the watch URL
5. **Verify** it loads correctly in the React app

Once deployed, your React app will automatically work with the bot backend! 🚀
