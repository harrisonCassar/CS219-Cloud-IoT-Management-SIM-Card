"""Flask app for the Main Flask 'Cloud-based' Server to take-in user input and expose data visualizations.

Author:
    Harrison Cassar, May 2023
"""

# For Flask form documentation, refer to: https://python-adv-web-apps.readthedocs.io/en/latest/flask_forms.html

import os

from flask import Flask, render_template, redirect, url_for, jsonify, request, make_response
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired
# from flask_wtf.csrf import CSRFProtect

from backend.util import send_change_carrier_message
from common.protocol_headers import CarrierIdField, gen_carrier_to_carrier_id_mapping

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
MAX_CARRIER = 5 # TODO: Specify actual list, perhaps with ENUMs

###################### on-server startup ######################

# init front-end info channels/state
current_carrier = 'Unknown'

# init helpful lookups
carrier_to_carrier_id_map = gen_carrier_to_carrier_id_mapping()
carrier_switch_choices = [
    ('AT&T',     'AT&T'),
    ('T-Mobile', 'T-Mobile'),
    ('Verizon',  'Verizon'),
    ('Invalid',  'Disconnect'),
]

######################## Flask support ########################

# globals
app = Flask(__name__, static_folder='static')

# Flask-WTF Forms
Bootstrap(app)
# csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = 'tfz1wBgMIh3r8aYRivXuo4imp6B7C9Aa' # Flask-WTF requires any encryption key.

class ChangeCarrierForm(FlaskForm):
    carrier = SelectField('Carrier', choices=carrier_switch_choices, validate_choice=True)
    submit = SubmitField('Submit')

######################## Util functions #######################

# def some_util_function():
#     pass

######################## Flask endpoints #######################

## pages

@app.route("/", methods=['POST', 'GET'])
def index():

    form_change_carrier = ChangeCarrierForm(carrier=(current_carrier if current_carrier != 'Unknown' and current_carrier != 'Disconnected' else 'Invalid'))

    return render_template(
        "index.html",
        current_carrier=current_carrier,
        form_change_carrier=form_change_carrier)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/grafana')
def grafana_home():
    # TODO: Make this URL non-hardcoded, perhaps using Docker-compose...?
    return redirect('http://localhost:8001/')


## routines

@app.route("/carrier_switch", methods=['POST'])
def carrier_switch():
    global current_carrier

    form_change_carrier = ChangeCarrierForm()

    # Change carrier to specification
    if form_change_carrier.validate_on_submit():

        # Extract useful form data.
        new_carrier_raw = form_change_carrier.carrier.data
        new_carrier = carrier_to_carrier_id_map.get(new_carrier_raw)

        # Switch carrier (send message + get ACK successfully + update our tracked state)
        if send_change_carrier_message(new_carrier):
            if new_carrier == CarrierIdField.INVALID:
                current_carrier = 'Disconnected'
            else:
                current_carrier = new_carrier_raw
        else:
            # TODO: Actually implement checking for NACK/error handling (tell user that we've somehow failed to send the message/get an ACK from the SIM card that we've changed the carrier!)
            print("We had an error changing carrier!")
            return redirect(url_for('index'))

    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)