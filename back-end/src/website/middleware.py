from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin


class GeneralMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        return response
