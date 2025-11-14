from config import get_db_engine

if __name__ == "__main__":
    db_engine = get_db_engine()

    if db_engine:
        print("\nДвижок SQLAlchemy готов к работе.")
