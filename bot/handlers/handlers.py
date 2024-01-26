import datetime
import time

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from asyncpg import UniqueViolationError

from loader import wb_tariffs_db, scheduler, bot, db
from logistics_info_processor import LogisticsInfoProcessor
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from utils import split_message
from wb_data_extractor import WBDataExtractor
from wb_parser import WBParser
from loader import engine
from models import User, Seller

router = Router()
SLEEP_TIME_WARNING = 4


async def delete_warning(message: Message, text: str):
    bot_message = await message.answer(text=text)
    time.sleep(SLEEP_TIME_WARNING)
    await message.delete()
    await bot_message.delete()


async def return_info(user_tg_id: int, api_token: str):
    wb_parser = WBParser(api_token)
    if await wb_parser.check_token():
        query = "SELECT id FROM users WHERE user_tg_id = $1"
        record = await db.pool.fetchrow(query, message.from_user.id)
        user_id = record.get("id")
        try:
            query = "INSERT INTO sellers (user_id, api_token, added_at) VALUES ($1, $2, $3) RETURNING id"
            record = await db.pool.fetchrow(
                query, user_id, api_token, datetime.datetime.today()
            )
        except UniqueViolationError:
            query = "SELECT id FROM sellers WHERE api_token = $1"
            record = await db.pool.fetchrow(query, api_token)
        seller_id = record.get("id")
        await message.answer(
            text="Спасибо! Теперь я буду присылать тебе изменение стоимости логистики для твоих товаров.\n\n"
            "Сейчас я проверю будут ли завтра измены коэффициенты на складах"
        )

        wb_data_extractor = WBDataExtractor(wb_parser, db, seller_id)
        await wb_data_extractor.insert_products()
        logistics_change_handler = LogisticsInfoProcessor(
            wb_tariffs_db, db, wb_data_extractor, seller_id
        )

        result_info = await logistics_change_handler.return_info()
        chunked_message = split_message(result_info)
        for chunk in chunked_message:
            await message.answer(text=chunk)
@router.message(CommandStart())
async def process_start_command(message: Message):
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.user_tg_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                new_user = User(
                    user_tg_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    added_at=datetime.datetime.now(),
                )
                session.add(new_user)
                await session.commit()
    hello_text = (
        "Привет! Я помогу с торговлей на Wildberries.\n Отправь мне в следующем сообщении API-токен, который можно получить в личном кабинете. "
        "А я буду присылать тебе изменение стоимости логистики для твоих товарах, лежащих на складах.\n\n"
        "Отправь просто токен, например: eyJ...iivg, только обычно они очень длинные"
    )
    await message.answer(text=hello_text)

            text="Спасибо! Теперь я буду присылать тебе изменение стоимости логистики для твоих товаров.\n\n"
            "Сейчас я проверю, будут ли завтра измены коэффициенты на складах.\n\n"
            "Если захочешь отписаться от уведомлений, то напиши мне: Стоп"
        )
        scheduler.add_job(
            func=return_info,
            args=(message.from_user.id, api_token),
            trigger="interval",
            days=1,
            id=str(message.from_user.id),
            next_run_time=datetime.datetime.now() + datetime.timedelta(days=1),
        )
    else:
        await message.answer(
            text="Wildberries'у не очень понравился этот токен, может быть есть другой?"
        )


@router.message(F.text.lover() == "стоп")
async def process_remove_notifications(message: Message):
    scheduler.remove_job(str(message.from_user.id))
    await message.answer(
        text="Окей, я больше не буду присылать тебе уведомления\n\n "
        "Если захочешь снова получать информацию об изменении логистики, "
        "то отправь мне токен заново"
    )


@router.message()
async def process_other_messages(message: Message):
    text = "Пока я принимаю только API ключ в ответ, а это не очень-то на него похоже"
    await delete_warning(message, text)


# async def main():
#     await db.create_pool()
#     await wb_tariffs_db.create_pool()
#     await db.create_tables()
#     query = "SELECT api_token FROM sellers WHERE id = $1"
#     record = await db.pool.fetchrow(query, 1)
#     api_token = record.get("api_token")
#     wb_parser = WBParser(api_token)
#     wb_data_extractor = WBDataExtractor(wb_parser, db, 1)
#     await wb_data_extractor.insert_products()
#     logistics_change_handler = LogisticsInfoProcessor(wb_tariffs_db, db, wb_data_extractor, 1)
#     message = await logistics_change_handler.return_info()
#     chunked_message = split_message(message)
#     for chunk in chunked_message:
#         print(chunk)
#     wb_parser.client.close()
# if __name__ == '__main__':
#     asyncio.run(main())
