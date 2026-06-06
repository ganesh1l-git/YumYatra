from django.db import models

# Create your models here.
class Customer(models.Model):
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    email = models.EmailField(max_length=50)
    phone = models.CharField(max_length=10)
    address = models.TextField(max_length=100)

class Restaurant(models.Model):
    name = models.CharField(max_length = 20)
    picture = models.URLField(max_length = 200, default='https://images.venuebookingz.com/22886-1777034898-wm-triple_eight_bar_(9).jpg')
    cuisine = models.CharField(max_length = 200)
    rating = models.FloatField()
    
class Item(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete = models.CASCADE, related_name = "items")
    name = models.CharField(max_length = 20)
    description = models.CharField(max_length = 200)
    price = models.FloatField()
    vegetarian = models.BooleanField(default=False)
    picture = models.URLField(max_length = 400, default='https://www.indiafilings.com/learn/wp-content/uploads/2024/08/How-to-Start-Food-Business.jpg')
    
class Cart(models.Model):
    customer = models.ForeignKey(Customer, on_delete = models.CASCADE, related_name = "cart")

    def total_price(self):
        return sum(ci.item.price * ci.quantity for ci in self.cart_items.all())

    def subtotal(self):
        return self.total_price()

    def gst(self):
        return round(self.subtotal() * 0.05, 2)

    def handling_fee(self):
        return 15.0 if self.cart_items.exists() else 0.0

    def delivery_fee(self):
        if not self.cart_items.exists():
            return 0.0
        return 0.0 if self.subtotal() >= 500 else 35.0

    def service_fee(self):
        return 10.0 if self.cart_items.exists() else 0.0

    def grand_total(self):
        if not self.cart_items.exists():
            return 0.0
        return round(self.subtotal() + self.gst() + self.handling_fee() + self.delivery_fee() + self.service_fee(), 2)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    created_at = models.DateTimeField(auto_now_add=True)
    subtotal = models.FloatField()
    gst = models.FloatField()
    handling_fee = models.FloatField()
    delivery_fee = models.FloatField()
    service_fee = models.FloatField()
    grand_total = models.FloatField()

    def __str__(self):
        return f"Order #{self.id} by {self.customer.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="order_items")
    price = models.FloatField()
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity} x {self.item.name} from {self.restaurant.name}"