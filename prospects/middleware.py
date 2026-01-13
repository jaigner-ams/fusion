from django.http import HttpResponseRedirect


class ProspectsSubdomainMiddleware:
    """
    Middleware to handle the prospects.amsfusion.com subdomain.
    When accessing this subdomain:
    - Redirects root URL to /prospects/
    - Only allows access to /prospects/ and /accounts/ URLs
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0]

        if host == 'prospects.amsfusion.com':
            # If accessing root, redirect to prospects list
            if request.path == '/':
                return HttpResponseRedirect('/prospects/')

            # Only allow prospects app URLs and auth URLs
            allowed_paths = ['/prospects/', '/accounts/', '/admin/', '/static/', '/media/']
            if not any(request.path.startswith(path) for path in allowed_paths):
                return HttpResponseRedirect('/prospects/')

        return self.get_response(request)
