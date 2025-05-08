from django.db import models
from django.contrib.auth.models import User
class Perfume(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_for_trade = models.BooleanField(default=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='perfume_images/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)

    CATEGORY_CHOICES = [
    ('men', 'Men'),
    ('women', 'Women'),
    ('unisex', 'Unisex'),
    ]
    
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='unisex')


    def __str__(self):
        return f"{self.name} by {self.brand}"

    @property
    def images(self):
        return self.perfumeimage_set.all()

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    perfume = models.ForeignKey(Perfume, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class PerfumeImage(models.Model):
    perfume = models.ForeignKey(Perfume, on_delete=models.CASCADE, related_name='additional_images')

    image = models.ImageField(upload_to='perfume_images/')

    def __str__(self):
        return f"Image for {self.perfume.name}"

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Cart of {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    perfume = models.ForeignKey(Perfume, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.perfume.name}"

ORDER_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('shipped', 'Shipped'),
    ('completed', 'Completed'),
]

class Order(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Order #{self.id} by {self.buyer.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    perfume = models.ForeignKey('Perfume', on_delete=models.CASCADE)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sold_items')
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

class Review(models.Model):
    perfume = models.ForeignKey(Perfume, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username} for {self.perfume.name}"

class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    perfume = models.ForeignKey('Perfume', on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'perfume')