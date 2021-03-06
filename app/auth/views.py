from flask import render_template, redirect, request, url_for, flash, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from .. import db
from ..models import User
from .forms import LoginForm, RegistrationForm, VerificationForm, ChangePasswordForm, ConferenceSettingsForm
from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import SyncGrant



@auth.before_app_request
def before_request():
    if current_user.is_authenticated \
            and not current_user.phone_number_confirmed \
            and request.endpoint \
            and request.endpoint[:5] != 'auth.' \
            and request.endpoint != 'static':
        return redirect(url_for('auth.unconfirmed'))
    elif current_user.is_authenticated \
        and (not current_user.twilio_account_sid \
            or not current_user.twilio_auth_token \
            or not current_user.twilio_number) \
        and request.endpoint \
        and request.endpoint[:5] != 'auth.' \
        and request.endpoint != 'static':
        return(redirect(url_for('auth.register', step="2")))

@auth.route('/unconfirmed', methods=['GET', 'POST'])
def unconfirmed():
    if current_user.is_anonymous or current_user.phone_number_confirmed:
        return redirect(url_for('main.index'))
    else:
        form = VerificationForm()
        if form.validate_on_submit():
            check = current_user.check_confirmation_code(form.code.data)
            if check:
                flash('Number confirmed!')
                authy_user = current_user.create_authy_user()
                if not authy_user:
                    flash('Unable to create authy id')
                flash('Authy ID created!')
                return redirect(url_for('main.index'))
            else:
                flash('Code invalid or expired, press resend to receive a new one')
                #return redirect(url_for('auth.unconfirmed'))
    return render_template('auth/unconfirmed.html', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            if not current_user.phone_number_confirmed:
                code = current_user.generate_confirmation_code()
                flash('{}'.format(code['message']))
                return redirect(url_for('auth.unconfirmed'))
            else:
                code = current_user.generate_2fa()
                flash('{}'.format(code['message']))
                return redirect(url_for('auth.verify'))
        else:
            flash('Invalid username or password.')
    return render_template('auth/login.html', form=form)

@auth.route('/verify', methods=['GET', 'POST'])
@login_required
def verify():
    form = VerificationForm()
    if form.validate_on_submit():
        check = current_user.check_2fa(form.code.data)
        if check:
            if current_user.twilio_account_sid is None or \
                current_user.twilio_auth_token is None or \
                current_user.twilio_number is None:
                twilio_form = ConferenceSettingsForm()
                return(redirect(url_for('auth.register', step='1', twilio_form=twilio_form)))
            return redirect(request.args.get('next') or url_for('main.index'))
        else:
            flash("Token expired or incorrect!")
    return render_template('auth/verify.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))

@auth.route('/resend_code', methods=['POST'])
def resend_code():
    code = current_user.generate_confirmation_code()
    print(code)
    return code['message']


@auth.route('/resend_authy', methods=['POST'])
@login_required
def resend_authy():
    code = current_user.generate_2fa()
    print(code)
    return code


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    twilio_form = ConferenceSettingsForm()
    print(current_user)
    print(request.args.get('step'))
    
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    first_name=form.first_name.data,
                    last_name=form.last_name.data,
                    password=form.password.data,
                    country_code=form.country_code.data,
                    phone=form.phone_number.data)
                    # twilio_account_sid=form.twilio_sid.data,
                    # twilio_auth_token=form.twilio_token.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration Successful, you may now log in!')
        
        return redirect(url_for('auth.login'))
    if twilio_form.validate_on_submit():
        print('Submitting Twilio Form!')
        current_user.twilio_account_sid = twilio_form.twilio_sid.data
        current_user.twilio_auth_token = twilio_form.twilio_token.data
        #current_user.twilio_number = twilio_form.twilio_phone.data

        db.session.add(current_user)
        db.session.commit()

        flash('Twilio Settings Updated! Setting up your number for conferencing!')
        conference = current_user.configure_conference(
            twilio_form.twilio_phone.data)
        if conference:
            flash('Conference URL successfully configured')
        else:
            flash('Error creating conference, contact Administrator')
        sync_map = current_user.configure_sync_map()
        if sync_map:
            flash('Sync Map Created! SID: {}'.format(current_user.sync_map_sid))
        else:
            flash('Sync Map failed to create')
       
        flash('Twilio Settings Confirmed!')
        return redirect(url_for('main.index'))
    if request.args.get('step') == '2':
        return render_template('auth/register.html', form=form, twilio_form=twilio_form, step='2')
    return render_template('auth/register.html', form=form, twilio_form=twilio_form, step='0')

@auth.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    password_form = ChangePasswordForm()
    conference_form = ConferenceSettingsForm()
    if password_form.validate_on_submit():
        if current_user.verify_password(password_form.old_password.data):
            current_user.password = password_form.password.data
            db.session.add(current_user)
            flash('Your password has been updated!')
            return redirect(url_for('auth.settings'))
        else:
            flash('Invalid current password')
    if conference_form.validate_on_submit():
        print("Submitting Conference Form")
        current_user.twilio_account_sid = conference_form.twilio_sid.data
        current_user.twilio_auth_token = conference_form.twilio_token.data
        #current_user.twilio_number = conference_form.twilio_phone.data
        db.session.add(current_user)
        db.session.commit()

        flash('Twilio Settings Updated! Setting up your number for conferencing!')
        conference = current_user.configure_conference(conference_form.twilio_phone.data)
        if conference:
            flash('Conference URL successfully configured')
        else:
            flash('Error creating conference, contact Administrator')
        sync_map = current_user.configure_sync_map()
        if sync_map:
            flash('Sync Map Created! SID: {}'.format(current_user.sync_map_sid))
        else:
            flash('Sync Map failed to create')
        return redirect(url_for('auth.settings'))
    return render_template('auth/settings.html', password_form=password_form, conference_form=conference_form)


@auth.route('/test_call', methods=['POST'])
@login_required
def test_call():
    payload = request.get_json()
    print(payload['twilio_sid'])
    print(payload['twilio_token'])
    print(payload['number'])
    user_phone = "{}{}".format(current_user.country_code, current_user.phone)
    print(current_user.phone)
    client = Client(payload['twilio_sid'], payload['twilio_token'])
    try:
        call = client.calls.create(
            to=user_phone,
            from_=payload['number'],
            url=url_for('static', filename='twiml/test_call.xml', _external=True),
            method='GET'
        )
        print(call.sid)
        return(call.sid)
    except Exception as e:
        print(e)
        return(e)


@auth.route('/token')
@login_required
def token():
    # get the userid from the incoming request
    identity = request.values.get('identity', None)
    # Create access token with credentials
    token = AccessToken(current_app.config['TWILIO_ACCOUNT_SID'],
                        current_app.config['TWILIO_API_KEY'],
                        current_app.config['TWILIO_API_SECRET'], identity=identity)
    # Create a Sync grant and add to token
    sync_grant = SyncGrant(service_sid=current_app.config['TWILIO_SYNC_SERVICE_SID'])
    token.add_grant(sync_grant)
    # Return token info as JSON
    return jsonify(identity=identity, token=token.to_jwt().decode('utf-8'))


@auth.route('/buy_number', methods=['POST'])
@login_required
def buy_number():
    payload = request.get_json()
    print(current_user)
    account_sid = payload['twilio_sid']
    auth_token = payload['twilio_token']
    client = Client(account_sid, auth_token)
    numbers = client.available_phone_numbers("GB") \
                    .local \
                    .list(voice_enabled=True, sms_enabled=True)

    print(numbers[0].phone_number)

    new_number = numbers[0].phone_number

    number = client.incoming_phone_numbers \
        .create(phone_number=new_number)

    return numbers[0].phone_number

