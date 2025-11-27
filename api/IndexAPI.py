import flask
from flask import render_template, request, redirect
from flask_login import current_user
from sqlalchemy import select, delete, and_
import random

blueprint = flask.Blueprint(
    'IndexAPI',
    __name__,
    template_folder='templates'
)

@blueprint.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')