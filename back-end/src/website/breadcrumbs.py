from django.utils.deprecation import MiddlewareMixin


class CrumbsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        """Adds an empty breadcrumb to every request
        , extra data is added by the add_crumbs function,
        called before template render (in the view)"""
        request._crumbs = []


def get_crumbs(request):
    """
    Return the message storage on the request if it exists,
    otherwise return an empty list.
    """
    return getattr(request, "_crumbs", [])


def add_crumbs(request, object_list=[]):
    """
    Attempt to add a message to the request using the 'messages' app.
    the crumbs is a list of tuples with (string, url)
    ie [('home', '/home', 'about us', '/about_us')]
    """
    try:
        crumbs = request._crumbs
    except AttributeError:
        if not hasattr(request, "META"):
            raise TypeError(
                "add_crumbs() argument must be an HttpRequest object, not "
                "'%s'." % request.__class__.__name__
            )
    else:
        return crumbs.extend(object_list)
