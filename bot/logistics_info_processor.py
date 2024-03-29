import datetime
import logging
from typing import Any

from database import Database
from wb_data_extractor import WBDataExtractor

BASE_VOLUME = 1


class LogisticsInfoProcessor:
    def __init__(
        self,
        wb_tariffs_db: Database,
        db: Database,
        data_extractor: WBDataExtractor,
        seller_id: int,
    ):
        self._seller_id = seller_id
        self._wb_tariffs_db = wb_tariffs_db
        self._data_extractor = data_extractor
        self._db = db
        self._tariffs_cache = {}

    async def get_stocks(self) -> set[tuple[int, str]]:
        """
        Получение данных об остатках на складах и занесение данных в бд
        """
        stocks_data = await self._data_extractor.extract_warehouses_stocks()
        stocks_list = []
        try:
            await self._db.insert_data("stocks", stocks_data)
        except Exception:
            logging.error("Не получилось записать данные в бд", exc_info=True)
        for stock in stocks_data:
            if stock.get("quantity"):
                stocks_list.append(
                    (stock.get("product_id"), stock.get("warehouse_name"))
                )
        return set(stocks_list)

    async def get_tariffs(
        self, date: datetime.date = datetime.date.today()
    ) -> list[dict]:
        """
        Получение тарифов на дату
        """
        if date in self._tariffs_cache:
            return self._tariffs_cache[date]
        query = "SELECT * FROM wb_warehouses_tariffs WHERE date = $1"
        tariffs = await self._wb_tariffs_db.pool.fetch(query, date)
        self._tariffs_cache = {date: tariffs}
        return tariffs

    async def check_changes(self) -> list[str | None]:
        """
        Проверка изменения тарифов и возврат списка с названиями складов
        """
        tariffs = await self.get_tariffs(
            datetime.date.today() + datetime.timedelta(days=1)
        )
        warehouses_data = []
        for tariff in tariffs:
            if tariff.get("box_delivery_and_storage_diff_sign"):
                warehouses_data.append(tariff.get("warehouse_name"))
        return warehouses_data

    async def get_relevant_stocks(self) -> list[tuple[int, str]]:
        """
        Получение данных об остатках на складах у которых будет изменен коэффициент
        """
        stocks = await self.get_stocks()
        warehouses_names = await self.check_changes()
        relevant_stocks = []
        for stock in stocks:
            if stock[1] in warehouses_names:
                relevant_stocks.append(stock)
        return relevant_stocks

    async def get_relevant_products(
        self,
    ) -> dict[Any, dict[str, list[str] | Any]]:
        """
        Получение данных о товарах, которые будут затронуты изменением тарифов
        """
        relevant_stocks = set(await self.get_relevant_stocks())
        query = "SELECT * FROM products WHERE seller_id = $1"
        products = await self._db.pool.fetch(query, self._seller_id)
        relevant_products = {}
        for stock in relevant_stocks:
            product = next(
                product
                for product in products
                if stock[0] == product.get("id")
            )
            if product:
                nm_id = product.get("nm_id")
                if nm_id not in relevant_products:
                    product_data = {
                        "vendor_code": product.get("vendor_code"),
                        "title": product.get("title"),
                        "length": product.get("length"),
                        "width": product.get("width"),
                        "height": product.get("height"),
                        "warehouse_name": [stock[1]],
                    }
                    relevant_products[nm_id] = product_data
                else:
                    relevant_products[nm_id]["warehouse_name"].append(stock[1])
        return relevant_products

    async def calculete_logistics(
        self,
        volume: float,
        warehouse_coefficient: float,
        base_rate: float,
        litter_rate: float,
    ) -> float:
        """
        Расчет стоимости логистики
        """
        if volume > BASE_VOLUME:
            base_logistics = (
                base_rate + (volume - BASE_VOLUME) * litter_rate
            ) * warehouse_coefficient
        else:
            base_logistics = base_rate * warehouse_coefficient
        return base_logistics

    async def return_info(self) -> str | None:
        """
        Возврат информации об изменении тарифов
        """
        todays_tariffs = await self.get_tariffs()
        tomorrows_tariffs = await self.get_tariffs(
            datetime.date.today() + datetime.timedelta(days=1)
        )
        if await self.check_changes():
            relevant_products = await self.get_relevant_products()
            if relevant_products:
                message = "Стоимость логистики для следующих товаров завтра изменится:\n\n"
                for index, product in enumerate(relevant_products):
                    nm_id = product
                    product = relevant_products.get(nm_id)
                    product_title = product.get("title")
                    vendor_code = product.get("vendor_code")
                    volume = (
                        product.get("length")
                        * product.get("width")
                        * product.get("height")
                    ) / 1000

                    url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
                    message += f"{index + 1}. [{product_title} ({vendor_code})]({url})\n"

                    warehouse_name = product.get("warehouse_name")
                    for warehouse in warehouse_name:
                        todays_tariff = next(
                            tariff
                            for tariff in todays_tariffs
                            if tariff.get("warehouse_name") == warehouse
                        )
                        tomorrows_tariff = next(
                            tariff
                            for tariff in tomorrows_tariffs
                            if tariff.get("warehouse_name") == warehouse
                        )
                        logistics_cost = []
                        for tariff in (todays_tariff, tomorrows_tariff):
                            warehouse_coefficient = (
                                float(
                                    tariff.get("box_delivery_and_storage_expr")
                                )
                                / 100
                            )
                            base_rate = float(tariff.get("box_delivery_base"))
                            litter_rate = float(
                                tariff.get("box_delivery_liter")
                            )
                            logistics = round(
                                await self.calculete_logistics(
                                    volume,
                                    warehouse_coefficient,
                                    base_rate,
                                    litter_rate,
                                ),
                                2,
                            )
                            logistics_cost.append(logistics)
                        current_logistics = logistics_cost[0]
                        next_logistics = logistics_cost[1]
                        if current_logistics < next_logistics:
                            message += "- 🔴 "
                        else:
                            message += "- 🟢 "
                        message += f"{warehouse}: {current_logistics}₽ -> {next_logistics}₽\n"
                    message += "\n"
                return message
            message = "Изменения тарифов, которые произойдут завтра, вас не коснутся!"
            return message
