import erppeek

from django.conf import settings

"""Singleton instance for the odoo connections. Will open one instance per thread
    Use it like OdooClient.Instance().search_read() etc
"""


class Singleton:
    def __init__(self, cls):
        self._cls = cls

    def Instance(self):
        try:
            return self._instance
        except AttributeError:
            self._instance = self._cls()
            return self._instance

    def __call__(self):
        raise TypeError("Please Access Client through client.instance()")

    def __instancecheck__(self, inst):
        return isinstance(inst, self._cls)


@Singleton
class OdooClient(erppeek.Client):
    def __init__(self):
        server = settings.ODOO_CREDS["url"]
        db = settings.ODOO_CREDS["db"]
        user = settings.ODOO_CREDS["usr"]
        password = settings.ODOO_CREDS["pw"]

        transport = None
        verbose = None
        self._set_services(server, transport, verbose)
        self.reset()
        self.context = None
        if db:  # Try to login
            self.login(user, password=password, database=db)
