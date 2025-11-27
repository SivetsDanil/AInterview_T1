import flask
from flask import render_template, request, redirect
from flask_login import current_user
from sqlalchemy import select, delete, and_
import random

blueprint = flask.Blueprint(
    'ResultsAPI',
    __name__,
    template_folder='templates'
)

@blueprint.route('/results', methods=['GET', 'POST'])
def index():
    return render_template('results.html')