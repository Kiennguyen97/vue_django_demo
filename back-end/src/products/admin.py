# Register your models here.
from customers.models import Addresses, CustomUser
from django import forms
from django.contrib import admin
from django.db import models
from django.db.models import Q
from django.forms import CheckboxSelectMultiple, RadioSelect
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.admin import widgets

from .models import (  # Brand,; Enquiry,; ProductTemplate,; ProductTemplateRel,
    Category,
    GalleryProduct,
    Option,
    Product,
    ProductOption,
    ProductOptionRel,
    GroupProduct,
    GroupProductRel,
    ProductOptionDependRel,
    OptionDependRel,
    ProductResource,
    ProductResourceRel,
    RelateProduct,
    Resource,
)
from .models_cart import (
    CartCoupon,
    CartCouponInstance,
    CartCouponLine,
    CartItem,
    CustomerCart,
)

# from .models_lists import (
#     ClosedPurchaseGroup,
#     ClosedPurchaseGroupItem,
#     ClosedPurchaseGroupRel,
#     Pricelist,
#     PricelistCustomerRel,
#     PricelistItem,
# )
from .models_order import Order, OrderInvoice, OrderInvoiceQuery, OrderItem
from .models_store_location import NZRegion, StoreLocation, StoreLocationEmail

# list field change to create new object
list_field_change = [
    "name",
    "slug",
    "code",
]

def resend_email_confirmation(modeladmin, request, queryset):
    for obj in queryset:
        obj.send_email_confirmation()


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = []

    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        try:
            self.fields["items"].queryset = OrderItem.objects.filter(
                order_uuid__exact=self.instance.uuid
            )
            self.fields["address_shipping"].queryset = Addresses.objects.filter(
                uuid__exact=self.instance.address_shipping.uuid
            )
            self.fields["address_billing"].queryset = Addresses.objects.filter(
                uuid__exact=self.instance.address_billing.uuid
            )
        except:
            self.fields["items"].queryset = OrderItem.objects.all()
            self.fields["address_shipping"].queryset = Addresses.objects.all()
            self.fields["address_billing"].queryset = Addresses.objects.all()


class OrderAdmin(admin.ModelAdmin):
    form = OrderForm
    list_display = ("uuid", "create_date", "get_pleasant")
    search_fields = ("uuid",)
    # list_editable = ("status",)
    readonly_fields = ("store_location",)
    formfield_overrides = {
        models.ManyToManyField: {"widget": CheckboxSelectMultiple},
    }

    fields = (
        "uuid",
        "order_notes",
        ("payment_type", "coupon"),
        "items",
        ("shipping_cost", "subtotal", "order_tax", "coupon_value"),
        ("order_total", "order_surcharge"),
        ("odoo_is_imported"),
        ("customer", "company_id", "purchase_order_ref"),
        ("address_shipping", "address_shipping_str"),
        ("address_billing", "address_billing_str"),
        "store_location",
    )

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(
            request,
            queryset,
            search_term,
        )

        if search_term[:4].lower() == "rat-":
            search_term = search_term[4:].lower()
            queryset = Order.objects.filter(uuid__startswith=search_term)
            return (queryset, True)

        return queryset, may_have_duplicates

    actions = [resend_email_confirmation]

    def get_pleasant(self, obj):
        return obj.get_pleasant_id()

    get_pleasant.short_description = "Order Id"

class CartItemForm(forms.ModelForm):
    class Meta:
        model = CartItem
        fields = "__all__"

class CartItemAdmin(admin.ModelAdmin):
    form = CartItemForm
    #      __str__ to list_display
    list_display = ("__str__", "create_date", "product", "product_quantity")
    ordering = ("-create_date",)
    search_fields = ("uuid", "product__name", "product__code")

# class PricelistCustomerRelInline(admin.TabularInline):
#     model = PricelistCustomerRel
#     extra = 1

# def formfield_for_foreignkey(self, db_field, request, **kwargs):
#     if db_field.name == "customer":
#         kwargs["queryset"] = CustomUser.objects.filter(~Q(company_id = None))
#     return super().formfield_for_foreignkey(db_field, request, **kwargs)


# class PricelistItemInline(admin.TabularInline):
#     model = PricelistItem
#     extra = 1
#     """
#     can_delete = False
#     max_num = 0
#
#     def has_change_permission(self, request, obj=None):
#         return False
#     """
#
#
# class PricelistAdmin(admin.ModelAdmin):
#     inlines = (PricelistCustomerRelInline, PricelistItemInline)


