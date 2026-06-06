from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
import razorpay

from .models import Customer, Item, Cart, Restaurant, CartItem, Order, OrderItem

# Create your views here.
def say_hello(request):
    #return HttpResponse("Hello from Delivery App")
    return render(request, 'index.html')

def open_signup(request):
    return render(request, 'signup.html')

def open_signin(request):
    return render(request, 'signin.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        try:
            Customer.objects.get(username=username)
            return HttpResponse("Duplicate username!")
        except:
            Customer.objects.create(
                username = username,
                password=password,
                email=email,
                phone=phone,
                address=address
            )
    return render(request, 'signin.html')

def signin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            customer = Customer.objects.get(username=username, password=password)
            request.session['username'] = username
            if username == 'admin':
                request.session['is_admin'] = True
                return redirect('admin_home')
            else:
                restaurantList = Restaurant.objects.all()
            return render(request, 'customer_home.html', {"restaurantList" : restaurantList, "username" : username})
        except Customer.DoesNotExist:
            return render(request, 'fail.html')
        
def open_add_restaurant(request):
    if not request.session.get('is_admin', False):
        return redirect('signin')
    return render(request, 'add_restaurant.html')

def add_restaurant(request):
    if not request.session.get('is_admin', False):
        return redirect('signin')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture')
        cuisine = request.POST.get('cuisine')
        rating = float(request.POST.get('rating') or 0)
        
        if not name or not cuisine:
            messages.error(request, 'Name and cuisine are required!')
            return redirect('open_add_restaurant')
            
        try:
            Restaurant.objects.get(name = name)
            messages.error(request, 'Duplicate restaurant name!')
            return redirect('open_add_restaurant')
        except:
            Restaurant.objects.create(
                name = name,
                picture = picture,
                cuisine = cuisine,
                rating = rating,
            )
            messages.success(request, f'Restaurant "{name}" added successfully!')
            return redirect('open_show_restaurant')
    return redirect('open_add_restaurant')

def open_show_restaurant(request):
    if not request.session.get('is_admin', False):
        return redirect('signin')
    restaurantList = Restaurant.objects.all()
    return render(request, 'show_restaurant.html', {'restaurantList': restaurantList})

def open_update_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    return render(request, 'update_restaurant.html', {"restaurant" : restaurant})

def update_restaurant(request, restaurant_id):
    if request.method == "POST":
        restaurant = Restaurant.objects.get(id=restaurant_id)
        name = request.POST.get("name")
        picture = request.POST.get("picture") or restaurant.picture
        cuisine = request.POST.get("cuisine")
        rating = float(request.POST.get("rating") or restaurant.rating)
        restaurant.name = name
        restaurant.picture = picture
        restaurant.cuisine = cuisine
        restaurant.rating = rating
        restaurant.save()
        
    restaurantList = Restaurant.objects.all()
    return redirect('open_show_restaurant')


def delete_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    restaurant.delete()

    restaurantList = Restaurant.objects.all()
    return render(request, 'show_restaurant.html',{"restaurantList" : restaurantList})

def open_update_menu(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    itemList = restaurant.items.all()
    #itemList = Item.objects.all()
    return render(request, 'update_menu.html',{"itemList" : itemList, "restaurant" : restaurant})
    
def update_menu(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        vegetarian = request.POST.get('vegetarian') == 'on'
        picture = request.POST.get('picture')
        
        try:
            Item.objects.get(name = name)
            return HttpResponse("Duplicate item!")
        except:
            Item.objects.create(
                restaurant = restaurant,
                name = name,
                description = description,
                price = price,
                vegetarian = vegetarian,
                picture = picture,
            )
    return redirect('admin_home')

def view_menu(request, restaurant_id, username):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    itemList = restaurant.items.all()
    #itemList = Item.objects.all()
    return render(request, 'customer_menu.html',{"itemList" : itemList,"restaurant" : restaurant, "username":username})

def add_to_cart(request, item_id, username):
    item = Item.objects.get(id=item_id)
    customer = Customer.objects.get(username=username)
    cart, created = Cart.objects.get_or_create(customer=customer)

    # Read quantity query parameter
    try:
        quantity = int(request.GET.get('quantity', 1))
        if quantity < 1:
            quantity = 1
    except ValueError:
        quantity = 1

    cart_item, ci_created = CartItem.objects.get_or_create(cart=cart, item=item)
    if not ci_created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()

    # Redirect back to the restaurant's menu
    return redirect('view_menu', restaurant_id=item.restaurant.id, username=username)

def remove_from_cart(request, item_id, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    if cart:
        CartItem.objects.filter(cart=cart, item_id=item_id).delete()
    return redirect('show_cart', username=username)

def show_cart(request, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    cart_items = cart.cart_items.all() if cart else []

    context = {
        "cart": cart,
        "cart_items": cart_items,
        "username": username,
    }
    if cart:
        subtotal = cart.subtotal()
        context.update({
            "subtotal": subtotal,
            "gst": cart.gst(),
            "handling_fee": cart.handling_fee(),
            "delivery_fee": cart.delivery_fee(),
            "service_fee": cart.service_fee(),
            "grand_total": cart.grand_total(),
            "free_delivery_diff": round(500.0 - subtotal, 2) if subtotal < 500 else 0.0,
        })
    else:
        context.update({
            "subtotal": 0.0,
            "gst": 0.0,
            "handling_fee": 0.0,
            "delivery_fee": 0.0,
            "service_fee": 0.0,
            "grand_total": 0.0,
            "free_delivery_diff": 500.0,
        })
    return render(request, 'cart.html', context)

def checkout(request, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    cart_items = cart.cart_items.all() if cart else []
    
    if not cart or not cart_items:
        return render(request, 'checkout.html', {
            'error': 'Your cart is empty!',
        })

    grand_total = cart.grand_total()
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    client.session.trust_env = False

    order_data = {
        'amount': int(grand_total * 100),  # Amount in paisa
        'currency': 'INR',
        'payment_capture': '1',  # Automatically capture payment
    }
    try:
        order = client.order.create(data=order_data)
    except Exception:
        return render(request, 'checkout.html', {
            'username': username,
            'cart_items': cart_items,
            'subtotal': cart.subtotal(),
            'gst': cart.gst(),
            'handling_fee': cart.handling_fee(),
            'delivery_fee': cart.delivery_fee(),
            'service_fee': cart.service_fee(),
            'grand_total': grand_total,
            'error': 'Payment service is currently unreachable. Please check your internet/proxy settings and try again.',
        })

    return render(request, 'checkout.html', {
        'username': username,
        'cart_items': cart_items,
        'subtotal': cart.subtotal(),
        'gst': cart.gst(),
        'handling_fee': cart.handling_fee(),
        'delivery_fee': cart.delivery_fee(),
        'service_fee': cart.service_fee(),
        'grand_total': grand_total,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'order_id': order['id'],  # Razorpay order ID
        'amount_paise': order_data['amount'],
    })

# Orders Page
def orders(request, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()

    # Fetch cart items before clearing
    cart_items = list(cart.cart_items.all()) if cart else []
    
    if not cart_items:
        # Show latest order if refresh happens or direct access
        latest_order = Order.objects.filter(customer=customer).order_by('-created_at').first()
        order_items = latest_order.order_items.all() if latest_order else []
        return render(request, 'orders.html', {
            'username': username,
            'customer': customer,
            'order_items': order_items,
            'order': latest_order,
        })

    # Create persisted order
    order = Order.objects.create(
        customer=customer,
        subtotal=cart.subtotal(),
        gst=cart.gst(),
        handling_fee=cart.handling_fee(),
        delivery_fee=cart.delivery_fee(),
        service_fee=cart.service_fee(),
        grand_total=cart.grand_total()
    )

    # Save order items
    order_items = []
    for ci in cart_items:
        oi = OrderItem.objects.create(
            order=order,
            item=ci.item,
            restaurant=ci.item.restaurant,
            price=ci.item.price,
            quantity=ci.quantity
        )
        order_items.append(oi)

    # Clear the cart items after order
    cart.cart_items.all().delete()

    return render(request, 'orders.html', {
        'username': username,
        'customer': customer,
        'order_items': order_items,
        'order': order,
    })

# Admin Dashboard with Sales Analytics
def admin_home(request):
    if not request.session.get('is_admin', False):
        return redirect('open_signin')

    today = timezone.localtime(timezone.now()).date()
    
    # Query order items from today
    today_order_items = OrderItem.objects.filter(order__created_at__date=today)
    
    restaurant_sales = {}
    for r in Restaurant.objects.all():
        restaurant_sales[r.id] = {
            'restaurant': r,
            'order_ids': set(),
            'order_count': 0,
            'sales_value': 0.0,
            'profit': 0.0,
        }

    for oi in today_order_items:
        r_id = oi.restaurant.id
        if r_id not in restaurant_sales:
            restaurant_sales[r_id] = {
                'restaurant': oi.restaurant,
                'order_ids': set(),
                'order_count': 0,
                'sales_value': 0.0,
                'profit': 0.0,
            }
        
        restaurant_sales[r_id]['order_ids'].add(oi.order.id)
        restaurant_sales[r_id]['sales_value'] += oi.price * oi.quantity

    total_orders_today = 0
    total_sales_today = 0.0
    total_profit_today = 0.0

    restaurant_reports = []
    for r_id, data in restaurant_sales.items():
        data['order_count'] = len(data['order_ids'])
        # Profit: 10% commission on sales value + ₹10 flat service fee per unique order today from that restaurant
        data['profit'] = round((data['sales_value'] * 0.10) + (data['order_count'] * 10.0), 2)
        data['sales_value'] = round(data['sales_value'], 2)
        
        total_orders_today += data['order_count']
        total_sales_today += data['sales_value']
        total_profit_today += data['profit']
        
        restaurant_reports.append(data)

    # Sort reports by sales value descending
    restaurant_reports.sort(key=lambda x: x['sales_value'], reverse=True)

    # Get all orders today for details
    today_orders = Order.objects.filter(created_at__date=today).order_by('-created_at')

    context = {
        'restaurant_reports': restaurant_reports,
        'today_orders': today_orders,
        'total_orders_today': total_orders_today,
        'total_sales_today': round(total_sales_today, 2),
        'total_profit_today': round(total_profit_today, 2),
    }
    return render(request, 'admin_home.html', context)
