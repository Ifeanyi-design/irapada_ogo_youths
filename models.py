from datetime import datetime
from extensions import db
from flask_login import UserMixin

# =================== USERS ===================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(500), nullable=False)
    gender = db.Column(db.String(10))
    profile_image = db.Column(db.String(100))
    admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One user can have multiple pre_users (staging records)
    pre_users = db.relationship('PreUser', backref='user', lazy=True)

# =================== PRE-USERS ===================
class PreUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # linked when registered
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tables = db.relationship('Table', backref='pre_user', lazy=True)
    contents = db.relationship('Content', backref='pre_user_owner', lazy=True)

# =================== TABLES ===================
class Table(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pre_user_id = db.Column(db.Integer, db.ForeignKey('pre_user.id'))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))

    # Relationships
    columns = db.relationship('Column', backref='table', lazy=True)
    contents = db.relationship('Content', backref='table_owner', lazy=True)

# =================== COLUMNS ===================
class Column(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    datatype = db.Column(db.String(50), default='string')

# =================== CONTENTS / CONTRIBUTIONS ===================
class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'), nullable=True)
    pre_user_id = db.Column(db.Integer, db.ForeignKey('pre_user.id'), nullable=True)
    column_id = db.Column(db.Integer, db.ForeignKey('column.id'), nullable=True)
    value = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Optional relationships for easy access
    column = db.relationship('Column')
    table = db.relationship('Table')
    pre_user = db.relationship('PreUser')
