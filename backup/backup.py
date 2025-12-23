import os
import time
import subprocess
import requests
import datetime
from urllib.parse import urlparse

DB_URL = os.getenv("DATABASE_URL")
YD_TOKEN = os.getenv("YANDEX_TOKEN")
BACKUP_DIR = "/backups"

BACKUP_INTERVAL = 86400


def get_db_params():
    """Безопасный парсинг DATABASE_URL"""
    try:
        parsed = urlparse(DB_URL)
        return {
            "host": parsed.hostname,
            "port": str(parsed.port),
            "user": parsed.username,
            "password": parsed.password,
            "dbname": parsed.path.lstrip('/')
        }
    except Exception as e:
        print(f"[Backup] Ошибка парсинга URL: {e}")
        return None


def create_dump():
    """Создает дамп базы данных"""
    params = get_db_params()
    if not params:
        return None

    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    filename = f"backup_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.sql.gz"
    filepath = os.path.join(BACKUP_DIR, filename)

    env = os.environ.copy()
    env["PGPASSWORD"] = params["password"]

    cmd = (
        f"pg_dump -h {params['host']} -p {params['port']} -U {params['user']} {params['dbname']} "
        f"| gzip > {filepath}"
    )

    print(f"[Backup] Создаю дамп {filename}...")
    try:
        subprocess.run(cmd, shell=True, env=env, check=True)
        print("[Backup] Дамп создан локально.")
        return filepath, filename
    except subprocess.CalledProcessError as e:
        print(f"[Backup] Ошибка pg_dump: {e}")
        return None, None


def upload_to_yandex(filepath, filename):
    """Загружает файл на Яндекс.Диск"""
    print(f"[Backup] Загружаю на Яндекс.Диск...")
    headers = {"Authorization": f"OAuth {YD_TOKEN}"}

    target_path = f"/bd_course_backup/{filename}"

    try:
        upload_url_resp = requests.get(
            "https://cloud-api.yandex.net/v1/disk/resources/upload",
            params={"path": target_path, "overwrite": "true"},
            headers=headers
        )

        if upload_url_resp.status_code != 200:
            print(f"[Backup] Ошибка API Яндекса: {upload_url_resp.json()}")
            return

        href = upload_url_resp.json().get("href")

        with open(filepath, 'rb') as f:
            upload_resp = requests.put(href, files={"file": f})

        if upload_resp.status_code == 201:
            print(f"[Backup] Успешно загружено на Яндекс.Диск!")
        else:
            print(f"[Backup] Ошибка загрузки: {upload_resp.status_code}")

    except Exception as e:
        print(f"[Backup] Ошибка сети: {e}")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
            print("[Backup] Локальный файл удален.")


def run_scheduler():
    while True:
        filepath, filename = create_dump()
        if filepath:
            upload_to_yandex(filepath, filename)
        time.sleep(BACKUP_INTERVAL)


if __name__ == "__main__":
    run_scheduler()
