from aiogram import Bot, Dispatcher
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import create_async_engine

from config_data.config import load_config
from database import Database

config = load_config(path=None)
bot = Bot(token=config.tg_bot.token, parse_mode="Markdown")
sentry_url = config.sentry_url.url
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
database_url = f"postgresql+asyncpg://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}"
engine = create_async_engine(database_url)

jobstores_url = (
    f"postgresql://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}"
)
jobstores = {"default": SQLAlchemyJobStore(url=jobstores_url)}
executors = {
    "default": AsyncIOExecutor(),
}
scheduler = AsyncIOScheduler(jobstores=jobstores, executors=executors)

dp = Dispatcher()
