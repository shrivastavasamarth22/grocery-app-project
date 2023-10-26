from flask import Flask, render_template, request, redirect, flash, url_for, send_file, abort
from sqlalchemy import func, and_
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from dotenv import load_dotenv
from datetime import datetime, timedelta

from functools import wraps
import io
import os

from models import db
from models import User, Category, Item, CartItem, Order, OrderItem, Cart, PromoCodes, Address

from functions import allowed_file, process_date, process_switch, get_all_rows
from states import STATES

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

db.init_app(app)

# CREATE LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)


# CREATE USER LOADER CALLBACK
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, int(user_id))


with app.app_context():
    db.create_all()


@app.context_processor
def inject_global():
    context = {
        'logged_in': current_user.is_authenticated,
        'entity': current_user,
        'categories': get_all_rows(Category),
    }

    # Check if the user is logged in and has a cart
    if current_user.is_authenticated:
        cart = Cart.query.filter_by(user_id=current_user.user_id).first()
        if cart:
            # Inject cart and cart items into the context
            context['cart'] = cart
            context['cart_items'] = CartItem.query.filter_by(cart_id=cart.cart_id).all()

    return context


def manager_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'manager':
            flash("Access denied. Manager role required.", "danger")
            return redirect(url_for('home'))
        return func(*args, **kwargs)

    return decorated_view


def customer_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'customer':
            flash("Please sign in to access this page", "danger")
            return redirect(url_for('signin'))
        return func(*args, **kwargs)

    return decorated_view


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404error.html'), 404


@app.route('/category-images/<int:category_id>')
def serve_category_image(category_id):
    category = db.get_or_404(Category, category_id)
    return send_file(io.BytesIO(category.picture), mimetype='image/jpeg')


@app.route('/item-images/<int:item_id>/<int:image_number>')
def serve_item_image(item_id, image_number):
    item = db.get_or_404(Item, item_id)

    # Determine which picture to serve based on image_number (1, 2, 3, or 4)
    if image_number == 1:
        image_data = item.picture1
    elif image_number == 2:
        image_data = item.picture2
    elif image_number == 3:
        image_data = item.picture3
    elif image_number == 4:
        image_data = item.picture4
    else:
        # Return a 404 error if an invalid image_number is provided
        abort(404)

    # Serve the image using send_file
    return send_file(io.BytesIO(image_data), mimetype='image/jpeg')


@app.route('/user-images/<int:user_id>')
@login_required
def serve_user_image(user_id):
    user = db.get_or_404(User, user_id)
    return send_file(io.BytesIO(user.image), mimetype='image/jpeg')


@app.route("/")
def home():
    # Get those items which are in stock and not expired
    items = db.session.execute(
        db.select(Item).where(Item.in_stock == True, Item.expiry_date > datetime.now().date())).scalars().all()
    return render_template('index.html', items=items)


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        # Find user by email entered
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()

        # Email doesn't exist or password incorrect.
        if not user or not check_password_hash(user.password, password):
            flash("Email or password incorrect")
            return redirect(url_for('signin'))
        elif user.role == 'customer':
            login_user(user)
            return redirect(url_for('home'))
        else:
            return redirect(url_for('dashboard_signin'))

    return render_template('signin.html')


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get('email')

        # Check if a customer with same email exists
        customer = db.session.execute(db.select(User).where(User.email == email, User.role == 'customer')).scalar()

        if customer:
            flash("You've already signed up with that email, sign in instead")
            return redirect(url_for('signin'))

        hash_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
        )

        # Create a new customer with the 'customer' role
        new_customer = User(
            email=email,
            password=hash_and_salted_password,
            name=request.form.get('name'),
            role='customer'  # Set the role as 'customer'
        )

        db.session.add(new_customer)
        db.session.commit()

        # Log in the newly created user
        login_user(new_customer)

        return redirect(url_for('home'))

    return render_template('signup.html')


