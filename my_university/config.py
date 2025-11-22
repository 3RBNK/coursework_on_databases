import os
from pathlib import Path
from dotenv import load_dotenv

base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / '.env'

load_dotenv(dotenv_path=env_path)


def get_db_url():
    try:
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT")
        db_name = os.getenv("POSTGRES_DB")

        if not all([user, password, host, port, db_name]):
            print("ОШИБКА: Не все переменные окружения для БД заданы в kdasjflkfads")
            return None

        database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
        return database_url

    except Exception as e:
        print(f"Ошибка при формировании URL БД: {e}")
        return None


def get_secret_key():
    return os.getenv("SECRET_KEY", "fallback_secret_key_if_none_found")
