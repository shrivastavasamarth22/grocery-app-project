from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


# CREATE TABLES

class User(db.Model, UserMixin):
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'customer' or 'manager'
    image = db.Column(db.LargeBinary, nullable=True)
    signup_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def get_id(self):
        return self.user_id

    def __repr__(self):
        return f"<User(user_id={self.user_id}, email='{self.email}', name='{self.name}', role='{self.role}')>"


class Category(db.Model):
    category_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    picture = db.Column(db.LargeBinary)

    def __repr__(self):
        return f"<Category(category_id={self.category_id}, name='{self.name}')>"


class Item(db.Model):
    item_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    manufacture_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    unit_name = db.Column(db.String(50), nullable=False)
    rate_per_unit = db.Column(db.Integer, nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'))
    picture1 = db.Column(db.LargeBinary)  # First image
    picture2 = db.Column(db.LargeBinary)  # Second image
    picture3 = db.Column(db.LargeBinary)  # Third image
    picture4 = db.Column(db.LargeBinary)  # Fourth image

    category = db.relationship('Category', backref=db.backref('items', lazy=True))

    def __repr__(self):
        return f"<Item(item_id={self.item_id}, name='{self.name}', rate_per_unit={self.rate_per_unit}, in_stock={self.in_stock}, manufacture_date={self.manufacture_date}, expiry_date={self.expiry_date}>"

class Cart(db.Model):
    cart_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    code = db.Column(db.String(20), db.ForeignKey('promo_codes.code'), nullable=True)

    user = db.relationship('User', backref=db.backref('carts', lazy=True))
    promo_code = db.relationship('PromoCodes', backref=db.backref('carts', lazy=True))

    def __repr__(self):
        return f"<Cart(cart_id={self.cart_id}, user_id={self.user_id}, total_amount={self.total_amount})>"

class CartItem(db.Model):
    cart_item_id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.cart_id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.item_id'))
    quantity = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)

    item = db.relationship('Item', backref=db.backref('cart_items', lazy=True))
    cart = db.relationship('Cart', backref=db.backref('cart_items', lazy=True))

    def __repr__(self):
        return f"<CartItem(cart_item_id={self.cart_item_id}, item_id={self.item_id}, quantity={self.quantity}, amount={self.amount})>"


class Order(db.Model):
    order_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    address_id = db.Column(db.Integer, db.ForeignKey('address.address_id'))
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    code = db.Column(db.String(20), db.ForeignKey('promo_codes.code'), nullable=True)
    payment_method = db.Column(db.String(20), nullable=False)
    delivery_instructions = db.Column(db.String(200))
    total_amount = db.Column(db.Float, nullable=False)

    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    address = db.relationship('Address', backref=db.backref('orders', lazy=True))
    promo_code = db.relationship('PromoCodes', backref=db.backref('orders', lazy=True))

    def __repr__(self):
        return f"<Order(order_id={self.order_id}, user_id={self.user_id}, total_amount={self.total_amount})>"


class OrderItem(db.Model):
    order_item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.order_id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.item_id'))
    quantity = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)

    item = db.relationship('Item', backref=db.backref('order_items', lazy=True))
    order = db.relationship('Order', backref=db.backref('order_items', lazy=True))

    def __repr__(self):
        return f"<OrderItem(order_item_id={self.order_item_id}, order_id={self.order_id}, item_id={self.item_id}, quantity={self.quantity}, amount={self.amount})>"


class Address(db.Model):
    address_id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), nullable=False)
    address1 = db.Column(db.String(150), nullable=False)
    address2 = db.Column(db.String(150))
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(150), nullable=False)
    state = db.Column(db.String(150), nullable=False)
    zip_code = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))

    user = db.relationship('User', backref=db.backref('addresses', lazy=True))

class PromoCodes(db.Model):
    code = db.Column(db.String(20), primary_key=True)
    deduction_value = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<PromoCode(code={self.code}, deduction_value={self.deduction_value})>"
