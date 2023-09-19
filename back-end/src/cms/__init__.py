"""
import requests

from django.conf import settings


def validate_recaptcha(req):
    if settings.CONFIG_ENV in ("dev", "test"):
        return True

    if not req.POST.get("g-recaptcha-response"):
        return False

    req = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={
            "secret": settings.RECAPTCHA_SECRET_KEY,
            "response": req.POST["g-recaptcha-response"],
        },
    )
    if req.json()["success"] == True:
        return True
    else:
        return False
"""
