"""Stores the current request in a contextvar so model signals and services
can attribute changes to an actor/IP without passing the request around."""
import contextvars

_current_request = contextvars.ContextVar("current_request", default=None)


def get_current_request():
    return _current_request.get()


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request.reset(token)
