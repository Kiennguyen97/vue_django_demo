from importlib import import_module


def load_module_by_name(name):
    """
    Given a command name and an application name, return the Command
    class instance. Allow all errors raised by the import process
    (ImportError, AttributeError) to propagate.
    """
    module = import_module("%s.%s" % ("odoo", name))
    return module


def get_module_name(name):
    return load_module_by_name(name)
