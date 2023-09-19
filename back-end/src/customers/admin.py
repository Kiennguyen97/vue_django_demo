from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.forms.models import BaseInlineFormSet
# from products.models_lists import (
#     ClosedPurchaseGroupRel,
#     Pricelist,
#     PricelistCustomerRel,
# )
from products.models_order import Order

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import Addresses, Company, CustomUser, GroupExtend


class ChildInlineFormSet(BaseInlineFormSet):
    def get_queryset(self):
        if self.instance.get_group_code() == "TRADE":
            qs = Order.objects.filter(company_id__uuid=self.instance.company_id.uuid)
        else:
            qs = Order.objects.filter(customer__id=self.instance.id)
        return qs


class OrderInline(admin.TabularInline):
    model = Order
    formset = ChildInlineFormSet
    extra = 0
    can_delete = False
    max_num = 0

    def has_change_permission(self, request, obj=None):
        return False


class CustomUserAdmin(UserAdmin):
    # inlines = [
    #     OrderInline,
    # ]
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ("email", "company_name", "role", "is_staff", "is_active", "is_superuser")
    list_filter = ("email", "company_name", "role", "is_staff", "is_active", "is_superuser")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "role",
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "first_name",
                    "last_name",
                    "company_id",
                    "group_id",
                    "company_name",
                    "email_override",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "first_name",
                    "last_name",
                    "company_id",
                    "group_id",
                    "user_permissions",
                ),
            },
        ),
    )
    search_fields = ("email",)
    ordering = ("email",)


class AddressInline(admin.TabularInline):
    model = Addresses
    extra = 0
    can_delete = False
    max_num = 0

    def has_change_permission(self, request, obj=None):
        return False


class CustomerInline(admin.TabularInline):
    model = CustomUser
    extra = 0
    can_delete = False
    max_num = 0
    fields = ("email", "first_name", "last_name")

    def has_change_permission(self, request, obj=None):
        return False


class OrderInline(admin.TabularInline):
    model = Order
    extra = 0
    can_delete = False
    max_num = 0
    show_change_link = True
    fields = (
        "uuid",
        "order_notes",
        "payment_type",
        "order_total",
        "purchase_order_ref",
    )

    def has_change_permission(self, request, obj=None):
        return False


# class PricelistInLine(admin.TabularInline):
#
#     model = PricelistCustomerRel
#     extra = 0
#     can_delete = False
#     max_num = 0
#
#     def has_change_permission(self, request, obj=None):
#         return False


class CompanyAdmin(admin.ModelAdmin):
    # inlines = (AddressInline, CustomerInline, OrderInline, PricelistInLine)  # before
    inlines = (AddressInline, CustomerInline, OrderInline)



# class CompanyClosedPurchaseGroupInLine(admin.TabularInline):
#     model = ClosedPurchaseGroupRel
#     extra = 0


# class CompanyPricelistInLine(admin.TabularInline):
#     model = PricelistCustomerRel
#     extra = 0
#     max_num = 1


# class CompanyCPGAndPricelistAdmin(admin.ModelAdmin):
#     inlines = (CompanyClosedPurchaseGroupInLine, CompanyPricelistInLine)


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Addresses)
admin.site.register(GroupExtend)
# admin.site.register(Company, CompanyCPGAndPricelistAdmin)  # before
admin.site.register(Company)
