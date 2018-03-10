from flask import current_app
from twilio.rest import Client


def twilio_lookup(number):
    app = current_app._get_current_object()
    client = Client(app.config['TWILIO_ACCOUNT_SID'],
                    app.config['TWILIO_AUTH_TOKEN'])

    number = client.lookups.phone_numbers(number).fetch(type="carrier")


    return number

