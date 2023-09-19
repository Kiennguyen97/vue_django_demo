import django_rq
from django_rq import job

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .utils import smtp_send

if settings.CONFIG_ENV == "dev":
    from fakeredis import FakeStrictRedis
    from rq import Queue

    def get_queue(lvl):
        # return django_rq.get_queue(lvl)
        ## throws away the task, useful for dev & testing
        ## environments where redis not available
        return Queue(connection=FakeStrictRedis())

else:

    def get_queue(lvl):
        return django_rq.get_queue(lvl)


def send_email_confirmation(order_obj):
    get_queue("default").enqueue(order_obj.send_email_confirmation)


@job
def send_shipping_confirmation(order_fulfil_obj):
    order_fulfil_obj.send_shipping_confirmation()


@job
def send_order_invoice(order_invoice_obj):
    order_invoice_obj.send_order_invoice()


def send_mail(**kwargs):
    EMAIL_CC = settings.EMAIL_CC
    recipient = []
    if kwargs["type_mail"] == "contact":
        sender = "Sales | Newtech <sales@newtech.co.nz>"
        subject = "RE: '"+kwargs["email"]+"' submitted the form from your 'Contact Us' page" + kwargs["subject"]
        # recipient.append(kwargs['email'])
        recipient = [EMAIL_CC]
        recipient.append(kwargs["email"])
        html_message = render_to_string(
            "mail_contact.html",
            {
                "name": kwargs["name"],
                "email": kwargs["email"],
                "phone": kwargs["phone"],
                "subject": kwargs["subject"],
                "message": kwargs["message"],
                "order_number": kwargs["order_number"],
                "BASE_URL": settings.BASE_URL,
            },
        )
        plain_message = strip_tags(html_message)
        # mail_admins(subject, plain_message, fail_silently=False, connection=None, html_message=html_message)
        # send_mail(subject, plain_message, EMAIL_HOST_USER, recepient,fail_silently = False, html_message=html_message)
        smtp_send(
            subject=subject,
            emails=recipient,
            body=plain_message,
            html_body=html_message,
            sender=sender
        )
    elif kwargs["type_mail"] == "enquiry_product":
        subject = "Amtech Medical Enquiry -" + kwargs["name_product"]
        recipient = [EMAIL_CC]
        html_message = render_to_string(
            "mail_enquiry.html",
            {
                "customer_name": kwargs["customer_name"],
                "email_address": kwargs["email_address"],
                "company_name": kwargs["company_name"],
                "notes": kwargs["notes"],
            },
        )
        plain_message = strip_tags(html_message)
        smtp_send(
            subject=subject,
            emails=recipient,
            body=plain_message,
            html_body=html_message,
        )

    elif kwargs["type_mail"] == "subscribe":
        subject = "Amtech Medical - " + kwargs["subject"]
        recipient = [EMAIL_CC]
        recipient.append(kwargs["email"])
        html_message = render_to_string(
            "mail_subscribe.html",
            {"BASE_URL": settings.BASE_URL},
        )
        plain_message = strip_tags(html_message)
        smtp_send(
            subject=subject,
            emails=recipient,
            body=plain_message,
            html_body=html_message,
        )
    elif kwargs["type_mail"] == "universal":
        subject = "You have a new form request"
        SALE_EMAIL = settings.DEFAULT_SALES_PERSON.get('email')
        recipient = [SALE_EMAIL]
        recipient.append(EMAIL_CC)
        recipient.append(kwargs["email"])
        # Attach the proof_purchase file to the email
        proof_purchase_file = kwargs["proof_purchase"]
        attachment = None
        if proof_purchase_file:
            file_data = b""
            for chunk in proof_purchase_file.chunks():
                file_data += chunk
            if file_data:
                attachment = (proof_purchase_file.name, file_data, proof_purchase_file.content_type)

        html_message = render_to_string(
            "mail_universal.html",
            {
                "towel_rail": kwargs["towel_rail"],
                "name": kwargs["name"],
                "company_name": kwargs["company_name"],
                "shipping_address": kwargs["shipping_address"],
                "email": kwargs["email"],
                "phone": kwargs["phone"],
                "proof_purchase": kwargs["proof_purchase"],
                "BASE_URL": settings.BASE_URL,
            },
        )
        attachments = []
        if attachment:
            attachments.append(attachment)

        plain_message = strip_tags(html_message)
        smtp_send(
            subject=subject,
            emails=recipient,
            body=plain_message,
            html_body=html_message,
            attachments=attachments,
        )


    return HttpResponse("success")


def generate_new_nonce():
    client_token = settings.BRAINTREE_GATEWAY.client_token.generate()
    return client_token


def generate_cache_nonce():
    client_token = settings.BRAINTREE_GATEWAY.client_token.generate()
    cache.set("NEXT_NONCE", client_token, timeout=9000)


def get_nonce():
    """is called in checkout, gets nonce
    from cache & regenerates another async,
    or generates a new one if cache is empty"""

    if cache.get("NEXT_NONCE"):
        nonce = cache.get("NEXT_NONCE")
        cache.delete("NEXT_NONCE")
    else:
        # generate new one
        nonce = generate_new_nonce()

    get_queue("default").enqueue(generate_cache_nonce)
    return nonce
