from customers.models import Addresses
from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.html import conditional_escape, html_safe
from django.utils.safestring import mark_safe

# from .models import Enquiry
from .models_cart import CartCoupon, CartCouponInstance
from .models_order import Order, OrderInvoiceQuery
from website.forms import BaseModelForm


class CheckoutForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super(CheckoutForm, self).__init__(*args, **kwargs)
        for field_name in self.fields:
            field = self.fields.get(field_name)
            if field:
                if type(field.widget) in (
                    forms.TextInput,
                    forms.DateInput,
                    forms.EmailInput,
                ):
                    field.widget = forms.TextInput(attrs={"placeholder": field.label})

    class Meta:
        model = Order
        fields = ["order_notes", "purchase_order_ref"]


class NewAddressForm(ModelForm):

    latitude = forms.FloatField(required=False)
    longitude = forms.FloatField(required=False)

    def __init__(self, *args, **kwargs):
        super(NewAddressForm, self).__init__(*args, **kwargs)
        for field_name in self.fields:
            field = self.fields.get(field_name)
            if field:
                # print(field.label)
                if field.label == "Address postal":
                    field.label = "Postal Code"
                if type(field.widget) in (
                    forms.TextInput,
                    forms.DateInput,
                ):
                    field.widget = forms.TextInput(attrs={"placeholder": field.label})

    def _html_output_with_alpine(
        self, normal_row, error_row, row_ender, help_text_html, errors_on_separate_row, field_name
    ):
        "Output HTML. Used by as_table(), as_ul(), as_p()."
        # Errors that should be displayed above all fields.
        top_errors = self.non_field_errors().copy()
        output, hidden_fields = [], []

        for name, field in self.fields.items():
            html_class_attr = ""
            bf = self[name]
            bf_errors = self.error_class(bf.errors)
            if bf.is_hidden:
                if bf_errors:
                    top_errors.extend(
                        [
                            ("(Hidden field %(name)s) %(error)s") % {"name": name, "error": str(e)}
                            for e in bf_errors
                        ]
                    )
                hidden_fields.append(str(bf))
            else:
                # Create a 'class="..."' attribute if the row should have any
                # CSS classes applied.
                css_classes = bf.css_classes()
                if css_classes:
                    html_class_attr = ' class="%s"' % css_classes

                if errors_on_separate_row and bf_errors:
                    output.append(error_row % str(bf_errors))

                if bf.label:
                    label = conditional_escape(bf.label)
                    label = bf.label_tag(label) or ""
                else:
                    label = ""

                if field.help_text:
                    help_text = help_text_html % field.help_text
                else:
                    help_text = ""
                template = ""
                if name == field_name:
                    template = '<template x-if="open"><ul class="ui-autocomplete ui-items">\
                      <template x-for="item in addresss"><li class="ui-item">\
                      <span x-text="item.label" @click="selectAddress(item.id)"></span>\
                      </li></template></ul></template>'

                output.append(
                    normal_row
                    % {
                        "errors": bf_errors,
                        "label": label,
                        "field": bf,
                        "help_text": help_text,
                        "html_class_attr": html_class_attr,
                        "css_classes": css_classes,
                        "field_name": bf.html_name,
                        "template": template,
                    }
                )

        if top_errors:
            output.insert(0, error_row % top_errors)

        if hidden_fields:  # Insert any hidden fields in the last row.
            str_hidden = "".join(hidden_fields)
            if output:
                last_row = output[-1]
                # Chop off the trailing row_ender (e.g. '</td></tr>') and
                # insert the hidden fields.
                if not last_row.endswith(row_ender):
                    # This can happen in the as_p() case (and possibly others
                    # that users write): if there are only top errors, we may
                    # not be able to conscript the last row for our purposes,
                    # so insert a new, empty row.
                    last_row = normal_row % {
                        "errors": "",
                        "label": "",
                        "field": "",
                        "help_text": "",
                        "html_class_attr": html_class_attr,
                        "css_classes": "",
                        "field_name": "",
                        "template": "",
                    }
                    output.append(last_row)
                output[-1] = last_row[: -len(row_ender)] + str_hidden + row_ender
            else:
                # If there aren't any rows in the output, just append the
                # hidden fields.
                output.append(str_hidden)
        return mark_safe("\n".join(output))

    def as_p_with_alpine(self):
        "Return this form rendered as HTML <p>s."
        # add alpine js to use autocomple when find address
        """
        normal_row='<p%(html_class_attr)s>%(label)s %(field)s%(help_text)s\
        <template x-if="open"><ul class="ui-autocomplete ui-items">\
        <template x-for="item in addresss"><li class="ui-item">\
        <span x-text="item.label" @click="selectAddress(item.id)"></span></li>\
        </template></ul></template></p>'
        """
        return self._html_output_with_alpine(
            normal_row="<p%(html_class_attr)s>%(label)s %(field)s%(help_text)s%(template)s</p>",
            error_row="%s",
            row_ender="</p>",
            help_text_html=' <span class="helptext">%s</span>',
            errors_on_separate_row=True,
            field_name="street_address_1",
        )

    class Meta:
        model = Addresses
        fields = [
            "name",
            "street_address_1",
            "street_address_2",
            "latitude",
            "longitude",
            "city",
            "phone",
            "address_postal",
        ]


class CartCouponForm(ModelForm):
    class Meta:
        model = CartCouponInstance
        fields = ["coupon_code"]

    def clean_coupon_code(self):
        data = self.cleaned_data["coupon_code"]
        if CartCoupon.objects.filter(coupon_code=data).first():
            return data
        else:
            raise ValidationError(
                "Invalid Coupon Code: %(coupon_code)s", params={"coupon_code": data}
            )


class OrderInvoiceQueryForm(ModelForm):
    class Meta:
        model = OrderInvoiceQuery
        fields = ["order_invoice_id", "query_type", "query_message"]
