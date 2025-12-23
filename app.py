import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysupersecretshop'

# --- CONFIGURATION FIXES ---
# This line now checks Render for the DATABASE_URL link first!
database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1) #

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///shop.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- ADMIN CONFIG ---
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

# --- ADMIN ROUTES ---
@app.route('/admin_lock', methods=['GET', 'POST'])
def admin_lock():
    if request.method == 'POST':
        if request.form.get('admin_pass') == ADMIN_SECRET_PASS:
            session['admin_verified'] = True
            return redirect(url_for('admin'))
        flash("Invalid Master Key!")
    return render_template('admin_lock.html')

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_verified', None)
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_verified'):
        return redirect(url_for('admin_lock'))

    if request.method == 'POST':
        f = request.files.get('image')
        if f:
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

@app.route('/delete/<int:id>')
def delete_product(id):
    if session.get('admin_verified'):
        p = Product.query.get(id)
        if p:
            db.session.delete(p)
            db.session.commit()
    return redirect(url_for('admin'))

@app.route('/delete_order/<int:id>')
def delete_order(id):
    if session.get('admin_verified'):
        order = Order.query.get(id)
        if order:
            db.session.delete(order)
            db.session.commit()
            flash("Order record cleared.")
    return redirect(url_for('admin'))

# --- USER SHOP ROUTES ---
@app.route('/')
def index():
    q = request.args.get('q')
    query = Product.query
    if q: query = query.filter(Product.name.contains(q))
    return render_template('index.html', products=query.all())

@app.route('/buy/<int:id>')
def buy_now(id):
    if not current_user.is_authenticated:
        flash("Please login or signup to buy!")
        return redirect(url_for('signup'))
    session['cart'] = [id] 
    return redirect(url_for('checkout'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_ids = session.get('cart', [])
    items = [Product.query.get(i) for i in cart_ids if Product.query.get(i)]
    total = sum(i.price for i in items)

    if request.method == 'POST':
        addr = request.form.get('address')
        pay_id = request.form.get('pay_number')
        summary = f"ITEMS: {', '.join([i.name for i in items])} | CONTACT: {pay_id} | ADDR: {addr}"

        new_order = Order(product_details=summary, total_price=total, user_id=current_user.id)
        db.session.add(new_order)
        db.session.commit()
        
        session.pop('cart', None)
        flash("Order placed!")
        return redirect(url_for('profile'))

    return render_template('checkout.html', items=items, total=total)

# --- AUTH ROUTES ---
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

@app.route('/cancel_order/<int:id>')
@login_required
def cancel_order(id):
    order = Order.query.get(id)
    if order and order.user_id == current_user.id:
        db.session.delete(order)
        db.session.commit()
        flash("Order cancelled.")
    return redirect(url_for('profile'))

# --- STARTUP ---
if __name__ == '__main__':
    with app.app_context(): 
        db.create_all() # This creates the tables in your evia-db
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
