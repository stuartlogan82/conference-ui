from flask import render_template, redirect, request, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from .. import db
from ..models import User
from .forms import LoginForm, RegistrationForm, VerificationForm, ChangePasswordForm, ConferenceSettingsForm


@auth.before_app_request
def before_request():
    if current_user.is_authenticated \
            and not current_user.phone_number_confirmed \
            and request.endpoint \
            and request.endpoint[:5] != 'auth.' \
            and request.endpoint != 'static':
        return redirect(url_for('auth.unconfirmed'))


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
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    first_name=form.first_name.data,
                    last_name=form.last_name.data,
                    password=form.password.data,
                    country_code=form.country_code.data,
                    phone=form.phone_number.data,
                    twilio_account_sid=form.twilio_sid.data,
                    twilio_auth_token=form.twilio_token.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration Successful, you may now log in!')
        
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

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
    return render_template('auth/settings.html', password_form=password_form, conference_form=conference_form)
