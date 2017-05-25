from flask import Flask, redirect, url_for, render_template, request, flash, session, jsonify

import decimal
import os
import uuid
from os.path import join, dirname
from dotenv import load_dotenv
import requests

app = Flask(__name__)
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
app.secret_key = os.environ.get('APP_SECRET_KEY')


API_URL = "https://paytest.smart2pay.com/v1"
CARD_API_URL = "https://securetest.smart2pay.com/v1"
auth_pair = (os.environ.get('SITE_ID'), os.environ.get('API_KEY'))


"""
{
  "Payment": {
    "SkinID": 0,
    "ClientIP": "",
    "MerchantTransactionID": "sdfsdfsd3434",
    "Amount": 1111,
    "Currency": "CAD",
    "ReturnURL": "http://iasi.smart2pay.com:7020/wpfirst/wp-content/plugins/smart2pay-api/includes/sdk/samples/_return.php",
    "Description": "",
    "PreapprovalID": 0,
    "MethodID": 69,
    "MethodOptionID": 0,
    "Guaranteed": null,
    "RedirectInIframe": null,
    "Details": {
      "BankCode": "",
      "AccountNumber": "",
      "IBAN": "",
      "BIC": "",
      "EntityID": "",
      "ReferenceID": "",
      "EntityNumber": "",
      "ReferenceNumber": "",
      "AccountHolder": "",
      "BankName": "",
      "SWIFT_BIC": "",
      "AccountCurrency": "",
      "PrepaidCard": "",
      "PrepaidCardPIN": "",
      "SerialNumbers": "",
      "Wallet": "",
      "PayerCountry": "",
      "PayerEmail": "",
      "PayerPhone": ""
    },
    "Customer": {
      "MerchantCustomerID": "",
      "Email": "",
      "FirstName": "",
      "LastName": "",
      "Gender": "",
      "DateOfBirth": "",
      "SocialSecurityNumber": "",
      "Phone": "",
      "Company": ""
    },
    "BillingAddress": {
      "Country": "",
      "City": "",
      "ZipCode": "",
      "State": "",
      "Street": "",
      "StreetNumber": "",
      "HouseNumber": "",
      "HouseExtension": ""
    },
    "ShippingAddress": {
      "Country": "",
      "City": "",
      "ZipCode": "",
      "State": "",
      "Street": "",
      "StreetNumber": "",
      "HouseNumber": "",
      "HouseExtension": ""
    },
    "TokenLifetime": 0
  }
}
"""


@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('new_checkout'))


@app.route('/checkouts/new', methods=['GET'])
def new_checkout():
    return render_template('checkouts/new.html')


@app.route('/checkouts/<tx_id>', methods=['GET'])
def show_checkout(tx_id):
    url = CARD_API_URL + '/payments/{}'.format(tx_id)
    resp = requests.get(url, auth=auth_pair)
    payment = session["payment"]
    result = {}
    s = payment["Status"]
    if s["ID"] == 11:  # Captured
        result = {
            'header': 'Sweet Success!',
            'icon': 'success',
            'message': ('Your test transaction has been successfully processed.'
                        'See the API response and try again.')
        }
    else:
        result = {
            'header': 'Transaction Failed',
            'icon': 'fail',
            'message': ('Your test transaction has a status of {} ({}): {}. See'
                        ' API response and try again.').format(s["ID"], s["Info"], s["Reasons"])
        }

    return render_template('checkouts/show.html', payment=payment, result=result)


@app.route('/checkouts', methods=['POST'])
def create_checkout():
    curr = request.form['currency']
    price_key = 'price_' + curr
    price = decimal.Decimal(request.form[price_key])
    tx_amount = int(request.form['amount']) * price * 100
    tx_data = {
        "Payment": {
            "MerchantTransactionID": str(uuid.uuid4()),
            "Amount": int(tx_amount),
            "Currency": curr,
            "ReturnURL": "https://smart2pay-demo-db2.herokuapp.com/redirect",
            "Customer": {
                "Email": "youremail@email.com"
            },
            "Card": {
                "HolderName": request.form['card_holder'],
                "Number": request.form['card_number'],
                "ExpirationMonth": request.form['card_exp_month'],
                "ExpirationYear": request.form['card_exp_year'],
                "SecurityCode": request.form['card_cvv']
            },
            "Capture": True,
            "GenerateCreditCardToken": True
        }
    }
    result = requests.post(CARD_API_URL + '/payments', json=tx_data, auth=auth_pair)
    payment = result.json()["Payment"]
    s = payment["Status"]
    session["payment"] = payment

    if s["ID"] == 11:  # Captured
        session["payment_method_token"] = payment["CreditCardToken"]
        return redirect(url_for('show_checkout', tx_id=payment["ID"]))
    else:
        return redirect(url_for('show_checkout', tx_id=payment["ID"]))


@app.route('/checkouts/one_more', methods=['POST'])
def create_checkout_more():
    price = decimal.Decimal(request.form["price"])

    tx_amount = price * 100
    tx_data = {
        "Payment": {
            "MerchantTransactionID": str(uuid.uuid4()),
            "Amount": int(tx_amount),
            "Currency": "USD",
            "ReturnURL": "https://smart2pay-demo-db2.herokuapp.com/redirect",
            "Customer": {
                "Email": "youremail@email.com"
            },
            "CreditCardToken": {
              "Value": session["payment_method_token"]["Value"],
            },      
            "Capture": True,
            "Retry": True,
            "GenerateCreditCardToken": True
        }
    }

    result = requests.post(CARD_API_URL + '/payments', json=tx_data, auth=auth_pair)
    payment = result.json()["Payment"]
    s = payment["Status"]

    session["payment"] = payment
    if s["ID"] == 11:  # Captured
        session["payment_method_token"] = payment["CreditCardToken"]
        return redirect(url_for('show_checkout', tx_id=payment["ID"]))
    else:
        return redirect(url_for('show_checkout', tx_id=payment["ID"]))


@app.route('/refund/partial', methods=['POST'])
def refund_partial():
    data = {
        "Refund": {
            "MerchantTransactionID": request.form["tx_id"],
            "Amount": int(decimal.Decimal(request.form["amount"])) * 100
        }
    }
    url = CARD_API_URL + '/payments/{}/refunds'.format(request.form["payment_id"])
    result = requests.post(url, json=data, auth=auth_pair)
    return jsonify(result.json())


@app.route('/refund', methods=['POST'])
def refund():
    url = CARD_API_URL + '/payments/{}'.format(request.form["payment_id"])
    resp = requests.get(url, auth=auth_pair)
    payment = resp.json()["Payment"]
    data = {
        "Refund": {
            "MerchantTransactionID": request.form["tx_id"],
            "Amount": payment["Amount"]
        }
    }
    url = CARD_API_URL + '/payments/{}/refunds'.format(request.form["payment_id"])
    result = requests.post(url, json=data, auth=auth_pair)
    return jsonify(result.json())


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4567, debug=True)