@app.route('/add-to-cart', methods=["POST"])
@login_required
@customer_required
def add_to_cart():
    if request.method == "POST":
        # Get the item from the database
        item_id = request.form.get('item_id')
        item = db.get_or_404(Item, item_id)

        # Check if the user has a cart
        cart = db.session.execute(db.select(Cart).where(Cart.user_id == current_user.user_id)).scalar()

        # If the user doesn't have a cart, create a new cart
        if not cart:
            cart = Cart(user_id=current_user.user_id)
            db.session.add(cart)
            db.session.commit()

        # Retrieve the quantity from the form
        quantity = int(request.form.get('quantity'))

        # Limit the quantity to 10
        quantity = min(quantity, 10)

        # Check if the item is already in the cart
        cart_item = db.session.execute(
            db.select(CartItem).where(CartItem.cart_id == cart.cart_id, CartItem.item_id == item_id)).scalar()

        if cart_item:
            # Update the quantity and amount of the cart item
            cart_item.quantity += quantity
            cart_item.amount += quantity * item.rate_per_unit
        else:
            # Create a new cart item
            cart_item = CartItem(
                cart_id=cart.cart_id,
                item_id=item_id,
                quantity=quantity,
                amount=quantity * item.rate_per_unit
            )
            db.session.add(cart_item)

        # Update the total amount of the cart
        cart.total_amount += quantity * item.rate_per_unit

        if quantity > 10:
            flash("You can add a maximum of 10 items at a time.", "cart-warning")

        db.session.commit()

        return_url = request.form.get('return_url')

        flash("Item added to cart successfully!", "cart-success")

        if return_url:
            return redirect(return_url)
        else:
            return redirect(url_for('cart'))


@app.route('/cart')
@login_required
@customer_required
def cart():
    return render_template('cart.html')


@app.route('/update_cart', methods=["POST"])
@login_required
@customer_required
def update_cart():
    cart = db.session.execute(db.select(Cart).where(Cart.user_id == current_user.user_id)).scalar()
    if request.method == "POST":
        cart_items = request.form.getlist('cart_item_id[]')
        quantities = request.form.getlist('quantity')

        for cart_item_id, quantity in zip(cart_items, quantities):
            cart_item = db.get_or_404(CartItem, cart_item_id)

            if cart_item:
                if int(quantity) == 0:
                    db.session.delete(cart_item)
                else:
                    cart_item.quantity = min(int(quantity), 10)  # Limit quantity to 10
                    cart_item.amount = cart_item.quantity * cart_item.item.rate_per_unit

        # Update the total amount of the cart
        cart.total_amount = sum(cart_item.amount for cart_item in cart.cart_items)

        db.session.commit()

    return redirect(url_for('cart'))


@app.route('/cart/apply-promo-code', methods=["POST"])
@login_required
@customer_required
def apply_promo_code():
    if request.method == "POST":
        code = request.form.get('promo_code')
        promo_code = db.session.execute(db.select(PromoCodes).where(PromoCodes.code == code)).scalar()
        if promo_code and promo_code.is_active:
            cart = db.session.execute(db.select(Cart).where(Cart.user_id == current_user.user_id)).scalar()
            cart.total_amount -= cart.total_amount * (promo_code.deduction_value / 100)
            cart.code = code
            db.session.commit()
            flash("Promo code applied successfully!", "promo-success")
        else:
            flash("Invalid promo code!", "promo-error")
    return redirect(url_for('cart'))


@app.route('/cart/remove-item/<int:cart_item_id>')
@login_required
@customer_required
def remove_cart_item(cart_item_id):
    cart = db.session.execute(db.select(Cart).where(Cart.user_id == current_user.user_id)).scalar()
    cart_items = db.session.execute(db.select(CartItem).where(CartItem.cart_id == cart.cart_id)).scalars().all()
    cart_item = db.get_or_404(CartItem, cart_item_id)
    if len(cart_items) == 1:
        db.session.delete(cart_item)
        cart.total_amount = 0
        cart.code = None
    else:
        cart.total_amount -= cart_item.amount
        db.session.delete(cart_item)
    db.session.commit()
    return redirect(url_for('cart'))


