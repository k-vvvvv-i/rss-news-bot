import feedparser
import time
import db

def escape_markdown(text):
    """Экранирует специальные символы Markdown для безопасной отправки в Telegram."""
    special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def fetch_news(feed_url):
    """Парсит RSS-ленту и возвращает список новых новостей в формате Markdown."""
    news = []
    feed = feedparser.parse(feed_url)
    if feed.bozo:  # Проверка на ошибки парсинга
        return news
    for entry in feed.entries[:5]:  # Берем последние 5 новостей
        entry_id = entry.get('id', entry.link)
        if db.is_new_entry(feed_url, entry_id):
            title = escape_markdown(entry.title)
            link = entry.link
            news.append(f"*{title}*\n{link}")
            db.add_news_entry(feed_url, entry_id, time.time())
    return news