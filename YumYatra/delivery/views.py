from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
import razorpay

from .models import Customer, Item, Cart, Restaurant, CartItem, Order, OrderItem, Coupon, Review, Favorite


# ---------------------------------------------------------------------------
# Public & Landing Pages
# ---------------------------------------------------------------------------
def say_hello(request):
    """Landing page with featured restaurant highlights."""
    featured_restaurants = Restaurant.objects.all()[:6]
    return render(request, 'index.html', {'featured_restaurants': featured_restaurants})


# ---------------------------------------------------------------------------
# Authentication: Sign In, Sign Up, Log Out
# ---------------------------------------------------------------------------
def open_signin(request):
    """Renders the signin page with optional pre-selected role."""
    active_role = request.GET.get('role', 'user')
    return render(request, 'signin.html', {'active_role': active_role})


def open_signup(request):
    """Renders the signup page."""
    active_role = request.GET.get('role', 'user')
    return render(request, 'signup.html', {'active_role': active_role})


def signup(request):
    """Registers a new Customer or Restaurant Partner."""
    if request.method == 'POST':
        role = request.POST.get('role', 'user').strip().lower()
        
        if role == 'restaurant':
            name = request.POST.get('name', '').strip()
            password = request.POST.get('password', '').strip()
            cuisine = request.POST.get('cuisine', '').strip()
            picture = request.POST.get('picture', '').strip()
            rating_val = request.POST.get('rating', '4.0')
            
            if not name or not cuisine:
                messages.error(request, 'Restaurant name and cuisine are required.')
                return render(request, 'signup.html', {'active_role': 'restaurant'})
            
            if Restaurant.objects.filter(name__iexact=name).exists():
                messages.error(request, f'A restaurant named "{name}" already exists. Please choose a different name.')
                return render(request, 'signup.html', {'active_role': 'restaurant'})
            
            try:
                rating = float(rating_val)
            except ValueError:
                rating = 4.0

            # Default password format: <RestaurantName>123 or restaurent123
            default_pwd = password if password else f"{name}123"

            Restaurant.objects.create(
                name=name,
                password=default_pwd,
                picture=picture or 'https://images.venuebookingz.com/22886-1777034898-wm-triple_eight_bar_(9).jpg',
                cuisine=cuisine,
                rating=rating,
            )
            messages.success(request, f'Restaurant "{name}" registered! Password set to {default_pwd}. Please sign in.')
            return redirect('/open_signin/?role=restaurant')

        else:
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip()

            if not username or not password or not email:
                messages.error(request, 'Username, email, and password are required.')
                return render(request, 'signup.html', {'active_role': 'user'})

            if Customer.objects.filter(username__iexact=username).exists():
                messages.error(request, f'Username "{username}" is already taken. Please choose another.')
                return render(request, 'signup.html', {'active_role': 'user'})

            Customer.objects.create(
                username=username,
                password=password,
                email=email,
                phone=phone,
                address=address
            )
            messages.success(request, 'Account created successfully! Please sign in.')
            return redirect('/open_signin/?role=user')

    return render(request, 'signup.html', {'active_role': 'user'})