@app.route('/checkout', methods=["GET", "POST"])
@login_required
@customer_required
def checkout():
    addresses = db.session.execute(db.select(Address).where(Address.user_id == current_user.user_id)).scalars().all()
    cart = db.session.execute(db.select(Cart).where(Cart.user_id == current_user.user_id)).scalar()
    cart_items = db.session.execute(db.select(CartItem).where(CartItem.cart_id == cart.cart_id)).scalars().all()
    item_subtotal = sum(cart_item.amount for cart_item in cart_items)

    if request.method == "POST":
        address_id = request.form.get('selected_address')
        delivery_instructions = request.form.get('delivery_instructions')
        payment_method = request.form.get('selected_payment_option')

        # Create a new order
        new_order = Order(
            user_id=current_user.user_id,
            address_id=address_id,
            delivery_instructions=delivery_instructions,
            payment_method=payment_method,
            total_amount=cart.total_amount + 20,
            code=cart.code
        )

        db.session.add(new_order)
        db.session.commit()

        # Get the latest order
        order = db.session.execute(db.select(Order).order_by(Order.order_id.desc())).scalar()

        # Create order items from cart items
        for cart_item in cart_items:
            new_order_item = OrderItem(
                order_id=order.order_id,
                item_id=cart_item.item_id,
                quantity=cart_item.quantity,
                amount=cart_item.amount
            )
            db.session.add(new_order_item)

        # Clear the cart and delete cart items
        cart.total_amount = 0.0
        cart.code = None

        for cart_item in cart_items:
            db.session.delete(cart_item)

        db.session.commit()

        return redirect(url_for('home'))

    return render_template('checkout.html', addresses=addresses, states=STATES, item_subtotal=item_subtotal)


@app.route('/search-product', methods=["GET", "POST"])
def search_product():
    if request.method == "POST":
        search_query = request.form.get('search-query')
        items = db.session.execute(
            db.select(Item).where(Item.name.ilike(f'%{search_query}%'), Item.in_stock == True,
                                  Item.expiry_date > datetime.now().date())).scalars().all()
        return render_template('search-results.html', items=items, search_query=search_query)


@app.route('/product-details/<int:item_id>')
def product_details(item_id):
    item = db.get_or_404(Item, item_id)

    related = db.session.query(Item).filter(
        and_(
            Item.category_id == item.category_id,
            Item.item_id != item.item_id
        )
    ).limit(4).all()
    return render_template('item-details.html', item=item, related_items=related)


@app.route('/category/<int:category_id>')
def category(category_id):
    category = db.get_or_404(Category, category_id)
    items = db.session.execute(db.select(Item).where(Item.category_id == category_id)).scalars().all()
    return render_template('category.html', category=category, items=items)


@app.route('/addresses')
@login_required
@customer_required
def addresses():
    addresses = db.session.execute(db.select(Address).where(Address.user_id == current_user.user_id)).scalars().all()
    return render_template('account-addresses.html', addresses=addresses, states=STATES)


@app.route('/addresses/create', methods=["POST"])
@login_required
@customer_required
def add_address():
    if request.method == "POST":
        return_url = request.form.get('return_url')
        new_address = Address(
            user_id=current_user.user_id,
            label=request.form.get('label'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            country=request.form.get('country'),
            address1=request.form.get('address1'),
            address2=request.form.get('address2'),
            zip_code=request.form.get('zip')
        )
        db.session.add(new_address)
        db.session.commit()
        return redirect(return_url)


@app.route('/addresses/delete')
@login_required
@customer_required
def delete_address():
    address_id = request.args.get('address_id')
    address = db.get_or_404(Address, address_id)
    db.session.delete(address)
    db.session.commit()
    return redirect(url_for('addresses'))


@app.route('/account-settings', methods=["GET", "POST"])
@login_required
@customer_required
def account_settings():
    user = db.session.execute(
        db.select(User).where(User.user_id == current_user.user_id, User.role == 'customer')).scalar()

    # Get the number of orders of the user
    user.num_orders = db.session.execute(
        db.select(func.count(Order.order_id)).where(Order.user_id == current_user.user_id)).scalar()

    if request.method == "POST":
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename):
                image_data = image.read()
                user.image = image_data
        db.session.commit()
        flash("Account updated successfully!", "account-success")
        return redirect(url_for('account_settings'))

    return render_template('account-settings.html', user=user)


