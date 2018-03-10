from flask import render_template, redirect, request, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from .. import db
from ..models import User
from .forms import LoginForm, RegistrationForm, VerificationForm


@auth.before_app_request
def before_request():
    if current_user.is_authenticated \
            and not current_user.phone_number_confirmed \
            and request.endpoint \
            and request.endpoint[:5] != 'auth.' \
            and request.endpoint != 'static':
        return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
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
                flash('Code invalid or expired')
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
        flash('Invalid username or password.')
    return render_template('auth/login.html', form=form)

@auth.route('/verify', methods=['GET', 'POST'])
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
        
        
        return redirect(url_for('auth.verify'))
    return render_template('auth/register.html', form=form)
