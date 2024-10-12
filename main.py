import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import random
import time
from datetime import datetime, timedelta
import asyncio
import aiohttp

# Bot token'ınızı buraya ekleyin
TOKEN = 'YOUR_BOT_TOKEN'
bot = telebot.TeleBot(TOKEN)

# Zorunlu kanal
REQUIRED_CHANNEL = '@nearowork'

# Veritabanı bağlantısı
conn = sqlite3.connect('coin_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Tabloları oluştur
cursor.execute('''
CREATE TABLE IF NOT EXISTS users 
(user_id INTEGER PRIMARY KEY, username TEXT, balance REAL, last_daily TIMESTAMP, 
 mining_power INTEGER DEFAULT 1, last_mining TIMESTAMP, last_work TIMESTAMP,
 experience INTEGER DEFAULT 0, level INTEGER DEFAULT 1)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions 
(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, 
 type TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS items 
(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, mining_power INTEGER)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_items 
(user_id INTEGER, item_id INTEGER, quantity INTEGER, 
 PRIMARY KEY (user_id, item_id))
''')

conn.commit()

# Örnek eşyaları ekle
cursor.execute("INSERT OR IGNORE INTO items (name, price, mining_power) VALUES (?, ?, ?)", 
               ("Basit Kazıcı", 100, 2))
cursor.execute("INSERT OR IGNORE INTO items (name, price, mining_power) VALUES (?, ?, ?)", 
               ("Gelişmiş Kazıcı", 500, 5))
cursor.execute("INSERT OR IGNORE INTO items (name, price, mining_power) VALUES (?, ?, ?)", 
               ("Süper Kazıcı", 2000, 20))
conn.commit()

# Ana menü için klavye oluştur
def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("💰 Bakiye", callback_data='balance'),
                 InlineKeyboardButton("⚔ Rullet Oyna", callback_data='gamble'))
    keyboard.row(InlineKeyboardButton("⛏ Madencilik", callback_data='mining'),
                 InlineKeyboardButton("💼 Çalış", callback_data='work'))
    keyboard.row(InlineKeyboardButton("🛒 Market", callback_data='market'),
                 InlineKeyboardButton("🏆 Seviye", callback_data='level'))
    keyboard.row(InlineKeyboardButton("🎁 Günlük Bonus", callback_data='daily_bonus'),
                 InlineKeyboardButton("📊 Sıralama", callback_data='leaderboard'))
    keyboard.row(InlineKeyboardButton("🎒 Envanter", callback_data='inventory'),
                 InlineKeyboardButton("📜 İşlem Geçmişi", callback_data='transaction_history'))
    keyboard.row(InlineKeyboardButton("💱 Coin Transfer", callback_data='transfer'),
                 InlineKeyboardButton("🔗 Referans", callback_data='referral'))
    return keyboard

# Kullanıcıyı veritabanına ekle veya güncelle
def update_user(user_id, username):
    cursor.execute('''
    INSERT OR REPLACE INTO users 
    (user_id, username, balance, last_daily, mining_power, last_mining, last_work, experience, level)
    VALUES (?, ?, 
            COALESCE((SELECT balance FROM users WHERE user_id = ?), 0),
            COALESCE((SELECT last_daily FROM users WHERE user_id = ?), NULL),
            COALESCE((SELECT mining_power FROM users WHERE user_id = ?), 1),
            COALESCE((SELECT last_mining FROM users WHERE user_id = ?), NULL),
            COALESCE((SELECT last_work FROM users WHERE user_id = ?), NULL),
            COALESCE((SELECT experience FROM users WHERE user_id = ?), 0),
            COALESCE((SELECT level FROM users WHERE user_id = ?), 1))
    ''', (user_id, username, user_id, user_id, user_id, user_id, user_id, user_id, user_id))
    conn.commit()

# Kanal üyeliğini kontrol et
def check_channel_subscription(user_id):
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except telebot.apihelper.ApiException:
        return False

# Hoş geldin mesajı ve kanal kontrolü
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    update_user(user_id, username)

    if not check_channel_subscription(user_id):
        bot.reply_to(message, f"Merhaba! Botu kullanabilmek için lütfen {REQUIRED_CHANNEL} kanalına katılın ve tekrar /start komutunu kullanın.")
        return

    welcome_message = "Hoş geldiniz, {}! 🎉