def signin(request):
    """
    Role-based authentication:
      - Admin: username='admin', password='admin123'
      - Restaurant: username matches restaurant.name, password matches restaurant.password or <name>123 / restaurent123
      - User: username and password match Customer model
    """
    if request.method == 'POST':
        role = request.POST.get('role', 'user').strip().lower()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        # 1. ADMIN AUTHENTICATION
        if role == 'admin':
            if username == 'admin' and password == 'admin123':
                request.session['is_admin'] = True
                request.session['is_restaurant'] = False
                request.session['is_customer'] = False
                request.session['role'] = 'admin'
                request.session['username'] = 'admin'
                messages.success(request, 'Logged in as Admin successfully!')
                return redirect('admin_home')
            else:
                messages.error(request, 'Invalid Admin credentials! Use username: admin and password: admin123')
                return render(request, 'signin.html', {
                    'active_role': 'admin',
                    'entered_username': username
                })

        # 2. RESTAURANT AUTHENTICATION
        elif role == 'restaurant':
            restaurant = Restaurant.objects.filter(name__iexact=username).first()
            if restaurant:
                clean_name = restaurant.name.lower().replace(' ', '')
                valid_passwords = [
                    restaurant.password,
                    f"{restaurant.name}123",
                    f"{restaurant.name.lower()}123",
                    f"{clean_name}123",
                    'restaurant123',
                    'restaurent123',
                    'rest123',
                ]
                if password in valid_passwords or password.lower() in [p.lower() for p in valid_passwords]:
                    request.session['is_admin'] = False
                    request.session['is_restaurant'] = True
                    request.session['is_customer'] = False
                    request.session['role'] = 'restaurant'
                    request.session['restaurant_id'] = restaurant.id
                    request.session['username'] = restaurant.name
                    messages.success(request, f'Welcome back, {restaurant.name}!')
                    return redirect('restaurant_home', restaurant_id=restaurant.id)

            messages.error(request, f'Invalid credentials for restaurant "{username}". Password is restaurant name + 123 (or restaurent123).')
            return render(request, 'signin.html', {
                'active_role': 'restaurant',
                'entered_username': username
            })

        # 3. CUSTOMER / USER AUTHENTICATION
        else:
            customer = Customer.objects.filter(username__iexact=username, password=password).first()
            if customer:
                request.session['is_admin'] = False
                request.session['is_restaurant'] = False
                request.session['is_customer'] = True
                request.session['role'] = 'user'
                request.session['username'] = customer.username
                request.session['customer_id'] = customer.id
                messages.success(request, f'Welcome back, {customer.username}!')
                return redirect('customer_home', username=customer.username)
            else:
                messages.error(request, 'Invalid customer username or password.')
                return render(request, 'signin.html', {
                    'active_role': 'user',
                    'entered_username': username
                })

    return render(request, 'signin.html', {'active_role': 'user'})


def logout_view(request):
    """Flushes session and redirects safely to the landing page."""
    request.session.flush()
    messages.info(request, 'You have been successfully logged out.')
    return redirect('say_hello')


# ---------------------------------------------------------------------------
# Customer Experience & Shopping Views
# ---------------------------------------------------------------------------
def customer_home(request, username=None):
    """Main customer discovery view with search, cuisine pills, and favorites filter."""
    user = username or request.session.get('username', 'Guest')
    customer = Customer.objects.filter(username=user).first()
    
    query = request.GET.get('q', '').strip()
    cuisine_filter = request.GET.get('cuisine', '').strip()
    filter_mode = request.GET.get('filter', '').strip()

    restaurants = Restaurant.objects.all()
    if query:
        restaurants = restaurants.filter(name__icontains=query)
    if cuisine_filter and cuisine_filter != 'all':
        restaurants = restaurants.filter(cuisine__icontains=cuisine_filter)

    # Favorite restaurant IDs for the current user
    user_fav_ids = set()
    if customer:
        user_fav_ids = set(Favorite.objects.filter(customer=customer).values_list('restaurant_id', flat=True))

    if filter_mode == 'favorites':
        restaurants = restaurants.filter(id__in=user_fav_ids)

    # Cart item count for current user
    cart_count = 0
    if customer:
        cart = Cart.objects.filter(customer=customer).first()
        if cart:
            cart_count = sum(ci.quantity for ci in cart.cart_items.all())

    # Get list of unique cuisines for filter pills
    all_cuisines = sorted(list(set([r.cuisine.strip() for r in Restaurant.objects.all() if r.cuisine])))

    context = {
        "restaurantList": restaurants,
        "username": user,
        "cart_count": cart_count,
        "query": query,
        "current_cuisine": cuisine_filter,
        "filter_mode": filter_mode,
        "all_cuisines": all_cuisines,
        "user_fav_ids": user_fav_ids,
    }
    return render(request, 'customer_home.html', context)


