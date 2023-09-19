from cgi import test
from typing import Any

import requests

from django import forms
from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm


def validate_recaptcha(self):
    cls_name = self.__class__.__name__
    if cls_name in settings.FORM_RECAPTCHA:
        try:
            secret_key = settings.RECAPTCHA_SECRET_KEY
            g_recaptcha_response = self.data["g-recaptcha-response"]
            try:
                if not g_recaptcha_response and settings.CONFIG_ENV not in ["dev", "test"]:
                    raise Exception("Invalid Recaptcha, please refresh the page and retry")
                else:
                    params = {"secret": secret_key, "response": g_recaptcha_response}
                    url_api = settings.RECAPTCHA_API
                    response = requests.get(url_api, params)
                    if response.status_code == 200:
                        result = response.json()
                        if (result.get("success") != True and settings.CONFIG_ENV not in [
                            "dev",
                            "test",
                        ]) or result.get("score", 0) <= 0.5:
                            raise Exception("Invalid Recaptcha, please refresh the page and retry")
            except Exception as e:
                self.add_error(None, str(e))
        except KeyError as e:
            self.add_error(None, "Invalid Recaptcha, please refresh the page and retry")


class BaseModelForm(forms.ModelForm):
    def _post_clean(self):
        validate_recaptcha(self)
        super()._post_clean()


class BaseForm(forms.Form):
    def _post_clean(self):
        validate_recaptcha(self)
        super()._post_clean()


class BaseUserCreationForm(UserCreationForm):
    def _post_clean(self):
        validate_recaptcha(self)
        super()._post_clean()


class BaseUserCreateWithInvitationForm(UserCreationForm):
    def _post_clean(self):
        validate_recaptcha(self)
        super()._post_clean()
