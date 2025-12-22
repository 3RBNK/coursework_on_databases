from flask import Flask
from flask_login import LoginManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from my_university.config import get_db_url, get_secret_key
from my_university.models import User

engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)
db_session = scoped_session(Session)

app = Flask(__name__)
app.config['SECRET_KEY'] = get_secret_key()

login_manager = LoginManager(app)
login_manager.login_view = 'main.login'
login_manager.login_message = "Пожалуйста, войдите, чтобы открыть эту страницу."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return db_session.query(User).get(int(user_id))


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


def register_blueprints():
    from my_university.routes import bp
    app.register_blueprint(bp)

if __name__ == '__main__':
    register_blueprints()
    print("Запуск сервера...")
    app.run(debug=True, host="0.0.0.0", port=5001)