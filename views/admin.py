from flask import Blueprint
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from app import db
from models.people_model import Person

admin_page = Blueprint("admin", __name__, static_folder="static", template_folder="templates")

admin = Admin(template_mode='bootstrap3')

# adds the database model to the Admin panel
admin.add_view(ModelView(Person, db.session))