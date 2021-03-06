from authorizenet import apicontractsv1
from authorizenet.apicontrollers import createTransactionController
from authorizenet.constants import constants
from django import forms
from django.contrib import messages
from collections import OrderedDict
from pretix.base.payment import BasePaymentProvider, PaymentException
from django.utils.translation import gettext as _
from django.core.validators import RegexValidator
import enum
import logging

logger = logging.getLogger(__name__)


class Authorizenet(BasePaymentProvider):
    identifier = "authorizenet"
    verbose_name = "Authorize.net Payment"
    public_name = "Credit Card Payment"

    @staticmethod
    def form_fields():
        return OrderedDict(
            [
                ('apiLoginID',
                 forms.CharField(
                     widget=forms.TextInput,
                     label=_('API Login ID'),
                     required=True
                 )),
                ('transactionKey',
                 forms.CharField(
                     widget=forms.TextInput,
                     label=_('Transaction Key'),
                     required=True
                 )),
                ('productionEnabled',
                 forms.BooleanField(
                     widget=forms.CheckboxInput,
                     label=_('Enable Production API'),
                     required=False,
                     initial=False
                 )),
                ('solutionID',
                 forms.CharField(
                     widget=forms.TextInput,
                     label=_('Solution ID'),
                     required=False
                 )),
                ('purchaseDescription',
                 forms.CharField(
                     widget=forms.TextInput(attrs={'placeholder': 'Appears on bank statements'}),
                     label=_('Purchase Description'),
                     required=True
                 )),
            ]
        )

    @property
    def settings_form_fields(self):
        d = OrderedDict(list(super().settings_form_fields.items()) + list(Authorizenet.form_fields().items()))
        d.move_to_end('purchaseDescription', last=False)
        d.move_to_end('transactionKey', last=False)
        d.move_to_end('apiLoginID', last=False)
        # d.move_to_end('solutionID', last=False)
        d.move_to_end('productionEnabled', last=False)
        d.move_to_end('_enabled', last=False)
        return d

    @property
    def payment_form_fields(self):
        states = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']
        states_choices = zip(states, states)
        return OrderedDict([
            ('firstName',
             forms.CharField(
                 widget=forms.TextInput,
                 label=_('First Name'),
                 required=True
             )),
            ('lastName',
             forms.CharField(
                 widget=forms.TextInput,
                 label=_('Last Name'),
                 required=True
             )),
            ('address',
             forms.CharField(
                 widget=forms.TextInput,
                 label=_('Street Address'),
                 required=True
             )),
            ('city',
             forms.CharField(
                 label=_('City'),
                 required=True
             )),
            ('state',
             forms.ChoiceField(
                 label=_('State'),
                 required=True,
                 choices=states_choices
             )),
            ('zip',
             forms.IntegerField(
                 widget=forms.TextInput,
                 label=_('Zipcode'),
                 required=True
             )),
            ('cardNumber',
             forms.CharField(
                 widget=forms.TextInput(attrs={'placeholder': 'Card Number, No Spaces'}),
                 label=_('Card Number'),
                 required=True,
                 validators=[RegexValidator(r"\d{15,19}")]
             )),
            ('cardExpiration',
             forms.CharField(
                 widget=forms.TextInput(attrs={"placeholder": "mm/yy"}),
                 help_text="Please use format MM/YY",
                 label=_("Card Expiration Date"),
                 required=True,
             )),
            ('cardCode',
             forms.CharField(
                 widget=forms.TextInput(attrs={'placeholder': "Code on Back of Card"}),
                 label=_('Card Code'),
                 required=True,
                 validators=[RegexValidator(r"\d{3}")]
             )),
        ])

    def settings_content_render(self, request):
        return """This is plugin is in alpha. Refunds are not supported through the plugin, but can be done manually on Authorize.net"""

    def payment_is_valid_session(self, request):
        """This is called at the time the user tries to place the order.
        It should return True if the user’s session is valid and all data
        your payment provider requires in future steps is present."""
        # Convert form data to str, this probably should go in form validation
        request.session['payment_authorizenet_cardCode'] = str(request.session['payment_authorizenet_cardCode'])
        request.session['payment_authorizenet_zip'] = str(request.session['payment_authorizenet_zip'])
        return True

    def checkout_confirm_render(self, request):
        """
        If the user has successfully filled in their payment data, they will be redirected to a confirmation
        page which lists all details of their order for a final review. This method should return the HTML which
        should be displayed inside the ‘Payment’ box on this page.
        """
        return "Your credit card information is forwarded to our payment processor using industry standard encryption. \
            It is not stored on our servers after the transaction is complete."

