from django.shortcuts import redirect
from django.conf import settings

class SimpleAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/login') and not request.session.get('authenticated'):
            return redirect('/login/')
        return self.get_response(request)
