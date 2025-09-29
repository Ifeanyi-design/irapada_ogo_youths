from flask import Flask, render_template, redirect, url_for, flash, request, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, PreUser, Table, Column, Content
import csv
from datetime import datetime, timedelta
from extensions import db
import os
from werkzeug.utils import secure_filename
from collections import defaultdict
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///youth.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def home():
    return redirect(url_for('dashboard'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        gender = request.form.get('gender')

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.')
            return redirect(url_for('register'))

        # Create new user
        new_user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            gender=gender
        )
        db.session.add(new_user)
        db.session.commit()



        flash('Registration successful. Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login successful!')
            return redirect(url_for('dashboard'))

        flash('Invalid email or password.')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    pre_user = current_user.pre_users[0] if current_user.pre_users else None
    tables = pre_user.tables if pre_user else []

    # Admin data
    users = User.query.all() if current_user.admin else None
    pre_users_list = PreUser.query.all() if current_user.admin else [pre_user] if pre_user else []

    table_map = defaultdict(list)  # table_id -> list of Content objects

    if pre_user:
        # Fetch contributions
        if current_user.admin:
            contributions = Content.query.order_by(Content.created_at.desc()).all()
        else:
            contributions = Content.query.filter_by(pre_user_id=pre_user.id).order_by(Content.created_at.desc()).all()

        # Group contributions by table
        for c in contributions:
            table_map[c.table_id].append(c)

    # Prepare columns for the first table to show headers in template
    columns = []
    if table_map:
        first_table_id = next(iter(table_map))
        columns = list({c.column for c in table_map[first_table_id] if c.column})

    return render_template(
        'dashboard.html',
        tables=tables,
        users=users,
        pre_users=pre_users_list,
        table_map=table_map,
        columns=columns
    )



@app.route('/account-settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        gender = request.form.get('gender')
        profile_image = request.files.get('profile_image')

        current_user.name = name
        current_user.gender = gender

        if email and email != current_user.email:
            if User.query.filter_by(email=email).first():
                flash('Email already in use.', 'error')
                return redirect(url_for('account_settings'))
            current_user.email = email

        if password:
            current_user.password_hash = generate_password_hash(password)

        if profile_image:
            filename = secure_filename(f"user_{current_user.id}_{profile_image.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_image.save(filepath)
            current_user.profile_image = filename

        db.session.commit()
        flash('Account updated successfully.', 'success')
        return redirect(url_for('account_settings'))

    return render_template('account_settings.html', user=current_user)

@app.route('/admin/log-contribution', methods=['GET', 'POST'])
@login_required
def admin_log_contribution():
    if not current_user.admin:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    pre_users = PreUser.query.all()
    tables = Table.query.all()

    # Prepare table-columns mapping for JS
    all_columns_for_table = {t.id: [{'id': c.id, 'name': c.name} for c in t.columns] for t in tables}

    if request.method == 'POST':
        pre_user_id = request.form.get('pre_user_id')
        table_id = request.form.get('table_select')

        if not pre_user_id or not table_id:
            flash('Please select a PreUser and Table.', 'error')
            return redirect(url_for('admin_log_contribution'))

        pre_user = PreUser.query.get(int(pre_user_id))
        table = Table.query.get(int(table_id))

        # Save contribution for each column
        for column in table.columns:
            value = request.form.get(f'column_{column.id}', '')
            content = Content(
                pre_user_id=pre_user.id,
                table_id=table.id,
                column_id=column.id,
                value=value
            )
            db.session.add(content)

        db.session.commit()
        flash(f'Contributions for {pre_user.name} logged successfully.', 'success')
        return redirect(url_for('admin_log_contribution'))

    return render_template(
        'admin_log_contribution.html',
        pre_users=pre_users,
        tables=tables,
        all_columns_for_table=all_columns_for_table
    )


@app.route('/contributions')
@login_required
def contributions():
    if current_user.admin:
        contributions = Content.query.order_by(Content.created_at.desc()).all()
        pre_users = PreUser.query.all()
    else:
        pre_user = current_user.pre_users[0] if current_user.pre_users else None
        if not pre_user:
            flash('No data available.', 'error')
            return redirect(url_for('dashboard'))
        contributions = (
            Content.query
            .filter_by(pre_user_id=pre_user.id)
            .order_by(Content.created_at.desc())
            .all()
        )
        pre_users = [pre_user]

    # Group contributions by table (like dashboard)
    table_map = defaultdict(list)  # table_id -> list of Content objects
    for c in contributions:
        table_map[c.table_id].append(c)

    # Prepare columns per table (deduplicated)
    columns_map = {}
    for table_id, contribs in table_map.items():
        columns_map[table_id] = list({c.column for c in contribs if c.column})

    return render_template(
        'contributions.html',
        table_map=table_map,
        pre_users=pre_users,
        columns_map=columns_map
    )

@app.route('/log-contribution', methods=['GET', 'POST'])
@login_required
def log_contribution():
    pre_user = current_user.pre_users[0] if current_user.pre_users else None
    if not pre_user:
        flash('No PreUser linked to your account.', 'error')
        return redirect(url_for('dashboard'))

    tables = Table.query.filter_by(pre_user_id=pre_user.id).all()
    columns = Column.query.join(Table).filter(Table.pre_user_id == pre_user.id).all()

    if request.method == 'POST':
        table_id = int(request.form.get('table_id'))
        column_id = int(request.form.get('column_id'))
        value = request.form.get('value')

        content = Content(pre_user_id=pre_user.id, table_id=table_id, column_id=column_id, value=value)
        db.session.add(content)
        db.session.commit()
        flash('Contribution logged successfully.', 'success')
        return redirect(url_for('contributions'))

    return render_template('log_contribution.html', tables=tables, columns=columns)


@app.route('/admin/mass-data')
@login_required
def admin_mass_data():
    if not current_user.admin:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    # Get all users and preusers
    users = User.query.all()
    pre_users = PreUser.query.filter(PreUser.user_id == None).all()  # unlinked PreUsers

    return render_template('admin_dashboard.html', users=users, pre_users=pre_users)


@app.route('/admin/preusers', methods=['GET', 'POST'])
@login_required
def admin_preuser():
    if not current_user.admin:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        gender = request.form.get('gender')

        pre_user = PreUser(name=name, email=email, phone=phone, gender=gender)
        db.session.add(pre_user)
        db.session.commit()
        flash('PreUser created successfully.')
        return redirect(url_for('admin_preuser'))

    pre_users = PreUser.query.all()
    return render_template('admin_preuser.html', pre_users=pre_users)


@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if not current_user.admin:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    users = User.query.filter(User.id != current_user.id).all()  # exclude self

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')  # 'make_admin' or 'remove_admin'

        user = User.query.get(int(user_id))
        if user:
            if action == 'make_admin':
                user.admin = True
            elif action == 'remove_admin':
                user.admin = False
            db.session.commit()
            flash('User role updated successfully.')
        return redirect(url_for('admin_users'))

    return render_template('admin_users.html', users=users)


@app.route('/admin/create-table', methods=['GET', 'POST'])
@login_required
def admin_create_table():
    if not current_user.admin:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    pre_users = PreUser.query.all()

    if request.method == 'POST':
        pre_user_id = int(request.form.get('pre_user_id'))
        table_name = request.form.get('table_name')
        description = request.form.get('description')

        table = Table(pre_user_id=pre_user_id, name=table_name, description=description)
        db.session.add(table)
        db.session.commit()
        flash('Table created successfully.')
        return redirect(url_for('admin_create_table'))

    return render_template('admin_create_table.html', pre_users=pre_users)

@app.route('/admin/add-column', methods=['GET', 'POST'])
@login_required
def admin_add_column():
    if not current_user.admin:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    tables = Table.query.all()

    if request.method == 'POST':
        table_id = int(request.form.get('table_id'))
        column_name = request.form.get('column_name')
        datatype = request.form.get('datatype')

        column = Column(table_id=table_id, name=column_name, datatype=datatype)
        db.session.add(column)
        db.session.commit()
        flash('Column added successfully.')
        return redirect(url_for('admin_add_column'))

    return render_template('admin_add_column.html', tables=tables)



@app.route('/admin/merge', methods=['GET', 'POST'])
@login_required
def admin_merge():
    if not current_user.admin:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    # PreUsers without a linked user
    unlinked_preusers = PreUser.query.filter_by(user_id=None).all()
    # Users without a linked preuser
    unlinked_users = User.query.filter(~User.pre_users.any()).all()

    if request.method == 'POST':
        pre_user_id = int(request.form.get('pre_user_id'))
        user_id = int(request.form.get('user_id'))

        pre_user = PreUser.query.get(pre_user_id)
        user = User.query.get(user_id)

        # Link them
        pre_user.user_id = user.id
        db.session.commit()
        flash(f'{pre_user.name} is now linked to {user.name}.')
        return redirect(url_for('admin_merge'))

    return render_template('admin_merge.html', preusers=unlinked_preusers, users=unlinked_users)


@app.route('/admin/export-filtered', methods=['GET', 'POST'])
@login_required
def admin_export_filtered():
    if not current_user.admin:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))

    pre_users = PreUser.query.all()
    tables = Table.query.all()

    if request.method == 'POST':
        pre_user_id = int(request.form.get('pre_user_id', 0))
        table_id = int(request.form.get('table_id', 0))
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        query = Content.query
        if pre_user_id:
            query = query.filter(Content.pre_user_id == pre_user_id)
        if table_id:
            query = query.filter(Content.table_id == table_id)
        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Content.created_at >= start_date)
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Content.created_at < end_date)

        contributions = query.all()

        def generate_csv():
            data = [['PreUser Name', 'User Name', 'Table', 'Column', 'Value', 'Date Logged']]
            for c in contributions:
                preuser_name = c.pre_user_owner.name if c.pre_user_owner else 'N/A'
                user_name = c.pre_user_owner.user.name if c.pre_user_owner and c.pre_user_owner.user else 'Not Registered'
                table_name = c.table_owner.name if c.table_owner else 'N/A'
                column_name = c.column.name if c.column else 'N/A'
                data.append([
                    preuser_name,
                    user_name,
                    table_name,
                    column_name,
                    c.value,
                    c.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])
            csv_file = csv.StringIO()
            writer = csv.writer(csv_file)
            for row in data:
                writer.writerow(row)
            csv_file.seek(0)
            return csv_file.getvalue()

        response = Response(generate_csv(), mimetype='text/csv')
        response.headers.set("Content-Disposition", "attachment", filename="filtered_contributions.csv")
        return response

    return render_template('admin_export_filtered.html', pre_users=pre_users, tables=tables)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)