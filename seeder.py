from app import app
from extensions import db
from models import User, PreUser, Table, Column, Content
from werkzeug.security import generate_password_hash, check_password_hash

with app.app_context():
    # Drop all tables and recreate them (optional)
    db.drop_all()
    db.create_all()

    # ------------------- CREATE A USER -------------------
    user1 = User(name="Ifeanyi Agada", email="ifeanyiagada123@gmail.com", password_hash=generate_password_hash("ifeanyi123"), admin=True)
    db.session.add(user1)
    db.session.commit()

    # ------------------- CREATE A PRE-USER -------------------
    pre1 = PreUser(name="Ifeanyi Agada", email="ifeanyiagada123@gmail.com", user_id=user1.id)
    db.session.add(pre1)
    db.session.commit()



    print("Database seeded successfully with one contributions table!")