def view_menu(request, restaurant_id, username):
    """View a restaurant's menu with veg/non-veg filter, reviews, and favorite toggle."""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    filter_type = request.GET.get('filter', 'all')
    search_item = request.GET.get('search', '').strip()

    items = restaurant.items.all()
    if filter_type == 'veg':
        items = items.filter(vegetarian=True)
    elif filter_type == 'nonveg':
        items = items.filter(vegetarian=False)
    
    if search_item:
        items = items.filter(name__icontains=search_item)

    # Calculate cart count, favorite status, and review eligibility
    customer = Customer.objects.filter(username=username).first()
    cart_count = 0
    is_favorited = False
    can_review = False
    has_pending_order = False
    user_review = None

    if customer:
        cart = Cart.objects.filter(customer=customer).first()
        if cart:
            cart_count = sum(ci.quantity for ci in cart.cart_items.all())
        is_favorited = Favorite.objects.filter(customer=customer, restaurant=restaurant).exists()
        
        # Check if customer has at least one delivered order from this restaurant
        can_review = OrderItem.objects.filter(
            restaurant=restaurant,
            order__customer=customer,
            order__status='Delivered'
        ).exists()

        if not can_review:
            has_pending_order = OrderItem.objects.filter(
                restaurant=restaurant,
                order__customer=customer
            ).exclude(order__status__in=['Delivered', 'Cancelled']).exists()

        user_review = Review.objects.filter(restaurant=restaurant, customer=customer).first()

    # Customer Reviews
    reviews = restaurant.reviews.all().order_by('-created_at')

    context = {
        "itemList": items,
        "restaurant": restaurant,
        "username": username,
        "current_filter": filter_type,
        "search_item": search_item,
        "cart_count": cart_count,
        "reviews": reviews,
        "is_favorited": is_favorited,
        "can_review": can_review,
        "has_pending_order": has_pending_order,
        "user_review": user_review,
    }
    return render(request, 'customer_menu.html', context)


def toggle_favorite(request, restaurant_id, username):
    """Toggle a restaurant in the customer's favorite list."""
    customer = get_object_or_404(Customer, username=username)
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    fav = Favorite.objects.filter(customer=customer, restaurant=restaurant).first()
    if fav:
        fav.delete()
        messages.info(request, f'Removed "{restaurant.name}" from your favorites.')
    else:
        Favorite.objects.create(customer=customer, restaurant=restaurant)
        messages.success(request, f'Added "{restaurant.name}" to your favorites! ❤️')

    referer = request.META.get('HTTP_REFERER')
    if referer and 'customer_home' in referer:
        return redirect('customer_home', username=username)
    return redirect('view_menu', restaurant_id=restaurant.id, username=username)


def add_review(request, restaurant_id, username):
    """Submit a customer review only if the customer has a delivered order from this restaurant."""
    if request.method == 'POST':
        customer = get_object_or_404(Customer, username=username)
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        # Verification check: Customer MUST have a delivered order from this restaurant
        has_delivered_order = OrderItem.objects.filter(
            restaurant=restaurant,
            order__customer=customer,
            order__status='Delivered'
        ).exists()

        if not has_delivered_order:
            messages.error(request, f'🔒 Only customers with a delivered order from {restaurant.name} can leave a review.')
            return redirect('view_menu', restaurant_id=restaurant_id, username=username)
        
        try:
            rating = int(request.POST.get('rating', 5))
            if rating < 1 or rating > 5:
                rating = 5
        except (ValueError, TypeError):
            rating = 5

        comment = request.POST.get('comment', '').strip()
        if not comment:
            messages.error(request, 'Please write a brief comment with your review.')
            return redirect('view_menu', restaurant_id=restaurant_id, username=username)

        Review.objects.update_or_create(
            restaurant=restaurant,
            customer=customer,
            defaults={'rating': rating, 'comment': comment}
        )

        # Recalculate average restaurant rating
        all_ratings = [r.rating for r in restaurant.reviews.all()]
        if all_ratings:
            restaurant.rating = round(sum(all_ratings) / len(all_ratings), 1)
            restaurant.save()

        messages.success(request, f'Thank you! Your verified review for {restaurant.name} ({rating}★) has been published.')

    return redirect('view_menu', restaurant_id=restaurant_id, username=username)


