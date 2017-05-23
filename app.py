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
auth_pair = ("33500", "fkSVyWtDtrQW05pS6VZlQytwoTzKiR4xWClOE5A9vASYWB9qJK")


@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('new_checkout'))


@app.route('/checkouts/new', methods=['GET'])
def new_checkout():
    return render_template('checkouts/new.html')


@app.route('/checkouts/<transaction_id>', methods=['GET'])
def show_checkout(transaction_id):
    transaction = braintree.Transaction.find(transaction_id)
    result = {}
    if transaction.status in TRANSACTION_SUCCESS_STATUSES:
        result = {
            'header': 'Sweet Success!',
            'icon': 'success',
            'message': ('Your test transaction has been successfully processed.'
                        'See the Braintree API response and try again.')
        }
    else:
        result = {
            'header': 'Transaction Failed',
            'icon': 'fail',
            'message': ('Your test transaction has a status of {}. See the Braintree'
                        ' API response and try again.').format(transaction.status)
        }

    return render_template('checkouts/show.html', transaction=transaction, result=result)

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
        "MethodID": 69,
        "ReturnURL": "https://smart2pay-demo-db2.herokuapp.com/redirect",
        "TokenLifetime": 0,
        "Customer": {
            "Email": "youremail@email.com"
        }
        }
    }
    result = requests.post(API_URL + '/payments', json=tx_data, auth=auth_pair)
    # import ipdb; ipdb.set_trace();
    return jsonify(result.json())
    # if result.is_success or result.transaction:
    #     session["payment_method_token"] = result.transaction.credit_card_details.token
    #     return redirect(url_for('show_checkout', transaction_id=result.transaction.id))
    # else:
    #     for x in result.errors.deep_errors:
    #         flash('Error: %s: %s' % (x.code, x.message))
    #     return redirect(url_for('new_checkout'))


@app.route('/redirect', methods=['POST', 'GET'])
def redirect():
    print("** REDIR METH**", request.method)
    print("** REDIR GET**", request.args)
    print("** REDIR POST/PUT**", request.form)
    print("** REDIR VALUES**", request.values)
    return "OK: {}".format(request)


@app.route('/checkouts/one_more', methods=['POST'])
def create_checkout_more():
    price = request.form['price']
    result = braintree.Transaction.sale({
        'amount': price,
        'payment_method_token': session["payment_method_token"],
        'options': {
            "submit_for_settlement": True,
        },
    })
    if result.is_success or result.transaction:
        # session["payment_method_token"] = result.transaction.credit_card_details.token
        return redirect(url_for('show_checkout', transaction_id=result.transaction.id))
    else:
        for x in result.errors.deep_errors:
            flash('Error: %s: %s' % (x.code, x.message))
        return redirect(url_for('new_checkout'))


@app.route('/refund', methods=['POST'])
def refund():
    result = braintree.Transaction.refund(request.form["tx_id"])
    if result.is_success or result.transaction:
        # session["payment_method_token"] = result.transaction.credit_card_details.token
        return redirect(url_for('show_checkout', transaction_id=result.transaction.id))
    else:
        for x in result.errors.deep_errors:
            flash('Error: %s: %s' % (x.code, x.message))
        return redirect(url_for('new_checkout'))
    # result = {}
    # if transaction.status in TRANSACTION_SUCCESS_STATUSES:
    #     result = {
    #         'header': 'Sweet Success!',
    #         'icon': 'success',
    #         'message': ('Your test transaction has been successfully processed.'
    #                     'See the Braintree API response and try again.')
    #     }
    # else:
    #     result = {
    #         'header': 'Transaction Failed',
    #         'icon': 'fail',
    #         'message': ('Your test transaction has a status of {}. See the Braintree'
    #                     ' API response and try again.').format(transaction.status)
    #     }

    # return render_template('checkouts/show.html', transaction=transaction,
    # result=result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4567, debug=True)
