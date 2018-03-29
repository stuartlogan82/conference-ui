import json
from flask import render_template, session, redirect, url_for, current_app, request
from . import main
from .forms import NameForm
from .. import db
from ..models import User, Participant
from ..models import Conference as UserConference
from ..email import send_email
from twilio.twiml.voice_response import Conference, Dial, VoiceResponse, Say
from twilio.rest import Client


@main.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user = User(username=form.name.data)
            db.session.add(user)
            session['known'] = False
            if current_app.config['ADMIN']:
                send_email(current_app.config['ADMIN'], 'New User',
                            'mail/new_user', user=user)
        else:
            session['known'] = True
        session['name'] = form.name.data
        return redirect(url_for('.index'))
    return render_template('index.html', 
                            form=form, 
                            name=session.get('name'),
                            known=session.get('known', False))


@main.route('/join_conference', methods=['POST'])
def join_conference():
    for key in request.form:
        print(key)
    account_sid = request.form['AccountSid']
    user = User.query.filter_by(twilio_account_sid=account_sid).first()
    response = VoiceResponse()
    dial = Dial()
    if user:
        greeting = response.say('You are entering {}\'s Conference Room'.format(user.first_name))
    dial.conference('The Marae',
                    status_callback=url_for('main.parse_events', _external=True),
                    status_callback_event='start end join leave mute hold speaker')
    response.append(dial)
    print(str(response))
    return str(response)


@main.route('/events', methods=['POST'])
def parse_events():
    account_sid = request.form['AccountSid']
    TWILIO_SYNC_SERVICE_SID = current_app.config['TWILIO_SYNC_SERVICE_SID']
    user = User.query.filter_by(twilio_account_sid=account_sid).first()
    print(user)
    print(user.sync_map_sid)
    TWILIO_SYNC_MAP_SID = user.sync_map_sid
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
    client = Client(current_app.config['TWILIO_ACCOUNT_SID'],
                    current_app.config['TWILIO_AUTH_TOKEN'])
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
        
        conference_id = UserConference.query.filter_by(call_sid=conference_sid).first()
        print(conference_id)
        if conference_id is None:
            user = User.query.filter_by(twilio_account_sid=account_sid).first()
            conference_data = UserConference(
            call_sid=conference_sid,
            name="The Marae",
            account_sid=account_sid
            )
            db.session.add(conference_data)
            db.session.commit()
            user.conferences.append(conference_data)
            conference_id = UserConference.query.filter_by(call_sid=conference_sid).first()

            
        participant = Participant(
            number=data['participantNumber'],
            direction=data['direction'],
            call_sid=data['callSid']
        )
        db.session.add(participant)
        db.session.commit()
        conference_id.participants.append(participant)
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
        participant = Participant.query.filter_by(
            call_sid=call_sid).first()
        print("PARTICIPANT >>> ")
        print(participant)
        client = Client(user.twilio_account_sid,
                        user.twilio_auth_token)
        call = client.calls(call_sid).fetch()
        print("DURATION >>> ")
        print(call.duration)
        participant.duration = call.duration
        db.session.add(participant)
        db.session.commit()
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


@main.route('/delete_map_items')
def delete_map_items():
    account_sid = request.form['AccountSid']
    TWILIO_SYNC_SERVICE_SID = current_app.config['TWILIO_SYNC_SERVICE_SID']
    user = User.query.filter_by(twilio_account_sid=account_sid).first()
    print(user)
    print(user.sync_map_sid)
    TWILIO_SYNC_MAP_SID = user.sync_map_sid
    client = Client(current_app.config['TWILIO_ACCOUNT_SID'],
                    current_app.config['TWILIO_AUTH_TOKEN'])

    conference_map = client.sync.services(TWILIO_SYNC_SERVICE_SID).sync_maps(user.sync_map_sid) \
        .sync_map_items \
        .list()

    print(conference_map)

    for item in conference_map:
        print("ITEM >>> ")
        print(item)
        delete_item = client.sync.services(TWILIO_SYNC_SERVICE_SID) \
            .sync_maps(user.sync_map_sid) \
            .sync_map_items(item.key) \
            .delete()

        print("MAP ITEM DELETED >>> {}".format(delete_item))
    return "OK", 200
