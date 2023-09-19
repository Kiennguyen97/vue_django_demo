from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from dateutil.relativedelta import relativedelta

from customers.models import CustomUser, GroupExtend
from products.models_order import Order, OrderItem

now = datetime.now()

mnth = (now - relativedelta(months=1)).month
yr = (datetime.today() - relativedelta(months=1)).year

# Dashboard report
def TradeCustomerOrder():
    # orders this month
    order = Order.objects.prefetch_related("items").filter(
        create_date__month=mnth, create_date__year=yr, customer__group_id__group_code="TRADE"
    )

    # customers created this month
    new_acc_cus = CustomUser.objects.filter(
        date_joined__month=mnth, date_joined__year=yr, group_id__group_code="TRADE"
    ).values_list("id", flat=True)

    total_sales = 0
    total_new_sales = 0
    cus_ordered = []
    for o in order:
        for item in o.items.all():
            total_sales += float(item.get_subtotal())

        if o.customer_id in new_acc_cus:
            cus_ordered.append(o.customer)
            for item in o.items.all():
                total_new_sales += float(item.get_subtotal())

    if len(order) > 0:
        avg_order = float(total_sales / (order.count()))
    else:
        avg_order = 0

    print("Account Holders - Trade Customers:")
    print("Orders(count):", order.count())
    print("Total Sales:$", round(total_sales, 3))
    print("Total New Sales:$", round(total_new_sales, 3))
    print("Avg Order-Basket size:$", round(avg_order, 3))
    print("No.new customers-ordered:", len(set(cus_ordered)))
    print("No.new accounts created:", new_acc_cus.count())


def RetailCustomerOrder():

    order = Order.objects.prefetch_related("items").filter(
        create_date__month=mnth, create_date__year=yr, customer__group_id__group_code="RETAIL"
    )
    print(len(order))

    new_acc_cus = CustomUser.objects.filter(
        date_joined__month=mnth, date_joined__year=yr, group_id__group_code="RETAIL"
    ).values_list("id", flat=True)

    total_sales = 0
    total_new_sales = 0
    cus_ordered = []

    for o in order:
        for item in o.items.all():
            total_sales += float(item.get_subtotal())

        if o.customer_id in new_acc_cus:
            cus_ordered.append(o.customer)

            for item in o.items.all():
                total_new_sales += float(item.get_subtotal())

    if len(order) > 0:
        avg_order = float(total_sales / (order.count()))
    else:
        avg_order = 0

    print("Cash Sales - Retail Customers:")
    print("Orders(count):", order.count())
    print("Total Sales:$", round(total_sales, 3))
    print("Total New Sales:$", round(total_new_sales, 3))
    print("Avg Order-Basket size:$", round(avg_order, 3))
    print("No.new customers-ordered:", len(set(cus_ordered)))
    print("No.new accounts created:", new_acc_cus.count())
    print("\n")


def Traffic_Overall():
    users = CustomUser.objects.count()
    new_users = CustomUser.objects.filter(date_joined__month=mnth, date_joined__year=yr)
    print("Traffic - Overall:")
    print("Users:", users)
    print("New Users:", new_users.count())
    print("\n")


def execute():
    print("================ DASHBOARD REPORT ====================")
    Traffic_Overall()
    RetailCustomerOrder()
    TradeCustomerOrder()