@app.route('/delete-account')
@login_required
@customer_required
def delete_account():
    user = db.get_or_404(User, current_user.user_id)
    # Delete all order items of the user
    db.session.execute(db.delete(OrderItem).where(OrderItem.order.user_id == current_user.user_id))
    # Delete all orders of the user
    db.session.execute(db.delete(Order).where(Order.user_id == current_user.user_id))
    # Delete all addresses of the user
    db.session.execute(db.delete(Address).where(Address.user_id == current_user.user_id))
    # Delete the user's cart items
    db.session.execute(db.delete(CartItem).where(CartItem.cart.user_id == current_user.user_id))
    # Delete the cart of the user
    db.session.execute(db.delete(Cart).where(Cart.user_id == current_user.user_id))


    db.session.delete(user)
    db.session.commit()
    logout_user()
    return redirect(url_for('home'))


@app.route('/orders')
@login_required
@customer_required
def orders():
    # Fetch all orders of the current user
    orders = db.session.execute(db.select(Order).where(Order.user_id == current_user.user_id)).scalars().all()

    # Get number of order items of the order
    for order in orders:
        order_items = db.session.execute(
            db.select(OrderItem).where(OrderItem.order_id == order.order_id)).scalars().all()
        order.num_items = len(order_items)

        print(order.num_items)

    return render_template('orders.html', orders=orders)


@app.route('/change-password', methods=["POST"])
@login_required
@customer_required
def change_password():
    user = db.get_or_404(User, current_user.user_id)
    new_password = request.form.get('new-password')
    current_password = request.form.get('current-password')
    if check_password_hash(user.password, current_password):
        new_password_hash = generate_password_hash(
            new_password,
            method='pbkdf2:sha256',
            salt_length=8
        )
        user.password = new_password_hash
        db.session.commit()
        flash('Password saved successfully!', 'password-success')
        return redirect(url_for('account_settings'))
    else:
        flash("Please enter the correct password for your account.", 'password-error')
        return redirect(url_for('account_settings'))


@app.route('/logout')
@login_required
@customer_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/dashboard/signin', methods=["GET", "POST"])
def dashboard_signin():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        # Find user by email entered
        user = db.session.execute(db.select(User).where(User.email == email, User.role == 'manager')).scalar()

        # Email doesn't exist or password incorrect.
        if not user or not check_password_hash(user.password, password):
            flash("Email or password incorrect")
            return redirect(url_for('dashboard_signin'))
        elif user.role != 'manager':
            flash("Access denied. Manager role required.", "danger")
            return redirect(url_for('dashboard_signin'))
        else:
            login_user(user)
            return redirect(url_for('dashboard'))

    return render_template('dashboard-signin.html')


@app.route('/dashboard/signup', methods=["GET", "POST"])
def dashboard_signup():
    if request.method == "POST":
        email = request.form.get('email')

        # Check if the email is valid (only allow freshcart.com emails)
        if not email.endswith('@freshcart.com'):
            flash("Only FreshCart Admins can sign up for a manager account.")
            return redirect(url_for('dashboard_signup'))

        # Check if a manager with same email exists
        manager = db.session.execute(db.select(User).where(User.email == email, User.role == 'manager')).scalar()

        if manager:
            flash("You've already signed up with that email, sign in instead")
            return redirect(url_for('dashboard_signin'))

        hash_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
        )

        # Create a new manager with the 'manager' role
        new_manager = User(
            email=email,
            password=hash_and_salted_password,
            name=request.form.get('name'),
            role='manager'  # Set the role as 'manager'
        )

        db.session.add(new_manager)
        db.session.commit()
        login_user(new_manager)
        return redirect(url_for('dashboard'))

    return render_template('dashboard-signup.html')