CoinMaster Bot'a hoş geldiniz! Burada coin kazanabilir, rullet oynayabilir, madencilik yapabilir ve çok daha fazlasını yapabilirsiniz.

🔑 Ana Özellikler:
• 💰 Coin kazanma ve biriktirme
• 🎲 Rullet oyunları
• ⛏ Madencilik sistemi
• 💼 Çalışma ve para kazanma
• 🛒 Eşya satın alma
• 🏆 Seviye sistemi
• 🎁 Günlük bonuslar
• 📊 Liderlik sıralaması
• 🎒 Envanter yönetimi
• 💱 Coin transferi
• 🔗 Referans sistemi

Hadi başlayalım! Ana menüyü görmek için aşağıdaki butona tıklayın.".format(message.from_user.first_name)
    
    bot.reply_to(message, welcome_message, reply_markup=main_menu_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    if not check_channel_subscription(user_id):
        bot.answer_callback_query(call.id, f"Lütfen önce {REQUIRED_CHANNEL} kanalına katılın.")
        return

    if call.data == 'balance':
        show_balance(call.message)
    elif call.data == 'gamble':
        start_gamble(call.message)
    elif call.data == 'daily_bonus':
        give_daily_bonus(call.message)
    elif call.data == 'leaderboard':
        show_leaderboard(call.message)
    elif call.data == 'mining':
        start_mining(call.message)
    elif call.data == 'work':
        start_work(call.message)
    elif call.data == 'market':
        show_market(call.message)
    elif call.data == 'level':
        show_level(call.message)
    elif call.data == 'inventory':
        show_inventory(call.message)
    elif call.data == 'transaction_history':
        show_transaction_history(call.message)
    elif call.data == 'transfer':
        start_transfer(call.message)
    elif call.data == 'referral':
        send_referral_link(call.message)
    elif call.data.startswith('buy_'):
        item_id = int(call.data.split('_')[1])
        buy_item(call.message, item_id)

def show_balance(message):
    user_id = message.chat.id
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        balance = result[0]
        bot.send_message(user_id, f"Mevcut bakiyeniz: {balance:.2f} coin", reply_markup=main_menu_keyboard())
    else:
        bot.send_message(user_id, "Hesabınız bulunamadı. Lütfen /start komutunu kullanarak başlayın.")

def start_gamble(message):
    user_id = message.chat.id
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result and result[0] > 0:
        bot.send_message(user_id, "Rullet oynamak için bir miktar seçin (1-100):")
        bot.register_next_step_handler(message, gamble)
    else:
        bot.send_message(user_id, "Rullet oynamak için yeterli bakiyeniz yok.", reply_markup=main_menu_keyboard())

def gamble(message):
    try:
        bet = int(message.text)
        if 1 <= bet <= 100:
            user_id = message.from_user.id
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            balance = cursor.fetchone()[0]
            if balance >= bet:
                if random.random() < 0.4:  # %40 kazanma şansı
                    winnings = bet * 2
                    new_balance = balance + bet
                    transaction_type = 'Rullet Kazancı'
                    bot.send_message(user_id, f"Tebrikler! {winnings} coin kazandınız. Yeni bakiyeniz: {new_balance:.2f}", reply_markup=main_menu_keyboard())
                else:
                    new_balance = balance - bet
                    transaction_type = 'Rullet Kaybı'
                    bot.send_message(user_id, f"Üzgünüm, {bet} coin kaybettiniz. Yeni bakiyeniz: {new_balance:.2f}", reply_markup=main_menu_keyboard())
                
                cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, user_id))
                cursor.execute('INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)', 
                               (user_id, bet if transaction_type == 'Rullet Kaybı' else winnings, transaction_type))
                add_experience(user_id, 5)  # Kumar oynamak için deneyim ekle
                conn.commit()
            else:
                bot.send_message(user_id, "Yetersiz bakiye.", reply_markup=main_menu_keyboard())
        else:
            bot.send_message(user_id, "Lütfen 1 ile 100 arasında bir sayı girin.", reply_markup=main_menu_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "Geçersiz giriş. Lütfen bir sayı girin.", reply_markup=main_menu_keyboard())

