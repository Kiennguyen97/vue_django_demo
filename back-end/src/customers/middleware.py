from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin


class CustomersMiddleware(MiddlewareMixin):
    def process_request(self, request):
        pass

    # def process_request(self, request):
    #     from products.models_lists import (
    #         ClosedPurchaseGroupItem,
    #         ClosedPurchaseGroupRel,
    #         PricelistCustomerRel,
    #         PricelistItem,
    #     )
    #
    #     """Adds an empty breadcrumb to every request
    #     , extra data is added by the add_crumbs function,
    #     called before template render (in the view)"""
    #     user = request.user
    #     # if logged into admin panel, get everything
    #     if user.is_staff:
    #         cache_key = user.id
    #         customer_type = "STAFF"
    #         access_view = ["OPEN", "TRADE", "LOGIN", "CLOSED"]
    #     # if logged in user, belonging to company
    #     elif user.id and user.company_id and user.get_group_code() == "TRADE":
    #         customer_type = "TRADE"
    #         cache_key = user.company_id.uuid
    #         access_view = ["OPEN", "TRADE", "LOGIN"]
    #     # if user logged in, not company (ie retail)
    #     elif user.id:
    #         cache_key = user.id
    #         customer_type = "RETAIL"
    #         access_view = ["OPEN", "LOGIN"]
    #     # if user not logged in
    #     else:
    #         cache_key = "NOT_LOGGED_IN"
    #         customer_type = "NOT_LOGGED_IN"
    #         access_view = ["OPEN"]
    #
    #     customer_info = cache.get(cache_key)
    #     if not customer_info:
    #         if customer_type == "TRADE":
    #             product_access = (
    #                 ClosedPurchaseGroupItem.objects.select_related("closed_purchase_group")
    #                 .filter(
    #                     closed_purchase_group__uuid__in=ClosedPurchaseGroupRel.objects.select_related(
    #                         "company"
    #                     )
    #                     .select_related("closed_purchase_group")
    #                     .filter(company__uuid=cache_key)
    #                     .values("closed_purchase_group__uuid"),
    #                 )
    #                 .values_list("product_id", flat=True)
    #             )
    #
    #             if len(product_access) == 0:
    #                 product_access = ["NULL"]
    #
    #             price_items = (
    #                 PricelistItem.objects.select_related("pricelist").filter(
    #                     pricelist__uuid__in=PricelistCustomerRel.objects.select_related(
    #                         "company", "pricelist"
    #                     )
    #                     .filter(company__uuid=cache_key)
    #                     .values("pricelist__uuid"),
    #                 )
    #             ).all()
    #             items = {}
    #             for obj in price_items:
    #                 if not items.get(obj.product_id):
    #                     items[obj.product_id] = obj.price
    #                 else:
    #                     old_price = items[obj.product_id]
    #                     if float(old_price) > float(obj.price):
    #                         items[obj.product_id] = obj.price
    #             if len(items):
    #                 pricelist_values = []
    #                 for k, x in items.items():
    #                     pricelist_values.append(tuple([k, float(x)]))
    #                 pricelist_value_string = str(pricelist_values).rstrip("]").lstrip("[")
    #             else:
    #                 pricelist_value_string = "('NULL', 0)"
    #         else:
    #             product_access = ["NULL"]
    #             items = {}
    #             pricelist_value_string = "('NULL', 0)"
    #
    #         customer_info = {
    #             "uuid": cache_key,
    #             "type": customer_type,
    #             "access_view": access_view,
    #             "product_access": product_access,
    #             "pricelist": items,
    #             "pricelist_value_string": pricelist_value_string,
    #         }
    #
    #         cache.set(cache_key, customer_info)
    #
    #     request.customer_info = customer_info
