import asyncio
import signal
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import config
import db
import rss_parser
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
import logging
import feedparser

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=config.TOKEN)
dp = Dispatcher()
scheduler = None
stopping = False

# Обработчик сигнала завершения
def shutdown(signum, frame):
    global stopping
    if not stopping:
        logger.info("Получен сигнал завершения (Ctrl+C)...")
        stopping = True
        asyncio.create_task(stop_bot())

async def stop_bot():
    """Останавливает бота, планировщик и закрывает сессии."""
    global scheduler, stopping
    if not stopping:
        return

    logger.info("Остановка бота...")
    
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Планировщик остановлен")
    
    await dp.stop_polling()
    logger.info("Polling остановлен")
    
    await asyncio.sleep(1)
    
    await bot.session.close()
    logger.info("Сессия бота закрыта")
    
    loop = asyncio.get_event_loop()
    tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
    logger.info("Бот полностью остановлен")

# Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    """Отправляет приветственное сообщение с описанием команд."""
    chat_id = message.chat.id
    db.init_db()
    await message.reply(
        "Привет! Я бот для управления новостями из RSS.\n"
        "Команды:\n"
        "/subscribe <название> <url> — добавить RSS-канал\n"
        "/unsubscribe <название> — удалить канал\n"
        "/list — список подписок\n"
        "/news — последние новости\n"
        "/schedule <минуты> — настроить интервал автоотправки"
    )

# Команда /subscribe
@dp.message(Command("subscribe"))
async def subscribe(message: types.Message):
    """Добавляет новую RSS-подписку после проверки URL и лимита."""
    chat_id = message.chat.id
    args = message.text.split(maxsplit=2)
    if len(args) != 3:
        await message.reply("Укажи название и URL: /subscribe <название> <url>")
        return
    name, url = args[1], args[2]
    subscriptions = db.get_subscriptions(chat_id)
    if len(subscriptions) >= 10:
        await message.reply("Достигнут лимит подписок (10). Удалите одну с помощью /unsubscribe.")
        return
    feed = feedparser.parse(url)
    if feed.bozo or not feed.entries:
        await message.reply("Невалидный RSS-URL. Проверьте ссылку.")
        return
    db.add_subscription(chat_id, name, url)
    await message.reply(f"Подписка на '{name}' добавлена!")

# Команда /unsubscribe
@dp.message(Command("unsubscribe"))
async def unsubscribe(message: types.Message):
    """Удаляет подписку по названию."""
    chat_id = message.chat.id
    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        await message.reply("Укажи название: /unsubscribe <название>")
        return
    name = args[1]
    if db.remove_subscription(chat_id, name):
        await message.reply(f"Подписка на '{name}' удалена!")
    else:
        await message.reply("Такой подписки нет.")

# Команда /list
@dp.message(Command("list"))
async def list_subscriptions(message: types.Message):
    """Показывает список подписок пользователя."""
    chat_id = message.chat.id
    subscriptions = db.get_subscriptions(chat_id)
    if subscriptions:
        response = "Ваши подписки:\n" + "\n".join([f"- {name}: {url}" for name, url in subscriptions.items()])
    else:
        response = "У вас нет подписок."
    await message.reply(response)

# Команда /news
@dp.message(Command("news"))
async def news(message: types.Message):
    """Отправляет последние новости из подписанных RSS-лент."""
    chat_id = message.chat.id
    subscriptions = db.get_subscriptions(chat_id)
    if not subscriptions:
        await message.reply("Вы не подписаны ни на один канал.")
        return
    for name, url in subscriptions.items():
        news_list = rss_parser.fetch_news(url)
        if news_list:
            for item in news_list:
                if len(item) > 4093:
                    item = item[:4093] + "..."
                try:
                    await message.reply(item, parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Ошибка при отправке новости: {e}, текст: {item}")
                    await message.reply(item, parse_mode=None)
        else:
            await message.reply(f"Нет новых новостей в '{name}'.")

# Команда /schedule
@dp.message(Command("schedule"))
async def set_schedule(message: types.Message):
    """Настраивает интервал автоматической отправки новостей."""
    args = message.text.split(maxsplit=1)
    if len(args) != 2 or not args[1].isdigit():
        await message.reply("Укажи интервал в минутах: /schedule <минуты>")
        return
    minutes = int(args[1])
    if minutes < 1:
        await message.reply("Интервал должен быть не менее 1 минуты.")
        return
    global scheduler
    scheduler.reschedule_job('send_news', trigger='interval', minutes=minutes)
    await message.reply(f"Интервал обновления установлен: {minutes} минут")

# Автоматическая отправка новостей
async def send_news():
    """Отправляет новости всем подписчикам по расписанию."""
    all_subscriptions = db.get_all_subscriptions()
    for chat_id, feeds in all_subscriptions.items():
        for name, url in feeds.items():
            news_list = rss_parser.fetch_news(url)
            if news_list:
                for item in news_list:
                    if len(item) > 4093:
                        item = item[:4093] + "..."
                    try:
                        await bot.send_message(chat_id, item, parse_mode="Markdown")
                    except Exception as e:
                        logger.error(f"Ошибка при автоотправке новости: {e}, текст: {item}")
                        await bot.send_message(chat_id, item, parse_mode=None)

# Основная функция
async def main():
    """Запускает бота и планировщик."""
    global scheduler
    scheduler = AsyncIOScheduler(timezone=timezone('Europe/Moscow'))
    scheduler.add_job(send_news, 'interval', seconds=1800, id='send_news')
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(stop_bot())
        loop.close()