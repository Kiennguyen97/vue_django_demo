from crum import get_current_user

from django.db import models
from django.utils.translation import gettext_lazy as _

# from .models import Product


# class Pricelist(models.Model):
#     uuid = models.CharField(primary_key=True, max_length=36)
#     name = models.CharField(max_length=200)
#     odoo_id = models.IntegerField()
#     company = models.ManyToManyField(
#         "customers.Company",
#         through="PricelistCustomerRel",
#         related_name="pricelists_all",
#     )
#
#     def __str__(self):
#         return self.name


# class PricelistCustomerRel(models.Model):
#     company = models.ForeignKey("customers.Company", on_delete=models.CASCADE)
#     pricelist = models.ForeignKey(Pricelist, on_delete=models.CASCADE)
#
#     def __str__(self):
#         try:
#             name = self.company.name + " - " + self.pricelist.name
#         except Exception as e:
#             name = ""
#         return name
#
#     class Meta:
#         unique_together = [["company", "pricelist"]]
#         verbose_name = _("Pricelist")
#         verbose_name_plural = _("Company List")


# class PricelistItem(models.Model):
#     pricelist = models.ForeignKey(Pricelist, on_delete=models.CASCADE, related_name="items")
#     product = models.ForeignKey("Product", on_delete=models.CASCADE)
#     price = models.DecimalField(max_digits=7, decimal_places=2)
#
#     def __str__(self):
#         return self.product.sku + " - " + self.pricelist.name
#
#     class Meta:
#         unique_together = [["pricelist", "product"]]


# class ClosedPurchaseGroup(models.Model):
#     uuid = models.CharField(primary_key=True, max_length=36)
#     name = models.CharField(max_length=200)
#     odoo_id = models.IntegerField()
#     company = models.ManyToManyField(
#         "customers.Company",
#         through="ClosedPurchaseGroupRel",
#         related_name="closed_purchase_groups_all",
#     )
#
#     def __str__(self):
#         return self.name
#
#     @property
#     def products(self):
#         return self.items.all().values_list("product", flat=True)


# class ClosedPurchaseGroupRel(models.Model):
#     company = models.ForeignKey("customers.Company", on_delete=models.CASCADE)
#     closed_purchase_group = models.ForeignKey(ClosedPurchaseGroup, on_delete=models.CASCADE)
#
#     def __str__(self):
#         try:
#             name = self.company.name + " - " + self.closed_purchase_group.name
#         except Exception as e:
#             name = ""
#         return name
#
#     class Meta:
#         unique_together = [["company", "closed_purchase_group"]]
#         verbose_name = _("Closed purchase group")
#         verbose_name_plural = _("Closed purchase group")


# class ClosedPurchaseGroupItem(models.Model):
#     closed_purchase_group = models.ForeignKey(
#         ClosedPurchaseGroup, on_delete=models.CASCADE, related_name="items"
#     )
#     product = models.ForeignKey("Product", on_delete=models.CASCADE)
#
#     def __str__(self):
#         return self.product.sku + " - " + self.closed_purchase_group.name