# class PricelistItemAdmin(admin.ModelAdmin):
#     list_display = ("pricelist", "product", "price")


class CategoryAdmin(admin.ModelAdmin):
    # def has_change_permission(self, request, obj=None):
    #     return False
    pass


class ProductOptionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["default_option"].queryset = Option.objects.filter(
            productoption_id=self.instance.productoption_id
        )

    class Meta:
        model = ProductOptionRel
        fields = "__all__"




class ProductOptionInline(admin.TabularInline):
    model = ProductOptionRel
    form = ProductOptionForm
    extra = 0
    autocomplete_fields = ["productoption"]

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj:
            product_same_group = obj.get_product_same_group()
            formset.form.base_fields['productoption'].queryset = ProductOption.objects.filter(
                Q(product_id=obj.pk) | Q(product_id=None) | Q(product_id__in=product_same_group)
            )
        return formset



class RelateProductInline(admin.TabularInline):
    model = RelateProduct
    extra = 0
    fk_name = "product"
    autocomplete_fields = ["relate_product"]


class GalleryProductAdminForm(forms.ModelForm):
    sku_matching = forms.ChoiceField(required=False)

    class Meta:
        model = GalleryProduct
        fields = (
            "image",
            "image_thumbnail",
            "hide_thumbnail",
            "sku_matching",
            "sequence",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace this with your dynamic choices logic
        product = self.instance.product
        dynamic_choices = [(' ', ' ')]
        if product:
            dynamic_choices.extend([(sku, sku) for sku in product.get_all_skus()])
        self.fields['sku_matching'].choices = dynamic_choices


class GalleryProductInline(admin.TabularInline):
    model = GalleryProduct
    extra = 0
    form = GalleryProductAdminForm
    fk_name = "product"


class ProductResourceInline(admin.TabularInline):
    model = ProductResourceRel
    extra = 0
    fk_name = "product"
    # def has_add_permission(self, request, obj=None):
    #     return False
    search_fields = ["product"]
    autocomplete_fields = ['productresource']


class GroupProductInlineProduct(admin.TabularInline):
    model = GroupProductRel
    extra = 0
    fk_name = "product"
    autocomplete_fields = ["group_product"]


class GroupProductInlineGroup(admin.TabularInline):
    model = GroupProductRel
    extra = 0
    fk_name = "group_product"
    autocomplete_fields = ["product"]


class GroupProductAdmin(admin.ModelAdmin):
    inlines = [
        GroupProductInlineGroup,
    ]
    search_fields = ["name"]
    fields = ["name", "description"]


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "name",
            "slug",
            "code",
            "list_price",
            "description_short",
            "description_long",
            "meta_description",
            "image_hover",
            "is_featured",
            "active",
            "can_purchase",
            # "category",
            "categories",
            "ordering",
            "dimension",
        )

class ProductAdmin(admin.ModelAdmin):
    search_fields = ["name", "code"]

    inlines = [
        ProductOptionInline,
        GroupProductInlineProduct,
        RelateProductInline,
        GalleryProductInline,
        ProductResourceInline,
    ]
    # def has_change_permission(self, request, obj=None):
    #     return False

    ## edit fields which display on the form
    form = ProductAdminForm

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_delete"] = False
        return super(ProductAdmin, self).changeform_view(
            request, object_id, extra_context=extra_context
        )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'categories':
            kwargs['widget'] = admin.widgets.FilteredSelectMultiple(
                verbose_name=db_field.verbose_name,
                is_stacked=False
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)

# class ProductTemplateRelInline(admin.TabularInline):
# model = ProductTemplateRel
# extra = 1


# class ProductTemplateAdmin(admin.ModelAdmin):
# search_fields = ["name", "product_ids__sku", "product_ids__name"]
# inlines = [ProductTemplateRelInline]


# class ClosedPurchaseGroupItemInline(admin.TabularInline):
#     model = ClosedPurchaseGroupItem
#     extra = 0


# class ClosedPurchaseGroupAdmin(admin.ModelAdmin):
#     inlines = [ClosedPurchaseGroupItemInline]


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0
    show_change_link = True



class OptionDependForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["depend_option"].queryset = Option.objects.filter(
            productoption_id=self.instance.depend_productoption_id
        )

    class Meta:
        model = OptionDependRel
        fields = "__all__"

