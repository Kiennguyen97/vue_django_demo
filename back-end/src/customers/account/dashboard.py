import math

from customers.account import BaseCustomerReload, CustomerReloadUps
from django.utils import timezone


@CustomerReloadUps.register_class
class CustomerDashboardReload(BaseCustomerReload):
    class_name = "customer_dashboard"

    def get_context_data(self, request):
        user = request.user
        chart_labels = []
        datasets = {"order": [], "money_spent": []}
        order_vals = {"order": {}, "money_spent": {}}
        max_order = 0
        max_money_spent = 0
        d = timezone.now()
        type_chart = request.data["type_chart"]
        month = request.data["month"]
        order_queryset = user.get_orders(**request.data)
        if type_chart.get("days"):
            for obj in order_queryset.all():
                day = obj.create_date.day
                if order_vals["order"].get(day):
                    order_vals["order"][day] = order_vals["order"][day] + 1
                else:
                    order_vals["order"][day] = 1

                if order_vals["money_spent"].get(day):
                    order_vals["money_spent"][day] = (
                        order_vals["money_spent"][day] + obj.order_total
                    )
                else:
                    order_vals["money_spent"][day] = obj.order_total

            # print('days: ', type_chart["days"])
            for day in type_chart["days"]:
                chart_labels.append(day)
                if int(month) > 0 and d.month == month and day > d.day:
                    continue

                if order_vals["order"].get(day):
                    if max_order < order_vals["order"][day]:
                        max_order = order_vals["order"][day]
                    datasets["order"].append(order_vals["order"][day])
                else:
                    datasets["order"].append(0)

                if order_vals["money_spent"].get(day):
                    if max_money_spent < order_vals["money_spent"][day]:
                        max_money_spent = order_vals["money_spent"][day]
                    datasets["money_spent"].append(order_vals["money_spent"][day])
                else:
                    datasets["money_spent"].append(0)

        elif type_chart.get("months"):
            chart_labels = type_chart["chart_labels"]
            for obj in order_queryset.all():
                month = obj.create_date.month
                if order_vals["order"].get(month):
                    order_vals["order"][month] = order_vals["order"][month] + 1
                else:
                    order_vals["order"][month] = 1

                if order_vals["money_spent"].get(month):
                    order_vals["money_spent"][month] = (
                        order_vals["money_spent"][month] + obj.order_total
                    )
                else:
                    order_vals["money_spent"][month] = obj.order_total

            for i in type_chart["months"]:
                if order_vals["order"].get(i):
                    if max_order < order_vals["order"][i]:
                        max_order = order_vals["order"][i]
                    datasets["order"].append(order_vals["order"][i])
                else:
                    datasets["order"].append(0)

                if order_vals["money_spent"].get(i):
                    if max_money_spent < order_vals["money_spent"][i]:
                        max_money_spent = order_vals["money_spent"][i]
                    datasets["money_spent"].append(order_vals["money_spent"][i])
                else:
                    datasets["money_spent"].append(0)
        elif type_chart.get("years"):
            chart_labels = type_chart["chart_labels"]
            for obj in order_queryset.all():
                year = obj.create_date.year
                if order_vals["order"].get(year):
                    order_vals["order"][year] = order_vals["order"][year] + 1
                else:
                    order_vals["order"][year] = 1

                if order_vals["money_spent"].get(year):
                    order_vals["money_spent"][year] = (
                        order_vals["money_spent"][year] + obj.order_total
                    )
                else:
                    order_vals["money_spent"][year] = obj.order_total

            for i in type_chart["years"]:
                if order_vals["order"].get(i):
                    if max_order < order_vals["order"][i]:
                        max_order = order_vals["order"][i]
                    datasets["order"].append(order_vals["order"][i])
                else:
                    datasets["order"].append(0)

                if order_vals["money_spent"].get(i):
                    if max_money_spent < order_vals["money_spent"][i]:
                        max_money_spent = order_vals["money_spent"][i]
                    datasets["money_spent"].append(order_vals["money_spent"][i])
                else:
                    datasets["money_spent"].append(0)

        max_order = (math.ceil(max_order / 50) + 1) * 50
        max_money_spent = (math.ceil(max_money_spent / 50) + 1) * 50

        context = {
            "chart_labels": chart_labels,
            "max_money_spent": max_money_spent,
            "max_order": max_order,
            "datasets_order": datasets["order"],
            "datasets_money_spent": datasets["money_spent"],
        }

        return context
