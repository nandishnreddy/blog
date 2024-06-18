from flask import Flask, render_template, redirect, url_for, request, abort, flash
from flask_bootstrap import Bootstrap5
import pymysql
import pymysql.cursors
from flask import session
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_manager
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, SubmitField, Form, DateField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditor, CKEditorField
from datetime import date, datetime
from flask_ckeditor import CKEditor
from functools import wraps
from flask_gravatar import Gravatar
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
Bootstrap5(app)

# MySQL configurations
app.config['MYSQL_HOST'] = os.environ.get('DB_HOST')
app.config['MYSQL_USER'] = os.environ.get('DB_USER')
app.config['MYSQL_PASSWORD'] =os.environ.get('DB_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('DB_NAME')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = pymysql.connect(host=app.config['MYSQL_HOST'],
                        user=app.config['MYSQL_USER'],
                        password=app.config['MYSQL_PASSWORD'],
                        db=app.config['MYSQL_DB'],
                        cursorclass=pymysql.cursors.DictCursor)

app.config['MYSQL_HOST'] = os.environ.get('DB_HOST')
app.config['MYSQL_USER'] = os.environ.get('DB_USER')
app.config['MYSQL_PASSWORD'] = os.environ.get('DB_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('DB_NAME')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class PostForm(Form):
    title = StringField('title', validators=[DataRequired()])
    subtitle = StringField('subtitle', validators=[DataRequired()])
    date = DateField('date')
    body = CKEditorField('body', validators=[DataRequired()])
    author = StringField('author', validators=[DataRequired()])
    img_url = StringField('img_url', validators=[DataRequired()])
    submit = SubmitField('submit')


form = PostForm()


class CreatePostForm(FlaskForm):
    title = StringField('title', validators=[DataRequired()])
    subtitle = StringField('subtitle', validators=[DataRequired()])
    date = StringField('date', validators=[DataRequired()])
    body = CKEditorField('body', validators=[DataRequired()])
    author = StringField('author', validators=[DataRequired()])
    img_url = StringField('img_url', validators=[DataRequired()])
    submit = SubmitField('submit')


class RegisterForm(FlaskForm):
    name = StringField('name', validators=[DataRequired()])
    email = StringField('email', validators=[DataRequired()])
    password = StringField('password', validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Let Me In!")


class CommentForm(FlaskForm):
    comment_text = CKEditorField('Comment', validators=[DataRequired()])
    submit = SubmitField('Submit comment')


ckeditor = CKEditor(app)


class user(UserMixin):
    def __init__(self, user_id, name, email, password):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.password = password

    def get_id(self):
        return str(self.user_id)


gravatar = Gravatar(app,
                    size=40,
                    rating='a',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


@login_manager.user_loader
def load_user(user_id):
    conn = mysql.cursor()
    conn.execute('SELECT * FROM user WHERE user_id = %s', (user_id))
    result = conn.fetchone()
    conn.close()
    if result:
        return user(user_id=result['user_id'], name=result['name'], email=result['email'],
                    password=result['password'], )

    return None


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.user_id != 1:
            return abort(404)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def home():
    conn = mysql.cursor()

    conn.execute("SELECT * FROM blog_table ORDER BY date DESC")
    posts = conn.fetchall()
    conn.close()
    return render_template('index.html', all_posts=posts)


@app.route("/users")
def user_list():
    conn = mysql.cursor()
    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM users ORDER BY username")
        users = cursor.fetchall()
    conn.close()
    return render_template("user/list.html", users=users)


@app.route("/users/create", methods=["GET", "POST"])
def user_create():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]

        conn = mysql.cursor()
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO users (username, email) VALUES (%s, %s)", (username, email))
            conn.commit()
            user_id = cursor.lastrowid
        conn.close()

        return redirect(url_for("user_detail", id=user_id))

    return render_template("user/create.html")


@app.route("/user/<int:id>")
def user_detail(id):
    conn = mysql.cursor()
    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM users WHERE post = %s", (id,))
        user = cursor.fetchone()
    conn.close()
    if not user:
        abort(404)
    return render_template("user/detail.html", user=user)


@app.route("/user/<int:id>/delete", methods=["GET", "POST"])
def user_delete(id):
    conn = mysql.cursor()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE post = %s", (id,))
        user = cursor.fetchone()
        if not user:
            abort(404)
        if request.method == "POST":
            cursor.execute("DELETE FROM users WHERE post = %s", (id,))
            conn.commit()
            conn.close()
            return redirect(url_for("user_list"))
    conn.close()
    return render_template("user/delete.html", user=user)


@app.route('/')
def get_all_posts():


    conn = mysql.cursor()
    conn.execute("SELECT * FROM blog_table ORDER BY date DESC")
    posts = conn.fetchall()
    posts_list = list(posts)
    mysql.commit()
    conn.close()
    print(posts_list)
    return render_template("index.html", all_posts=posts)



@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def show_post(post_id):
    conn = mysql.cursor()
    conn.execute('SELECT * FROM blog_table WHERE post = %s', (post_id,))
    post = conn.fetchone()
    # conn.close()
    if not post:
        abort(404)


    conn.execute('''
            SELECT comments.text, user.name AS comment_author,user.email AS comment_author_email
            FROM comments
            JOIN user ON comments.user_id = user.user_id 
            WHERE comments.post = %s
        ''', (post_id,))
    comments = conn.fetchall()
    comment_form = CommentForm()
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))
        if comment_form.validate_on_submit():
            text = comment_form.comment_text.data
            user_id = current_user.get_id()
            conn = mysql.cursor()
            conn.execute('INSERT INTO comments(text, user_id, post) VALUES(%s, %s, %s)', (text, user_id, post_id))
            mysql.commit()
            conn.close()
            return redirect(url_for('show_post', post_id=post_id))
    conn.close()
    return render_template("post.html", post=post, current_user=current_user, comments=comments, form=comment_form)


