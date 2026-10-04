from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
import razorpay

from .models import Customer, Item, Cart, Restaurant, CartItem, Order, OrderItem, Coupon, Review, Favorite, Address


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
    """Renders the customer signin page (or requested role if provided in URL)."""
    active_role = request.GET.get('role', 'user')
    return render(request, 'signin.html', {'active_role': active_role})


def partner_signin(request):
    """Renders ONLY the Restaurant Partner signin page."""
    return render(request, 'signin.html', {'active_role': 'restaurant'})


def admin_signin(request):
    """Renders ONLY the Admin Portal signin page."""
    return render(request, 'signin.html', {'active_role': 'admin'})


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

            if username.lower() in ['admin', 'guest', 'root', 'system']:
                messages.error(request, f'Username "{username}" is reserved. Please choose another.')
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
# ---------------------------------------------------------------------------
# Cart Helper & Management Utilities
# ---------------------------------------------------------------------------
def get_customer_cart(customer):
    """Guarantees a single canonical Cart for the customer and cleanly merges any duplicates."""
    if not customer:
        return None
    carts = Cart.objects.filter(customer=customer).order_by('id')
    if not carts.exists():
        return Cart.objects.create(customer=customer)
    main_cart = carts.first()
    if carts.count() > 1:
        for extra_cart in carts[1:]:
            for ci in extra_cart.cart_items.all():
                existing_ci = main_cart.cart_items.filter(item=ci.item).first()
                if existing_ci:
                    existing_ci.quantity += ci.quantity
                    existing_ci.save()
                else:
                    ci.cart = main_cart
                    ci.save()
            extra_cart.delete()
    return main_cart


# ---------------------------------------------------------------------------
# Customer Experience & Shopping Views
# ---------------------------------------------------------------------------
def customer_home(request, username=None):
    """Main customer discovery view with search, cuisine pills, and favorites filter."""
    user = username or request.session.get('username')
    if not user or user == 'Guest':
        messages.info(request, 'Please sign in to browse and place orders.')
        return redirect('open_signin')

    customer = Customer.objects.filter(username=user).first()
    if not customer:
        messages.error(request, f'Customer account "{user}" not found. Please sign in.')
        return redirect('open_signin')
    
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
        cart = get_customer_cart(customer)
        if cart:
            cart_count = sum(ci.quantity for ci in cart.cart_items.all())

    # Get list of unique cuisines for filter pills
    all_cuisines = sorted(list(set([r.cuisine.strip() for r in Restaurant.objects.all() if r.cuisine])))

    # Delivery Address for Swiggy/Zomato style address picker
    active_address = customer.get_active_address() if customer else None
    saved_addresses = customer.saved_addresses.all().order_by('-is_default', '-id') if customer else []

    context = {
        "restaurantList": restaurants,
        "username": user,
        "customer": customer,
        "active_address": active_address,
        "saved_addresses": saved_addresses,
        "cart_count": cart_count,
        "query": query,
        "current_cuisine": cuisine_filter,
        "filter_mode": filter_mode,
        "all_cuisines": all_cuisines,
        "user_fav_ids": user_fav_ids,
    }
    return render(request, 'customer_home.html', context)


# ---------------------------------------------------------------------------
# Address Management Views (Swiggy / Zomato style)
# ---------------------------------------------------------------------------
def save_address(request, username):
    """Saves a new delivery address (Home, Work, Other) for the customer."""
    customer = get_object_or_404(Customer, username=username)
    if request.method == 'POST':
        tag = request.POST.get('tag', 'Home').strip()
        flat_house = request.POST.get('flat_house', '').strip()
        area = request.POST.get('area', '').strip()
        landmark = request.POST.get('landmark', '').strip()
        city = request.POST.get('city', 'Bengaluru').strip()
        is_default = request.POST.get('is_default') in ['true', 'True', '1', 'on'] or not customer.saved_addresses.exists()

        if not flat_house or not area:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return JsonResponse({'status': 'error', 'message': 'Flat/House and Area are required.'}, status=400)
            messages.error(request, 'Flat/House and Area are required.')
            return redirect(request.META.get('HTTP_REFERER', 'customer_home'))

        if is_default:
            customer.saved_addresses.update(is_default=False)

        address = Address.objects.create(
            customer=customer,
            tag=tag if tag in ['Home', 'Work', 'Other'] else 'Home',
            flat_house=flat_house,
            area=area,
            landmark=landmark,
            city=city or 'Bengaluru',
            is_default=is_default
        )

        if is_default:
            customer.address = address.full_address()
            customer.save(update_fields=['address'])

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'status': 'success',
                'message': 'Address saved successfully!',
                'address': {
                    'id': address.id,
                    'tag': address.tag,
                    'flat_house': address.flat_house,
                    'area': address.area,
                    'landmark': address.landmark,
                    'city': address.city,
                    'full_address': address.full_address(),
                    'is_default': address.is_default
                }
            })
        messages.success(request, f'Address "{tag}" saved successfully!')
    return redirect(request.META.get('HTTP_REFERER', 'customer_home'))


