import flask
from flask import render_template, request, redirect


blueprint = flask.Blueprint(
    'InterviewAPI',
    __name__,
    template_folder='templates'
)

@blueprint.route('/interview', methods=['GET', 'POST'])
def index():
    return render_template('interview.html')