def add_to_cart(request, item_id, username):
    """Add item with quantity to customer cart."""
    item = get_object_or_404(Item, id=item_id)
    customer = get_object_or_404(Customer, username=username)
    cart, _ = Cart.objects.get_or_create(customer=customer)

    try:
        quantity = int(request.GET.get('quantity', 1))
        if quantity < 1:
            quantity = 1
    except (ValueError, TypeError):
        quantity = 1

    cart_item, ci_created = CartItem.objects.get_or_create(cart=cart, item=item)
    if not ci_created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()

    messages.success(request, f'Added {quantity}x "{item.name}" to cart!')
    return redirect('view_menu', restaurant_id=item.restaurant.id, username=username)


def remove_from_cart(request, item_id, username):
    """Remove item from customer cart."""
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    if cart:
        CartItem.objects.filter(cart=cart, item_id=item_id).delete()
        messages.info(request, 'Item removed from your cart.')
    return redirect('show_cart', username=username)


def apply_coupon(request, username):
    """Apply promo code coupon to current session cart."""
    if request.method == 'POST':
        code = request.POST.get('coupon_code', '').strip().upper()
        customer = get_object_or_404(Customer, username=username)
        cart = Cart.objects.filter(customer=customer).first()

        if not cart or not cart.cart_items.exists():
            messages.error(request, 'Your cart is empty!')
            return redirect('show_cart', username=username)

        coupon = Coupon.objects.filter(code__iexact=code, is_active=True).first()
        if not coupon:
            messages.error(request, f'Coupon code "{code}" is invalid or expired.')
            return redirect('show_cart', username=username)

        subtotal = cart.subtotal()
        if subtotal < coupon.min_order_value:
            messages.error(request, f'Coupon "{code}" requires a minimum order value of ₹{coupon.min_order_value}. Add ₹{round(coupon.min_order_value - subtotal, 2)} more.')
            return redirect('show_cart', username=username)

        discount = coupon.calculate_discount(subtotal, cart.delivery_fee())
        request.session['coupon_code'] = coupon.code
        messages.success(request, f'Coupon "{coupon.code}" applied! You saved ₹{discount}.')

    return redirect('show_cart', username=username)


def remove_coupon(request, username):
    """Remove applied coupon from session."""
    request.session.pop('coupon_code', None)
    messages.info(request, 'Coupon removed.')
    return redirect('show_cart', username=username)


def show_cart(request, username):
    """Review customer cart with complete fee breakdown and coupons."""
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    cart_items = cart.cart_items.all() if cart else []
    
    available_coupons = Coupon.objects.filter(is_active=True)
    applied_coupon_code = request.session.get('coupon_code')
    applied_coupon = None
    discount_amount = 0.0

    context = {
        "cart": cart,
        "cart_items": cart_items,
        "username": username,
        "available_coupons": available_coupons,
        "applied_coupon_code": applied_coupon_code,
    }

    if cart and cart_items.exists():
        subtotal = cart.subtotal()
        delivery_fee = cart.delivery_fee()

        if applied_coupon_code:
            applied_coupon = Coupon.objects.filter(code__iexact=applied_coupon_code, is_active=True).first()
            if applied_coupon and subtotal >= applied_coupon.min_order_value:
                discount_amount = applied_coupon.calculate_discount(subtotal, delivery_fee)
            else:
                # Invalidate if conditions no longer met
                request.session.pop('coupon_code', None)
                applied_coupon_code = None

        grand_total = max(0.0, round(cart.grand_total() - discount_amount, 2))

        context.update({
            "subtotal": subtotal,
            "gst": cart.gst(),
            "handling_fee": cart.handling_fee(),
            "delivery_fee": delivery_fee,
            "service_fee": cart.service_fee(),
            "discount_amount": discount_amount,
            "applied_coupon": applied_coupon,
            "grand_total": grand_total,
            "free_delivery_diff": round(500.0 - subtotal, 2) if subtotal < 500 else 0.0,
        })
    else:
        context.update({
            "subtotal": 0.0,
            "gst": 0.0,
            "handling_fee": 0.0,
            "delivery_fee": 0.0,
            "service_fee": 0.0,
            "discount_amount": 0.0,
            "grand_total": 0.0,
            "free_delivery_diff": 500.0,
        })
    return render(request, 'cart.html', context)


