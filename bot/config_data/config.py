from dataclasses import dataclass

from environs import Env


@dataclass
class DatabaseConfig:
    postgres_db: str
    db_host: str
    postgres_user: str
    postgres_password: str
    db_port: int


@dataclass
class TgBot:
    token: str


@dataclass
class Config:
    tg_bot: TgBot
    db: DatabaseConfig
    wb_tariffs_db: DatabaseConfig


def load_config(path: str | None) -> Config:
    env: Env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot(token=env("BOT_TOKEN")),
        db=DatabaseConfig(
            postgres_db=env("POSTGRES_DB_1"),
            db_host=env("DB_HOST_1"),
            postgres_user=env("POSTGRES_USER_1"),
            postgres_password=env("POSTGRES_PASSWORD_1"),
            db_port=env.int("DB_PORT_1"),
        ),
        wb_tariffs_db=DatabaseConfig(
            postgres_db=env("POSTGRES_DB_2"),
            db_host=env("DB_HOST_2"),
            postgres_user=env("POSTGRES_USER_2"),
            postgres_password=env("POSTGRES_PASSWORD_2"),
            db_port=env.int("DB_PORT_2"),
        ),
    )
