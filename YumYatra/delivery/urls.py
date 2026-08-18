from django.urls import path
from . import views

urlpatterns = [
    # Landing & Auth
    path('', views.say_hello, name='say_hello'),
    path('open_signup/', views.open_signup, name='open_signup'),
    path('open_signin/', views.open_signin, name='open_signin'),
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.logout_view, name='logout'),

    # Customer Discovery & Ordering
    path('customer_home/', views.customer_home, name='customer_home_default'),
    path('customer_home/<str:username>/', views.customer_home, name='customer_home'),
    path('view_menu/<int:restaurant_id>/<str:username>/', views.view_menu, name='view_menu'),
    path('toggle_favorite/<int:restaurant_id>/<str:username>/', views.toggle_favorite, name='toggle_favorite'),
    path('add_review/<int:restaurant_id>/<str:username>/', views.add_review, name='add_review'),

    # Cart & Coupons
    path('add_to_cart/<int:item_id>/<str:username>/', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<int:item_id>/<str:username>/', views.remove_from_cart, name='remove_from_cart'),
    path('show_cart/<str:username>/', views.show_cart, name='show_cart'),
    path('apply_coupon/<str:username>/', views.apply_coupon, name='apply_coupon'),
    path('remove_coupon/<str:username>/', views.remove_coupon, name='remove_coupon'),

    # Checkout, Receipts, Tracking & History
    path('checkout/<str:username>/', views.checkout, name='checkout'),
    path('direct_order/<str:username>/', views.direct_order, name='direct_order'),
    path('orders/<str:username>/', views.orders, name='orders'),
    path('track_order/<int:order_id>/<str:username>/', views.track_order, name='track_order'),
    path('my_orders/<str:username>/', views.my_orders, name='my_orders'),
    path('reorder/<int:order_id>/<str:username>/', views.reorder, name='reorder'),

    # Restaurant Partner Portal & Order Management
    path('restaurant_home/<int:restaurant_id>/', views.restaurant_home, name='restaurant_home'),
    path('delete_menu_item/<int:item_id>/', views.delete_menu_item, name='delete_menu_item'),
    path('update_order_status/<int:order_id>/', views.update_order_status, name='update_order_status'),

    # Admin Portal & Management
    path('admin_home/', views.admin_home, name='admin_home'),
    path('open_add_restaurant/', views.open_add_restaurant, name='open_add_restaurant'),
    path('add_restaurant/', views.add_restaurant, name='add_restaurant'),
    path('open_show_restaurant/', views.open_show_restaurant, name='open_show_restaurant'),
    path('open_update_restaurant/<int:restaurant_id>/', views.open_update_restaurant, name='open_update_restaurant'),
    path('update_restaurant/<int:restaurant_id>/', views.update_restaurant, name='update_restaurant'),
    path('delete_restaurant/<int:restaurant_id>/', views.delete_restaurant, name='delete_restaurant'),
    path('open_update_menu/<int:restaurant_id>/', views.open_update_menu, name='open_update_menu'),
    path('update_menu/<int:restaurant_id>/', views.update_menu, name='update_menu'),
]
