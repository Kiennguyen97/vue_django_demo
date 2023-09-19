import uuid

import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    password_validation,
    update_session_auth_hash,
)
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from odoo.utils import redirect_account_dashboard
from products.utils import move_guest_to_customer_cart

from .account import customer_reload_ups
from .forms import (
    AddNewCustomerForm,
    AddressForm,
    Customerform,
    RegisterForm,
    RegisterFromInvitationForm,
    SingInForm,
)
from .models import Addresses, Company, CustomUser
from .utils import InvitationStatus


class PasswordChangeFormRel(PasswordChangeForm):
    error_messages = {
        **SetPasswordForm.error_messages,
        "password_incorrect": _(
            "Your current password was entered incorrectly. Please enter it again."
        ),
    }

    old_password = forms.CharField(
        label=_("Current password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "autofocus": True}),
    )

    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label=_("Confirm New Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )

    def as_p_rel(self):
        "Return this form rendered as HTML <p>s."
        return self._html_output(
            # normal_row="<p%(html_class_attr)s>%(label)s %(field)s%(help_text)s</p>",
            normal_row="<p%(html_class_attr)s>%(label)s %(field)s</p>",
            error_row="%s",
            row_ender="</p>",
            help_text_html=' <span class="helptext">%s</span>',
            errors_on_separate_row=False,
        )


class UserSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )

    def as_p_rel(self):
        "Return this form rendered as HTML <p>s."
        return self._html_output(
            normal_row="<p%(html_class_attr)s>%(label)s %(field)s%(help_text)s</p>",
            error_row="%s",
            row_ender="</p>",
            help_text_html=' <span class="helptext">%s</span>',
            errors_on_separate_row=False,
        )


class PasswordResetConfirmViewRel(auth_views.PasswordResetConfirmView):
    template_name = "password_reset_confirm.html"
    form_class = UserSetPasswordForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.validlink:

            # dont show message on initial page load
            if self.request.method == "GET":
                pass
            else:
                message_dict = self.form_class.error_messages
                if message_dict:
                    for key, value in message_dict.items():
                        messages.error(self.request, value)

            context["validlink"] = True
        else:
            context.update(
                {
                    "form": None,
                    "title": _("Password reset unsuccessful"),
                    "validlink": False,
                }
            )
        return context


def handle_sign_in_redirect(request, default_redirect="dashboard"):
    ### logic to handle the redirect from the sign in / register page
    ### keep it all in here
    if request.session.get("referrer"):
        return redirect(request.session["referrer"])

    else:
        return redirect(default_redirect)


def handle_individual_signup(request):
    form = RegisterForm(request.POST)
    if form.is_valid():
        user = form.save()
        login(request, user)
        move_guest_to_customer_cart(request, user)
        messages.success(request, "Thanks for signing up - Welcome to Amtech!")
        return handle_sign_in_redirect(request)
    else:
        context = {}
        context["form"] = form
        context["cls_name"] = form.__class__.__name__
        context["formerrors"] = ", ".join([x[0] for _, x in form.errors.items()])
        messages.error(request, context["formerrors"])
        return render(request, "register-amtech.html", context)


def handle_company_signup(request, customer_id, is_invitation):
    form = RegisterFromInvitationForm(request.POST)
    data = form.data
    if form.is_valid():
        customer_query = CustomUser.objects.filter(
            id=customer_id, invitation_status=InvitationStatus.PENDING
        )
        if not customer_query.exists():
            messages.error(request, "The customer doesn't exist or accepted the invitation.")
        else:
            customer = customer_query.first()
            customer.invitation_status = InvitationStatus.APPROVED
            customer.set_password(data.get("password1"))
            customer.save()
            login(request, customer)
            move_guest_to_customer_cart(request, customer)
            messages.success(request, "Thanks for signing up - Welcome to Amtech!")
            return handle_sign_in_redirect(request)
    else:
        context = {}
        context["form"] = form
        context["cls_name"] = form.__class__.__name__
        context["formerrors"] = ", ".join([_ + ": " + x[0] for _, x in form.errors.items()])
        messages.error(request, context["formerrors"])
        return redirect(
            f"{reverse('register')}?is_invitation={is_invitation}&customer_id={customer_id}"
        )


def register_amtech(request):
    """Register page, used if customer fills it out, or if they sign up from an invitation"""

    is_invitation = bool(request.GET.get("is_invitation"))
    customer_id = request.GET.get("customer_id")

    if request.method == "POST":
        if is_invitation and customer_id:
            return handle_company_signup(request, customer_id, is_invitation)
        else:
            return handle_individual_signup(request)

    ### if method = GET
    company_name = ""
    form = RegisterForm()

    if is_invitation:
        cleanse_customer_id = str(uuid.UUID(customer_id))
        customer_query = CustomUser.objects.filter(
            id=cleanse_customer_id, invitation_status=InvitationStatus.PENDING
        )
        if not customer_query.exists():
            messages.error(
                request, "This invitation is not valid, please contact your administrator"
            )
        else:
            customer = customer_query.first()
            company_name = customer.company_id.name
            form = RegisterFromInvitationForm(
                initial={
                    "first_name": customer.first_name,
                    "last_name": customer.last_name,
                    "company_name": customer.company_id.name if customer.company_id.name else "",
                    "email": customer.email,
                },
            )

    context = {
        "is_invitation": is_invitation,
        "customer_id": customer_id,
        "company_name": company_name,
        "form": form,
        "cls_name": form.__class__.__name__,
    }
    return render(request, "register-amtech.html", context)


def sign_in(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        CustomUser.check_reply_email(request)
        form = SingInForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(email=email, password=password)
            if user:
                login(request, user)
                move_guest_to_customer_cart(request, user)
                messages.success(request, "You have logged in")
                return handle_sign_in_redirect(request)
            else:
                messages.info(request, "Try again! username or password is incorrect")
        else:
            messages.error(request, ", ".join([x[0] for _, x in form.errors.items()]))
    else:
        form = SingInForm()

    context = {"form": form, "cls_name": form.__class__.__name__}
    return render(request, "login.html", context)


def sign_out(request):
    logout(request)
    messages.success(request, "You have logged out")
    return redirect("login")


@login_required(login_url="login")
def change_password(request):
    try:
        if request.method == "POST":
            form = PasswordChangeFormRel(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)  # Important!
                messages.success(request, "Your password was successfully updated!")
                logout(request)
                return redirect("login")
            else:
                form = PasswordChangeFormRel(request.user)
                message_dict = form.error_messages
                if message_dict:
                    for key, value in message_dict.items():
                        messages.error(request, value)
                return redirect("update_customer", pk=request.user.id)
        else:
            form = PasswordChangeFormRel(request.user)
            return redirect("update_customer", pk=request.user.id)
    except Exception as exc:
        form = PasswordChangeFormRel(request.user)
        messages.error(request, "Error")
        return redirect("update_customer", pk=request.user.id)


@login_required(login_url="login")
def account(request):
    user = request.user
    context = {"user": user}
    return render(request, "account.html", context)


@method_decorator(login_required, name="dispatch")
class UpdateCustomer(UpdateView):
    model = CustomUser
    form_class = Customerform
    template_name = "account.html"
    # success_url= reverse_lazy('index')

    def get_context_data(self, **kwargs):
        if self.object.id == self.request.user.id:
            context = super().get_context_data(**kwargs)
            context["user"] = CustomUser.objects.get(id=self.request.user.id)
            context["company"] = self.request.user.get_company()
            context["form_pass"] = PasswordChangeFormRel(self.request.user)
            return context
        else:
            messages.error(self.request, "You are not allowed to edit this account.")
            return None

    def get_success_url(self):
        return reverse_lazy("update_customer", kwargs={"pk": self.request.user.id})

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Details updated")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class AddressCreateView(CreateView):
    model = Addresses
    form_class = AddressForm
    template_name = "add_address.html"
    success_url = reverse_lazy("index")

    def get_success_url(self):
        return reverse_lazy("address_book", kwargs={"pk": self.request.user.id})

    def form_invalid(self, form):
        msg_string = ""
        for _, y in form.errors.items():
            msg_string += y[0]
        messages.error(self.request, msg_string)
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        if self.request.user.get_group_code() == "TRADE":
            form.instance.company_id = self.request.user.company_id
        else:
            form.instance.customer = self.request.user
        messages.success(self.request, "Address Created")
        return super(AddressCreateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = CustomUser.objects.get(id=self.request.user.id)
        return context


@api_view(("GET",))
@login_required(login_url="login")
def get_address_suggestion(request):
    term = request.GET.get("term")
    url = f"{settings.ADDRESSRIGHT_API_ENPOIN}/autocomplete.json"
    params = {"api_key": settings.ADDRESSRIGHT_API_KEY, "term": term}
    response = requests.get(url=url, params=params)
    return Response(response.json())


@api_view(("GET",))
@login_required(login_url="login")
def get_address_suggestion_detail(request):
    address_id = request.GET.get("address_id")
    url = f"{settings.ADDRESSRIGHT_API_ENPOIN}/address.json"
    params = {"api_key": settings.ADDRESSRIGHT_API_KEY, "id": address_id}
    response = requests.get(url=url, params=params)
    return Response(response.json())


@method_decorator(login_required, name="dispatch")
class AddressUpdateView(UpdateView):
    model = Addresses
    form_class = AddressForm
    template_name = "edit_address.html"
    slug_url_kwarg = "uuid"
    slug_field = "uuid"

    def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        self.access_required(request, *args, **kwargs)
        return super().get(self, request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.access_required(request, *args, **kwargs)
        return super().post(self, request, *args, **kwargs)

    def access_required(self, request, *args, **kwargs):
        address = Addresses.objects.get(uuid=self.kwargs.get("uuid"))
        current_user = self.request.user
        if current_user.get_group_code() == "TRADE":
            if current_user.company_id.uuid != address.company_id.uuid:
                message = "You are not allowed to edit this address."
                return redirect_account_dashboard(self.request, message)
        else:
            if current_user.id != address.customer.id:
                message = "You are not allowed to edit this address."
                return redirect_account_dashboard(self.request, message)

    def get_success_url(self):
        return reverse_lazy("address_book", kwargs={"pk": self.request.user.id})

    def get_object(self, queryset=None):
        return Addresses.objects.get(uuid=self.kwargs.get("uuid"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = CustomUser.objects.get(id=self.request.user.id)
        return context

    def form_valid(self, form):
        messages.success(self.request, "Address updated")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class AddressBook(UpdateView):
    model = CustomUser
    form_class = Customerform
    template_name = "address_book.html"
    # success_url= reverse_lazy('index')

    def get_context_data(self, **kwargs):
        if self.object.id == self.request.user.id:
            context = super().get_context_data(**kwargs)
            context["user"] = CustomUser.objects.get(id=self.request.user.id)
            return context
        else:
            messages.error(self.request, "You are not allowed to edit this account.")
            return None

    def get_success_url(self):
        return reverse_lazy("address_book", kwargs={"pk": self.request.user.id})

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Details updated")
        return super().form_valid(form)


@login_required(login_url="login")
def dashboard(request):
    user = request.user
    all_orders = user.get_orders()
    order_count = all_orders.count()
    order_total = all_orders.aggregate(total=Sum("order_total"))
    context = {
        "user": user,
        "default_selas_person_name": settings.DEFAULT_SALES_PERSON["name"],
        "default_selas_person_email": settings.DEFAULT_SALES_PERSON["email"],
        "order_count": order_count,
        "order_totals": order_total["total"] if order_count else 0,
    }
    return render(request, "dashboard.html", context)


@login_required(login_url="login")
def user_management(request):
    user = request.user

    if user.company_id:
        customers_approved, count_customers_approved = CustomUser().get_user_management(
            type_filter="total", company_id=user.company_id, current_user_id=user.id
        )
        (
            customers_pending_invitations,
            count_customers_pending_invitations,
        ) = CustomUser().get_user_management(
            type_filter="pending_invitations", company_id=user.company_id, current_user_id=user.id
        )
    else:
        customers_approved = []
        count_customers_approved = 0
        customers_pending_invitations = []
        count_customers_pending_invitations = 0

    context = {
        "user": user,
        "customers_approved": customers_approved,
        "total_customers_approved": count_customers_approved,
        "customers_pending_invitations": customers_pending_invitations,
        "total_customers_pending_invitations": count_customers_pending_invitations,
    }
    return render(request, "user_management.html", context)


@api_view(["POST"])
@login_required(login_url="login")
def customer_reload(request):
    cls_name = request.headers["Class-Name"]
    class_up = customer_reload_ups.get_class(cls_name)()
    context = class_up.get_context_data(request)
    return Response(context)


@login_required(login_url="login")
def add_new_user(request):
    try:
        form = AddNewCustomerForm(request.POST)
        data = form.data
        user = request.user
        CustomUser().add_new_customer(
            data.get("first_name"),
            data.get("last_name"),
            data.get("email"),
            data.get("role"),
            user.company_id,
            user,
        )
        success_msg = "This user has been invited. They will be able to access your account once they accept the email invitation."
        messages.success(request, success_msg)
        return redirect("user_management")

    except Exception as exc:
        messages.error(request, exc)
        return redirect("user_management")


@api_view(("GET",))
@login_required(login_url="login")
def get_list_customer(request):
    try:
        user = request.user
        type_filter = request.GET.get("type_filter")
        keyword = request.GET.get("keyword")
        page_size = int(request.GET.get("page_size")) if request.GET.get("page_size") else None
        order_by = request.GET.get("order_by")
        result = None
        if user.company_id:
            data, total = CustomUser().get_user_management(
                type_filter=type_filter,
                company_id=user.company_id,
                current_user_id=user.id,
                keyword=keyword,
                order_by=order_by,
                page_size=page_size,
            )
            result_html = None
            if type_filter == "total":
                result_html = render_to_string(
                    "customer-part/um-total-user.html", context={"data": data, "user": user}
                )
            else:
                result_html = render_to_string(
                    "customer-part/um-customer-pending-invatation.html", context={"data": data}
                )
            result = {
                "data_html": result_html,
                "count": len(data),
                "total": total,
            }
            return Response(result, status=200)
        return Response(status=404, data=None)
    except Exception as exc:
        print("exc: ", exc)
        return Response(status=400)


def handle_delete(customer_id, request):

    customer_query = CustomUser.objects.filter(id=customer_id)

    if not customer_query.exists():
        messages.error(request, "This customer does not exist.")
    else:
        customer = customer_query.first()
        if customer.company_id_id != request.user.company_id_id:
            messages.error(request, "You do not have permission to delete this customer.")

        elif customer.email == request.user.email:
            messages.error(request, "You do not have permission to delete this customer.")
        else:
            customer.is_active = False
            customer.save()


@api_view(("GET",))
@login_required(login_url="login")
def delete_customer(request):

    customer_id = request.GET.get("customer_id")
    if not customer_id:
        messages.error(request, "The id of customer is required.")

    handle_delete(customer_id, request)
    return redirect("user_management")
