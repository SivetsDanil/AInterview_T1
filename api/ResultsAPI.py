import flask
from flask import render_template, request, redirect


blueprint = flask.Blueprint(
    'ResultsAPI',
    __name__,
    template_folder='templates'
)

@blueprint.route('/results', methods=['GET', 'POST'])
def index():
    return render_template('results.html')