#    def checkout_prepare(self, request, cart):
#        raise Exception("checkout break")
#        return True

    def execute_payment(self, request, payment):
        """
        Charge a credit card
        """

        # Create a merchantAuthenticationType object with authentication details
        merchantAuth = apicontractsv1.merchantAuthenticationType()
        merchantAuth.name = self.settings.apiLoginID
        merchantAuth.transactionKey = self.settings.transactionKey

        # Create the payment data for a credit card
        creditCard = apicontractsv1.creditCardType()
        creditCard.cardNumber = request.session['payment_authorizenet_cardNumber']
        creditCard.expirationDate = request.session['payment_authorizenet_cardExpiration']
        creditCard.cardCode = request.session['payment_authorizenet_cardCode']

        # Add the payment data to a paymentType object
        paymentData = apicontractsv1.paymentType()
        paymentData.creditCard = creditCard

        # Create order information
        order = apicontractsv1.orderType()
        order.invoiceNumber = payment.order.code
        # invoiceNumber must be <= 20 char
        order.description = self.settings.purchaseDescription
        # Presumably, description will show in bank statements

        # Set the customer's Bill To address
        customerAddress = apicontractsv1.customerAddressType()
        customerAddress.firstName = request.session['payment_authorizenet_firstName']
        customerAddress.lastName = request.session['payment_authorizenet_lastName']
        # customerAddress.company = "Reebok"
        customerAddress.address = request.session['payment_authorizenet_address']
        customerAddress.city = request.session['payment_authorizenet_city']
        customerAddress.state = request.session['payment_authorizenet_state']
        customerAddress.zip = request.session['payment_authorizenet_zip']
        # customerAddress.country = "USA"

        # Set the customer's identifying information
        # customerData = apicontractsv1.customerDataType()
        # customerData.type = "individual"
        # customerData.id = "99999456654"
        # customerData.email = "EllenJohnson@example.com"

        # Add values for transaction settings
        duplicateWindowSetting = apicontractsv1.settingType()
        duplicateWindowSetting.settingName = "duplicateWindow"
        # Set duplicateWindow to 10min. Subsequent identical transactions will be rejected.
        # https://developer.authorize.net/api/reference/features/payment_transactions.html#Transaction_Settings
        duplicateWindowSetting.settingValue = "600"
        # set windowSetting to 1 for development. TODO: do this in test mode
        # duplicateWindowSetting.settingValue = "1"
        settings = apicontractsv1.ArrayOfSetting()
        settings.setting.append(duplicateWindowSetting)

        # Create a transactionRequestType object and add the previous objects to it.
        transactionrequest = apicontractsv1.transactionRequestType()
        transactionrequest.transactionType = "authCaptureTransaction"
        transactionrequest.amount = payment.amount
        transactionrequest.payment = paymentData
        transactionrequest.order = order
        transactionrequest.billTo = customerAddress
        # transactionrequest.customer = customerData
        transactionrequest.transactionSettings = settings
        # transactionrequest.lineItems = line_items

        # Assemble the complete transaction request
        createtransactionrequest = apicontractsv1.createTransactionRequest()
        createtransactionrequest.merchantAuthentication = merchantAuth
        # Send Payment ID to help track request.
        # TCP should handle this but checking it is important for security
        createtransactionrequest.refId = str(payment.id)
        createtransactionrequest.transactionRequest = transactionrequest
        # Create the controller
        createtransactioncontroller = createTransactionController(createtransactionrequest)
        # BooleanField is not deserializing properly
        # this might be a bug in pretix or perhaps django-hierarkey
        if self.settings.get('productionEnabled', as_type=bool):
            createtransactioncontroller.setenvironment(constants.PRODUCTION)
        createtransactioncontroller.execute()

        response = createtransactioncontroller.getresponse()

        responseCodes = enum.IntEnum(
            'responseCodes',
            [('Approved', 1),
             ('Declined', 2),
             ('Error', 3),
             ('Held_for_Review', 4),
             ]
        )

        def log_messages(request, transId, messagelist, action='authorizenet.payment.message'):
            for message in messagelist:
                payment.order.log_action(action, data={
                    'transId': transId or 0,
                    'resultCode': message.code.text,
                    # for some reason the response.messages.message is missing the .text member
                    'description': message.description.text if hasattr(message, 'description') else message['text'].text,
                })

        def log_errors(request, transId, errorlist, action='authorizenet.payment.error'):
            for error in errorlist:
                payment.order.log_action(action, data={
                    'transId': transId or 0,
                    'errorCode': error.errorCode.text,
                    'errorText': error.errorText.text,
                })

        def show_messages(request, messagelist, level=messages.INFO):
            for message in messagelist:
                messages.add_message(request, level, message.description.text)

        def show_errors(request, errorlist, level=messages.ERROR, message_text=None):
            for error in errorlist:
                messages.add_message(request, level, error.errorText.text)

        if response is not None:
            try:
                transId = int(response.transactionResponse.transId)
            except AttributeError:
                transId = 0
            # Check to see if the API request was successfully received and acted upon
            # if response.messages.resultCode == 'Ok':
            if hasattr(response, 'transactionResponse') and hasattr(response.transactionResponse, 'responseCode'):
                if response.transactionResponse.responseCode == responseCodes.Approved:
                    messagelist = response.transactionResponse.messages.message
                    payment.info = {'id': response.transactionResponse.transId}
                    log_messages(request, transId, messagelist, action='authorizenet.payment.approved')
                    show_messages(request, response.transactionResponse.messages.message, level=messages.SUCCESS)
                    payment.confirm()

                elif response.transactionResponse.responseCode == responseCodes.Declined:
                    log_errors(request, transId, response.transactionResponse.errors.error, action='authorizenet.payment.decline')
                    show_errors(request, response.transactionResponse.errors.error)
                    payment.fail({'reason': response.transactionResponse.errors.error[0].errorText.text,
                                  'transId': response.transactionResponse.transId.text})
                # Error response handling
                # elif response.transactionResponse.responseCode == responseCodes.Error:
                elif response.transactionResponse.responseCode == responseCodes.Error:
                    # If the resultCode is not 'Ok', there's something wrong with the API request
                    # errors.error is the list
                    log_errors(request, transId, response.transactionResponse.errors.error)
                    show_errors(request, response.transactionResponse.errors.error)
                    payment.fail(info={'error': response.transactionResponse.errors.error[0].errorText.text})
                    raise PaymentException('Transaction Declined')

                # we don't use hold for review
                elif response.transactionResponse.responseCode == responseCodes.Held_for_Review:
                    log_messages(request, transId, response.transactionResponse.messages.message)
                    show_messages(request, response.transactionResponse.messages.message)

            # Or, maybe log errors if the API request wasn't successful
            else:
                # no transactionResponse or no responseCode
                payment.fail(info={'error': 'API request failed. No Transaction Response'})
                # messages is django system for showing info to the user
                # message is the variable containing the message
                # import pdb; pdb.set_trace()
                log_messages(request, transId, response.messages.message, action='authorizenet.payment.failure')

                messages.error(request, 'API request error, please try again later')
                # no messages or errors
                # raise PaymentException("Failed Transaction with no error or message")

        else:
            payment.order.log_action('authorizenet.payment.fail')
            payment.fail({'error': 'could not contact gateway, response was None'})
            raise PaymentException('Could not contact API gateway, please try again later')
# vim:tw=139