def give_daily_bonus(message):
    user_id = message.chat.id
    cursor.execute('SELECT balance, last_daily FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        balance, last_daily = result
        now = datetime.now()
        if last_daily is None or now - datetime.fromisoformat(last_daily) > timedelta(days=1):
            bonus = random.randint(50, 200)
            new_balance = balance + bonus
            cursor.execute('UPDATE users SET balance = ?, last_daily = ? WHERE user_id = ?', 
                           (new_balance, now.isoformat(), user_id))
            cursor.execute('INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)', 
                           (user_id, bonus, 'Günlük Bonus'))
            add_experience(user_id, 10)  # Günlük bonus için deneyim ekle
            conn.commit()
            bot.send_message(user_id, f"Günlük bonusunuz: {bonus} coin! Yeni bakiyeniz: {new_balance:.2f}", reply_markup=main_menu_keyboard())
        else:
            next_bonus = datetime.fromisoformat(last_daily) + timedelta(days=1)
            wait_time = next_bonus - now
            hours, remainder = divmod(wait_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            bot.send_message(user_id, f"Bir sonraki bonusunuza {hours} saat {minutes} dakika kaldı.", reply_markup=main_menu_keyboard())
    else:
        bot.send_message(user_id, "Hesabınız bulunamadı. Lütfen /start komutunu kullanarak başlayın.")

def show_leaderboard(message):
    cursor.execute('SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10')
    leaders = cursor.fetchall()
    leaderboard_text = "🏆 En Zengin 10 Kullanıcı 🏆\n\n"
    for idx, (username, balance) in enumerate(leaders, start=1):
        leaderboard_text += f"{idx}. {username}: {balance:.2f} coin\n"
    bot.send_message(message.chat.id, leaderboard_text, reply_markup=main_menu_keyboard())


            # ... (Önceki kod aynen devam ediyor)

def start_mining(message):
    user_id = message.chat.id
    cursor.execute('SELECT mining_power, last_mining FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        mining_power, last_mining = result
        now = datetime.now()
        if last_mining is None or now - datetime.fromisoformat(last_mining) > timedelta(minutes=5):
            earnings = random.uniform(0.1, 0.5) * mining_power
            cursor.execute('UPDATE users SET balance = balance + ?, last_mining = ? WHERE user_id = ?', 
                           (earnings, now.isoformat(), user_id))
            cursor.execute('INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)', 
                           (user_id, earnings, 'Madencilik'))
            add_experience(user_id, 15)  # Madencilik için deneyim ekle
            conn.commit()
            bot.send_message(user_id, f"Madencilik tamamlandı! {earnings:.2f} coin kazandınız.", reply_markup=main_menu_keyboard())
        else:
            next_mining = datetime.fromisoformat(last_mining) + timedelta(minutes=5)
            wait_time = next_mining - now
            minutes, seconds = divmod(wait_time.seconds, 60)
            bot.send_message(user_id, f"Bir sonraki madenciliğe {minutes} dakika {seconds} saniye kaldı.", reply_markup=main_menu_keyboard())
    else:
        bot.send_message(user_id, "Hesabınız bulunamadı. Lütfen /start komutunu kullanarak başlayın.")

def start_work(message):
    user_id = message.chat.id
    cursor.execute('SELECT last_work FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        last_work = result[0]
        now = datetime.now()
        if last_work is None or now - datetime.fromisoformat(last_work) > timedelta(hours=1):
            earnings = random.uniform(10, 50)
            cursor.execute('UPDATE users SET balance = balance + ?, last_work = ? WHERE user_id = ?', 
                           (earnings, now.isoformat(), user_id))
            cursor.execute('INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)', 
                           (user_id, earnings, 'Çalışma'))
            add_experience(user_id, 20)  # Çalışma için deneyim ekle
            conn.commit()
            bot.send_message(user_id, f"Çalışmanız tamamlandı! {earnings:.2f} coin kazandınız.", reply_markup=main_menu_keyboard())
        else:
            next_work = datetime.fromisoformat(last_work) + timedelta(hours=1)
            wait_time = next_work - now
            hours, remainder = divmod(wait_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            bot.send_message(user_id, f"Bir sonraki çalışmanıza {hours} saat {minutes} dakika kaldı.", reply_markup=main_menu_keyboard())
    else:
        bot.send_message(user_id, "Hesabınız bulunamadı. Lütfen /start komutunu kullanarak başlayın.")

def show_market(message):
    user_id = message.chat.id
    cursor.execute('SELECT * FROM items')
    items = cursor.fetchall()
    market_text = "🛒 Market 🛒\n\n"
    keyboard = InlineKeyboardMarkup()
    for item in items:
        item_id, name, price, mining_power = item
        market_text += f"{name} - Fiyat: {price} coin, Madencilik Gücü: +{mining_power}\n"
        keyboard.add(InlineKeyboardButton(f"Satın Al: {name}", callback_data=f'buy_{item_id}'))
    keyboard.add(InlineKeyboardButton("Ana Menü", callback_data='main_menu'))
    bot.send_message(user_id, market_text, reply_markup=keyboard)

def buy_item(message, item_id):
    user_id = message.chat.id
    cursor.execute('SELECT balance, mining_power FROM users WHERE user_id = ?', (user_id,))
    user_result = cursor.fetchone()
    cursor.execute('SELECT name, price, mining_power FROM items WHERE id = ?', (item_id,))
    item_result = cursor.fetchone()
    
    if user_result and item_result:
        balance, current_mining_power = user_result
        item_name, item_price, item_mining_power = item_result
        
        if balance >= item_price:
            new_balance = balance - item_price
            new_mining_power = current_mining_power + item_mining_power
            cursor.execute('UPDATE users SET balance = ?, mining_power = ? WHERE user_id = ?', 
                           (new_balance, new_mining_power, user_id))
            cursor.execute('INSERT OR REPLACE INTO user_items (user_id, item_id, quantity) VALUES (?, ?, COALESCE((SELECT quantity FROM user_items WHERE user_id = ? AND item_id = ?), 0) + 1)', 
                           (user_id, item_id, user_id, item_id))
            cursor.execute('INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)', 
                           (user_id, -item_price, f'Satın Alma: {item_name}'))
            add_experience(user_id, 25)  # Eşya satın alma için deneyim ekle
            conn.commit()
            bot.send_message(user_id, f"{item_name} satın aldınız! Yeni bakiyeniz: {new_balance:.2f} coin, Yeni madencilik gücünüz: {new_mining_power}", reply_markup=main_menu_keyboard())
        else:
            bot.send_message(user_id, "Yetersiz bakiye.", reply_markup=main_menu_keyboard())
    else:
        bot.send_message(user_id, "Bir hata oluştu. Lütfen tekrar deneyin.", reply_markup=main_menu_keyboard())

def show_inventory(message):
    user_id = message.chat.id
    cursor.execute('''
    SELECT i.name, ui.quantity, i.mining_power 
    FROM user_items ui 
    JOIN items i ON ui.item_id = i.id 
    WHERE ui.user_id = ?
    ''', (user_id,))
    items = cursor.fetchall()
    
    if items:
        inventory_text = "🎒 Envanteriniz 🎒\n\n"
        for name, quantity, mining_power in items:
            inventory_text += f"{name} x{quantity} - Madencilik Gücü: +{mining_power}\n"
    else:
        inventory_text = "Envanteriniz boş. Marketten eşya satın alabilirsiniz."
    
    bot.send_message(user_id, inventory_text, reply_markup=main_menu_keyboard())

def show_transaction_history(message):
    user_id = message.chat.id
    cursor.execute('''
    SELECT amount, type, timestamp 
    FROM transactions 
    WHERE user_id = ? 
    ORDER BY timestamp DESC 
    LIMIT 10
    ''', (user_id,))
    transactions = cursor.fetchall()
    
    if transactions:
        history_text = "📜 Son 10 İşlem 📜\n\n"
        for amount, type, timestamp in transactions:
            history_text += f"{timestamp}: {type} - {amount:.2f} coin\n"
    else:
        history_text = "Henüz hiç işlem yapmadınız."
    
    bot.send_message(user_id, history_text, reply_markup=main_menu_keyboard())

def start_transfer(message):
    bot.reply_to(message, "Coin transfer etmek istediğiniz kullanıcının ID'sini girin:")
    bot.register_next_step_handler(message, get_transfer_amount)

def get_transfer_amount(message):
    try:
        recipient_id = int(message.text)
        if recipient_id == message.from_user.id:
            bot.reply_to(message, "Kendinize transfer yapamazsınız.", reply_markup=main_menu_keyboard())
            return
        
        bot.reply_to(message, "Transfer etmek istediğiniz miktarı girin:")
        bot.register_next_step_handler(message, process_transfer, recipient_id)
    except ValueError:
        bot.reply_to(message, "Geçersiz kullanıcı ID'si. Lütfen tekrar deneyin.", reply_markup=main_menu_keyboard())

def process_transfer(message, recipient_id):
    try:
        amount = float(message.text)
        if amount <= 0:
            bot.reply_to(message, "Geçersiz miktar. Lütfen pozitif bir sayı girin.", reply_markup=main_menu_keyboard())
            return
        
        sender_id = message.from_user.id
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (sender_id,))
        sender_balance = cursor.fetchone()[0]
        
        if sender_balance >= amount:
            cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, sender_id))
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, recipient_id))
            cursor.execute('INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)', 
                           (sender_id, -amount, f'Transfer to {recipient_id}'))
            cursor.execute('INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)', 
                           (recipient_id, amount, f'Transfer from {sender_id}'))
            add_experience(sender_id, 10)  # Transfer için deneyim ekle
            conn.commit()
            bot.reply_to(message, f"{amount:.2f} coin başarıyla transfer edildi.", reply_markup=main_menu_keyboard())
            bot.send_message(recipient_id, f"{sender_id} kullanıcısından {amount:.2f} coin aldınız.")
        else:
            bot.reply_to(message, "Yetersiz bakiye.", reply_markup=main_menu_keyboard())
    except ValueError:
        bot.reply_to(message, "Geçersiz miktar. Lütfen bir sayı girin.", reply_markup=main_menu_keyboard())

