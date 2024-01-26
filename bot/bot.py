import asyncio
import logging

from aiogram import Dispatcher

from handlers import handlers
from loader import bot, dp, wb_tariffs_db, scheduler, db

logger = logging.getLogger(__name__)


async def shutdown(dispatcher: Dispatcher):
    await dispatcher.storage.close()
    logger.info("Storage closed")
    await dispatcher.storage.wait_closed()


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d #%(levelname)-8s "
        "[%(asctime)s] - %(name)s - %(message)s",
    )

    logger.info("Starting bot")
    await db.create_pool()
    await wb_tariffs_db.create_pool()

    logger.info("Database is created")
    dp.include_router(handlers.router)

    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, on_shutdown=shutdown)


if __name__ == "__main__":
    asyncio.run(main())