def checkout(request, username):
    """Payment checkout with Razorpay or instant direct checkout fallback."""
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    cart_items = cart.cart_items.all() if cart else []
    
    if not cart or not cart_items.exists():
        return render(request, 'checkout.html', {
            'error': 'Your cart is empty! Please add some delicious items first.',
            'username': username
        })

    subtotal = cart.subtotal()
    delivery_fee = cart.delivery_fee()
    applied_coupon_code = request.session.get('coupon_code')
    discount_amount = 0.0
    applied_coupon = None

    if applied_coupon_code:
        applied_coupon = Coupon.objects.filter(code__iexact=applied_coupon_code, is_active=True).first()
        if applied_coupon and subtotal >= applied_coupon.min_order_value:
            discount_amount = applied_coupon.calculate_discount(subtotal, delivery_fee)

    grand_total = max(0.0, round(cart.grand_total() - discount_amount, 2))

    context = {
        'username': username,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'gst': cart.gst(),
        'handling_fee': cart.handling_fee(),
        'delivery_fee': delivery_fee,
        'service_fee': cart.service_fee(),
        'discount_amount': discount_amount,
        'applied_coupon': applied_coupon,
        'grand_total': grand_total,
    }

    # Attempt Razorpay Order Creation
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        client.session.trust_env = False
        order_data = {
            'amount': int(grand_total * 100),
            'currency': 'INR',
            'payment_capture': '1',
        }
        order = client.order.create(data=order_data)
        context.update({
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'order_id': order['id'],
            'amount_paise': order_data['amount'],
            'razorpay_ready': True,
        })
    except Exception:
        context.update({
            'razorpay_ready': False,
            'gateway_warning': 'Razorpay gateway is in offline mode. You can complete your order instantly using Direct / Cash on Delivery checkout below.',
        })

    return render(request, 'checkout.html', context)


def direct_order(request, username):
    """Direct/COD order placement with coupon discount and live tracking transition."""
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    cart_items = list(cart.cart_items.all()) if cart else []

    if not cart_items:
        return redirect('my_orders', username=username)

    subtotal = cart.subtotal()
    delivery_fee = cart.delivery_fee()
    applied_coupon_code = request.session.get('coupon_code')
    discount_amount = 0.0

    if applied_coupon_code:
        coupon = Coupon.objects.filter(code__iexact=applied_coupon_code, is_active=True).first()
        if coupon and subtotal >= coupon.min_order_value:
            discount_amount = coupon.calculate_discount(subtotal, delivery_fee)

    grand_total = max(0.0, round(cart.grand_total() - discount_amount, 2))

    order = Order.objects.create(
        customer=customer,
        subtotal=subtotal,
        gst=cart.gst(),
        handling_fee=cart.handling_fee(),
        delivery_fee=delivery_fee,
        service_fee=cart.service_fee(),
        discount_amount=discount_amount,
        coupon_code=applied_coupon_code,
        grand_total=grand_total,
        status='Placed',
        estimated_delivery_minutes=30
    )

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

    # Empty cart & clear coupon session
    cart.cart_items.all().delete()
    request.session.pop('coupon_code', None)

    return render(request, 'orders.html', {
        'username': username,
        'customer': customer,
        'order_items': order_items,
        'order': order,
    })