@app.route('/new_post', methods=['GET', 'POST'])
@admin_only
def new_post():
    form = PostForm()
    if request.method == 'POST':
        title = request.form['title']
        subtitle = request.form['subtitle']
        date = request.form['date']
        body = request.form['body']
        author = request.form['author']
        img_url = request.form['img_url']
        author_id = session['user_id']
        conn = mysql.cursor()
        conn.execute("INSERT INTO blog_table(title, subtitle, date, body, author, img_url, author_id) VALUES (%s, %s, "
                     "%s, %s, %s, %s,%s)",
                     (title, subtitle, date, body, author, img_url, author_id))
        mysql.commit()
        conn.close()
        return redirect(url_for('home'))

    return render_template("make-post.html", form=form)



@app.route("/edit_post/<int:post_id>", methods=['GET', 'POST'])
@admin_only
def edit_post(post_id):
    conn = mysql.cursor()

    # Fetch the post data
    conn.execute('SELECT * FROM blog_table WHERE post = %s', (post_id,))
    post = conn.fetchone()
    conn.close()

    if not post:
        abort(404)

    form = CreatePostForm()

    if request.method == 'GET':
        # Populate form with existing post data for editing
        form.title.data = post['title']
        form.subtitle.data = post['subtitle']
        form.date.data = post['date']
        form.body.data = post['body']
        form.author.data = post['author']
        form.img_url.data = post['img_url']

    elif request.method == 'POST' and form.validate_on_submit():
        # Update post in the database
        title = form.title.data
        subtitle = form.subtitle.data
        date = form.date.data
        body = form.body.data
        author = form.author.data
        img_url = form.img_url.data

        conn = mysql.cursor()
        conn.execute(
            "UPDATE blog_table SET title = %s, subtitle = %s, date = %s, body = %s, author = %s, img_url = %s WHERE "
            "post = %s",
            (title, subtitle, date, body, author, img_url, post_id)
        )
        mysql.commit()
        conn.close()

        return redirect(url_for("show_post", post_id=post_id))

    return render_template("make-post.html", form=form, is_edit=True)



@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    conn = mysql.cursor()
    conn.execute("DELETE FROM blog_table WHERE post = %s", (post_id,))
    mysql.commit()
    conn.close()

    return redirect(url_for('home'))


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if request.method == 'POST' and form.validate_on_submit():
        hash_and_salted = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        conn = mysql.cursor()
        conn.execute('INSERT INTO user(name, email, password) VALUES(%s, %s, %s)',
                     (form.name.data, form.email.data, hash_and_salted))
        mysql.commit()

        conn.execute('SELECT * FROM user WHERE email=%s', form.email.data)
        result = conn.fetchone()

        if result:
            session['user_id'] = result['user_id']
            users = user(user_id=result['user_id'], name=result['name'], email=result['email'],
                         password=result['password'])
            login_user(users)
        conn.close()
        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')
        conn = mysql.cursor()
        conn.execute('SELECT * FROM user WHERE email = %s', (email,))
        result = conn.fetchone()

        if result and check_password_hash(result['password'], password):
            users = user(user_id=result['user_id'], name=result['name'], email=result['email'],
                         password=result['password'])
            if not user:
                flash("The provided e-mail and password do not match please try again!!!")
                conn.close()
                return redirect(url_for("login"))
            elif not check_password_hash(result['password'], password):
                flash("The password is incorrect please try again!!!")
                conn.close()
                return redirect(url_for("login"))
            else:
                login_user(users)
                session['user_id'] = result['user_id']
                conn.close()
                return redirect(url_for("get_all_posts"))

    return render_template("login.html", form=form, curreny_user=current_user)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    return redirect(url_for("home"))


# Below is the code from previous lessons. No changes needed.
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=False, port=5003)
