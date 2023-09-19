from customers import views
from customers.account import backorder as account_backorder_view
from customers.account import dashboard  # don't remove me
from customers.account import order as account_order_view
from customers.account import order_invoice as account_order_invoice_view
from customers.forms import CustomPasswordResetForm
from django.contrib.auth import views as auth_views
from django.urls import path

urlpatterns = [
    path("login/", views.sign_in, name="login"),
    path("register/", views.register_amtech, name="register"),
    path("sign_out/", views.sign_out, name="sign_out"),
    path("change_password/", views.change_password, name="change_password"),
    path(
        "reset_password/",
        auth_views.PasswordResetView.as_view(
            template_name="password_reset_form.html",
            form_class=CustomPasswordResetForm,
            subject_template_name="password_reset_subject.txt",
            email_template_name="password_reset_email.html",
        ),
        name="reset_password",
    ),
    path(
        "reset_password_sent/",
        auth_views.PasswordResetDoneView.as_view(template_name="password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.PasswordResetConfirmViewRel.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset_password_complete/",
        auth_views.PasswordResetCompleteView.as_view(template_name="password_reset_complete.html"),
        name="password_reset_complete",
    ),
    # path("account/", views.account, name="account"),
    path(
        "update_customer/<str:pk>/",
        views.UpdateCustomer.as_view(),
        name="update_customer",
    ),
    path("add-address/", views.AddressCreateView.as_view(), name="add_address"),
    path("get-address-suggestion", views.get_address_suggestion, name="get_address_suggestion"),
    path(
        "get-address-suggestion-detail",
        views.get_address_suggestion_detail,
        name="get_address_suggestion_detail",
    ),
    path(
        "update_address/<str:uuid>/",
        views.AddressUpdateView.as_view(),
        name="update_address",
    ),
    path("order-view/<str:order_id>/", account_order_view.order_view, name="order_view"),
    path("invoices/<str:pk>/", account_order_invoice_view.OrderInvoice.as_view(), name="invoices"),
    path(
        "order-history/<str:pk>/",
        account_order_view.OrderHistory.as_view(),
        name="order_history",
    ),
    path(
        "address-book/<str:pk>/",
        views.AddressBook.as_view(),
        name="address_book",
    ),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("user_management/", views.user_management, name="user_management"),
    path("api/reload", views.customer_reload, name="customer_reload"),
    path("add_new_customer/", views.add_new_user, name="add_new_user"),
    path("get-customer/", views.get_list_customer, name="get_list_customer"),
    path("delete-customer/", views.delete_customer, name="delete_customer"),
    path("backorder/<str:pk>/", account_backorder_view.Backorder.as_view(), name="backorder"),
    path(
        "invoice/query",
        account_order_invoice_view.customer_invoice_query,
        name="customer_invoice_query",
    ),
    path("invoice/download", account_order_invoice_view.invoice_download, name="invoice_download"),
]
