from aiogram import Bot, Dispatcher

from config_data.config import load_config
from database import Database

config = load_config(path=None)
bot = Bot(token=config.tg_bot.token, parse_mode="Markdown")
db = Database(
    name=config.db.postgres_db,
    user=config.db.postgres_user,
    password=config.db.postgres_password,
    host=config.db.db_host,
    port=config.db.db_port,
)
wb_tariffs_db = Database(
    name=config.wb_tariffs_db.postgres_db,
    user=config.wb_tariffs_db.postgres_user,
    password=config.wb_tariffs_db.postgres_password,
    host=config.wb_tariffs_db.db_host,
    port=config.wb_tariffs_db.db_port,
)
dp = Dispatcher(
    # storage=storage
)
