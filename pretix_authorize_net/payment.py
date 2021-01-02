from authorizenet import apicontractsv1
from authorizenet.apicontrollers import createTransactionController
from django import forms
from django.contrib import messages
from collections import OrderedDict
from pretix.base.payment import BasePaymentProvider, PaymentException
from django.utils.translation import gettext as _
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
                ('solutionID',
                 forms.CharField(
                     widget=forms.TextInput,
                     label=_('Solution ID'),
                     required=False
                 )),

            ]
        )

    @property
    def settings_form_fields(self):
        d = OrderedDict(list(super().settings_form_fields.items()) + list(Authorizenet.form_fields().items()))
        d.move_to_end('apiLoginID', last=False)
        d.move_to_end('transactionKey', last=False)
        # d.move_to_end('solutionID', last=False)
        d.move_to_end('_enabled', last=False)
        return d

    @property
    def payment_form_fields(self):
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
             forms.CharField(
                 label=_('State'),
                 required=True
             )),
            ('zip',
             forms.IntegerField(
                 widget=forms.TextInput,
                 label=_('Zipcode'),
                 required=True
             )),
            ('cardNumber',
             forms.CharField(
                 widget=forms.TextInput,
                 label=_('Card Number'),
                 required=True
             )),
            ('cardExpiration',
             forms.CharField(
                 widget=forms.TextInput(attrs={'placeholder': "mm/yy"}),
                 label=_('Card Expiration Date'),
                 required=True
             )),
            ('cardCode',
             forms.IntegerField(
                 widget=forms.TextInput(attrs={'placeholder': "Code on Back of Card"}),
                 label=_('Card Code'),
                 required=True
             )),
        ])

    def settings_content_render(self, request):
        return "This is plugin is in alpha. Refunds are not supported, but can be done manually on Authorize.net"

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
        return "working on it. this is checkout_confirm_render output"

#    def checkout_prepare(self, request, cart):
#        raise Exception("checkout break")
#        return True

    def execute_payment(self, request, payment):
        """
        Charge a credit card
        """

        # Create a merchantAuthenticationType object with authentication details
        # retrieved from the constants file
        merchantAuth = apicontractsv1.merchantAuthenticationType()
        merchantAuth.name = self.settings.apiLoginID
        merchantAuth.transactionKey = self.settings.transactionKey

        # Create the payment data for a credit card
        creditCard = apicontractsv1.creditCardType()
        from pprint import pprint
        logger.debug(pprint(vars(request.session)))
        creditCard.cardNumber = request.session['payment_authorizenet_cardNumber']
        creditCard.expirationDate = request.session['payment_authorizenet_cardExpiration']
        creditCard.cardCode = request.session['payment_authorizenet_cardCode']

        # Add the payment data to a paymentType object
        paymentData = apicontractsv1.paymentType()
        paymentData.creditCard = creditCard

        # Create order information
        order = apicontractsv1.orderType()
        order.invoiceNumber = payment.order.full_code
        # invoiceNumber must be <= 20 char
        order.description = "SiTFH 2021 Tickets"
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
        customerData = apicontractsv1.customerDataType()
        customerData.type = "individual"
        customerData.id = "99999456654"
        customerData.email = "EllenJohnson@example.com"

        # Add values for transaction settings
        duplicateWindowSetting = apicontractsv1.settingType()
        duplicateWindowSetting.settingName = "duplicateWindow"
        # Set duplicateWindow to 10min. Subsequent identical transactions will be rejected.
        # https://developer.authorize.net/api/reference/features/payment_transactions.html#Transaction_Settings
        duplicateWindowSetting.settingValue = "600"
        # set windowSetting to 1 for development. TODO: do this in test mode
        duplicateWindowSetting.settingValue = "1"
        settings = apicontractsv1.ArrayOfSetting()
        settings.setting.append(duplicateWindowSetting)

        # I'm not sure where these end up going, so we may not ever implement them
#        line_item_1 = apicontractsv1.lineItemType()
#        line_item_1.itemId = "12345"
#        line_item_1.name = "first"
#        line_item_1.description = "Here's the first line item"
#        line_item_1.quantity = "2"
#        line_item_1.unitPrice = "12.95"
#        line_item_2 = apicontractsv1.lineItemType()
#        line_item_2.itemId = "67890"
#        line_item_2.name = "second"
#        line_item_2.description = "Here's the second line item"
#        line_item_2.quantity = "3"
#        line_item_2.unitPrice = "7.95"

        # build the array of line items