def orders(request, username):
    """Order confirmation and receipt screen."""
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    cart_items = list(cart.cart_items.all()) if cart else []
    
    if not cart_items:
        latest_order = Order.objects.filter(customer=customer).order_by('-created_at').first()
        order_items = latest_order.order_items.all() if latest_order else []
        return render(request, 'orders.html', {
            'username': username,
            'customer': customer,
            'order_items': order_items,
            'order': latest_order,
        })

    subtotal = cart.subtotal()
    delivery_fee = cart.delivery_fee()
    applied_coupon_code = request.session.get('coupon_code')
    discount_amount = 0.0

    if applied_coupon_code:
        coupon = Coupon.objects.filter(code__iexact=applied_coupon_code, is_active=True).first()
        if coupon and subtotal >= coupon.min_order_value:
            discount_amount = coupon.calculate_discount(subtotal, delivery_fee)

    grand_total = max(0.0, round(cart.grand_total() - discount_amount, 2))

    order = Order.objects.create(
        customer=customer,
        subtotal=subtotal,
        gst=cart.gst(),
        handling_fee=cart.handling_fee(),
        delivery_fee=delivery_fee,
        service_fee=cart.service_fee(),
        discount_amount=discount_amount,
        coupon_code=applied_coupon_code,
        grand_total=grand_total,
        status='Placed',
        estimated_delivery_minutes=30
    )

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

    cart.cart_items.all().delete()
    request.session.pop('coupon_code', None)

    return render(request, 'orders.html', {
        'username': username,
        'customer': customer,
        'order_items': order_items,
        'order': order,
    })


# ---------------------------------------------------------------------------
# Live Order Tracking & Order History Views
# ---------------------------------------------------------------------------
def track_order(request, order_id, username):
    """Live interactive order tracking page with animated status pipeline and ETA."""
    customer = get_object_or_404(Customer, username=username)
    order = get_object_or_404(Order, id=order_id, customer=customer)
    order_items = order.order_items.all()

    # Step index mapping
    status_order = ['Placed', 'Confirmed', 'Preparing', 'Out for Delivery', 'Delivered']
    try:
        current_step = status_order.index(order.status)
    except ValueError:
        current_step = 0

    progress_percent = int((current_step / (len(status_order) - 1)) * 100)

    context = {
        'order': order,
        'order_items': order_items,
        'username': username,
        'customer': customer,
        'current_step': current_step,
        'progress_percent': progress_percent,
        'status_order': status_order,
    }
    return render(request, 'track_order.html', context)


def my_orders(request, username):
    """Customer portal to view past order history, invoices, and reorder."""
    customer = get_object_or_404(Customer, username=username)
    orders_list = customer.orders.all().order_by('-created_at')

    context = {
        'username': username,
        'customer': customer,
        'orders': orders_list,
    }
    return render(request, 'my_orders.html', context)


def reorder(request, order_id, username):
    """1-Click Reorder: populates cart with items from a past order."""
    customer = get_object_or_404(Customer, username=username)
    past_order = get_object_or_404(Order, id=order_id, customer=customer)
    cart, _ = Cart.objects.get_or_create(customer=customer)

    # Clear current cart
    cart.cart_items.all().delete()

    # Repopulate cart with past items
    count = 0
    for oi in past_order.order_items.all():
        CartItem.objects.create(
            cart=cart,
            item=oi.item,
            quantity=oi.quantity
        )
        count += oi.quantity

    messages.success(request, f'Reordered {count} items from Order #{past_order.id}! Added straight to your cart.')
    return redirect('show_cart', username=username)


