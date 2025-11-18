import configparser
import os
from pathlib import Path


def get_db_url():
    """
    Читает конфигурацию из файла config.ini, строит URL для подключения.
    """
    try:
        base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / 'config.ini'

        if not config_path.exists():
            print(f"ОШИБКА: Файл конфига не найден по пути: {config_path}")
            return None

        config = configparser.ConfigParser()
        config.read(config_path)

        if 'postgresql' not in config:
            print("ОШИБКА: В config.ini нет секции [postgresql]")
            return None

        db_config = config['postgresql']
        host = db_config.get('host')
        port = db_config.get('port')
        user = db_config.get('user')
        password = db_config.get('password')
        db_name = db_config.get('database', db_config.get('db_name'))

        if not all([host, port, user, password, db_name]):
            print("ОШИБКА: Не все поля заполнены в config.ini")
            return None

        database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
        return database_url

    except Exception as e:
        print(f"Критическая ошибка при чтении конфига: {e}")
        return None