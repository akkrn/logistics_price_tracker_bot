import datetime
import json
import logging
from http import HTTPStatus
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class WBParser:
    def __init__(
        self,
        api_token: str,
    ):
        self._api_token = api_token
        self.client = aiohttp.ClientSession()

    async def __request(self, *args, **kwargs):
        headers = {
            "Accept": "*/*",
            "Authorization": self._api_token,
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        }
        kwargs["headers"] = headers
        return await self.client.request(*args, **kwargs)

    async def check_token(self) -> bool:
        """
        Проверка токена
        """
        try:
            url = "https://suppliers-api.wildberries.ru/api/v3/offices"
            response = await self.__request("GET", url)
            if response.status != HTTPStatus.OK:
                raise Exception(
                    f"Failed to get data, status: {response.status}\n"
                    f"Message: {await response.json()}"
                )
            return True
        except Exception as e:
            logger.error(e)
            return False

    async def get_products(self) -> list[Any]:
        """
        Парсинг информации о товарах продавцов
        """
        products_data = []
        try:
            url = "https://suppliers-api.wildberries.ru/content/v2/get/cards/list"
            payload = {
                "settings": {
                    "filter": {"withPhoto": -1},
                    "cursor": {"limit": 1000},
                }
            }
            while True:
                response = await self.__request(
                    "POST", url, data=json.dumps(payload)
                )
                if response.status != HTTPStatus.OK:
                    raise Exception(
                        f"Failed to get data, status: {response.status} \n"
                        f"Message: {await response.json()}"
                    )
                data = await response.json()
                product_data = data.get("cards")
                if product_data:
                    products_data.extend(product_data)
                    if (
                        data.get("cursor").get("total")
                        >= payload["settings"]["cursor"]["limit"]
                    ):
                        payload["settings"]["cursor"]["nmID"] = data.get(
                            "cursor"
                        ).get("nmID")
                        payload["settings"]["cursor"]["updatedAt"] = data.get(
                            "cursor"
                        ).get("updatedAt")
                    else:
                        break
                else:
                    break
        except Exception as e:
            logger.error(e)

        return products_data

    async def get_warehouses_stocks(
        self, date: datetime.date = "2019-06-20"
    ) -> list[Any]:
        """
        Парсинг информации о остатках товарах продавца на складе
        """
        try:
            url = f"https://statistics-api.wildberries.ru/api/v1/supplier/stocks?dateFrom={date}"
            response = await self.__request("GET", url)
            if response.status != HTTPStatus.OK:
                raise Exception(
                    f"Failed to get data, status: {response.status} \n"
                    f"Message: {await response.json()}"
                )
            data = await response.json()
            return data
        except Exception as e:
            logger.error(e)