def update_order_status(request, order_id):
    """Allows restaurant partner or admin to update the order progression status."""
    if not request.session.get('is_restaurant') and not request.session.get('is_admin'):
        return redirect('open_signin')

    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status') or request.GET.get('status')

    valid_statuses = ['Placed', 'Confirmed', 'Preparing', 'Out for Delivery', 'Delivered', 'Cancelled']
    if new_status in valid_statuses:
        order.status = new_status
        order.save()
        messages.success(request, f'Order #{order.id} status updated to "{new_status}"!')

    # Redirect back to caller
    if request.session.get('is_restaurant'):
        rest_id = request.session.get('restaurant_id')
        return redirect('restaurant_home', restaurant_id=rest_id)
    return redirect('admin_home')


# ---------------------------------------------------------------------------
# Restaurant Partner Experience Views
# ---------------------------------------------------------------------------
def restaurant_home(request, restaurant_id):
    """Dedicated portal for restaurant partner to manage menu and view sales."""
    if not request.session.get('is_restaurant') and not request.session.get('is_admin'):
        return redirect('open_signin')

    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    today = timezone.localtime(timezone.now()).date()

    # Restaurant-specific orders and revenue today
    today_order_items = OrderItem.objects.filter(restaurant=restaurant, order__created_at__date=today).order_by('-order__created_at')
    order_ids = set(oi.order.id for oi in today_order_items)
    order_count = len(order_ids)
    sales_value = sum(oi.price * oi.quantity for oi in today_order_items)
    
    # Unique orders for status management
    restaurant_orders = Order.objects.filter(order_items__restaurant=restaurant).distinct().order_by('-created_at')[:20]

    # Top selling items
    items = restaurant.items.all()

    context = {
        'restaurant': restaurant,
        'items': items,
        'order_count': order_count,
        'sales_value': round(sales_value, 2),
        'today_order_items': today_order_items,
        'restaurant_orders': restaurant_orders,
    }
    return render(request, 'restaurant_home.html', context)


def delete_menu_item(request, item_id):
    """Deletes a menu item and returns to the menu editor."""
    item = get_object_or_404(Item, id=item_id)
    rest_id = item.restaurant.id
    item_name = item.name
    item.delete()
    messages.success(request, f'Item "{item_name}" deleted successfully.')
    
    if request.session.get('is_restaurant'):
        return redirect('restaurant_home', restaurant_id=rest_id)
    return redirect('open_update_menu', restaurant_id=rest_id)


# ---------------------------------------------------------------------------
# Admin Portal & Management Views
# ---------------------------------------------------------------------------
def admin_home(request):
    """Admin Dashboard with Sales Analytics and Platform Controls."""
    if not request.session.get('is_admin', False):
        return redirect('open_signin')

    today = timezone.localtime(timezone.now()).date()
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
        # Profit: 10% commission + ₹10 flat service fee per unique order
        data['profit'] = round((data['sales_value'] * 0.10) + (data['order_count'] * 10.0), 2)
        data['sales_value'] = round(data['sales_value'], 2)
        
        total_orders_today += data['order_count']
        total_sales_today += data['sales_value']
        total_profit_today += data['profit']
        restaurant_reports.append(data)

    restaurant_reports.sort(key=lambda x: x['sales_value'], reverse=True)
    today_orders = Order.objects.filter(created_at__date=today).order_by('-created_at')

    context = {
        'restaurant_reports': restaurant_reports,
        'today_orders': today_orders,
        'total_orders_today': total_orders_today,
        'total_sales_today': round(total_sales_today, 2),
        'total_profit_today': round(total_profit_today, 2),
    }
    return render(request, 'admin_home.html', context)


def open_add_restaurant(request):
    """Render Add Restaurant page (Admin only)."""
    if not request.session.get('is_admin', False):
        return redirect('open_signin')
    return render(request, 'add_restaurant.html')


