
import os
import datetime
import functools

from flask import (
        Flask, render_template, jsonify,
        request, session, redirect, abort, escape
    )

import ninjam
from database import db_session
from models import User, Site

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['login'] = user
            # XXX: url_for("user") raise BuildError
            return redirect("/user")
    if 'login' in session:
        return redirect('/user')
    return render_template('login_form.html')

@app.route('/logout')
def logout():
    if 'login' in session:
        del session['login']
    return redirect('/')

def require_login(func):
    @functools.wraps(func)
    def _wrapped(*args, **kw):
        user = session.get('login', None)
        if not user:
            return redirect('/login')
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
    return render_template('page_not_found.html', error=error)

# tear-down for Database(SQLAlchemy)
@app.after_request
def shutdown_session(response):
    db_session.remove()
    return response

if __name__ == '__main__':
    app.run(port=8000, debug=True)
