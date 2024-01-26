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
