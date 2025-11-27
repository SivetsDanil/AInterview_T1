import flask
from flask import render_template, request, redirect


blueprint = flask.Blueprint(
    'IndexAPI',
    __name__,
    template_folder='templates'
)

@blueprint.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')