class OptionDependRelInline(admin.TabularInline):
    model = OptionDependRel
    form = OptionDependForm
    fk_name = 'option'
    extra = 0
    autocomplete_fields = ["depend_productoption"]

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj and obj.productoption:
            product_same_group = []
            if obj.productoption.product:
                product_same_group = obj.productoption.product.get_product_same_group()
            formset.form.base_fields['depend_productoption'].queryset = ProductOption.objects.filter(
                Q(product=obj.productoption.product) | Q(product__in=product_same_group)
            )
        return formset

class OptionAdmin(admin.ModelAdmin):
    inlines = [OptionDependRelInline]
    list_display = ['name', 'productoption', 'sku_addition', 'price_adjust']
    readonly_fields = ['productoption']
    search_fields = ['name']

class ProductOptionDependForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["depend_option"].queryset = Option.objects.filter(
            productoption_id=self.instance.depend_productoption_id
        )

    class Meta:
        model = ProductOptionDependRel
        fields = "__all__"

class ProductOptionDependRelInline(admin.TabularInline):
    model = ProductOptionDependRel
    form = ProductOptionDependForm
    fk_name = 'productoption'
    extra = 0
    autocomplete_fields = ["depend_productoption"]

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj and obj.product:
            product_same_group = obj.product.get_product_same_group()
            formset.form.base_fields['depend_productoption'].queryset = ProductOption.objects.filter(
                Q(product=obj.product) | Q(product__in=product_same_group)
            )
        return formset


class ProductOptionAdmin(admin.ModelAdmin):
    inlines = [OptionInline, ProductOptionDependRelInline]
    list_display = ['option_name', 'option_type', 'display_choice']
    search_fields = ['option_name']
    autocomplete_fields = ['product']
    actions = ["copy_product_option"]
    change_form_template = "change_form.html"

    @admin.action(description="Copy selected product options")
    def copy_product_option(self, request, queryset):
        product_options_success = []
        product_options_error = []
        for obj in queryset:
            try:
                option_list = obj.copy_options()
                depend_option_list = obj.copy_depend_options()
                obj.pk = None
                option_name = obj.option_name
                obj.option_name = f"{obj.option_name} (copy)"
                obj.save()
                for option in option_list:
                    option.productoption = obj
                    option.save()
                for depend_option in depend_option_list:
                    depend_option.productoption = obj
                    depend_option.save()
                product_options_success.append(option_name)
            except:
                product_options_error.append(obj.option_name)
        self.message_user(request, f"Successfully copied {product_options_success.__len__()} product options")
        self.message_user(request, f"Product options {product_options_success} copied successfully")
        self.message_user(request, f"Product options {product_options_error} copied failed", level=messages.ERROR)

    def response_change(self, request, obj):
        if "_popup" in request.POST:
            request.POST._mutable = True
            del request.POST["_popup"]
            request.POST._mutable = False
        return super().response_change(request, obj)

    def render_change_form(self, request, context, *args, **kwargs):
        context["is_popup"] = "0"
        return super().render_change_form(request, context, *args, **kwargs)

class ResourceInline(admin.TabularInline):
    model = Resource
    extra = 0


# class ProductAdmin(admin.ModelAdmin):
#     search_fields = ['slug','name']


class ProductResourceAdmin(admin.ModelAdmin):
    inlines = [ResourceInline]
    autocomplete_fields = ["product"]
    search_fields = ["name", "product__name"]


class StoreLocationEmailInline(admin.TabularInline):
    model = StoreLocationEmail


class StoreLocationAdmin(admin.ModelAdmin):
    inlines = [StoreLocationEmailInline]
    readonly_fields = ("uuid",)
    list_display = ["name", "district", "region", "zip_code", "phone_number", "active", "can_appear_checkout"]
    search_fields = ["name"]


admin.site.register(Product, ProductAdmin)
admin.site.register(CartItem,CartItemAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(CustomerCart)
admin.site.register(CartCoupon)
admin.site.register(CartCouponInstance)
admin.site.register(CartCouponLine)
admin.site.register(Category, CategoryAdmin)
admin.site.register(OrderInvoice)
admin.site.register(OrderInvoiceQuery)
admin.site.register(ProductOption, ProductOptionAdmin)
admin.site.register(Option, OptionAdmin)
admin.site.register(ProductResource, ProductResourceAdmin)
admin.site.register(GroupProduct, GroupProductAdmin)

admin.site.register(StoreLocation, StoreLocationAdmin)
admin.site.register(NZRegion)
