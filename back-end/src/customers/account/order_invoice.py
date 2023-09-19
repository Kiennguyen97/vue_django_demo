from rest_framework.decorators import api_view
from rest_framework.response import Response

from customers.account import BaseCustomerReload, CustomerReloadUps
from customers.forms import Customerform
from customers.models import CustomUser
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView
from products.forms import OrderInvoiceQueryForm


@method_decorator(login_required, name="dispatch")
class OrderInvoice(UpdateView):
    model = CustomUser
    form_class = Customerform
    template_name = "account/invoices.html"

    def get_context_data(self, **kwargs):
        if self.object.id == self.request.user.id:
            context = super().get_context_data(**kwargs)
            context["query_type"] = settings.INVOICE_QUERY_TYPE
            return context
        else:
            messages.error(self.request, "You are not allowed to edit this account.")
            return None


@login_required(login_url="login")
def invoice_download(request):
    invoices = request.user.get_order_invoices(uuid=request.GET.get("uuid"))
    if invoices.exists():
        invoice = invoices.first()
        if invoice.pdf_url and invoice.pdf_url != "":
            return redirect(invoice.generate_pdf_presigned_url())
        else:
            messages.error(request, "Invoice not available, please try again later.")
            return HttpResponse("Invoice not available, please try again later.")
    else:
        messages.error(request, "Invoice not found.")
        return HttpResponse("Invoice not found.")


@api_view(("POST",))
@login_required(login_url="login")
def customer_invoice_query(request):
    form = OrderInvoiceQueryForm(request.POST)
    if form.is_valid():
        enquiry = form.save(commit=False)
        enquiry.customer_id = request.user
        enquiry.save()

        messages.success(request, "Your Invoice query was successfully submitted.")
        form.instance.send_email()
    else:
        messages.error(request, ", ".join([x[0] for _, x in form.errors.items()]))

    message_html = render_to_string("message.html", None, request, using=None)

    return HttpResponse((message_html), status=200, content_type="text/html")


@CustomerReloadUps.register_class
class CustomerOrderInvoicesReload(BaseCustomerReload):
    class_name = "customer_invoices"

    def get_context_data(self, request):
        post_data = request.data
        kwargs = {}
        number_item = 20
        if "from" in post_data:
            kwargs["from"] = post_data["from"]
        if "to" in post_data:
            kwargs["to"] = post_data["to"]
        if "query" in post_data:
            kwargs["query"] = post_data["query"]

        invoices = request.user.get_order_invoices(**kwargs)
        paginator = Paginator(invoices, number_item)
        page_number = post_data.get("page") if post_data.get("page") else 1

        page_obj = paginator.get_page(page_number)
        order_invoices = []
        for obj in page_obj:
            order_invoices.append(
                {
                    "id": obj.uuid,
                    "name": obj.name,
                    "total_exc_gst": obj.total_exc_gst,
                    "total_inc_gst": obj.total_inc_gst,
                    "date_invoice": obj.date_invoice.strftime("%d/%m/%Y")
                    if obj.date_invoice
                    else "",
                    "due_date": obj.due_date.strftime("%d/%m/%Y") if obj.due_date else "",
                    "invoice_source": obj.invoice_source,
                    "payment_status": obj.payment_status,
                    "is_download": True if obj.pdf_url else False,
                    "pdf_url": reverse("invoice_download") + "?uuid=" + obj.uuid,
                }
            )
        page_ranges = []
        for i in page_obj.paginator.page_range:
            page_ranges.append(i)
        context = {
            "items": order_invoices,
            "pagination": {
                "has_previous": page_obj.has_previous(),
                "previous_page_number": page_obj.previous_page_number()
                if page_obj.has_previous()
                else 0,
                "has_next": page_obj.has_next(),
                "next_page_number": page_obj.next_page_number() if page_obj.has_next() else 0,
                "number": page_obj.number,
                "previous_hellip": int(page_obj.number) - 4,
                "num_pages": page_obj.paginator.num_pages,
                "next_hellip": int(page_obj.number) + 4,
                "page_ranges": page_ranges,
                "number_previous_hellip": int(page_obj.number) - 5,
                "number_next_hellip": int(page_obj.number) + 5,
            },
        }
        return context
