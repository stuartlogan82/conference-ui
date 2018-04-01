import os
import json
from flask import Flask, request, jsonify, render_template, session, redirect, \
    url_for, flash
from flask_script import Manager, Shell
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand



from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import SyncGrant

from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import SyncGrant

app = Flask(__name__)


TWILIO_SYNC_MAP_SID = "MPa390d0599a4a4be898f028305a95e3b6"



moment = Moment(app)
db = SQLAlchemy(app)
manager = Manager(app)
migrate = Migrate(app, db)

mail = Mail(app)





c







@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)

@app.errorhandler(404)
def page_not_found(e):
    print(e)
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    print(e)
    return render_template('500.html'), 500


@app.route('/events', methods=['POST']) 
def parse_events():
    request_dict = {}
    request_dict = request.form.to_dict()
    print(request_dict)
    event = request_dict['StatusCallbackEvent']
    if 'CallSid' in request_dict:
        call_sid = request_dict['CallSid']
    else:
        call_sid = None
    conference_sid = request_dict['ConferenceSid']
    muted = False if 'Muted' not in request_dict or request_dict['Muted'] == 'false' else True
    print(event)
    client = Client(os.environ.get('TWILIO_ACCOUNT_SID'),
                    os.environ.get('TWILIO_AUTH_TOKEN'))
    if event == 'participant-join':
        
        call = client.calls(call_sid).fetch()
        print(call)
        print("CALL DETAILS {}".format(call.from_formatted))
        participant_number = call.from_formatted if call.direction == "inbound" else call.to_formatted 
        data = {
            "callSid": call_sid,
            "participantNumber": participant_number,
            "direction": call.direction,
            "muted": False,
            "speaking": False,
            "dropped": False
        }
        print("DATA >>> {}".format(data))

        map_item = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
            .sync_maps(TWILIO_SYNC_MAP_SID) \
            .sync_map_items \
            .create(key=call_sid, data=data)

        print("MAP ITEM >>> {}".format(map_item))
        return "OK", 200
    elif event == 'participant-speech-start':
        print("{} >>> SPEAKING!".format(call_sid))

        current_data = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
                    .sync_maps(TWILIO_SYNC_MAP_SID) \
                    .sync_map_items(call_sid) \
                    .fetch()
        new_data = current_data.data
        new_data["speaking"] = True
        data = json.dumps(new_data)
        map_item = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
                    .sync_maps(TWILIO_SYNC_MAP_SID) \
                    .sync_map_items(call_sid) \
                    .update(data=str(data))
        return "OK", 200

    elif event == 'participant-speech-stop':
        print("{} >>> STOPPED SPEAKING!".format(call_sid))
        current_data = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
                    .sync_maps(TWILIO_SYNC_MAP_SID) \
                    .sync_map_items(call_sid) \
                    .fetch()
        new_data = current_data.data
        new_data["speaking"] = False
        data = json.dumps(new_data)
        map_item = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
                    .sync_maps(TWILIO_SYNC_MAP_SID) \
                    .sync_map_items(call_sid) \
                    .update(data=str(data))
        return "OK", 200

    elif event == 'participant-leave':
        print("{} >>> LEFT THE CONFERENCE!".format(call_sid))
        current_data = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
                    .sync_maps(TWILIO_SYNC_MAP_SID) \
                    .sync_map_items(call_sid) \
                    .fetch()
        new_data = current_data.data
        new_data["speaking"] = False
        new_data["muted"] = False
        new_data["dropped"] = True
        data = json.dumps(new_data)
        map_item = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
                    .sync_maps(TWILIO_SYNC_MAP_SID) \
                    .sync_map_items(call_sid) \
                    .update(data=str(data))
        return "OK", 200
    elif event == 'conference-end':
        delete_map_items()
        return "ITEMS DELETED", 200
    elif event == 'participant-mute':
        print("{} >>> MUTED!".format(call_sid))

        current_data = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
                    .sync_maps(TWILIO_SYNC_MAP_SID) \
                    .sync_map_items(call_sid) \
                    .fetch()
        new_data = current_data.data
        new_data["muted"] = True
        data = json.dumps(new_data)
        map_item = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
                    .sync_maps(TWILIO_SYNC_MAP_SID) \
                    .sync_map_items(call_sid) \
                    .update(data=str(data))
        return "OK", 200
    elif event == 'participant-unmute':
        print("{} >>> UNMUTED!".format(call_sid))

        current_data = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
                    .sync_maps(TWILIO_SYNC_MAP_SID) \
                    .sync_map_items(call_sid) \
                    .fetch()
        new_data = current_data.data
        new_data["muted"] = False
        data = json.dumps(new_data)
        map_item = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
                    .sync_maps(TWILIO_SYNC_MAP_SID) \
                    .sync_map_items(call_sid) \
                    .update(data=str(data))
        return "OK", 200
    else:
        print("EVENT >>> {}".format(event))
        return "OK", 200

@app.route('/token')
def token():
    # get the userid from the incoming request
    identity = request.values.get('identity', None)
    # Create access token with credentials
    token = AccessToken(TWILIO_ACCOUNT_SID, TWILIO_API_KEY,
                        TWILIO_API_SECRET, identity=identity)
    # Create a Sync grant and add to token
    sync_grant = SyncGrant(service_sid=TWILIO_SYNC_SERVICE_SID)
    token.add_grant(sync_grant)
    # Return token info as JSON
    return jsonify(identity=identity, token=token.to_jwt().decode('utf-8'))

@app.route('/delete_map_items')
def delete_map_items():
    client = Client(os.environ.get('TWILIO_ACCOUNT_SID'),
                    os.environ.get('TWILIO_AUTH_TOKEN'))

    conference_map = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
        .sync_maps(TWILIO_SYNC_MAP_SID) \
        .sync_map_items \
        .list()

    print(conference_map)

    for item in conference_map:
        print("ITEM >>> ")
        print(item)
        delete_item = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
            .sync_maps(TWILIO_SYNC_MAP_SID) \
            .sync_map_items(item.key) \
            .delete()

        print("MAP ITEM DELETED >>> {}".format(delete_item))
    return "OK", 200

@app.route('/dial', methods=['GET', 'POST'])
def dial():
    print(request.json)
    number = request.json['number']
    print(number)
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    call = client.calls.create(
        to=number,
        from_=TWILIO_NUMBER,
        url="https://handler.twilio.com/twiml/EH9cb1bd0b596dc3eb8eb2cff6df11f0ae"
    )

    return "OK", 200

@app.route('/mute', methods=['POST'])
def mute():
    participant = request.json['participant']
    mute_on = request.json['muteOn']
    conf_sid = request.json['conferenceSid']
    client = Client(current_user.twilio_account_sid, current_user.twilio_auth_token)

    participant = client.conferences('StusConference') \
                    .participants(participant) \
                    .update(muted=mute_on)

    return participant.muted, 200



