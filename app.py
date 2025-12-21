import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysupersecretshop'
basedir = os.path.abspath(os.path.dirname(__file__))

# --- FIXED DATABASE NAME ---
# Changed 'shop.dp' to 'shop.db' to match your GitHub file
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'shop.db')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MASTER SECRET CONFIG ---
ADMIN_SECRET_PASS = "razi1321"

# --- MODELS ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    orders = db.relationship('Order', backref='customer', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(100))
    stock = db.Column(db.Integer, default=10)
    category = db.Column(db.String(50))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_details = db.Column(db.Text) 
    total_price = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

@app.route('/')
def index():
    q = request.args.get('q')
    query = Product.query
    if q: query = query.filter(Product.name.contains(q))
    return render_template('index.html', products=query.all())

@app.route('/admin_lock', methods=['GET', 'POST'])
def admin_lock():
    if request.method == 'POST':
        if request.form.get('admin_pass') == ADMIN_SECRET_PASS:
            session['admin_verified'] = True
            return redirect(url_for('admin'))
        flash("Invalid Master Key!")
    return render_template('admin_lock.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_verified'):
        return redirect(url_for('admin_lock'))

    if request.method == 'POST':
        f = request.files.get('image')
        if f:
            # Ensure upload folder exists before saving
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], f.filename))
            p = Product(
                name=request.form.get('name'), 
                price=request.form.get('price'), 
                stock=request.form.get('stock'), 
                category=request.form.get('category'), 
                image=f.filename
            )
            db.session.add(p)
            db.session.commit()
            flash("Product added successfully!")
            return redirect(url_for('admin'))
    
    products = Product.query.all()
    orders = Order.query.order_by(Order.id.desc()).all() 
    return render_template('admin.html', products=products, orders=orders)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        if User.query.filter_by(username=u).first():
            flash("Username already taken!")
            return redirect(url_for('signup'))
        new_user = User(username=u, password=generate_password_hash(p))
        db.session.add(new_user); db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        flash("Invalid Credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    my_orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', orders=my_orders)

# --- APP STARTUP ---
if __name__ == '__main__':
    with app.app_context():
        # THIS CREATES THE TABLES AUTOMATICALLY
        db.create_all() 
        if not os.path.exists(app.config['UPLOAD_FOLDER']): 
            os.makedirs(app.config['UPLOAD_FOLDER'])
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)get to let Render choose the port automatically
    port = int(os.environ.get("PORT", 10000))

    app.run(host='0.0.0.0', port=port)
