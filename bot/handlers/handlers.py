import datetime
import time

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from apscheduler.triggers.cron import CronTrigger
from asyncpg import UniqueViolationError

from loader import wb_tariffs_db, scheduler, bot, db, async_session
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
    query = "SELECT id FROM users WHERE user_tg_id = $1"
    record = await db.pool.fetchrow(query, user_tg_id)
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
    wb_data_extractor = WBDataExtractor(wb_parser, db, seller_id)
    await wb_data_extractor.insert_products()
    logistics_change_handler = LogisticsInfoProcessor(
        wb_tariffs_db, db, wb_data_extractor, seller_id
    )
    result_info = await logistics_change_handler.return_info()
    if result_info:
        chunked_message = split_message(result_info)
        for chunk in chunked_message:
            await bot.send_message(user_tg_id, chunk)
    await wb_parser.client.close()


@router.message(CommandStart())
async def process_start_command(message: Message):
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
        "А я буду присылать тебе изменение стоимости логистики для твоих товаров, лежащих на складах.\n\n"
        "Отправь просто токен, например: eyJ...iivg, только обычно они очень длинные"
    )
    await message.answer(text=hello_text)


@router.message(F.text.len() >= 200)
async def process_api_token(message: Message):
    api_token = max(message.text.split(" "))
    wb_parser = WBParser(api_token)
    if await wb_parser.check_token():
        await wb_parser.client.close()
        await message.answer(
            text="Спасибо! Теперь я буду присылать тебе изменение стоимости логистики для твоих товаров.\n\n"
            "Сейчас я проверю, будут ли завтра измены коэффициенты на складах.\n\n"
            "Если захочешь отписаться от уведомлений, то напиши мне: Стоп"
        )
        await return_info(message.from_user.id, api_token)
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


@router.message(F.text.lower() == "стоп")
async def process_remove_notifications(message: Message):
    try:
        scheduler.remove_job(str(message.from_user.id))
    finally:
        await message.answer(
        text="Окей, я больше не буду присылать тебе уведомления\n\n "
        "Если захочешь снова получать информацию об изменении логистики, "
        "то отправь мне токен заново"
        )



@router.message()
async def process_other_messages(message: Message):
    text = "Пока я принимаю только API ключ в ответ, а это не очень-то на него похоже"
    await delete_warning(message, text)


# @router.message(F.text.len() >= 200)
# async def process_api_token(message: Message):
#     scheduler.add_job(
#         func=call_master,
#         args=(message.from_user.id, "Токен"),
#         trigger="interval",
#         day=1,
#         id=str(message.from_user.id),
#         next_run_time=datetime.datetime.now() + datetime.timedelta(days=1),
#     )
#     api_token = max(message.text.split(" "))
#     wb_parser = WBParser(api_token)
#     async_session = sessionmaker(
#         engine, expire_on_commit=False, class_=AsyncSession
#     )
#     async with async_session() as session:
#         async with session.begin():
#             if await wb_parser.check_token():
#                 user = await session.sca(
#                     select(User).where(User.user_tg_id == message.from_user.id)
#                 )
#                 try:
#                     new_seller = Seller(
#                         user_id=user.id,
#                         api_token=api_token,
#                         added_at=datetime.datetime.now(),
#                     )
#                     session.add(new_seller)
#                     await session.commit()
#                     seller_id = new_seller.id
#                 except UniqueViolationError:
#                     await session.rollback()
#                     seller = await session.execute(
#                         select(Seller).where(Seller.api_token == api_token)
#                     )
#                     seller_id = seller.scalar_one().id
#                 await message.answer(text=f"cпасибо юзер с айди {seller_id}")
#                 await message.answer(
#                     text="Спасибо! Теперь я буду присылать тебе изменение стоимости логистики для твоих товаров.\n\n"
#                     "Сейчас я проверю будут ли завтра измены коэффициенты на складах.\n\n"
#                     "Если захочешь отписаться от уведомлений, то напиши мне: Стоп"
#                 )
#
#             #     wb_data_extractor = WBDataExtractor(wb_parser, db, seller_id)
#             #     await wb_data_extractor.insert_products()
#             #     logistics_change_handler = LogisticsInfoProcessor(
#             #         wb_tariffs_db, db, wb_data_extractor, seller_id
#             #     )
#             #
#             #     result_info = await logistics_change_handler.return_info()
#             #     chunked_message = split_message(result_info)
#             #     for chunk in chunked_message:
#             #         await message.answer(text=chunk)
#             # else:
#             #     await message.answer(
#             #         text="Wildberries'у не очень понравился этот токен, может быть есть другой?"
#             #     )
#     await wb_parser.client.close()
