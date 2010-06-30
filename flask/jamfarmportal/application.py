
import os
import datetime
import functools

from flask import (
        Flask, render_template, jsonify,
        request, session, redirect, abort, escape
    )
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

import ninjam
from database import db_session
from models import User, Site
from utils import generate_password, is_valid_email

app = Flask(__name__)
app.secret_key = "\x7fE?yW\x9c\xceP\xc0\x06'\x97f\xd6\xddL\xe3pu\xd8\x87.FR"

@app.route('/favicon.ico')
def favicon():
    return redirect("http://ninjam.com/favicon.ico")


@app.route('/')
def index():
    return render_template('index.html',
        timestamp=datetime.datetime.today(),
        server_list=Site.query.all())


@app.route('/admin/')
def admin_index():
    return render_template('admin.html')

@app.route('/admin/db/')
def admin_db_dump():
    # For debug/admin db view
    return render_template('admin_db.html',
        users=User.query.all(),
        sites=Site.query.all())

@app.route('/admin/db/delete/<table>', methods=['POST'])
def admin_db_delete(table):
    assert table in ('user','site')
    values = request.form.getlist('selected')
    try:
        if table == 'user':
            for uid in values:
                for site in Site.query.filter(Site.owner==uid):
                    db_session.delete(site)
                for user in User.query.filter(User.id==uid):
                    db_session.delete(user)
            db_session.commit()
        elif table == 'site':
            for sid in values:
                site = Site.query.filter(Site.id==sid).one()
                db_session.delete(site)
            db_session.commit()
    except NoResultFound:
        db_session.rollback()
            
    return redirect('/admin/db/dump')

@app.route('/signup', methods=['GET', 'POST'])
def register():
    # XXX: POST ... Bad Request
    if request.method == 'POST':
        email = request.form['email']
        if not is_valid_email(email):
            reason = 'not valid email address'
            return render_template('signup_error.html', reason=reason)
        try:
            user = User(email, password=generate_password())
            db_session.add(user)
            db_session.commit()
        except IntegrityError, e:
            reason = '%s already exists' % escape(email)
            return render_template('signup_error.html', reason=reason)
            
        # Send password to mail
        return redirect('/')
    return render_template('signup_form.html')

@app.route('/signin', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user'] = user
            # XXX: url_for("user") raise BuildError
            return redirect("/user")
    if 'user' in session:
        return redirect('/user')
    return render_template('signin_form.html')

@app.route('/signout')
def logout():
    if 'user' in session:
        del session['user']
    return redirect('/')

def require_login(func):
    @functools.wraps(func)
    def _wrapped(*args, **kw):
        user = session.get('user', None)
        if not user:
            return redirect('/signin')
        return func(user, *args, **kw)
    return _wrapped

@app.route('/user')
@require_login
def user_page(user):
    server_list = Site.query.filter_by(owner=user.id)
    return render_template('user_page.html', user=user, server_list=server_list)

@app.route('/server/add', methods=["POST"])
@require_login
def add_server(user):
    if request.method == 'POST':
        server = request.form['server']
        username = request.form['status_username']
        password = request.form['status_password']
        comment = request.form['comment']
        website = request.form['website']
        
        site = Site(user.id, server, username, password, comment, website)
        db_session.add(site)
        db_session.commit()
    return redirect('/user')
    
@app.route('/server/delete/<server>')
@require_login
def del_server(user, server):
    site = Site.query.filter_by(owner=user.id, server=server).first()  
    db_session.delete(site)
    db_session.commit()
    return redirect('/user')

@app.route('/server/status/<server>')
def get_state(server):
    site = Site.query.filter_by(server=server).first()
    if site:
        host,port = server.split(':')
        username = site.username.encode('utf-8')
        password = site.password.encode('utf-8')
        data = ninjam.get_status((host,int(port)), username, password, encoding='sjis')
        return jsonify(data)
    abort(404)

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html', title='Not Found', reason=error)

# tear-down for Database(SQLAlchemy)
@app.after_request
def shutdown_session(response):
    db_session.remove()
    return response

if __name__ == '__main__':
    app.run(port=8000, debug=True)
