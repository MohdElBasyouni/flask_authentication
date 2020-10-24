from flask import Flask, jsonify, abort, request, Response
import mysql.connector
import json
import os
import signal
from flask_login import LoginManager, UserMixin, login_required
import logging
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor



sched = BackgroundScheduler()
# I'm disabling Logging as other parts of the code need to have clear log without too much of nothing to do logs
logging.getLogger('apscheduler.scheduler').propagate = False
def job():
    print('Hello')
# The ID here is mandatory to remove this function from Background once needed
sched.add_job(job, 'interval', seconds=10, id='main')


# Flask def
app = Flask(__name__)
# app.config['ENV'] = 'development'
app.config['ENV'] = 'deployment'
# app.config['DEBUG'] = True
# app.config['TESTING'] = True

app.secret_key = 'KEYSECRET'  # Change this!
login_manager = LoginManager()
login_manager.init_app(app)


def sendMail(subject, body, attach, email):
    subject = 'LOCAL - ' + subject
    if email == None:
        to = 'product_owner_mail@mail.com'
    else:
        to = email
    yag = yagmail.SMTP("scrum_mail@mail.com", 'password')
    yag.send(
        to=to,
        subject= subject,
        contents=body, 
        attachments=attach,
    )

def db_check():
    mydb = mysql.connector.connect(host="localhost",user="Manager",password="ManagerPWD",database = "DBNAME")
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute('SELECT USERNAME, TOKEN, CREDIT FROM USERS')
    rows = mycursor.fetchall()
    newdata = [{dic['USERNAME']: (dic['TOKEN'], dic['CREDIT'])} for dic in rows]
    diction_user_token = {}
    for item in newdata:
        for key, value in item.items():
            diction_user_token[key] = value
    user_database = diction_user_token
    return user_database


class User(UserMixin):
    # Load your users from DB here if you wish to have an instant from it, otherwise put in the get function below
	# user_database = db_check()
    # Sample of the returned data
    # user_database = {"melbasyouni": ("p50Bux2fe1JCLkkkVYqt6r,G", 10000000),"JaneDoe": ("Jane", 10000000)}
    def __init__(self, username, password):
        self.id = username
        self.password = password

    @classmethod
    def get(cls,id):
        user_database = db_check()
        # Sample of the returned data
        # user_database = {"melbasyouni": ("p50Bux2fe1JCLkkkVYqt6r,G", 10000000),"JaneDoe": ("Jane", 10000000)}
        return user_database.get(id)


@login_manager.request_loader
# API Request should have ?token=username:password at the end of the URL
def load_user(request):
    global credit_score
    token = request.headers.get('Authorization')
    if token is None:
        token = request.args.get('token')
    if token is not None:
        username,password = token.split(":")
        user_entry = User.get(username)
        if (user_entry is not None):
            user = User(username,user_entry)
            if (user.password[0] == password):
                # Check if user has credit and update global variable
                if (user.password[1] > 0):
                    new_value = user.password[1] - 1
                    credit_score = True
                    # Update the Database with the new credit for this user
                    sql_queries.users_credit_update_API(user.password[0], new_value)
                    return user
                else:
                    credit_score = False
                    return user
    return None

@login_manager.unauthorized_handler
def unauthorized_callback():
    return (jsonify({'Status': 'Access Not Authorized'}), 201)


@app.before_request
def before():
    print("This is executed BEFORE each request.")


@app.route('/_ah/warmup')
def warmup():
    # Handle your warmup logic here, e.g. set up a database connection pool
    return '', 200, {}



@app.route('/api/v1.0/banks_data/<bank>/', methods = ['GET'])
@login_required
def banks_data(bank):
    # Check if user has credit
    if credit_score == True:
        if bank != None:
            # Return the needed Data
            return (jsonify({'Data': 'Hope you get the data'}), 201)
        else:
            return (jsonify({'Status': 'Requested Bank Code can not be None'}), 201)
    # Check if user has credit failed
    else:
        return (jsonify({'Status': 'No enough credit for this account'}), 201)


@app.route('/stopServer', methods=['GET'])
@login_required
def stopServer():
    try:
        logging.info("Stopping Flask API")
        subject = 'Flask API Logic Stopped'
        body = 'Flask API Logic Stopped with embedded functions.'
        # Remove Background Function before stopping the Flask API
        if sched is not None:
            sched.remove_job('main')
        # Good Idea to send Mail in case API stopped
        sendMail(subject, body, None, None)
        os.kill(os.getpid(), signal.SIGINT)
        return jsonify({ "success": True, "message": "Server is Stopping..." })
    except Exception as err:
        logging.info("Something went wrong with Flask API, error is '" + str(err) + "'")
        subject = 'Flask API Logic Stopping Failed'
        body = "Something went wrong with Flask API, error is '" + str(err) + "'"
        # Good Idea to send Mail in case API failed to stop
        sendMail(subject, body, None, None)
        return (jsonify({'Status': 'Something went wrong when stopping server'}), 201)


if __name__ == '__main__':
    try:
        sched.start()
        app.run(host='0.0.0.0', port=5000)
        # In case SSL is needed, an adhoc ssl context can be added as a parameter to the app.run
        # ssl_context='adhoc'
    except Exception as err:
        logging.info("Something went wrong with Flask API, error is '" + str(err) + "'")
        subject = 'Flask API Logic Failed'
        body = "Something went wrong with Flask API, error is '" + str(err) + "'"
        # It's a good idea to send Mail in case the App Failed to run => A Cloud Practice I'm using
        sendMail(subject, body, None, None)