def add_restaurant(request):
    """Process Add Restaurant submission (Admin only)."""
    if not request.session.get('is_admin', False):
        return redirect('open_signin')
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        password = request.POST.get('password', '').strip()
        picture = request.POST.get('picture', '').strip()
        cuisine = request.POST.get('cuisine', '').strip()
        rating = float(request.POST.get('rating') or 4.0)
        
        if not name or not cuisine:
            messages.error(request, 'Restaurant name and cuisine are required!')
            return redirect('open_add_restaurant')
            
        if Restaurant.objects.filter(name__iexact=name).exists():
            messages.error(request, f'A restaurant named "{name}" already exists!')
            return redirect('open_add_restaurant')

        default_pwd = password if password else f"{name}123"

        Restaurant.objects.create(
            name=name,
            password=default_pwd,
            picture=picture or 'https://images.venuebookingz.com/22886-1777034898-wm-triple_eight_bar_(9).jpg',
            cuisine=cuisine,
            rating=rating,
        )
        messages.success(request, f'Restaurant "{name}" onboarded successfully!')
        return redirect('open_show_restaurant')

    return redirect('open_add_restaurant')


def open_show_restaurant(request):
    """View all registered restaurants."""
    if not request.session.get('is_admin', False):
        return redirect('open_signin')
    restaurant_list = Restaurant.objects.all()
    return render(request, 'show_restaurant.html', {'restaurantList': restaurant_list})


def open_update_restaurant(request, restaurant_id):
    """Render Edit Restaurant page."""
    if not request.session.get('is_admin', False):
        return redirect('open_signin')
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    return render(request, 'update_restaurant.html', {"restaurant": restaurant})


def update_restaurant(request, restaurant_id):
    """Process Update Restaurant submission."""
    if not request.session.get('is_admin', False):
        return redirect('open_signin')

    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        picture = request.POST.get("picture", "").strip() or restaurant.picture
        cuisine = request.POST.get("cuisine", "").strip()
        rating = float(request.POST.get("rating") or restaurant.rating)
        password = request.POST.get("password", "").strip()
        
        if name:
            restaurant.name = name
        restaurant.picture = picture
        if cuisine:
            restaurant.cuisine = cuisine
        restaurant.rating = rating
        if password:
            restaurant.password = password
        restaurant.save()
        messages.success(request, f'Restaurant "{restaurant.name}" updated successfully!')
        
    return redirect('open_show_restaurant')


def delete_restaurant(request, restaurant_id):
    """Delete a restaurant and its related items."""
    if not request.session.get('is_admin', False):
        return redirect('open_signin')
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    name = restaurant.name
    restaurant.delete()
    messages.success(request, f'Restaurant "{name}" deleted.')
    return redirect('open_show_restaurant')


def open_update_menu(request, restaurant_id):
    """Manage menu items for a specific restaurant."""
    if not request.session.get('is_admin', False) and not request.session.get('is_restaurant', False):
        return redirect('open_signin')
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    items = restaurant.items.all()
    return render(request, 'update_menu.html', {"itemList": items, "restaurant": restaurant})
    

def update_menu(request, restaurant_id):
    """Add a new dish to a restaurant's menu."""
    if not request.session.get('is_admin', False) and not request.session.get('is_restaurant', False):
        return redirect('open_signin')
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        price = float(request.POST.get('price') or 0)
        vegetarian = request.POST.get('vegetarian') == 'on'
        picture = request.POST.get('picture', '').strip()
        
        if not name or price <= 0:
            messages.error(request, 'Dish name and a valid price are required.')
            return redirect('open_update_menu', restaurant_id=restaurant.id)

        if Item.objects.filter(restaurant=restaurant, name__iexact=name).exists():
            messages.error(request, f'Dish "{name}" is already in this restaurant menu!')
            return redirect('open_update_menu', restaurant_id=restaurant.id)

        Item.objects.create(
            restaurant=restaurant,
            name=name,
            description=description,
            price=price,
            vegetarian=vegetarian,
            picture=picture or 'https://www.indiafilings.com/learn/wp-content/uploads/2024/08/How-to-Start-Food-Business.jpg',
        )
        messages.success(request, f'Dish "{name}" added to menu successfully!')

    return redirect('open_update_menu', restaurant_id=restaurant.id)