@app.route('/dashboard')
@login_required
@manager_required
def dashboard():
    # Fetch the total amount of all orders in the present month
    total_amount = db.session.execute(
        db.select(func.sum(Order.total_amount)).where(
            func.extract('month', Order.date) == datetime.now().month)).scalar()

    if total_amount is None:
        total_amount = 0

    # Fetch the total number of customers
    total_customers = db.session.execute(db.select(func.count(User.user_id)).where(User.role == 'customer')).scalar()
    # Calculate the date seven days ago
    seven_days_ago = datetime.now() - timedelta(days=7)
    # Query the database to count new customers in the last 7 days
    new_customers = db.session.execute(db.select(func.count(User.user_id)).where(User.role == 'customer',
                                                                                 User.signup_date >= seven_days_ago)).scalar()

    # Fetch the total number of orders
    total_orders = db.session.execute(db.select(func.count(Order.order_id))).scalar()
    # Fetch new orders in the last 7 days
    new_orders = db.session.execute(db.select(func.count(Order.order_id)).where(Order.date >= seven_days_ago)).scalar()

    # Fetch the top 5 most recent orders
    recent_orders = db.session.execute(db.select(Order).order_by(Order.order_id.desc()).limit(5)).scalars().all()

    return render_template('dashboard.html', total_customers=total_customers, new_customers=new_customers,
                           total_orders=total_orders, total_amount=total_amount, new_orders=new_orders,
                           recent_orders=recent_orders)


@app.route('/dashboard/logout')
@login_required
@manager_required
def dashboard_logout():
    logout_user()
    return redirect(url_for('dashboard_signin'))


@app.route('/dashboard/categories')
@login_required
@manager_required
def dashboard_categories():
    categories = db.session.execute(db.select(Category).order_by(Category.category_id)).scalars().all()

    return render_template('dashboard-categories.html', categories=categories)


@app.route('/dashboard/categories/create', methods=["GET", "POST"])
@login_required
@manager_required
def add_category():
    if request.method == "POST":
        category_name = request.form.get("name")
        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename):
                image_data = image.read()  # Read image data as bytes
                new_category = Category(name=category_name, picture=image_data)
                db.session.add(new_category)
                db.session.commit()
                return redirect(url_for('dashboard_categories'))

    return render_template('add-category.html')


@app.route('/dashboard/categories/delete')
@login_required
@manager_required
def delete_category():
    category_id = request.args.get('category_id')
    category = db.get_or_404(Category, category_id)
    db.session.delete(category)
    db.session.commit()
    return redirect(url_for('dashboard_categories'))


@app.route('/dashboard/categories/update', methods=["GET", "POST"])
@login_required
@manager_required
def update_category():
    category_id = request.args.get('category_id')
    category = db.get_or_404(Category, category_id)
    if request.method == "POST":
        updated_name = request.form.get("name")
        if 'image' in request.files:
            updated_image = request.files['image']
            if updated_image and allowed_file(updated_image.filename):
                updated_image_data = updated_image.read()  # Read image data as bytes
                category.name = updated_name
                category.picture = updated_image_data
                db.session.commit()
                return redirect(url_for('dashboard_categories'))
    return render_template('update-category.html', category=category)


@app.route('/dashboard/products')
@login_required
@manager_required
def dashboard_products():
    # Get current datetime
    now = datetime.now().date()
    items = db.session.execute(db.select(Item).order_by(Item.item_id)).scalars().all()
    return render_template('dashboard-products.html', products=items, now=now)


