import json
from flask import render_template, session, redirect, url_for, current_app, request, jsonify
from flask_login import login_required, current_user
from . import main
from .forms import NameForm
from .. import db
from ..models import User, Participant
from ..models import Conference as UserConference
from ..email import send_email
from twilio.twiml.voice_response import Conference, Dial, VoiceResponse, Say, Hangup
from twilio.rest import Client
from pprint import pprint
from datetime import datetime

@main.route('/', methods=['GET', 'POST'])
def index():
    pprint(current_user)
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
        pprint(key)
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
    pprint(str(response))
    return str(response)


@main.route('/events', methods=['POST'])
def parse_events():
    account_sid = request.form['AccountSid']
    TWILIO_SYNC_SERVICE_SID = current_app.config['TWILIO_SYNC_SERVICE_SID']
    user = User.query.filter_by(twilio_account_sid=account_sid).first()
    pprint(user)
    pprint(user.sync_map_sid)
    TWILIO_SYNC_MAP_SID = user.sync_map_sid
    request_dict = {}
    request_dict = request.form.to_dict()
    pprint(request_dict)

    event = request_dict['StatusCallbackEvent']
    pprint(event)
    if 'CallSid' in request_dict:
        call_sid = request_dict['CallSid']
    else:
        call_sid = None
    conference_sid = request_dict['ConferenceSid']
    muted = False if 'Muted' not in request_dict or request_dict['Muted'] == 'false' else True
    pprint(event)
    client = Client(current_app.config['TWILIO_ACCOUNT_SID'],
                    current_app.config['TWILIO_AUTH_TOKEN'])
    if event == 'participant-join':

        call = client.calls(call_sid).fetch()
        pprint(call)
        pprint("CALL DETAILS {}".format(call.from_formatted))
        participant_number = call.from_formatted if call.direction == "inbound" else call.to_formatted
        data = {
            "conferenceSid": conference_sid,
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
            user.send_sms("Your conference has started! {} is already in The Marae {}".format(participant_number, url_for('main.index', _external=True)))
            
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
        print("conference-end!")
        conference_data = UserConference.query.filter_by(call_sid=conference_sid).first()
        user = User.query.filter_by(twilio_account_sid=account_sid).first()
        client = Client(user.twilio_account_sid, user.twilio_auth_token)
        twilio_conference = client.conferences(conference_sid).fetch()
        conference_data.region = twilio_conference.region
        start_time = datetime.strptime(conference_data.date_created, '%Y-%m-%d %H:%M:%S.%f')
        conference_data.duration = round((datetime.utcnow() - start_time).total_seconds())
        db.session.add(conference_data)
        db.session.commit()
        print(twilio_conference.region)
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

@main.route('/dial', methods=['GET', 'POST'])
def dial():
    print(current_user)
    print(request.json)
    number = request.json['number']
    #user = User.query.filter_by(twilio_account_sid=account_sid).first()
    print(number)
    client = Client(current_user.twilio_account_sid, current_user.twilio_auth_token)

    call = client.calls.create(
        to=number,
        from_=current_user.twilio_number,
        url=url_for('main.add_participant', _external=True)
    )

    return "OK", 200


@main.route('/add_participant', methods=['GET', 'POST'])
def add_participant():
    account_sid = request.form['AccountSid']
    user = User.query.filter_by(twilio_account_sid=account_sid).first()
    resp = VoiceResponse()
    with resp.gather(numDigits=1, action=url_for('main.join_or_drop', 
                    _external=True), 
                    method="POST", 
                    timeout=5) as g:
        g.say("You have been invited to {} {}'s conference, press 1 to accept".format(user.first_name, user.last_name))

    return str(resp)


@main.route('/join_or_drop', methods=['GET', 'POST'])
def join_or_drop():
    account_sid = request.form['AccountSid']
    user = User.query.filter_by(twilio_account_sid=account_sid).first()
    digit_pressed = request.form.get('Digits')
    print(digit_pressed)
    resp = VoiceResponse()
    if digit_pressed:
        print("Digit Pressed")
        if digit_pressed == "1":
            print("1 pressed!")
            with Dial() as dial:
                dial.conference('The Marae')
            
            resp.append(dial)
            print(resp)
    else:
        resp.hangup()

    return(str(resp))



@main.route('/mute', methods=['POST'])
def mute():
    
    participant = request.json['participant']
    mute_on = request.json['muteOn']
    conf_sid = request.json['conferenceSid']
    client = Client(current_user.twilio_account_sid, current_user.twilio_auth_token)

    participant = client.conferences(conf_sid) \
                    .participants(participant) \
                    .update(muted=mute_on)

    return str(participant.muted), 200


@main.route('/drop', methods=['POST'])
def drop():

    participant = request.json['participant']
    # drop = request.json['drop']
    # conf_sid = request.json['conferenceSid']
    client = Client(current_user.twilio_account_sid,
                    current_user.twilio_auth_token)

    call = client.calls(participant) \
        .update(status="completed")

    return "Participant dropped!", 200

@main.route('/previous_conferences', methods=['GET', 'POST'])
def previous_conferences():
    conference_array = []
    page = request.args.get('page', 1, type=int)
    pagination = current_user.conferences.order_by(UserConference.date_created.desc()).paginate(
        page, per_page=6, error_out=False
    )

    conferences = pagination.items

    for conference in conferences:
        new_conf = {
            'id': conference.id,
            'callSid': conference.call_sid,
            'name': conference.name,
            'dateCreated': conference.date_created,
            'participants': [],

        }
        for participant in conference.participants:
            pprint((participant.number))
            new_participant = {
                'id': participant.id,
                'number': participant.number,
                'duration': participant.duration,
                'direction': participant.direction,
                'callSid': participant.call_sid
            }
            new_conf['participants'].append(new_participant)
        conference_array.append(new_conf)
    json.dumps(conference_array)
    return jsonify(conference_array), 200
