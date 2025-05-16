# rss-news-bot

# Telegram-бот для RSS-новостей
Бот, который собирает новости из RSS-лент и отправляет их в Telegram. Поддерживает управление подписками и автоматическую отправку.

## Возможности
- Подписка на RSS-ленты: `/subscribe <название> <url>`
- Отписка: `/unsubscribe <название>`
- Список подписок: `/list`
- Получение новостей: `/news`
- Настройка расписания: `/schedule <минуты>`

## Технологии
- Python, aiogram, feedparser, SQLite, APScheduler

## Установка
1. Клонируйте репозиторий: `git clone https://github.com/yourusername/rss-news-bot`
2. Создайте виртуальное окружение: `python -m venv venv`
3. Активируйте: `source venv/bin/activate` (Windows: `venv\Scripts\activate`)
4. Установите зависимости: `pip install -r requirements.txt`
5. Укажите токен бота в `config.py`
6. Запустите: `python bot.py`

## Примечания
- Получите токен бота у @BotFather.
- База данных SQLite (`subscriptions.db`) создаётся автоматически.
