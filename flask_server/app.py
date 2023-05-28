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

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
DEFAULT_KAFKA_ADDRESS = "kafka"
DEFAULT_KAFKA_PORT = 29092
DEFAULT_GRAFANA_ADDRESS = "localhost" # Grafana exposes itself on the host at port 3000
DEFAULT_GRAFANA_PORT = 3000
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
# TODO: Perhaps use ENUMs...? Better style + more robust to change down the road.
# TODO: See if we can get this to be live-updated on the browser page? Currently just static, and only updates once the user refreshes the page.
current_carrier = 'Unknown'
carrier_switch_status = 'Not yet started' # Current options: "Not yet started", "Success", "Failure", "In progress", "Unknown"

# init helpful lookups
carrier_switch_choices = ['AT&T', 'T-Mobile', 'Verizon', 'Disconnect']

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
        carrier_switch_status=carrier_switch_status,
        form_change_carrier=form_change_carrier)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/grafana')
def grafana_home():
    return redirect(f'http://localhost:{DEFAULT_GRAFANA_PORT}')


## routines

@app.route('/carrier_switch_status', methods=['POST'])
def carrier_switch_status_update():

    global current_carrier
    global carrier_switch_status

    # Extract (and validate) relevant arguments representing our status.
    args_dict = request.get_json(force=True) # force=True necessary posting forgot to set MIME type to 'application/json'

    status_raw = args_dict.get('status')
    modem_current_carrier = args_dict.get('carrier')

    if not status_raw or not modem_current_carrier:
        print("ERROR: Post of Carrier Switch status is missing arguments.")
        return redirect(url_for('index'))

    print(f"Post of Carrier Switch status: {status_raw}, {modem_current_carrier}")

    # Assume that the Modem's current carrier is a valid carrier choice.
    # Perhaps this is reasonable anyway, as maybe we only want to support a certain
    # set of carriers with this cloud interface, but the Modem/SIM may have more that
    # it can possibly be set to.
    #
    # if modem_current_carrier not in carrier_switch_choices:
    #     print(f"ERROR: Post of Carrier Switch status indicates a carrier that is not supported {modem_current_carrier}.")
    #     return redirect(url_for('index'))

    # Decode status, and update our internal state.
    if status_raw == 'ACK':
        carrier_switch_status = "Success"
        current_carrier = modem_current_carrier
    elif status_raw == 'NACK':
        carrier_switch_status = "Failure"
        current_carrier = modem_current_carrier
    else:
        print(f"ERROR: Received unknown Carrier Switch status {status_raw}.")
        carrier_switch_status = "Unknown"
        current_carrier = "Unknown"

    return redirect(url_for('index'))


@app.route("/carrier_switch", methods=['POST'])
def carrier_switch():

    global current_carrier
    global carrier_switch_status

    form_change_carrier = ChangeCarrierForm()

    # TODO: Perhaps add some kind of check for if we've already begun a request?
    # This will avoid unncessary communication + protect spamming of carrier switch.
    # We should, however, add some form of timeout in case the UDP server and/or Modem client
    # experience some problem that prevents an ACK being sent back through the above
    # "carrier_switch_status" endpoint. Perhaps we can use Flask's Celery plugin for this..?
    #
    # if carrier_switch_status != 'Not yet started' and carrier_switch_status != 'Success':
    #     print("Cannot start a Carrier Switch Request until the previous one has been resolved.")

    # Change carrier to specification.
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
        carrier_switch_status = 'In progress'

    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)