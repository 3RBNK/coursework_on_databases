import os
from minio import Minio
from datetime import timedelta


MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio:9000')
ACCESS_KEY = os.getenv('MINIO_ROOT_USER', 'minioadmin')
SECRET_KEY = os.getenv('MINIO_ROOT_PASSWORD', 'minioadmin')
BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME', 'university-materials')

client = Minio(
    MINIO_ENDPOINT,
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    secure=False
)


def ensure_bucket_exists():
    """Проверяет наличие бакета и создает его, если нет"""
    if not client.bucket_exists(BUCKET_NAME):
        client.make_bucket(BUCKET_NAME)
        print(f"Бакет '{BUCKET_NAME}' создан.")


def upload_file_to_minio(file_data, object_name, content_type):
    """Загружает файл в хранилище"""
    ensure_bucket_exists()

    file_data.seek(0, 2)
    size = file_data.tell()
    file_data.seek(0)

    client.put_object(
        BUCKET_NAME,
        object_name,
        file_data,
        size,
        content_type=content_type
    )
    return object_name


def get_download_url(object_name):
    """Генерирует временную ссылку на скачивание"""
    url = client.get_presigned_url(
        "GET",
        BUCKET_NAME,
        object_name,
        expires=timedelta(hours=1)
    )

    if 'minio:9000' in url:
        url = url.replace('minio:9000', 'localhost:9000')

    return url


def get_file_content(object_name):
    """
    Получает сам файл (поток данных) из MinIO.
    Возвращает объект ответа MinIO.
    """
    try:
        response = client.get_object(BUCKET_NAME, object_name)
        return response
    except Exception as e:
        print(f"Ошибка при получении файла из MinIO: {e}")
        return None


def delete_file_from_minio(object_name):
    """
    Удаляет объект из хранилища MinIO.
    """
    try:
        client.remove_object(BUCKET_NAME, object_name)
        print(f"Файл {object_name} успешно удален из MinIO.")
    except Exception as e:
        print(f"Ошибка при удалении файла из MinIO: {e}")