import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Post, Comment
from config import Config
from sqlalchemy.sql.expression import func

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

@app.after_request
def add_cache_control(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/')
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    print(f"Current user: {current_user}")  # Debug print
    print(f"Session in index: {session}")  # Debug print
    return render_template('index.html', posts=posts, current_user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        print(f"Login attempt - Username: {username}, User found: {user}")  # Debug print
        if user and check_password_hash(user.password, password):
            login_user(user)
            print(f"User logged in: {user}")  # Debug print
            print(f"Session after login: {session}")  # Debug print
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'error')
        else:
            new_user = User(username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Registration successful. You are now logged in.', 'success')
            return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        content = request.form.get('content')
        image = request.files.get('image')
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
        else:
            image_path = None
        new_post = Post(content=content, image=image_path, user_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('index'))
    return render_template('create_post.html')

@app.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all()
    return render_template('profile.html', user=user, posts=posts)

@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow_user(username):
    user_to_follow = User.query.filter_by(username=username).first()
    if user_to_follow and user_to_follow != current_user:
        current_user.follow(user_to_follow)
        db.session.commit()
        flash(f'You are now following {username}', 'success')
    return redirect(url_for('profile', username=username))

@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow_user(username):
    user_to_unfollow = User.query.filter_by(username=username).first()
    if user_to_unfollow:
        current_user.unfollow(user_to_unfollow)
        db.session.commit()
        flash(f'You have unfollowed {username}', 'info')
    return redirect(url_for('profile', username=username))

@app.route('/comment', methods=['POST'])
@login_required
def add_comment():
    post_id = request.form.get('post_id')
    content = request.form.get('content')
    post = Post.query.get(post_id)
    if post:
        new_comment = Comment(content=content, user_id=current_user.id, post_id=post.id)
        db.session.add(new_comment)
        db.session.commit()
        flash('Your comment has been added.', 'success')
    return redirect(url_for('index'))

@app.route('/discover')
def discover():
    print(f"Current user in discover: {current_user}")  # Debug print
    random_users = User.query.order_by(func.random()).limit(5).all()
    random_posts = Post.query.order_by(func.random()).limit(10).all()
    
    if current_user.is_authenticated:
        random_users = [user for user in random_users if user.id != current_user.id]
    
    return render_template('discover.html', users=random_users, posts=random_posts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
