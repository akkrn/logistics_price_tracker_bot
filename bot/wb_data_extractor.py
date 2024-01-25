import json
import logging

from database import Database
from wb_parser import WBParser
from utils import str_to_date

logger = logging.getLogger(__name__)


class WBDataExtractor:
    def __init__(self, wb_parser: WBParser, db: Database, seller_id: int):
        self._wb_parser = wb_parser
        self._db = db
        self._seller_id = seller_id

    """
    Класс для извлечения данных с API Wildberries
    """

    async def get_products_info_data(self) -> list[dict]:
        """
        Получение данных о товарах из бд
        """
        query = "SELECT id, nm_id FROM products WHERE seller_id = $1"
        return await self._db.pool.fetch(query, self._seller_id)

    async def insert_products(self):
        """
        Извлечение данных о товарах и вставка в бд
        """
        products_data = await self._wb_parser.get_products()
        products_list = []
        for product in products_data:
            product_data = {
                "seller_id": self._seller_id,
                "nm_id": product.get("nmID"),
                "imt_id": product.get("imtID"),
                "nm_uuid": product.get("nmUUID"),
                "subject_id": product.get("subjectID"),
                "subject_name": product.get("subjectName"),
                "vendor_code": product.get("vendorCode"),
                "brand": product.get("brand"),
                "title": product.get("title"),
                "description": product.get("description"),
                "video": product.get("video"),
                "photos": json.dumps(
                    product.get("photos"), ensure_ascii=False
                ),
                "length": product.get("dimensions").get("length"),
                "width": product.get("dimensions").get("width"),
                "height": product.get("dimensions").get("height"),
                "characteristics": json.dumps(
                    product.get("characteristics"), ensure_ascii=False
                ),
                "sizes": json.dumps(product.get("sizes"), ensure_ascii=False),
                "tags": json.dumps(product.get("tags"), ensure_ascii=False),
                "created_at": str_to_date(product.get("createdAt")),
                "updated_at": str_to_date(product.get("updatedAt")),
            }
            products_list.append(product_data)
        await self._db.insert_data("products", products_list)

    async def extract_warehouses_stocks(self):
        """
        Извлечение данных о товарах и вставка в бд
        """
        products_info_data = await self.get_products_info_data()
        stocks_data = await self._wb_parser.get_warehouses_stocks()
        stocks_list = []
        for stock in stocks_data:
            product_id = next(
                (
                    row.get("id")
                    for row in products_info_data
                    if stock.get("nmId") == row.get("nm_id")
                ),
                None,
            )
            if not product_id:
                logger.error(
                    f"Товар с nm_id == {stock.get('nmId')} не найден в базе данных."
                )
                continue
            stock_data = {
                "seller_id": self._seller_id,
                "product_id": product_id,
                "last_change_date": str_to_date(stock.get("lastChangeDate")),
                "warehouse_name": stock.get("warehouseName"),
                "supplier_article": stock.get("supplierArticle"),
                "barcode": stock.get("barcode"),
                "quantity": stock.get("quantity"),
                "in_way_to_client": stock.get("inWayToClient"),
                "in_way_from_client": stock.get("inWayFromClient"),
                "quantity_full": stock.get("quantityFull"),
                "category": stock.get("category"),
                "subject": stock.get("subject"),
                "brand": stock.get("brand"),
                "tech_size": stock.get("techSize"),
                "price": stock.get("Price"),
                "discount": stock.get("Discount"),
                "is_supply": stock.get("isSupply"),
                "is_realization": stock.get("isRealization"),
                "sc_code": stock.get("SCCode"),
            }
            stocks_list.append(stock_data)
        return stocks_list
