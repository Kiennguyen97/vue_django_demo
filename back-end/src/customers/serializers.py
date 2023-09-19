from dataclasses import dataclass

from rest_framework import serializers


@dataclass
class OrderOdooSerializer(object):
    order_id: str
    order_number: str
    customer_name: str
    confirmation_date: str
    client_order_ref: str
    delivery_address: str
    # deliv_name: str
    # carrier_id: int
    subtotal: float
    coupon: str
    coupon_value: float
    shipping_cost: float
    admin_fee: float
    order_tax: float
    # payment_type: str
    order_surcharge: float
    order_total: float
    # track_link: str


@dataclass
class OrderOdooDelivery(object):
    name: str
    tracking_link: str
    # carrier: str


@dataclass
class OrderItemOdooSerializer(object):
    sku: str
    product_name: str
    product_quantity: str
    qty_delivered: str
    product_price: str

    def get_subtotal(self):
        return float(self.product_quantity * self.product_price)

    def get_product_sku(self):
        return self.sku

    def get_product_name(self):
        return self.product_name
