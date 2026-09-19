from django.db import models
from datetime import timedelta

class ProductType:
    NORMAL = "NORMAL"
    SEASONAL = "SEASONAL"
    EXPIRABLE = "EXPIRABLE"

class Product(models.Model):
    name              = models.CharField(max_length=100)
    type              = models.CharField(max_length=20)
    available         = models.IntegerField(default=0)
    lead_time         = models.IntegerField(default=0)
    expiry_date       = models.DateField(null=True, blank=True)
    season_start_date = models.DateField(null=True, blank=True)
    season_end_date   = models.DateField(null=True, blank=True)

    class Meta:
        app_label = 'orders'

    def is_in_stock(self):
        return self.available > 0

    def is_in_season(self, today):
        """A season is open strictly between its start and end dates."""
        return self.season_start_date < today < self.season_end_date

    def is_expired(self, today):
        return self.expiry_date <= today

    def restock_date(self, today):
        """The day a replenishment ordered today would arrive."""
        return today + timedelta(days=self.lead_time)