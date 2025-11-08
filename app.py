from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy 
# Flask-Loginのインポート --- (※1)
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app: Flask = Flask(__name__)

# 🔹 PostgreSQL用設定（Render環境変数から読み込み）
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://")
elif db_url and db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")

db = SQLAlchemy(app)

# ログインマネージャーの設定 --- (※2)
app.config['SECRET_KEY'] = os.urandom(24)
login_manager = LoginManager()
login_manager.init_app(app)

# ユーザーモデルの作成 --- (※3)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(25))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100))
    contents = db.Column(db.String(100))


# ユーザーを読み込むためのコールバック --- (※4)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ログインユーザー名を保持する変数 --- (※5)
@app.before_request
def set_login_user_name():
    global login_user_name
    login_user_name = current_user.username if current_user.is_authenticated else None


# アカウント登録 --- (※6)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    
    elif request.method == "POST":
        input_username_for_signup = request.form.get('username')
        input_password_for_signup = request.form.get('password')
        # Userのインスタンスを作成
        new_user_instance = User(username=input_username_for_signup, 
                                 password=generate_password_hash(input_password_for_signup))
        db.session.add(new_user_instance)
        db.session.commit()
        return redirect('login')


# ログイン --- (※7)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        return render_template("login.html")
    
    elif request.method == "POST":
        input_username_for_login = request.form.get('username')
        input_password_for_login = request.form.get('password')
        # Userテーブルからusernameに一致するユーザを取得
        user = User.query.filter_by(username=input_username_for_login).first()
        if check_password_hash(user.password, input_password_for_login):
            login_user(user)
            return redirect('/')
    # 認証失敗時の処理
    error_message_for_user = "ユーザー名またはパスワードが正しくありません。"
    return render_template("login.html", error_message=error_message_for_user)

# ログアウト --- (※8)
@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')

@app.route("/")
def index():
    input_for_search_word: str = request.args.get("search_word")

    if input_for_search_word is None:
        message_list: list[Message] = Message.query.all()
    else:
        message_list: list[Message] = Message.query.filter(Message.contents.like(f"%{input_for_search_word}%")).all()

    return render_template(
        "top.html",
        current_user_name=login_user_name,
        messages_to_display=message_list,
        search_word=input_for_search_word,
    )

# 書き込み機能 --- (※9)
@app.route("/write", methods=["GET", "POST"])
def write_new_message():
    if request.method == "GET":
        return render_template("write.html", current_user_name=login_user_name)

    elif request.method == "POST":
        input_message_for_post: str = request.form.get("contents")
        input_username_for_post: str = request.form.get("user_name")
        new_message_record = Message(user_name=input_username_for_post, contents=input_message_for_post)
        db.session.add(new_message_record)
        db.session.commit()

        return redirect(url_for("index"))

@app.route("/update/<int:message_id>", methods=["GET", "POST"])
def update_message(message_id: int):
    target_message: Message = Message.query.get(message_id)

    if request.method == "GET":
        return render_template("update.html", current_username=login_user_name, updated_message=target_message)

    elif request.method == "POST":
        target_message.contents = request.form.get("contents")
        db.session.commit()

        return redirect(url_for("index"))

@app.route("/delete/<int:message_id>")
def delete_message(message_id: int):
    message: Message = Message.query.get(message_id)
    db.session.delete(message)
    db.session.commit()

    return redirect(url_for("index"))


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=False)
