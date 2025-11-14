import configparser
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError


def get_db_engine():
    """
    Читает конфигурацию из файла config.ini, строит URL для подключения
    и создает движок SQLAlchemy.
    """
    try:
        config = configparser.ConfigParser()
        config.read('config.ini')

        db_config = config['postgresql']
        host = db_config.get('host')
        port = db_config.get('port')
        user = db_config.get('user')
        password = db_config.get('password')
        db_name = db_config.get('db_name')


        database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"

        engine = create_engine(database_url, echo=True)

        with engine.connect() as connection:
            print("Соединение с базой данных установлено успешно!")

        return engine

    except FileNotFoundError:
        print("Ошибка: Файл конфигурации 'config.ini' не найден.")
        return None
    except KeyError:
        print("Ошибка: В файле 'config.ini' не найдена секция [postgresql] или необходимые ключи.")
        return None
    except SQLAlchemyError as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return None