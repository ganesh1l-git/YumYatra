from django.core.management.base import BaseCommand
from django.core.management import call_command
from delivery.models import Restaurant, Item, Coupon, Customer

class Command(BaseCommand):
    help = 'Seeds initial restaurants, menu items, coupons, and sample users into the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Checking database status..."))
        try:
            call_command('loaddata', 'initial_data')
            self.stdout.write(self.style.SUCCESS(
                f"Successfully seeded database! Total restaurants: {Restaurant.objects.count()}, "
                f"items: {Item.objects.count()}, coupons: {Coupon.objects.count()}, customers: {Customer.objects.count()}"
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error seeding database: {e}"))
