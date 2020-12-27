from django.utils.translation import gettext_lazy

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")

__version__ = '0.1.0'


class AuthorizenetApp(PluginConfig):
    name = 'pretix_authorize_net'
    verbose_name = 'Authorize.net'

    class PretixPluginMeta:
        name = gettext_lazy('Authorize.net')
        author = 'trysten'
        description = gettext_lazy('Authorize.net payment provider plugin')
        visible = True
        version = __version__
        category = 'PAYMENT'
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # NOQA


default_app_config = 'pretix_authorize_net.AuthorizenetApp'
