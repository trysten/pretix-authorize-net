from django.dispatch import receiver
from pretix.base.signals import register_payment_providers
# Register your receivers here

@receiver(register_payment_providers, dispatch_uid='payment_authorizenet')
def register_payment_provider(sender, **kwargs):
    from .payment import Authorizenet
    return Authorizenet
