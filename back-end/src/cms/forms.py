from django import forms
from website.forms import BaseModelForm

from .models import Contact, Subscribe, Universal


class ContactForm(BaseModelForm):
    email_address = forms.EmailField()
    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)
        for field_name in self.fields:
            field = self.fields.get(field_name)
            print(field_name)
            if field:
                if type(field.widget) in (
                    forms.TextInput,
                    forms.DateInput,
                    forms.CharField,
                ):
                    field.widget = forms.TextInput()
                elif type(field.widget) == forms.EmailInput:
                    field.widget.input_type = 'email'
    class Meta:
        model = Contact
        fields = ["name","email_address","subject", "phone_number", "message", "order_number"]


class UniversalForm(BaseModelForm):
    email_address = forms.EmailField()
    def __init__(self, *args, **kwargs):
        super(UniversalForm, self).__init__(*args, **kwargs)
        for field_name in self.fields:
            field = self.fields.get(field_name)
            if field:
                field.required = True
                if field_name == "phone_number":
                    field.widget.input_type = 'tel'
                    field.widget.attrs.update({'placeholder': 'Enter your phone number'})
                    # pattern only numbers
                    field.widget.attrs.update({'pattern': '[0-9]*'})

                elif type(field.widget) in (
                    forms.TextInput,
                    forms.DateInput,
                    forms.CharField,
                ):
                    field.widget = forms.TextInput()
                elif type(field.widget) == forms.EmailInput:
                    field.widget.input_type = 'email'

                if field_name == 'name':
                    field.widget.attrs.update({'placeholder': 'Enter your name'})
                elif field_name == 'company_name':
                    field.widget.attrs.update({'placeholder': 'Enter your company name'})
                elif field_name == 'shipping_address':
                    field.widget.attrs.update({'placeholder': 'Enter address'})
                elif field_name == 'email_address':
                    field.widget.attrs.update({'placeholder': 'Enter your email'})

    class Meta:
        model = Universal
        fields = ["towel_rail", "name", "company_name", "shipping_address", "email_address", "phone_number", "proof_purchase"]


class SubscribeForm(BaseModelForm):
    class Meta:
        model = Subscribe
        fields = ["email_address"]
