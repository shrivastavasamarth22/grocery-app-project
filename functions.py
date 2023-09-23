from datetime import datetime
import re
from models import db

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_date(input_str_date):
    # Parse the input date string into a date object
    input_date = datetime.strptime(input_str_date, '%Y-%m-%d').date()
    return input_date


def process_switch(switch_input):
    switch_boolean = switch_input == 'on'
    return switch_boolean


def get_all_rows(model):
    try:
        rows = db.session.execute(db.select(model)).scalars().all()
        return rows
    except Exception as e:
        return None