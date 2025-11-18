from config import get_db_url

if __name__ == "__main__":
    db_engine = get_db_url()

    if db_engine:
        print("\nДвижок SQLAlchemy готов к работе.")
