import uuid

from django.db import models


# Create your models here.
class Contact(models.Model):
    uuid = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=50, blank=True)
    email_address = models.EmailField(max_length=255, unique=False)
    create_date = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    message = models.TextField(max_length=255, blank=False)
    order_number = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name + " - " + self.email_address

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(Contact, self).save(*args, **kwargs)

    class Meta:
        ordering = ["-create_date"]



class Universal(models.Model):
    class TOWEL_RAIL(models.TextChoices):
    #     ST65, ST75, ST78, SL125, SL115, C100, SL130
        DEFAULT = ("", "Select towel rail type") # default
        ST65 = ("ST65", "ST65")
        ST75 = ("ST75", "ST75")
        ST78 = ("ST78", "ST78")
        SL125 = ("SL125", "SL125")
        SL115 = ("SL115", "SL115")
        C100 = ("C100", "C100")
        SL130 = ("SL130", "SL130")

    uuid = models.CharField(primary_key=True, max_length=36, default="")
    towel_rail = models.CharField(max_length=50, blank=True, choices=TOWEL_RAIL.choices)
    name = models.CharField(max_length=50, blank=True)
    company_name = models.CharField(max_length=100, blank=True)
    shipping_address = models.CharField(max_length=255, blank=True)
    email_address = models.EmailField(max_length=255, unique=False)
    create_date = models.DateTimeField(auto_now_add=True)
    phone_number = models.CharField(max_length=15, blank=True)
    proof_purchase = models.FileField(upload_to="proof_purchase", blank=True)

    def __str__(self):
        return self.name + " - " + self.email_address

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(Universal, self).save(*args, **kwargs)

    class Meta:
        ordering = ["-create_date"]


class Subscribe(models.Model):
    uuid = models.CharField(primary_key=True, max_length=36)
    email_address = models.EmailField(max_length=255)
    create_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Subscribe - {self.email_address}"

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(Subscribe, self).save(*args, **kwargs)
