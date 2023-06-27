from flask import Flask, render_template, request, redirect, url_for, flash
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


# CREATE DATABASE recipe_db;


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root@localhost/recipe_db'

db = SQLAlchemy(app)
jwt = JWTManager(app)


# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    recipes = db.relationship('Recipe', backref='author', lazy=True)
    favorite_recipes = db.relationship('Recipe', secondary='favorites', backref=db.backref('favorited_by', lazy=True))
    comments = db.relationship('Comment', backref='user', lazy=True)


# Recipe model
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='recipe', lazy=True)


# Favorites association table
favorites = db.Table('favorites',
                     db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                     db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True)
                     )


# Comment model
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)


# Routes
@app.route('/')
def home():
    recipes = Recipe.query.all()
    return render_template('templates/home.html', recipes=recipes)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please login.')
        return redirect(url_for('login'))

    return render_template('templates/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash('Invalid username or password.')
            return redirect(url_for('login'))

        access_token = create_access_token(identity=username)
        return redirect(url_for('profile', username=username, access_token=access_token))

    return render_template('templates/login.html')


@app.route('/profile/<username>', methods=['GET', 'POST'])
@jwt_required()
def profile(username):
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        new_recipe = Recipe(title=title, content=content)
        db.session.add(new_recipe)
        db.session.commit()

        flash('Recipe created successfully.')
        return redirect(url_for('profile', username=username))

    user = User.query.filter_by(username=username).first()
    recipes = user.recipes
    return render_template('templates/profile.html', username=username, recipes=recipes)


@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
@jwt_required()
def edit_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if request.method == 'POST':
        recipe.title = request.form['title']
        recipe.content = request.form['content']
        db.session.commit()

        flash('Recipe updated successfully.')
        return redirect(url_for('profile', username=get_jwt_identity()))

    return render_template('edit_recipe.html', recipe=recipe)


@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
@jwt_required()
def delete_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    db.session.delete(recipe)
    db.session.commit()

    flash('Recipe deleted successfully.')
    return redirect(url_for('profile', username=get_jwt_identity()))


@app.route('/recipes')
def view_recipes():
    recipes = Recipe.query.all()
    return render_template('templates/view_recipes.html', recipes=recipes)


@app.route('/search_recipes', methods=['POST'])
def search_recipes():
    search_query = request.form['search_query']
    recipes = Recipe.query.filter(Recipe.title.ilike(f'%{search_query}%')).all()
    return render_template('templates/view_recipes.html', recipes=recipes)


@app.route('/recipe/<int:recipe_id>')
def view_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    return render_template('templates/view_recipe.html', recipe=recipe)


@app.route('/recipe/<int:recipe_id>/favorite', methods=['POST'])
@jwt_required()
def favorite_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    user = User.query.filter_by(username=get_jwt_identity()).first()
    user.favorite_recipes.append(recipe)
    db.session.commit()

    flash('Recipe added to favorites.')
    return redirect(url_for('templates/view_recipe', recipe_id=recipe_id))


@app.route('/recipe/<int:recipe_id>/comment', methods=['POST'])
@jwt_required()
def comment_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    user = User.query.filter_by(username=get_jwt_identity()).first()
    comment_text = request.form['comment_text']

    new_comment = Comment(text=comment_text, user=user, recipe=recipe)
    db.session.add(new_comment)
    db.session.commit()

    flash('Comment added.')
    return redirect(url_for('view_recipe', recipe_id=recipe_id))


if __name__ == '__main__':
    app.run(debug=True)