#        line_items = apicontractsv1.ArrayOfLineItem()
#        line_items.lineItem.append(line_item_1)
#        line_items.lineItem.append(line_item_2)

        # Create a transactionRequestType object and add the previous objects to it.
        transactionrequest = apicontractsv1.transactionRequestType()
        transactionrequest.transactionType = "authCaptureTransaction"
        transactionrequest.amount = payment.amount
        transactionrequest.payment = paymentData
        transactionrequest.order = order
        transactionrequest.billTo = customerAddress
        transactionrequest.customer = customerData
        transactionrequest.transactionSettings = settings
#       transactionrequest.lineItems = line_items

        # Assemble the complete transaction request
        createtransactionrequest = apicontractsv1.createTransactionRequest()
        createtransactionrequest.merchantAuthentication = merchantAuth
        # Send Payment ID to help track request.
        # TCP should handle this but checking it is important for security
        createtransactionrequest.refId = str(payment.id)
        createtransactionrequest.transactionRequest = transactionrequest
        # Create the controller
        createtransactioncontroller = createTransactionController(createtransactionrequest)
        createtransactioncontroller.execute()

        response = createtransactioncontroller.getresponse()

        class responseCodes(enum.Enum):
            Approved = 1
            Declined = 2
            Error = 3
            Held_for_Review = 4

        if response is not None:
            # Check to see if the API request was successfully received and acted upon
            if response.messages.resultCode == 'Ok':
                # import pdb; pdb.set_trace()
                # The API request was successful
                if response.transactionResponse.responseCode == responseCodes.Approved:
                    payment.info = {'id': response.transactionResponse.transId}
                    # logger.info(request, 'Successfully created transaction with Transaction ID: %s' % response.transactionResponse.transId)
                    # logger.info(request, 'Transaction Response Code: %s' % response.transactionResponse.responseCode)
                    # logger.info(request, 'Message Code: %s' % response.transactionResponse.messages.message[0].code)
                    # logger.info(request, 'Description: %s' % response.transactionResponse.messages.message[0].description)
                    for message in response.transactionResponse.messages.message:
                        # messages.message is an list containing the messages. wtf?
                        payment.order.log_action('authorizenet.payment.success', data={
                            'resultCode': message.code.text,
                            'description': message.description,
                        })
                        messages.success(request, message.description)
                    payment.confirm()

                elif response.transactionResponse.responseCode == responseCodes.Declined:
                    for message in response.transactionResponse.messages.message:
                        payment.order.log_action('authorizenet.payment.decline', data={
                            'resultCode': message.code.text,
                            'description': message.description,
                        })
                        messages.error(request, 'Card Declined')
                    payment.fail({'reason': response.transactionResponse.messages.message[0].description})

                elif response.transactionResponse.responseCode == responseCodes.Error:
                    # logger.error('Transaction returned OK but no message')
                    # If the resultCode is not 'Ok', there's something wrong with the API request
                    if hasattr(response.transactionResponse, 'errors') is True:
                        # errors.error is the list
                        for error in response.transactionResponse.errors.error:
                            payment.order.log_action('authorizenet.payment.error', data={
                                'errorCode': error.errorCode.text,
                                'errorText': error.errorText,
                            })
                            messages.warning(request, 'Error Code:  %s' % error.errorCode.text)
                            messages.warning(request, 'Error message: %s' % error.errorText)
                    else:
                        raise PaymentException('Transaction returned OK with no message or error', code='responseError')
                        # no errors either? why is this in the example code?
                    payment.fail({'error': error.errorText.text})

            # Or, log errors if the API request wasn't successful
            else:
                messages.error(request, 'API request failed, please try again later')
                if hasattr(response, 'transactionResponse') is True and hasattr(response.transactionResponse, 'errors') is True:
                    for error in response.transactionResponse.errors.error:
                        payment.order.log_action('authorizenet.payment.error', data={
                            'errorCode': error.errorCode.text,
                            'errorText': error.errorText.text,
                        })
                        messages.error(request, 'Error Code: %s' % error.errorCode.text)
                        messages.error(request, 'Error message: %s' % error.errorText)
                else:
                    # messages is django system for showing info to the user
                    # message is the variable containing the message
                    # TODO: disambiguate message vs messages
                    # note the messages here are on response, not response.transactionResponse
                    # they come from the authorizenet sdk, presumably
                    for message in response.messages.message:
                        payment.order.log_action('authorizenet.payment.fail', data={
                            'errorCode': message.code.text,
                            'errorText': message.text,
                        })
                        messages.error(request, 'Error Code: %s' % message.code.text)
                        messages.error(request, 'Error message: %s' % message.text.text)
                    raise PaymentException("Failed Transaction with no errors")
        else:
            payment.order.log_action('authorizenet.payment.fail')
            # messages.error(request, 'Could not contact API gateway. Please try again later.')
            raise PaymentException('Could not contact API gateway, please try again later')
# vim:tw=139
