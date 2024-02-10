import asyncio
import datetime
import time

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from apscheduler.jobstores.base import ConflictingIdError
from apscheduler.triggers.cron import CronTrigger
from jwt import DecodeError

from loader import wb_tariffs_db, scheduler, bot, db, async_session
from logistics_info_processor import LogisticsInfoProcessor
from sqlalchemy import select, text, func
from sqlalchemy.dialects.postgresql import insert
from utils import split_message
from wb_data_extractor import WBDataExtractor
from wb_parser import WBParser
from models import User, Seller
from wb_token import WildberriesToken

from utils import create_inline_kb

router = Router()
SLEEP_TIME_WARNING = 4
TIME_LIST = [
    "07:00",
    "08:00",
    "09:00",
    "10:00",
    "11:00",
    "12:00",
    "13:00",
    "14:00",
    "15:00",
    "16:00",
    "17:00",
    "18:00",
    "19:00",
    "20:00",
    "21:00",
    "22:00",
]


async def delete_warning(message: Message, text: str):
    bot_message = await message.answer(text=text)
    time.sleep(SLEEP_TIME_WARNING)
    await message.delete()
    await bot_message.delete()


async def return_info(seller_id: int, api_token: str) -> str | None:
    wb_parser = WBParser(api_token)
    wb_data_extractor = WBDataExtractor(wb_parser, db, seller_id)
    await wb_data_extractor.insert_products()
    logistics_change_handler = LogisticsInfoProcessor(
        wb_tariffs_db, db, wb_data_extractor, seller_id
    )
    result_info = await logistics_change_handler.return_info()
    if result_info:
        async with async_session() as session:
            result = await session.execute(
                select(User).join(User.sellers).where(Seller.id == seller_id)
            )
            user_tg_id = result.scalars().first().user_tg_id
        chunked_message = split_message(result_info)
        for chunk in chunked_message:
            await bot.send_message(user_tg_id, chunk)
    await wb_parser.client.close()
    return result_info


@router.message(CommandStart())
async def process_start_command(message: Message):
    async with async_session() as session:
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
    error_text = (
        "Wildberries'у не очень понравился этот токен, может быть есть другой?"
    )
    try:
        wb_token_check = WildberriesToken(api_token)
        if not wb_token_check.is_expired():
            async with async_session() as session:
                user = await session.execute(
                    select(User).where(User.user_tg_id == message.from_user.id)
                )
                user = user.scalar_one()
                stmt = (
                    insert(Seller)
                    .values(
                        user_id=user.id,
                        api_token=api_token,
                        added_at=datetime.datetime.now(),
                    )
                    .on_conflict_do_update(
                        constraint="user_token_key",
                        set_={"updated_at": datetime.datetime.now()},
                    )
                )
                await session.execute(stmt)
                await session.commit()
            time_keyboard = create_inline_kb(4, *TIME_LIST)
            await message.answer(
                text="Выбери время, в которое ты хочешь получать уведомления. Время указано по московскому часовому поясу.",
                reply_markup=time_keyboard,
            )
        else:
            await message.answer(text=error_text)
    except DecodeError:
        await message.answer(text=error_text)


@router.callback_query(F.data.in_(TIME_LIST))
async def process_time(callback: CallbackQuery):
    selected_time = datetime.datetime.strptime(callback.data, "%H:%M").time()
    moscow_timezone = datetime.timezone(datetime.timedelta(hours=3))
    notification_time = datetime.datetime.combine(
        datetime.datetime.utcnow().date(), selected_time
    )
    notification_time = notification_time.replace(
        tzinfo=datetime.timezone.utc
    ).astimezone(moscow_timezone)
    notification_time += datetime.timedelta(days=1)
    await callback.message.edit_text(
        text=f"Спасибо! Теперь я буду присылать тебе изменение стоимости логистики для твоих товаров.\n\n"
        f"При наличии изменений в тарифах, уведомления будут приходить в {selected_time.strftime('%H:%M')}\n\n"
        "Сейчас я проверю, будут ли завтра измены коэффициенты на складах.\n\n"
        "Если захочешь отписаться от уведомлений, то напиши мне: Стоп"
    )
    async with async_session() as session:
        stmt = (
            select(Seller)
            .join(Seller.user)
            .order_by(func.coalesce(Seller.updated_at, Seller.added_at).desc())
            .where(User.user_tg_id == callback.from_user.id)
        )
        result = await session.execute(stmt)
        seller = result.scalars().first()
        await asyncio.sleep(5)
        result = await return_info(seller.id, seller.api_token)
        if not result:
            await callback.message.answer(
                text="Я все проверил, завтра изменения тарифов не планируются"
            )
        try:
            scheduler.add_job(
                func=return_info,
                args=(seller.id, seller.api_token),
                trigger=CronTrigger(
                    hour=selected_time.hour,
                    minute=selected_time.minute,
                    timezone=moscow_timezone,
                ),
                id=str(seller.id),
                next_run_time=notification_time,
            )
        except ConflictingIdError:
            scheduler.reschedule_job(
                str(seller.id),
                trigger=CronTrigger(
                    hour=selected_time.hour,
                    minute=selected_time.minute,
                    timezone=moscow_timezone,
                ),
                next_run_time=notification_time,
            )


@router.message(F.text.lower() == "стоп")
async def process_remove_notifications(message: Message):
    async with async_session() as session:
        stmt = (
            select(Seller)
            .join(Seller.user)
            .where(User.user_tg_id == message.from_user.id)
        )
        result = await session.execute(stmt)
        sellers = result.scalars()
        query = "SELECT id FROM apscheduler_jobs"
        result = await session.execute(text(query))
        jobs_id = result.scalars().all()
        sellers_dict = {}
        for seller in sellers:
            if str(seller.id) in jobs_id:
                sellers_dict[str(seller.id)] = datetime.datetime.strftime(
                    seller.added_at, "%d.%m.%Y %H:%M"
                )
        if len(sellers_dict) > 1:
            token_keyboard = create_inline_kb(2, **sellers_dict)
            await message.answer(
                text=(
                    "У тебя несколько токенов, выбери тот, у которого ты хочешь остановить уведомления. "
                    "Указаны даты добавления токенов"
                ),
                reply_markup=token_keyboard,
            )
        elif len(sellers_dict) == 1:
            try:
                scheduler.remove_job(*sellers_dict)
            finally:
                await message.answer(
                    text="Окей, я больше не буду присылать тебе уведомления\n\n "
                    "Если захочешь снова получать информацию об изменении логистики, "
                    "то отправь мне токен заново"
                )
        else:
            await message.answer(
                text="У тебя пока нет добавленных токенов, поэтому я не могу присылать тебе уведомления"
            )


@router.callback_query()
async def process_remove_notification(callback: CallbackQuery):
    seller_id = callback.data
    try:
        scheduler.remove_job(str(seller_id))
    finally:
        await callback.message.edit_text(
            text="Окей, я больше не буду присылать тебе уведомления\n\n "
            "Если захочешь снова получать информацию об изменении логистики, "
            "то отправь мне токен заново"
        )


@router.message()
async def process_other_messages(message: Message):
    text = "Пока я принимаю только API ключ в ответ, а это не очень-то на него похоже"
    await delete_warning(message, text)
