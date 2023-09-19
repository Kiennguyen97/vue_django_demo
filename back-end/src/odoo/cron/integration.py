from .integration_abstract import get_module_name


def execute(*args, **kwargs):
    app = get_module_name(args[0])
    app.execute()
