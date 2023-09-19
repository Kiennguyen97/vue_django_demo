import datetime
import os
import uuid

from django.db import models


class NZRegion(models.Model):
    uuid = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=256)

    def __str__(self):
        return f"NZ Region - {self.name}"

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(NZRegion, self).save(*args, **kwargs)

    def get_all_items():
        object_list = NZRegion.objects.values("uuid", "name")
        return list(object_list)


###### StoreLocation ######
# class StoreLocationAccessManager(models.Manager):
#     def get_queryset(self):
#         queryset = super().get_queryset()
#         queryset = queryset.filter(active=True)
#         return queryset

class StoreLocation(models.Model):
    class Meta:
        ordering = [
            "name",
        ]

    uuid = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=256)
    street = models.CharField(max_length=256)
    suburb = models.CharField(max_length=256, blank=True, null=True)
    district = models.CharField(max_length=256)
    region = models.ForeignKey(
        NZRegion, on_delete=models.CASCADE, related_name="store_location_items"
    )
    zip_code = models.CharField(max_length=256, blank=True, null=True)
    phone_number = models.CharField(max_length=50)
    logo = models.FileField(upload_to="images/store_location/", blank=True, null=True)
    thank_link = models.CharField(max_length=256, blank=True, null=True)
    active = models.BooleanField(default=True)
    can_appear_checkout = models.BooleanField(default=False)

    #objects = StoreLocationAccessManager()

    def __str__(self):
        return f"Stock Location - {self.name}"

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(StoreLocation, self).save(*args, **kwargs)

    def get_store_location_by_region_id(region_id):
        if isinstance(region_id, list):
            region_ids = region_id
        else:
            region_ids = [region_id]

        store_lists = StoreLocation.objects.select_related("region").filter(
            region__uuid__in=region_ids,
            active=True
        )

        resellers = []
        return store_lists, resellers

    def get_all_store_location(can_appear_checkout=False):
        store_lists = StoreLocation.objects.select_related("region").filter(active=True)
        if can_appear_checkout:
            store_lists = store_lists.filter(can_appear_checkout=True)
        return store_lists.all(), []


    def get_customer_emails(self):
        return [x.email for x in self.customer_emails.all()]


class StoreLocationEmail(models.Model):
    class Meta:
        verbose_name = "Customer Email Address"
        verbose_name_plural = "Customer Email Addresses"

    store_location = models.ForeignKey(
        StoreLocation, on_delete=models.CASCADE, related_name="customer_emails"
    )
    email = models.EmailField(max_length=100)

    def __str__(self):
        return f"Customer Email {self.email} - {self.store_location.name}"
