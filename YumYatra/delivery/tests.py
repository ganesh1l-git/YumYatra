from django.test import TestCase, Client
from django.urls import reverse
from .models import Customer, Restaurant, Item, Cart, CartItem, Order, OrderItem, Coupon, Review, Favorite, Address


class AuthenticationAndWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = Customer.objects.create(
            username='ganesh_k',
            password='ganesh',
            email='ganesh@example.com',
            phone='9876543210',
            address='123 Main Street'
        )
        self.restaurant = Restaurant.objects.create(
            name='The Pizza Oven',
            password='rest123',
            cuisine='Italian',
            rating=4.8
        )
        self.item = Item.objects.create(
            restaurant=self.restaurant,
            name='Margherita Pizza',
            description='Cheesy wood-fired pizza',
            price=299.0,
            vegetarian=True
        )
        self.coupon = Coupon.objects.create(
            code='FIRSTBITE',
            description='50% OFF up to 120',
            discount_percent=50.0,
            max_discount=120.0,
            min_order_value=199.0
        )

    def test_admin_login_success(self):
        response = self.client.post(reverse('signin'), {
            'role': 'admin',
            'username': 'admin',
            'password': 'admin123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('admin_home'))
        self.assertTrue(self.client.session.get('is_admin'))

    def test_admin_login_invalid_password(self):
        response = self.client.post(reverse('signin'), {
            'role': 'admin',
            'username': 'admin',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid Admin credentials')
        self.assertFalse(self.client.session.get('is_admin', False))

    def test_user_login_success(self):
        response = self.client.post(reverse('signin'), {
            'role': 'user',
            'username': 'ganesh_k',
            'password': 'ganesh'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('customer_home', kwargs={'username': 'ganesh_k'}))
        self.assertEqual(self.client.session.get('username'), 'ganesh_k')

    def test_user_login_failure(self):
        response = self.client.post(reverse('signin'), {
            'role': 'user',
            'username': 'ganesh_k',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid customer username or password')

    def test_restaurant_login_success(self):
        response = self.client.post(reverse('signin'), {
            'role': 'restaurant',
            'username': 'The Pizza Oven',
            'password': 'rest123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('restaurant_home', kwargs={'restaurant_id': self.restaurant.id}))
        self.assertTrue(self.client.session.get('is_restaurant'))

    def test_restaurant_login_failure(self):
        response = self.client.post(reverse('signin'), {
            'role': 'restaurant',
            'username': 'The Pizza Oven',
            'password': 'wrongpassword'
        })
        self.assertContains(response, 'Invalid credentials for restaurant')

    def test_coupon_application_and_order_flow(self):
        # Add item to cart
        self.client.get(f"/add_to_cart/{self.item.id}/{self.customer.username}/?quantity=2")

        # Apply coupon
        coupon_res = self.client.post(reverse('apply_coupon', kwargs={'username': self.customer.username}), {
            'coupon_code': 'FIRSTBITE'
        })
        self.assertEqual(coupon_res.status_code, 302)
        self.assertEqual(self.client.session.get('coupon_code'), 'FIRSTBITE')

        # View cart with coupon applied
        cart_res = self.client.get(reverse('show_cart', kwargs={'username': self.customer.username}))
        self.assertEqual(cart_res.status_code, 200)
        self.assertContains(cart_res, 'FIRSTBITE Applied!')
        self.assertContains(cart_res, '120.0') # 120 cap

        # Direct checkout
        order_res = self.client.get(reverse('direct_order', kwargs={'username': self.customer.username}))
        self.assertEqual(order_res.status_code, 200)
        self.assertContains(order_res, 'Order Placed Successfully!')

        # Verify DB order
        order = Order.objects.filter(customer=self.customer).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'Placed')
        self.assertEqual(order.coupon_code, 'FIRSTBITE')
        self.assertEqual(order.discount_amount, 120.0)

    def test_live_order_tracking_and_status_update(self):
        # Create an order
        order = Order.objects.create(
            customer=self.customer,
            subtotal=299.0,
            gst=14.95,
            handling_fee=15.0,
            delivery_fee=35.0,
            service_fee=10.0,
            grand_total=373.95,
            status='Placed'
        )
        OrderItem.objects.create(
            order=order,
            item=self.item,
            restaurant=self.restaurant,
            price=299.0,
            quantity=1
        )

        # Track order view
        track_res = self.client.get(reverse('track_order', kwargs={'order_id': order.id, 'username': self.customer.username}))
        self.assertEqual(track_res.status_code, 200)
        self.assertContains(track_res, f'Tracking Order #{order.id}')
        self.assertContains(track_res, 'Cooking')

        # Update order status to 'Preparing' as restaurant partner
        session = self.client.session
        session['is_restaurant'] = True
        session['restaurant_id'] = self.restaurant.id
        session.save()

        status_res = self.client.get(f"{reverse('update_order_status', kwargs={'order_id': order.id})}?status=Preparing")
        self.assertEqual(status_res.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.status, 'Preparing')

    def test_1_click_reorder(self):
        # Create a past order
        order = Order.objects.create(
            customer=self.customer,
            subtotal=299.0,
            gst=14.95,
            handling_fee=15.0,
            delivery_fee=35.0,
            service_fee=10.0,
            grand_total=373.95,
            status='Delivered'
        )
        OrderItem.objects.create(
            order=order,
            item=self.item,
            restaurant=self.restaurant,
            price=299.0,
            quantity=3
        )

        # Trigger reorder
        reorder_res = self.client.get(reverse('reorder', kwargs={'order_id': order.id, 'username': self.customer.username}))
        self.assertEqual(reorder_res.status_code, 302)

        # Verify cart now contains 3x Margherita Pizza
        cart = Cart.objects.get(customer=self.customer)
        self.assertEqual(cart.cart_items.count(), 1)
        self.assertEqual(cart.cart_items.first().quantity, 3)

    def test_review_submission_and_rating_recalculation(self):
        # 1. Attempt review without delivered order -> Should fail
        res_fail = self.client.post(reverse('add_review', kwargs={'restaurant_id': self.restaurant.id, 'username': self.customer.username}), {
            'rating': '5',
            'comment': 'I have not ordered yet'
        }, follow=True)
        self.assertContains(res_fail, 'Only customers with a delivered order')
        self.assertFalse(Review.objects.filter(restaurant=self.restaurant, customer=self.customer).exists())

        # 2. Create a Delivered Order for this customer & restaurant
        delivered_order = Order.objects.create(
            customer=self.customer,
            subtotal=299.0,
            gst=14.95,
            handling_fee=15.0,
            delivery_fee=35.0,
            service_fee=10.0,
            grand_total=373.95,
            status='Delivered'
        )
        OrderItem.objects.create(
            order=delivered_order,
            item=self.item,
            restaurant=self.restaurant,
            price=299.0,
            quantity=1
        )

        # 3. Attempt review with delivered order -> Should succeed
        res_success = self.client.post(reverse('add_review', kwargs={'restaurant_id': self.restaurant.id, 'username': self.customer.username}), {
            'rating': '5',
            'comment': 'Exceptional crispy crust and savory sauce!'
        }, follow=True)
        self.assertContains(res_success, 'Your verified review')

        review = Review.objects.filter(restaurant=self.restaurant, customer=self.customer).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.rating, 5)

        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.rating, 5.0)

    def test_favorite_bookmarking(self):
        # Toggle favorite on
        fav_res = self.client.get(reverse('toggle_favorite', kwargs={'restaurant_id': self.restaurant.id, 'username': self.customer.username}))
        self.assertEqual(fav_res.status_code, 302)
        self.assertTrue(Favorite.objects.filter(customer=self.customer, restaurant=self.restaurant).exists())

        # Toggle favorite off
        fav_res2 = self.client.get(reverse('toggle_favorite', kwargs={'restaurant_id': self.restaurant.id, 'username': self.customer.username}))
        self.assertEqual(fav_res2.status_code, 302)
        self.assertFalse(Favorite.objects.filter(customer=self.customer, restaurant=self.restaurant).exists())

    def test_ajax_add_to_cart_and_auto_quantity(self):
        # Adding with quantity 0 should auto-fallback to 1
        res = self.client.get(
            f"/add_to_cart/{self.item.id}/{self.customer.username}/?quantity=0",
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['cart_count'], 1)
        self.assertEqual(data['item_quantity'], 1)

        # Adding 2 more via AJAX
        res2 = self.client.get(
            f"/add_to_cart/{self.item.id}/{self.customer.username}/?quantity=2",
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2['cart_count'], 3)
        self.assertEqual(data2['item_quantity'], 3)

    def test_update_cart_quantity_increment_decrement_and_set(self):
        # Initial item
        self.client.get(f"/add_to_cart/{self.item.id}/{self.customer.username}/?quantity=2")

        # Increment
        res_inc = self.client.get(
            f"/update_cart_quantity/{self.item.id}/{self.customer.username}/?action=increment",
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res_inc.status_code, 200)
        self.assertEqual(res_inc.json()['item_quantity'], 3)

        # Decrement
        res_dec = self.client.get(
            f"/update_cart_quantity/{self.item.id}/{self.customer.username}/?action=decrement",
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res_dec.status_code, 200)
        self.assertEqual(res_dec.json()['item_quantity'], 2)

        # Set to 0 -> Removes item
        res_zero = self.client.get(
            f"/update_cart_quantity/{self.item.id}/{self.customer.username}/?action=set&quantity=0",
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res_zero.status_code, 200)
        self.assertTrue(res_zero.json()['item_removed'])
        self.assertEqual(res_zero.json()['cart_count'], 0)

    def test_clear_cart(self):
        self.client.get(f"/add_to_cart/{self.item.id}/{self.customer.username}/?quantity=3")
        res = self.client.get(reverse('clear_cart', kwargs={'username': self.customer.username}), follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Your Cart is Empty')

    def test_separate_login_screens(self):
        # Customer login only
        res_cust = self.client.get(reverse('open_signin'))
        self.assertEqual(res_cust.status_code, 200)
        self.assertContains(res_cust, 'Customer Sign In')
        self.assertNotContains(res_cust, 'role-selector')
        self.assertNotContains(res_cust, 'AUTHENTICATE AS ADMIN')

        # Partner login only
        res_partner = self.client.get(reverse('partner_signin'))
        self.assertEqual(res_partner.status_code, 200)
        self.assertContains(res_partner, 'Partner Portal')
        self.assertContains(res_partner, 'SIGN IN AS PARTNER')
        self.assertNotContains(res_partner, 'role-selector')

        # Admin login only
        res_admin = self.client.get(reverse('admin_signin'))
        self.assertEqual(res_admin.status_code, 200)
        self.assertContains(res_admin, 'Admin Portal')
        self.assertContains(res_admin, 'AUTHENTICATE AS ADMIN')
        self.assertNotContains(res_admin, 'role-selector')

    def test_address_management_lifecycle(self):
        # 1. Save new address
        save_res = self.client.post(reverse('save_address', kwargs={'username': self.customer.username}), {
            'tag': 'Home',
            'flat_house': 'Flat 402, Lotus Orchid',
            'area': '100ft Road, Indiranagar',
            'landmark': 'Near Metro',
            'city': 'Bengaluru',
            'is_default': '1'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(save_res.status_code, 200)
        save_data = save_res.json()
        self.assertEqual(save_data['status'], 'success')
        addr_id = save_data['address']['id']

        addr = Address.objects.get(id=addr_id)
        self.assertEqual(addr.tag, 'Home')
        self.assertTrue(addr.is_default)
        self.assertIn('Indiranagar', addr.full_address())

        # 2. Add second address (Work)
        work_res = self.client.post(reverse('save_address', kwargs={'username': self.customer.username}), {
            'tag': 'Work',
            'flat_house': 'Embassy Tech Village',
            'area': 'Bellandur',
            'city': 'Bengaluru',
            'is_default': '0'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        work_id = work_res.json()['address']['id']
        work_addr = Address.objects.get(id=work_id)
        self.assertFalse(work_addr.is_default)

        # 3. Select second address as active
        sel_res = self.client.post(reverse('select_address', kwargs={'username': self.customer.username, 'address_id': work_id}),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(sel_res.status_code, 200)
        work_addr.refresh_from_db()
        addr.refresh_from_db()
        self.assertTrue(work_addr.is_default)
        self.assertFalse(addr.is_default)

        # 4. Direct order uses active address
        self.client.get(f"/add_to_cart/{self.item.id}/{self.customer.username}/?quantity=1")
        order_res = self.client.get(f"/direct_order/{self.customer.username}/?address_id={work_id}")
        self.assertEqual(order_res.status_code, 200)
        order = Order.objects.filter(customer=self.customer).order_by('-created_at').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.delivery_address, work_addr.full_address())



