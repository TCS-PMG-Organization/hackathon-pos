from datetime import datetime, timedelta
import mongo as mongo
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
from bson.objectid import ObjectId
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
from dateutil.relativedelta import relativedelta
import json, urllib3, requests, random, smtplib, os, sys


class MyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(MyEncoder, self).default(obj)


app = Flask(__name__)
app.json_encoder = MyEncoder

################################### Database Configuration ############################
MONGODB_USER = "admin"
MONGODB_PASSWORD = "admin"
MONGODB_DATABASE = "Edge_BankDB"
#MONGODB_DOMAIN = "45a49dbf-us-east.lb.appdomain.cloud"
MONGODB_DOMAIN = "1e1b849f-eu-de.lb.appdomain.cloud"
MONGODB_PORT = "27017"

try:
    if (MONGODB_USER == None or MONGODB_PASSWORD == None):
        MONGODB_URL = "mongodb://" + MONGODB_DOMAIN + ":" + MONGODB_PORT
    else:
        MONGODB_URL = "mongodb://" + MONGODB_USER + ":" + MONGODB_PASSWORD + "@" + MONGODB_DOMAIN + ":" + MONGODB_PORT

        POS_Client = MongoClient(MONGODB_URL)
except Exception as ex:
    print("Oops!! Something went wrong in the mongo db connection, the detailed error id : " + ex)
    sys.exit(0)

try:
    Edge_BankDB = POS_Client[MONGODB_DATABASE]
    Edge_Users = Edge_BankDB['Edge_Users']
    Edge_Passwords = Edge_BankDB['Edge_Passwords']
    Edge_Transactions = Edge_BankDB['Transactions']
    Edge_Transaction_Rules = Edge_BankDB['Transaction_Rule']
    Edge_Fraud_Transactions = Edge_BankDB['Fraud_Transactions']
except Exception as ex:
    print(
        "Cannot connect to the bank database!!! Check value of the Environment Variable \"MONGODB_DATABASE\". This cannot be left blank.")


################################### Api calls ###################################




@app.route("/login", methods=['POST'])
def login():
    msg = ""
    login_data = request.get_json()

    username = str(login_data["username"])
    password = str(login_data["password"])
    username_query = {"user_name": username}
    password_query = {"user_password": password}

    if (Edge_Users.count_documents(username_query) == 1) and (Edge_Passwords.count_documents(password_query) == 1):
        data = Edge_Users.find_one(username_query)

        msg = {"error": "false",
               "errorMsg": "User found",
               "role": data['role'],
               "bank_id": data['bank_id'],
               "country_id": data['country_id'],
               "token": "null"}
    else:
        msg = {"error": "true",
               "errorMsg": "User not found",
               "bank_id": "null",
               "country_id": "null",
               "token": "null"}

    return jsonify(msg)


@app.route("/submit_payment", methods=['POST'])
def submit_payment():
    msg = ""
    try:
        submitdata = request.json
        _name = submitdata['name']
        _amount = submitdata['amount']
        _card_no = submitdata['card_no']
        _card_type = submitdata['card_type']
        _merchant_category = submitdata['merchant_category']
        _expiry_date = submitdata['expiry_date']
        _security_code = submitdata['security_code']
        _zip_code = submitdata['zip_code']
        _timestamp = submitdata['timestamp']
        _order_id = submitdata['order_id']

        _time_rule = get_time_limit_rule()
        _amount_rule = get_amount_limit_rule()
        _zipcode_rule = get_zipcode_rule()
        _translimit_rule = get_transaction_limit_rule()

        start_time_str = _time_rule['start_time']
        start_time =""
        if start_time_str == '9PM':
            start_time =str(datetime.now().date())+' '+'21:00:00'
        sart_time_value = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')

        end_time_str = _time_rule['end_time']
        end_time = ""
        if end_time_str == '6AM':
            end_time = str(datetime.now().date()) + ' ' + '06:00:00'
        end_time_value = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')

        ts = int(_timestamp)
        timestamp_value = datetime.fromtimestamp(ts)

        amt_rule_value = _amount_rule['limit']
        zip_code_rule_value = _zipcode_rule['zipcode_value']


        if _name and _amount and _card_no and _card_type and _expiry_date and _security_code and _zip_code and request.method == 'POST':
            if  _amount > amt_rule_value or _zip_code != zip_code_rule_value or timestamp_value > sart_time_value or timestamp_value < end_time_value:
                Edge_Fraud_Transactions.insert_one(submitdata)
                msg = {"status": "error",
                       "status_msg": "This ia fraudulant transaction!!!",
                       "transactionID": "null"}
                #insert into fraud trans table & raise error
            else:
              _insertedID = Edge_Transactions.insert_one(submitdata).inserted_id
              msg = {"status": "success", "status_msg": "Your Transaction was successful !!!", "transactionID": str(_insertedID)}

    except ex:
        msg = {"status": "error" + str(ex),
                    "status_msg": "Your Transaction was not successful !!!",
                "transactionID": "null"}
    return jsonify(msg)

def get_time_limit_rule():
    msgrules= ""
    rule=""
    msgrules = Edge_Transaction_Rules.find()
    for row in msgrules:
        if row["rule_type"] == "time":
            rule = row
    return rule

def get_amount_limit_rule():
    msgrules= ""
    rule=""
    msgrules = Edge_Transaction_Rules.find()
    for row in msgrules:
        if row["rule_type"] == "amount":
            rule = row
    return rule

def get_zipcode_rule():
    msgrules= ""
    rule=""
    msgrules = Edge_Transaction_Rules.find()
    for row in msgrules:
        if row["rule_type"] == "zipcode":
            rule = row
    return rule

def get_transaction_limit_rule():
    msgrules= ""
    rule=""
    msgrules = Edge_Transaction_Rules.find()
    for row in msgrules:
        if row["rule_type"] == "transaction_limit":
            rule = row

    return rule
###################################


if __name__ == "__main__":
    app.run(port=5000, debug=True)