@app.route('/dashboard/products/create', methods=["GET", "POST"])
@login_required
@manager_required
def add_product():
    if request.method == "POST":
        images = [request.files[f'image{i}'] for i in range(1, 5)]
        image_data = []

        # Process each image file
        for image in images:
            if image and allowed_file(image.filename):
                image_bytes = image.read()  # Read image data as bytes
                image_data.append(image_bytes)

        # Create a new Item with multiple images
        new_item = Item(
            name=request.form.get('name'),
            manufacture_date=process_date(request.form.get('manufacture_date')),
            expiry_date=process_date(request.form.get('expiry_date')),
            unit_name=request.form.get('unit'),
            rate_per_unit=int(request.form.get('price')),
            in_stock=process_switch(request.form.get('in_stock')),
            category_id=int(request.form.get('category')),
            picture1=image_data[0] if len(image_data) >= 0 else None,
            picture2=image_data[1] if len(image_data) >= 1 else None,
            picture3=image_data[2] if len(image_data) >= 2 else None,
            picture4=image_data[3] if len(image_data) >= 3 else None
        )

        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('dashboard_products'))

    categories = db.session.execute(db.select(Category)).scalars().all()
    return render_template('add-product.html', categories=categories)


@app.route('/dashboard/products/delete')
@login_required
@manager_required
def delete_product():
    item_id = request.args.get('item_id')
    item = db.get_or_404(Item, item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('dashboard_products'))


@app.route('/dashboard/products/update', methods=["GET", "POST"])
@login_required
@manager_required
def update_product():
    item_id = request.args.get('item_id')
    item = db.get_or_404(Item, item_id)

    if request.method == "POST":
        images = [request.files[f'image{i}'] for i in range(1, 5)]
        image_data = []

        # Process each image file
        for image in images:
            if image and allowed_file(image.filename):
                image_bytes = image.read()
                image_data.append(image_bytes)
            else:
                image_data.append(None)

        # Update the item with new data
        item.name = request.form.get('name')
        item.manufacture_date = process_date(request.form.get('manufacture_date'))
        item.expiry_date = process_date(request.form.get('expiry_date'))
        item.unit_name = request.form.get('unit')
        item.rate_per_unit = int(request.form.get('price'))
        item.in_stock = process_switch(request.form.get('in_stock'))
        item.category_id = int(request.form.get('category'))

        # Update the images if new images were provided
        if any(image_data):
            item.picture1 = image_data[0] if image_data[0] else item.picture1
            item.picture2 = image_data[1] if image_data[1] else item.picture2
            item.picture3 = image_data[2] if image_data[2] else item.picture3
            item.picture4 = image_data[3] if image_data[3] else item.picture4

        db.session.commit()
        return redirect(url_for('dashboard_products'))

    categories = get_all_rows(Category)
    return render_template('update-product.html', product=item, categories=categories)


@app.route('/dashboard/orders')
@login_required
@manager_required
def dashboard_orders():
    orders = db.session.execute(db.select(Order).order_by(Order.order_id.desc())).scalars().all()
    return render_template('dashboard-orders.html', orders=orders)


@app.route('/dashboard/order-expanded/<int:order_id>')
@login_required
@manager_required
def order_expanded(order_id):
    order = db.get_or_404(Order, order_id)
    order_items = db.session.execute(db.select(OrderItem).where(OrderItem.order_id == order_id)).scalars().all()
    # Get order subtotal
    order.subtotal = sum(order_item.amount for order_item in order_items)

    return render_template('dashboard-order-expanded.html', order=order, order_items=order_items)


@app.route('/dashboard/orders/delete')
@login_required
@manager_required
def delete_order():
    order_id = request.args.get('order_id')
    order = db.get_or_404(Order, order_id)
    db.session.delete(order)
    db.session.commit()
    return redirect(url_for('dashboard_orders'))


