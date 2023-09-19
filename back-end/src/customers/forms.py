from django_rq import job

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    PasswordResetForm,
    UserChangeForm,
    UserCreationForm,
)
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.template import loader
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from products.utils import smtp_send
from website.forms import (
    BaseForm,
    BaseUserCreateWithInvitationForm,
    BaseUserCreationForm,
)

from .models import Addresses, CustomUser

UserModel = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)

    def clean(self):
        cleaned_data = super(CustomUserCreationForm, self).clean()
        group_id = cleaned_data.get("group_id")
        company_id = cleaned_data.get("company_id")
        if group_id and group_id.group_code == "TRADE" and not company_id:
            raise forms.ValidationError("Company is a required field.")
        return cleaned_data

    class Meta(UserCreationForm):
        model = CustomUser
        fields = ("email",)


class CustomUserChangeForm(UserChangeForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)

    def clean(self):
        cleaned_data = super(CustomUserChangeForm, self).clean()
        group_id = cleaned_data.get("group_id")
        company_id = cleaned_data.get("company_id")
        if group_id and group_id.group_code == "TRADE" and not company_id:
            raise forms.ValidationError("Company is a required field.")
        return cleaned_data

    class Meta:
        model = CustomUser
        fields = ("email",)


class RegisterForm(BaseUserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    company_name = forms.CharField(max_length=36, required=False)

    class Meta:
        model = CustomUser
        fields = ("email", "first_name", "last_name", "company_name")


class RegisterFromInvitationForm(BaseUserCreateWithInvitationForm):
    widg = forms.TextInput(attrs={"readonly": "readonly"})

    first_name = forms.CharField(max_length=150, widget=widg)
    last_name = forms.CharField(max_length=150, widget=widg)
    company_name = forms.CharField(max_length=36, required=False, widget=widg)
    email = forms.CharField(max_length=50, widget=widg)

    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "company_name")


class AddNewCustomerForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.CharField(max_length=150)
    role = forms.CharField(max_length=15)

    class Meta:
        model = CustomUser
        fields = ("email", "first_name", "last_name", "role")


class SingInForm(BaseForm):
    email = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "Email"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Password"}))


@job
def send_async(false, **kwargs):
    user = kwargs["user"]
    user_email = getattr(user, kwargs["email_field_name"])
    context = {
        "email": user_email,
        "domain": kwargs["domain"],
        "site_name": kwargs["site_name"],
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "user": user,
        "token": kwargs["token_generator"].make_token(user),
        "protocol": "https" if kwargs["use_https"] else "http",
        "host": kwargs["host"],
        "BASE_URL": settings.BASE_URL,
        **(kwargs["extra_email_context"] or {}),
    }

    html_body = render_to_string("password_reset_email.html", context)
    smtp_send(
        # subject_template_name,
        subject="Reset Your Password | Amtech Medical",
        emails=[user_email],
        html_body=html_body,
        body=strip_tags(html_body),
    )


class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super(CustomPasswordResetForm, self).__init__(*args, **kwargs)

    email = forms.CharField(
        label=_("Email"),
        max_length=254,
        widget=forms.TextInput(attrs={"autocomplete": "email"}),
    )

    def save(
        self,
        domain_override=None,
        subject_template_name="password_reset_subject.txt",
        email_template_name="password_reset_email.html",
        use_https=False,
        token_generator=default_token_generator,
        from_email=None,
        request=None,
        html_email_template_name=None,
        extra_email_context=None,
    ):
        """
        Generate a one-use only link for resetting password and send it to the
        user.
        """
        email = self.cleaned_data["email"]
        if email.find("@") == -1:
            email = email + settings.EMAIL_NO_REPLY
            email_field_name = UserModel.get_email_override_field_name()
        else:
            email_field_name = UserModel.get_email_field_name()
        if not domain_override:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override

        host = request.build_absolute_uri("/")
        host = host[:-1]
        for user in self.get_users(email):
            send_async.delay(
                false=False,
                user=user,
                domain=domain,
                site_name=site_name,
                token_generator=token_generator,
                use_https=use_https,
                host=host,
                email_field_name=email_field_name,
                extra_email_context=extra_email_context,
            )


class Customerform(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)

    # def clean(self):
    #     cleaned_data = super(Customerform, self).clean()
    #     group_id = cleaned_data.get("group_id")
    #     company_id = cleaned_data.get("company_id")
    #     if group_id:
    #         if group_id.group_code == 'TRADE' and not company_id:
    #             raise forms.ValidationError("Company is a required field.")
    #     return cleaned_data
    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email_override")


class AddressForm(forms.ModelForm):

    latitude = forms.FloatField(required=False)
    longitude = forms.FloatField(required=False)

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)
        for field_name in self.fields:
            field = self.fields.get(field_name)
            # if field_name in fields_index:
            #     print('field: ', field)
            #     field.widget = forms.TextInput(attrs={"tabindex": fields_index[field_name]})
            if field:
                if type(field.widget) in (
                    forms.TextInput,
                    forms.DateInput,
                    forms.CharField,
                ):
                    field.widget = forms.TextInput(attrs={"placeholder": field.label})
            fields_index = {"name": 1, "phone": 2}
            if field_name in fields_index:
                field.widget.attrs["tabindex"] = fields_index[field_name]

    class Meta:
        model = Addresses
        fields = [
            "name",
            "street_address_1",
            "street_address_2",
            "city",
            "phone",
            "address_postal",
            "type_address",
            "latitude",
            "longitude",
        ]
