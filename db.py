import sqlite3

def init_db():
    """Инициализирует базу данных с таблицами subscriptions и last_news."""
    conn = sqlite3.connect('subscriptions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                 (chat_id INTEGER, feed_name TEXT, feed_url TEXT, UNIQUE(chat_id, feed_name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS last_news
                 (feed_url TEXT, entry_id TEXT, timestamp REAL, UNIQUE(feed_url, entry_id))''')
    conn.commit()
    conn.close()

def add_subscription(chat_id, feed_name, feed_url):
    """Добавляет новую подписку в таблицу subscriptions."""
    conn = sqlite3.connect('subscriptions.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO subscriptions (chat_id, feed_name, feed_url) VALUES (?, ?, ?)',
              (chat_id, feed_name, feed_url))
    conn.commit()
    conn.close()

def remove_subscription(chat_id, feed_name):
    """Удаляет подписку по chat_id и feed_name."""
    conn = sqlite3.connect('subscriptions.db')
    c = conn.cursor()
    c.execute('DELETE FROM subscriptions WHERE chat_id = ? AND feed_name = ?', (chat_id, feed_name))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_subscriptions(chat_id):
    """Возвращает словарь подписок для chat_id."""
    conn = sqlite3.connect('subscriptions.db')
    c = conn.cursor()
    c.execute('SELECT feed_name, feed_url FROM subscriptions WHERE chat_id = ?', (chat_id,))
    result = c.fetchall()
    conn.close()
    return {row[0]: row[1] for row in result}

def get_all_subscriptions():
    """Возвращает словарь всех подписок, сгруппированных по chat_id."""
    conn = sqlite3.connect('subscriptions.db')
    c = conn.cursor()
    c.execute('SELECT chat_id, feed_name, feed_url FROM subscriptions')
    result = c.fetchall()
    conn.close()
    subscriptions = {}
    for chat_id, feed_name, feed_url in result:
        if chat_id not in subscriptions:
            subscriptions[chat_id] = {}
        subscriptions[chat_id][feed_name] = feed_url
    return subscriptions

def add_news_entry(feed_url, entry_id, timestamp):
    """Добавляет запись о новости в таблицу last_news."""
    conn = sqlite3.connect('subscriptions.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO last_news (feed_url, entry_id, timestamp) VALUES (?, ?, ?)',
              (feed_url, entry_id, timestamp))
    conn.commit()
    conn.close()

def is_new_entry(feed_url, entry_id):
    """Проверяет, является ли новость новой (отсутствует в last_news)."""
    conn = sqlite3.connect('subscriptions.db')
    c = conn.cursor()
    c.execute('SELECT 1 FROM last_news WHERE feed_url = ? AND entry_id = ?', (feed_url, entry_id))
    result = c.fetchone()
    conn.close()
    return result is None