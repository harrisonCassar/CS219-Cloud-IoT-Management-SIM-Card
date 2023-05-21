#!/usr/bin/env python

# For Flask form documentation, refer to: https://python-adv-web-apps.readthedocs.io/en/latest/flask_forms.html

from flask import Flask, render_template, redirect, url_for, jsonify, request, make_response
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
# from flask_wtf.csrf import CSRFProtect

import os
from datetime import datetime

from .backend.util import send_change_carrier_message

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
MAX_CARRIER = 5 # TODO: Specify actual list, perhaps with ENUMs

###################### on-server startup ######################

# init front-end info channels/state
current_carrier = 0 # 0 is an "invalid" carrier; this will change once we use ENUMs to specify carriers.

######################## Flask support ########################

# globals
app = Flask(__name__, static_folder='static')

# Flask-WTF Forms
Bootstrap(app)
# csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = 'tfz1wBgMIh3r8aYRivXuo4imp6B7C9Aa' # Flask-WTF requires any encryption key.

class ChangeCarrierForm(FlaskForm):
    carrier = StringField('Carrier', validators=[DataRequired()])
    submit = SubmitField('Submit')

######################## Util functions #######################

# def some_util_function():
#     pass

######################## Flask endpoints #######################

## pages

@app.route("/", methods=['POST', 'GET'])
def index():

    form_change_carrier = ChangeCarrierForm()

    return render_template(
        "index.html",
        current_carrier=current_carrier,
        form_change_carrier=form_change_carrier)


@app.route('/about')
def about():
    return render_template('about.html')


## routines

@app.route("/carrier_switch", methods=['POST'])
def carrier_switch():
    global current_carrier

    form_change_carrier = ChangeCarrierForm()

    # Change carrier to specification
    if form_change_carrier.validate_on_submit():

        # Extract useful form data.
        new_carrier_raw = form_change_carrier.carrier.data

        # Check carrier is valid.
        if not new_carrier_raw.isnumeric() or int(new_carrier_raw) > MAX_CARRIER:
            # TODO: Pass/indicate error to front-end; but for now, let's just ignore (perhaps we can perform this validation with a custom validator as a part of WTF forms?)
            return redirect(url_for('index'))
        
        new_carrier = int(new_carrier_raw)

        # Switch carrier (send message + get ACK successfully + update our tracked state)
        if send_change_carrier_message(new_carrier):
            current_carrier = new_carrier
        else:
            # TODO: Implement better error handling (tell user that we've somehow failed to send the message/get an ACK from the SIM card that we've changed the carrier!)
            print("We had an error changing carrier!")
            return redirect(url_for('index'))

    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)