def select_address(request, username, address_id):
    """Sets a saved address as the active/default delivery address."""
    customer = get_object_or_404(Customer, username=username)
    address = get_object_or_404(Address, id=address_id, customer=customer)
    customer.saved_addresses.update(is_default=False)
    address.is_default = True
    address.save(update_fields=['is_default'])
    customer.address = address.full_address()
    customer.save(update_fields=['address'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'status': 'success',
            'message': f'Active delivery address set to {address.tag}.',
            'address': {
                'id': address.id,
                'tag': address.tag,
                'full_address': address.full_address(),
            }
        })
    messages.success(request, f'Active delivery address set to {address.tag}.')
    return redirect(request.META.get('HTTP_REFERER', 'customer_home'))


def delete_address(request, username, address_id):
    """Deletes a saved address for the customer."""
    customer = get_object_or_404(Customer, username=username)
    address = get_object_or_404(Address, id=address_id, customer=customer)
    was_default = address.is_default
    address.delete()

    if was_default:
        next_addr = customer.saved_addresses.first()
        if next_addr:
            next_addr.is_default = True
            next_addr.save(update_fields=['is_default'])
            customer.address = next_addr.full_address()
            customer.save(update_fields=['address'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({'status': 'success', 'message': 'Address deleted successfully.'})
    messages.info(request, 'Address deleted.')
    return redirect(request.META.get('HTTP_REFERER', 'customer_home'))


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

    # Calculate cart count, item quantities in cart, favorite status, and review eligibility
    customer = Customer.objects.filter(username=username).first()
    cart_count = 0
    cart_items_map = {}
    is_favorited = False
    can_review = False
    has_pending_order = False
    user_review = None

    if customer:
        cart = get_customer_cart(customer)
        if cart:
            cart_count = sum(ci.quantity for ci in cart.cart_items.all())
            cart_items_map = {ci.item_id: ci.quantity for ci in cart.cart_items.all()}
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

    # Attach in_cart_qty for each item
    item_list = []
    for it in items:
        it.in_cart_qty = cart_items_map.get(it.id, 0)
        item_list.append(it)

    # Customer Reviews
    reviews = restaurant.reviews.all().order_by('-created_at')
    active_address = customer.get_active_address() if customer else None
    saved_addresses = customer.saved_addresses.all().order_by('-is_default', '-id') if customer else []

    context = {
        "itemList": item_list,
        "restaurant": restaurant,
        "username": username,
        "customer": customer,
        "active_address": active_address,
        "saved_addresses": saved_addresses,
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
    if referer:
        return redirect(referer)
    return redirect('customer_home', username=username)


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
    """Add item with quantity to customer cart. Supports both standard redirect and AJAX JSON."""
    item = get_object_or_404(Item, id=item_id)
    customer = get_object_or_404(Customer, username=username)
    cart = get_customer_cart(customer)

    qty_val = request.POST.get('quantity') or request.GET.get('quantity')
    try:
        quantity = int(qty_val) if qty_val is not None else 1
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

    total_cart_count = sum(ci.quantity for ci in cart.cart_items.all())

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json' or request.POST.get('format') == 'json'

    if is_ajax:
        return JsonResponse({
            'status': 'success',
            'message': f'Added {quantity}x "{item.name}" to cart!',
            'cart_count': total_cart_count,
            'item_id': item.id,
            'item_name': item.name,
            'item_quantity': cart_item.quantity,
            'item_price': item.price,
            'item_subtotal': round(item.price * cart_item.quantity, 2),
            'cart_subtotal': cart.subtotal(),
            'grand_total': cart.grand_total(),
        })

    messages.success(request, f'Added {quantity}x "{item.name}" to cart!')
    return redirect('view_menu', restaurant_id=item.restaurant.id, username=username)


def update_cart_quantity(request, item_id, username):
    """Update item quantity in cart (increment, decrement, or set value). Supports AJAX and standard redirects."""
    item = get_object_or_404(Item, id=item_id)
    customer = get_object_or_404(Customer, username=username)
    cart = get_customer_cart(customer)

    action = request.POST.get('action') or request.GET.get('action') or 'set'
    qty_val = request.POST.get('quantity') or request.GET.get('quantity')

    cart_item = CartItem.objects.filter(cart=cart, item=item).first()
    item_removed = False

    if action == 'increment':
        if cart_item:
            cart_item.quantity += 1
            cart_item.save()
        else:
            cart_item = CartItem.objects.create(cart=cart, item=item, quantity=1)
    elif action == 'decrement':
        if cart_item:
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
                cart_item = None
                item_removed = True
    elif action == 'set':
        try:
            quantity = int(qty_val)
        except (ValueError, TypeError):
            quantity = 1

        if quantity <= 0:
            if cart_item:
                cart_item.delete()
                cart_item = None
                item_removed = True
        else:
            if cart_item:
                cart_item.quantity = quantity
                cart_item.save()
            else:
                cart_item = CartItem.objects.create(cart=cart, item=item, quantity=quantity)

    total_cart_count = sum(ci.quantity for ci in cart.cart_items.all())
    subtotal = cart.subtotal()
    delivery_fee = cart.delivery_fee()
    
    # Recalculate coupon if applied
    applied_coupon_code = request.session.get('coupon_code')
    discount_amount = 0.0
    applied_coupon = None
    if applied_coupon_code:
        applied_coupon = Coupon.objects.filter(code__iexact=applied_coupon_code, is_active=True).first()
        if applied_coupon and subtotal >= applied_coupon.min_order_value:
            discount_amount = applied_coupon.calculate_discount(subtotal, delivery_fee)
        else:
            request.session.pop('coupon_code', None)
            applied_coupon_code = None

    grand_total = max(0.0, round(cart.grand_total() - discount_amount, 2))

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json' or request.POST.get('format') == 'json'

    if is_ajax:
        return JsonResponse({
            'status': 'success',
            'cart_count': total_cart_count,
            'item_id': item.id,
            'item_name': item.name,
            'item_removed': item_removed,
            'item_quantity': cart_item.quantity if cart_item else 0,
            'item_price': item.price,
            'item_subtotal': round(item.price * cart_item.quantity, 2) if cart_item else 0.0,
            'subtotal': subtotal,
            'gst': cart.gst(),
            'handling_fee': cart.handling_fee(),
            'delivery_fee': delivery_fee,
            'service_fee': cart.service_fee(),
            'discount_amount': discount_amount,
            'applied_coupon_code': applied_coupon_code,
            'grand_total': grand_total,
            'free_delivery_diff': round(500.0 - subtotal, 2) if subtotal < 500 else 0.0,
            'cart_empty': not cart.cart_items.exists(),
        })

    return redirect('show_cart', username=username)


def remove_from_cart(request, item_id, username):
    """Remove item from customer cart. Supports AJAX and standard redirects."""
    customer = get_object_or_404(Customer, username=username)
    item = Item.objects.filter(id=item_id).first()
    item_name = item.name if item else 'Item'
    cart = get_customer_cart(customer)
    if cart:
        CartItem.objects.filter(cart=cart, item_id=item_id).delete()
        messages.info(request, f'"{item_name}" removed from your cart.')

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json'
    if is_ajax:
        total_cart_count = sum(ci.quantity for ci in cart.cart_items.all()) if cart else 0
        subtotal = cart.subtotal() if cart else 0.0
        delivery_fee = cart.delivery_fee() if cart else 0.0
        
        applied_coupon_code = request.session.get('coupon_code')
        discount_amount = 0.0
        if applied_coupon_code and cart:
            applied_coupon = Coupon.objects.filter(code__iexact=applied_coupon_code, is_active=True).first()
            if applied_coupon and subtotal >= applied_coupon.min_order_value:
                discount_amount = applied_coupon.calculate_discount(subtotal, delivery_fee)
            else:
                request.session.pop('coupon_code', None)
                applied_coupon_code = None

        grand_total = max(0.0, round(cart.grand_total() - discount_amount, 2)) if cart else 0.0

        return JsonResponse({
            'status': 'success',
            'cart_count': total_cart_count,
            'item_id': item_id,
            'item_name': item_name,
            'item_removed': True,
            'subtotal': subtotal,
            'gst': cart.gst() if cart else 0.0,
            'handling_fee': cart.handling_fee() if cart else 0.0,
            'delivery_fee': delivery_fee,
            'service_fee': cart.service_fee() if cart else 0.0,
            'discount_amount': discount_amount,
            'grand_total': grand_total,
            'free_delivery_diff': round(500.0 - subtotal, 2) if subtotal < 500 else 0.0,
            'cart_empty': not cart.cart_items.exists() if cart else True,
        })

    return redirect('show_cart', username=username)


def clear_cart(request, username):
    """Empty all items from customer cart."""
    customer = get_object_or_404(Customer, username=username)
    cart = get_customer_cart(customer)
    if cart:
        cart.cart_items.all().delete()
    request.session.pop('coupon_code', None)
    messages.info(request, 'Your cart has been cleared.')
    return redirect('show_cart', username=username)


def apply_coupon(request, username):
    """Apply promo code coupon to current session cart."""
    if request.method == 'POST':
        code = request.POST.get('coupon_code', '').strip().upper()
        customer = get_object_or_404(Customer, username=username)
        cart = get_customer_cart(customer)

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
    cart = get_customer_cart(customer)
    cart_items = cart.cart_items.select_related('item', 'item__restaurant').all() if cart else []
    
    available_coupons = Coupon.objects.filter(is_active=True)
    applied_coupon_code = request.session.get('coupon_code')
    applied_coupon = None
    discount_amount = 0.0

    # Determine last visited restaurant from cart items
    last_restaurant = None
    if cart_items:
        last_restaurant = cart_items.last().item.restaurant

    context = {
        "cart": cart,
        "cart_items": cart_items,
        "username": username,
        "available_coupons": available_coupons,
        "applied_coupon_code": applied_coupon_code,
        "last_restaurant": last_restaurant,
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
    cart = get_customer_cart(customer)
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

    active_address = customer.get_active_address()
    saved_addresses = customer.saved_addresses.all().order_by('-is_default', '-id')

    context = {
        'username': username,
        'customer': customer,
        'active_address': active_address,
        'saved_addresses': saved_addresses,
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
            'amount': int(round(grand_total * 100)),
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
    """Direct/COD order placement with coupon discount, address recording and live tracking transition."""
    customer = get_object_or_404(Customer, username=username)
    cart = get_customer_cart(customer)
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

    # Resolve delivery address
    active_address = customer.get_active_address()
    selected_addr_id = request.POST.get('address_id') or request.GET.get('address_id')
    if selected_addr_id:
        custom_addr = customer.saved_addresses.filter(id=selected_addr_id).first()
        if custom_addr:
            active_address = custom_addr

    delivery_addr_str = active_address.full_address() if active_address else (customer.address or "Indiranagar, Bengaluru")

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
        estimated_delivery_minutes=30,
        delivery_address=delivery_addr_str
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
    cart = get_customer_cart(customer)
    cart_items = list(cart.cart_items.all()) if cart else []
    
    if not cart_items:
        latest_order = Order.objects.filter(customer=customer).order_by('-created_at').first()
        if not latest_order:
            messages.info(request, "You don't have any active or past orders yet.")
            return redirect('customer_home', username=username)
        order_items = latest_order.order_items.all()
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

    active_address = customer.get_active_address()
    selected_addr_id = request.POST.get('address_id') or request.GET.get('address_id')
    if selected_addr_id:
        custom_addr = customer.saved_addresses.filter(id=selected_addr_id).first()
        if custom_addr:
            active_address = custom_addr

    delivery_addr_str = active_address.full_address() if active_address else (customer.address or "Indiranagar, Bengaluru")

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
        estimated_delivery_minutes=30,
        delivery_address=delivery_addr_str
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
    cart = get_customer_cart(customer)

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
    total_orders_today = today_orders.count()

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
        try:
            rating = float(request.POST.get('rating') or 4.5)
        except (ValueError, TypeError):
            rating = 4.5
        
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
            picture=picture or 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&auto=format&fit=crop&q=80',
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
        try:
            rating = float(request.POST.get("rating") or restaurant.rating)
        except (ValueError, TypeError):
            rating = restaurant.rating
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
    
    redirect_target = 'restaurant_home' if request.session.get('is_restaurant') else 'open_update_menu'

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        try:
            price = float(request.POST.get('price') or 0)
        except (ValueError, TypeError):
            price = 0.0
        vegetarian = request.POST.get('vegetarian') == 'on'
        picture = request.POST.get('picture', '').strip()
        
        if not name or price <= 0:
            messages.error(request, 'Dish name and a valid price are required.')
            return redirect(redirect_target, restaurant_id=restaurant.id)

        if Item.objects.filter(restaurant=restaurant, name__iexact=name).exists():
            messages.error(request, f'Dish "{name}" is already in this restaurant menu!')
            return redirect(redirect_target, restaurant_id=restaurant.id)

        Item.objects.create(
            restaurant=restaurant,
            name=name,
            description=description,
            price=price,
            vegetarian=vegetarian,
            picture=picture or 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&auto=format&fit=crop&q=80',
        )
        messages.success(request, f'Dish "{name}" added to menu successfully!')

    return redirect(redirect_target, restaurant_id=restaurant.id)
