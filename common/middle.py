class DisableCSRFMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        setattr(request, "_dont_enforce_csrf_checks", True)
        response = self.get_response(request)
        return response


class NoCacheMiddleware(object):
    """Tell the browser to never reuse anything while developing.

    Django sends no ``Cache-Control`` header for pages or static files, so
    browsers cache both heuristically. The result is an edit that appears to do
    nothing until you empty the cache by hand — Safari makes this especially
    easy to trip over. Only installed when DEBUG is on.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Cache-Control"] = "no-store, max-age=0"
        return response
