# import aioredis
from dataclasses import dataclass, field

import asyncpg
from asyncpg import Pool


@dataclass
class Database:
    name: str
    user: str
    password: str
    host: str
    port: int
    pool: Pool = field(init=False, default=None)

    async def create_pool(self):
        self.pool = await asyncpg.create_pool(
            database=self.name,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
        )

    async def create_tables(self):
        queries = [
            """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_tg_id INTEGER UNIQUE,
                    username VARCHAR UNIQUE,
                    first_name VARCHAR,
                    last_name VARCHAR,
                    added_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS sellers (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    api_token VARCHAR NOT NULL,
                    added_at TIMESTAMP,
                    UNIQUE (user_id, api_token),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                );
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    seller_id INTEGER,
                    nm_id INTEGER,
                    imt_id INTEGER,
                    nm_uuid VARCHAR,
                    subject_id INTEGER,
                    subject_name VARCHAR,
                    vendor_code VARCHAR,
                    brand VARCHAR,
                    title VARCHAR,
                    description TEXT,
                    video VARCHAR,
                    photos JSON,
                    length FLOAT,
                    width FLOAT,
                    height FLOAT,
                    characteristics JSON,
                    sizes JSON,
                    tags JSON,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    UNIQUE (seller_id, nm_id),
                    FOREIGN KEY (seller_id) REFERENCES sellers (id)
                );
                CREATE TABLE IF NOT EXISTS warehouses_stocks (
                    id SERIAL PRIMARY KEY,
                    seller_id INTEGER NOT NULL,
                    product_id INTEGER,
                    last_change_date TIMESTAMP,
                    warehouse_name VARCHAR,
                    supplier_article VARCHAR,
                    barcode VARCHAR,
                    quantity INTEGER,
                    in_way_to_client INTEGER,
                    in_way_from_client INTEGER,
                    quantity_full INTEGER,
                    category VARCHAR,
                    subject VARCHAR,
                    brand VARCHAR,
                    tech_size VARCHAR,
                    price FLOAT,
                    discount FLOAT,
                    is_supply BOOLEAN,
                    is_realization BOOLEAN,
                    sc_code VARCHAR,
                    UNIQUE (seller_id, last_change_date, warehouse_name, product_id),
                    FOREIGN KEY (seller_id) REFERENCES sellers (id),
                    FOREIGN KEY (product_id) REFERENCES products (id)
                );
            """
        ]
        for query in queries:
            await self.pool.execute(query)

    #
    #     async def get_user(self, user_id: int) -> asyncpg.Record | None:
    #         async with self.pool.acquire() as connection:
    #             return await connection.fetchrow(
    #                 "SELECT * FROM users WHERE user_id = $1", user_id
    #             )
    #
    #     async def add_user(
    #         self, user_id: int, username: str, first_name: str, last_name: str
    #     ) -> None:
    #         async with self.pool.acquire() as connection:
    #             await connection.execute(
    #                 """
    #                 INSERT INTO users (user_id, username, first_name, last_name,
    #                 created_at)
    #                 VALUES ($1, $2, $3, $4, $5)
    #             """,
    #                 user_id,
    #                 username,
    #                 first_name,
    #                 last_name,
    #                 datetime.now(),
    #             )
    #
    #     async def get_rate_for_date(self, date: datetime) -> float | None:
    #         async with self.pool.acquire() as connection:
    #             result = await connection.fetchrow(
    #                 "SELECT rate FROM keyratecbr WHERE date <= $1 ORDER BY date DESC "
    #                 "LIMIT 1",
    #                 date,
    #             )
    #             result = float(result[0])
    #             return result if result else None
    #
    #     async def add_penalty(
    #         self,
    #         user_id: int,
    #         start_date: datetime,
    #         end_date: datetime,
    #         object_cost: float,
    #         penalty: float,
    #     ) -> None:
    #         async with self.pool.acquire() as connection:
    #             await connection.execute(
    #                 """
    #                 INSERT INTO penalties (user_id, start_date, end_date, object_cost,
    #                 penalty)
    #                 VALUES ($1, $2, $3, $4, $5)
    #             """,
    #                 user_id,
    #                 start_date,
    #                 end_date,
    #                 object_cost,
    #                 penalty,
    #             )
    #
    #     async def add_defects(
    #         self,
    #         user_id: int,
    #         city: str,
    #         object_name: str,
    #         object_square: float,
    #         compensation: float,
    #     ) -> None:
    #         async with self.pool.acquire() as connection:
    #             await connection.execute(
    #                 """
    #                 INSERT INTO defects (user_id, city, object_name,
    #                 object_square, compensation)
    #                 VALUES ($1, $2, $3, $4, $5)
    #             """,
    #                 user_id,
    #                 city,
    #                 object_name,
    #                 object_square,
    #                 compensation,
    #             )
    #
    #     async def add_question(
    #         self,
    #         user_id: int,
    #         question: str,
    #         answer: str,
    #     ) -> None:
    #         async with self.pool.acquire() as connection:
    #             await connection.execute(
    #                 """
    #                 INSERT INTO questions (user_id, question, answer)
    #                 VALUES ($1, $2, $3)
    #             """,
    #                 user_id,
    #                 question,
    #                 answer,
    #             )
    #
    #
    # # async def create_redis_pool():
    # #     return await aioredis.from_url("redis://localhost:6379", db=5)

    async def insert_data(
        self,
        table_name,
        data,
        returning_fields=None,
        conflict_target=None,
        update_fields=None,
    ):
        if isinstance(data, dict):
            data = [data]
        if data:
            keys = data[0].keys()
            columns = ", ".join(keys)
            values_placeholders = ", ".join(
                f"${i + 1}" for i in range(len(keys))
            )
            values = [tuple(item[key] for key in keys) for item in data]
            if returning_fields:
                query = (
                    f"INSERT INTO {table_name} ({columns}) VALUES {', '.join(map(lambda x: str(x).replace('None', 'NULL'),values))} ON "
                    f"CONFLICT DO NOTHING RETURNING {', '.join(returning_fields)};"
                )
                result = await self.pool.fetch(query)
                print(result)
                return result
            if conflict_target and update_fields:
                update_expressions = ", ".join(
                    f"{field} = EXCLUDED.{field}" for field in update_fields
                )
                query = (
                    f"INSERT INTO {table_name} ({columns}) VALUES "
                    f"({values_placeholders}) ON CONFLICT ({conflict_target}) "
                    f"DO UPDATE SET {update_expressions};"
                )
            else:
                query = (
                    f"INSERT INTO {table_name} ({columns}) VALUES ("
                    f"{values_placeholders}) ON CONFLICT DO NOTHING;"
                )
            print("DEBUG QUERY:", query)
            await self.pool.executemany(query, values)