@app.route('/dashboard/customers')
@login_required
@manager_required
def dashboard_customers():
    customers = db.session.execute(
        db.select(User).where(User.role == 'customer').order_by(User.user_id)).scalars().all()
    return render_template('dashboard-customers.html', customers=customers)


@app.route('/dashboard/customers/delete')
@login_required
@manager_required
def delete_customer():
    customer_id = request.args.get('customer_id')
    customer = db.get_or_404(User, customer_id)
    # Delete all order items of the user
    db.session.execute(db.delete(OrderItem).where(OrderItem.order.user_id == customer_id))
    # Delete all orders of the user
    db.session.execute(db.delete(Order).where(Order.user_id == customer_id))
    # Delete all addresses of the user
    db.session.execute(db.delete(Address).where(Address.user_id == customer_id))
    # Delete the user's cart items
    db.session.execute(db.delete(CartItem).where(CartItem.cart.user_id == customer_id))
    # Delete the cart of the user
    db.session.execute(db.delete(Cart).where(Cart.user_id == customer_id))

    # Delete the user
    db.session.delete(customer)
    db.session.commit()
    return redirect(url_for('dashboard_customers'))


@app.route('/dashboard/account', methods=["GET", "POST"])
@login_required
@manager_required
def dashboard_account():
    user = db.session.execute(
        db.select(User).where(User.user_id == current_user.user_id, User.role == 'manager')).scalar()
    if request.method == "POST":
        user.name = request.form.get('name')
        # Check if the email is valid (only allow freshcart.com emails)
        if not user.email.endswith('@freshcart.com'):
            flash("Please use FreshCart emails for manager account.", "account-error")
            return redirect(url_for('dashboard_account'))
        user.email = request.form.get('email')

        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename):
                image_data = image.read()
                user.image = image_data

        db.session.commit()
        flash("Account updated successfully!", "account-success")
        return redirect(url_for('dashboard_account'))

    return render_template('dashboard-account-settings.html', user=user)


@app.route('/dashboard/change-password', methods=["POST"])
@login_required
@manager_required
def dashboard_change_password():
    user = db.get_or_404(User, current_user.user_id)
    new_password = request.form.get('new-password')
    current_password = request.form.get('current-password')
    if check_password_hash(user.password, current_password):
        new_password_hash = generate_password_hash(
            new_password,
            method='pbkdf2:sha256',
            salt_length=8
        )
        user.password = new_password_hash
        db.session.commit()
        flash('Password saved successfully!', 'password-success')
        return redirect(url_for('dashboard_account'))
    else:
        flash("Please enter the correct password for your account.", 'password-error')
        return redirect(url_for('dashboard_account'))


@app.route('/dashboard/promo-codes', methods=["GET", "POST"])
@login_required
@manager_required
def promo_codes():
    promo_codes = get_all_rows(PromoCodes)
    if request.method == "POST":
        code = request.form.get('code')
        deduction_value = int(request.form.get('value'))
        is_active = process_switch(request.form.get('is_active'))
        new_promo_code = PromoCodes(code=code, deduction_value=deduction_value, is_active=is_active)
        db.session.add(new_promo_code)
        db.session.commit()
        return redirect(url_for('promo_codes'))

    return render_template('dashboard-promo-codes.html', promo_codes=promo_codes)


@app.route('/dashboard/promo-codes/toggle')
@login_required
@manager_required
def toggle_code():
    code = request.args.get('code')
    promo_code = db.get_or_404(PromoCodes, code)
    promo_code.is_active = not promo_code.is_active
    db.session.commit()
    return redirect(url_for('promo_codes'))


@app.route('/dashboard/promo-codes/delete')
@login_required
@manager_required
def delete_code():
    code = request.args.get('code')
    promo_code = db.get_or_404(PromoCodes, code)
    db.session.delete(promo_code)
    db.session.commit()
    return redirect(url_for('promo_codes'))


if __name__ == "__main__":
    app.run(debug=True)
