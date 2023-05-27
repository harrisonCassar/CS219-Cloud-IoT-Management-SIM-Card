"""Flask app for the Main Flask 'Cloud-based' Server to take-in user input and expose data visualizations.

Author:
    Harrison Cassar, May 2023
"""

# For Flask form documentation, refer to: https://python-adv-web-apps.readthedocs.io/en/latest/flask_forms.html

import os
import json

from flask import Flask, render_template, redirect, url_for, jsonify, request, make_response
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired
# from flask_wtf.csrf import CSRFProtect

from confluent_kafka import Producer

from backend.util import send_change_carrier_message

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
DEFAULT_KAFKA_ADDRESS = "kafka"
DEFAULT_KAFKA_PORT = 29092
KAFKA_TOPIC_DOWNSTREAM_REQUESTS = 'downstream-request'

######################## Helper functions #######################

def producer_error_cb(err):
    print(f'ERROR with Kafka Producer: {err}')

def handle_producer_event_cb(err, msg):
    if err is not None:
        print(f'ERROR when attempting to produce a Kafka message: {err}')
    else:
        print(f'Produced message on topic {msg.topic()} with value of {msg.value().decode("utf-8")}')

###################### on-server startup ######################

# init front-end info channels/state
current_carrier = 'Unknown'

# init helpful lookups
carrier_switch_choices = [
    ('AT&T',     'AT&T'),
    ('T-Mobile', 'T-Mobile'),
    ('Verizon',  'Verizon'),
    ('Disconnect',  'Disconnect'),
]

# Setup Kafka Producer.
producer = Producer({
    'bootstrap.servers':f'{DEFAULT_KAFKA_ADDRESS}:{DEFAULT_KAFKA_PORT}',
    "error_cb": producer_error_cb
})

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
    # TODO: Attempt to get Grafana going.
    return redirect('http://localhost:3000/')


## routines

@app.route("/carrier_switch", methods=['POST'])
def carrier_switch():
    global current_carrier

    form_change_carrier = ChangeCarrierForm()

    # Change carrier to specification
    if form_change_carrier.validate_on_submit():

        # Extract useful form data.
        new_carrier = form_change_carrier.carrier.data

        # NOTE: Due to possible unknown behavior at Modem/SIM causing an unexpected carrier switch,
        # we cannot safely/confidently rely on a cached "current carrier" value at front-end.
        # Therefore, we'll always send the message.
        #
        # if new_carrier == current_carrier:
        #     print("Already switched to this carrier!")
        #     return redirect(url_for('index'))

        # Format a "Carrier Switch Perform" request.
        msg = {
            'type'      : 'carrier-switch-perform',
            'metadata'  : new_carrier
        }
        msg_raw = json.dumps(msg).encode('utf-8')

        # Send Carrier Switch Perform request to Kafka. This will kickstart the process, but our held state will only be reflected once an ACK is received through the "carrier_switch_status" endpoint.
        producer.poll(0)
        producer.produce(KAFKA_TOPIC_DOWNSTREAM_REQUESTS, msg_raw, callback=handle_producer_event_cb)
        producer.flush()

        # Update current carrier switch state.
        # TODO: Represent Carrier Switch state as "In Progress" and DON'T change current carrier state just yet. Let some other endpoint set this status ("carrier_switch_status" endpoint).
        if new_carrier == 'Disconnect':
            current_carrier = 'Disconnected'
        else:
            current_carrier = new_carrier

    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)