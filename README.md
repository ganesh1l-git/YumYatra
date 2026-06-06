# YumYatra 🍕

YumYatra is a modern, premium Django-based food delivery web application that allows customers to explore restaurants, order meals, and track checkout details, while providing admins with a clean management and sales performance dashboard.

## Features

### 🛒 Customer Experience
- **Interactive Restaurant & Menu Explorer**: View available partners, cuisine details, and customer ratings.
- **Cart Management**: Add items to the cart, specify quantities, and easily remove items.
- **Dynamic Fee Breakdown**: Automatic calculations for:
  - Subtotal
  - GST (5%)
  - Restaurant Handling Fee (₹15)
  - Delivery Fee (₹35, free for orders above ₹500)
  - Services Fee (₹10)
- **Invoice Receipts**: Post-checkout invoice summary detailing items purchased and overall transaction metrics.

### ⚙️ Admin Portal
- **Dashboard & Performance Analytics**: Real-time summary metrics of Gross Order Value (GOV), total orders, and platform profits (10% commission + ₹10 flat service fee per order).
- **Restaurant Performance**: Grouped statistics showing sales value, platform commission, and order counts per restaurant.
- **Order Log**: Live feed of daily transactions and detailed fee structures.
- **Partner Management**: Onboard and manage restaurant details, menu items, prices, and cover pictures.

## Tech Stack
- **Backend**: Python, Django
- **Frontend**: HTML5, CSS3 (Premium Glassmorphism Style)
- **Database**: SQLite3
- **Payment API**: Razorpay integration