def send_referral_link(message):
    user_id = message.from_user.id
    referral_link = f"https://t.me/CoinnMasterBot?start={user_id}"
    bot.reply_to(message, f"İşte referans linkiniz: {referral_link}\nBu linki kullanarak arkadaşlarınızı davet edin ve bonus kazanın!")

def give_referral_bonus(referrer_id, new_user_id):
    bonus = 50  # Referans bonusu miktarı
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (bonus, referrer_id))
    cursor.execute('INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)', 
                   (referrer_id, bonus, 'Referans Bonusu'))
    add_experience(referrer_id, 50)  # Referans bonusu için deneyim ekle
    conn.commit()
    bot.send_message(referrer_id, f"Tebrikler! Yeni bir kullanıcı referans linkinizi kullandı. {bonus} coin kazandınız!")

def add_experience(user_id, amount):
    cursor.execute('UPDATE users SET experience = experience + ? WHERE user_id = ?', (amount, user_id))
    cursor.execute('SELECT experience, level FROM users WHERE user_id = ?', (user_id,))
    experience, level = cursor.fetchone()
    
    new_level = level
    while experience >= new_level * 100:
        new_level += 1
    
    if new_level > level:
        cursor.execute('UPDATE users SET level = ? WHERE user_id = ?', (new_level, user_id))
        conn.commit()
        bot.send_message(user_id, f"🎉 Tebrikler! Seviye atladınız. Yeni seviyeniz: {new_level}")

def show_level(message):
    user_id = message.chat.id
    cursor.execute('SELECT experience, level FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        experience, level = result
        next_level_exp = level * 100
        level_text = f"🏆 Mevcut Seviyeniz: {level}\n"
        level_text += f"📊 Deneyim Puanınız: {experience}/{next_level_exp}\n"
        level_text += f"🔜 Bir sonraki seviyeye: {next_level_exp - experience} XP kaldı"
        bot.send_message(user_id, level_text, reply_markup=main_menu_keyboard())
    else:
        bot.send_message(user_id, "Hesabınız bulunamadı. Lütfen /start komutunu kullanarak başlayın.")

# Ana döngü
def main():
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"An error occurred: {e}")
        time.sleep(5)
        main()

if __name__ == '__main__':
    main()