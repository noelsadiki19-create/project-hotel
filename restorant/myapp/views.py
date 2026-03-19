from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import Food, Cart, CartItem, Order, OrderItem, Payment, TableBooking
from .mpesa_utils import MpesaAPI, process_payment_callback
from .sms_utils import send_payment_sms, send_order_sms, send_booking_sms
import json

# HOME PAGE
def index(request):
    foods = Food.objects.filter(is_available=True)[:6]  # Get first 6 available foods
    context = {
        'foods': foods,
        'categories': Food.CATEGORY_CHOICES
    }
    return render(request, 'index.html', context)

# MENU PAGE
def menu(request):
    foods = Food.objects.filter(is_available=True)
    context = {
        'foods': foods,
        'categories': Food.CATEGORY_CHOICES
    }
    return render(request, 'menu.html', context)

# ABOUT PAGE
def about(request):
    return render(request, 'about.html')

# BOOK TABLE PAGE
def book(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        number_of_persons = request.POST.get('number_of_persons')
        booking_date = request.POST.get('booking_date')
        booking_time = request.POST.get('booking_time')
        special_requests = request.POST.get('special_requests', '')
        
        # Validate required fields
        if not all([name, email, phone, number_of_persons, booking_date]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'book.html')
        
        try:
            # Create table booking
            booking = TableBooking.objects.create(
                user=request.user if request.user.is_authenticated else None,
                name=name,
                email=email,
                phone=phone,
                number_of_persons=int(number_of_persons),
                booking_date=booking_date,
                booking_time=booking_time if booking_time else None,
                special_requests=special_requests,
                status='pending'
            )
            messages.success(request, f'Table booking created! Reference: #{booking.id}')
            return render(request, 'book.html', {'booking_id': booking.id})
        except Exception as e:
            messages.error(request, f'Error creating booking: {str(e)}')
            return render(request, 'book.html')
    
    return render(request, 'book.html')

# LOGIN PAGE
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect('index')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')

# REGISTER PAGE
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validate passwords match
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'register.html')
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'register.html')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'register.html')
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'register.html')
    
    return render(request, 'register.html')

# LOGOUT
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('index')

# DASHBOARD PAGE
@login_required(login_url='login')
def dashboard(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('index')
    
    # Food Statistics
    foods = Food.objects.all()
    total_foods = foods.count()
    available_foods = foods.filter(is_available=True).count()
    unavailable_foods = foods.filter(is_available=False).count()
    
    # Get foods by category
    category_stats = {}
    for code, label in Food.CATEGORY_CHOICES:
        category_stats[label] = foods.filter(category=code).count()
    
    # Order Statistics
    orders = Order.objects.all()
    total_orders = orders.count()
    pending_orders = orders.filter(status='pending').count()
    completed_orders = orders.filter(status='completed').count()
    
    # Reservation Statistics
    bookings = TableBooking.objects.all()
    total_bookings = bookings.count()
    pending_bookings = bookings.filter(status='pending').count()
    confirmed_bookings = bookings.filter(status='confirmed').count()
    recent_bookings = bookings[:5]  # Get 5 most recent
    
    context = {
        'total_foods': total_foods,
        'available_foods': available_foods,
        'unavailable_foods': unavailable_foods,
        'foods': foods,
        'category_stats': category_stats,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'recent_bookings': recent_bookings,
    }
    return render(request, 'dashboard.html', context)

# ADD FOOD PAGE
@login_required(login_url='login')
def add_food(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('index')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        category = request.POST.get('category')
        is_available = request.POST.get('is_available') == 'on'
        image = request.FILES.get('image')
        
        # Validate required fields
        if not name or not price or not category:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'add_food.html', {'categories': Food.CATEGORY_CHOICES})
        
        # Check if food item already exists
        if Food.objects.filter(name__iexact=name).exists():
            messages.error(request, f'A food item named "{name}" already exists. Please use a different name.')
            return render(request, 'add_food.html', {'categories': Food.CATEGORY_CHOICES})
        
        try:
            food = Food.objects.create(
                name=name,
                description=description,
                price=price,
                category=category,
                is_available=is_available,
                image=image
            )
            messages.success(request, f'Food item "{food.name}" added successfully!')
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f'Error adding food: {str(e)}')
            return render(request, 'add_food.html', {'categories': Food.CATEGORY_CHOICES})
    
    context = {
        'categories': Food.CATEGORY_CHOICES
    }
    return render(request, 'add_food.html', context)

# EDIT FOOD PAGE
@login_required(login_url='login')
def edit_food(request, food_id):
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('index')
    
    food = get_object_or_404(Food, id=food_id)
    
    if request.method == 'POST':
        food.name = request.POST.get('name', food.name)
        food.description = request.POST.get('description', food.description)
        food.price = request.POST.get('price', food.price)
        food.category = request.POST.get('category', food.category)
        food.is_available = request.POST.get('is_available') == 'on'
        
        if request.FILES.get('image'):
            food.image = request.FILES.get('image')
        
        try:
            food.save()
            messages.success(request, f'Food item "{food.name}" updated successfully!')
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f'Error updating food: {str(e)}')
    
    context = {
        'food': food,
        'categories': Food.CATEGORY_CHOICES
    }
    return render(request, 'edit_food.html', context)

# DELETE FOOD PAGE
@login_required(login_url='login')
def delete_food(request, food_id):
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('index')
    
    food = get_object_or_404(Food, id=food_id)
    food_name = food.name
    
    if request.method == 'POST':
        food.delete()
        messages.success(request, f'Food item "{food_name}" deleted successfully!')
        return redirect('dashboard')
    
    context = {
        'food': food
    }
    return render(request, 'delete_food.html', context)


# HELPER FUNCTION - Get or create user's cart
def get_or_create_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


# ADD TO CART
@login_required(login_url='login')
@require_http_methods(["POST"])
def add_to_cart(request, food_id):
    food = get_object_or_404(Food, id=food_id)
    cart = get_or_create_cart(request.user)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity < 1:
        messages.error(request, 'Invalid quantity.')
        return redirect('menu')
    
    try:
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            food=food,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        messages.success(request, f'{food.name} added to cart!')
    except Exception as e:
        messages.error(request, f'Error adding to cart: {str(e)}')
    
    return redirect('menu')


# VIEW CART
@login_required(login_url='login')
def view_cart(request):
    cart = get_or_create_cart(request.user)
    cart_items = cart.cartitem_set.all()
    total_price = cart.get_total_price()
    item_count = cart.get_item_count()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total_price': total_price,
        'item_count': item_count,
    }
    return render(request, 'cart.html', context)


# REMOVE FROM CART
@login_required(login_url='login')
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    food_name = cart_item.food.name
    
    try:
        cart_item.delete()
        messages.success(request, f'{food_name} removed from cart.')
    except Exception as e:
        messages.error(request, f'Error removing from cart: {str(e)}')
    
    return redirect('view_cart')


# UPDATE CART ITEM QUANTITY
@login_required(login_url='login')
def update_cart_item(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity < 1:
            cart_item.delete()
            messages.success(request, f'{cart_item.food.name} removed from cart.')
        elif quantity != cart_item.quantity:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, f'{cart_item.food.name} quantity updated.')
        
        return redirect('view_cart')
    
    return redirect('view_cart')


# CHECKOUT PAGE
@login_required(login_url='login')
def checkout(request):
    cart = get_or_create_cart(request.user)
    cart_items = cart.cartitem_set.all()
    
    if not cart_items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('view_cart')
    
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name')
        customer_email = request.POST.get('customer_email')
        customer_phone = request.POST.get('customer_phone')
        delivery_address = request.POST.get('delivery_address')
        special_instructions = request.POST.get('special_instructions', '')
        
        # Validate required fields
        if not all([customer_name, customer_email, customer_phone, delivery_address]):
            messages.error(request, 'Please fill in all required fields.')
            context = {
                'cart': cart,
                'cart_items': cart_items,
                'total_price': cart.get_total_price(),
                'user': request.user,
            }
            return render(request, 'checkout.html', context)
        
        try:
            # Create order
            total_price = cart.get_total_price()
            order = Order.objects.create(
                user=request.user,
                total_price=total_price,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                delivery_address=delivery_address,
                special_instructions=special_instructions,
                payment_status='pending',
            )
            
            # Create order items from cart items
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    food=cart_item.food,
                    quantity=cart_item.quantity,
                    price_at_order=cart_item.food.price,
                )
            
            # Create payment record
            Payment.objects.create(
                order=order,
                amount=total_price,
                phone_number=customer_phone,
                status='pending'
            )
            
            # Clear cart
            cart_items.delete()
            
            # Redirect to M-Pesa payment
            return redirect('process_mpesa_payment', order_id=order.id)
        except Exception as e:
            messages.error(request, f'Error placing order: {str(e)}')
            context = {
                'cart': cart,
                'cart_items': cart_items,
                'total_price': cart.get_total_price(),
                'user': request.user,
            }
            return render(request, 'checkout.html', context)
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total_price': cart.get_total_price(),
        'user': request.user,
    }
    return render(request, 'checkout.html', context)


# ORDER CONFIRMATION PAGE
@login_required(login_url='login')
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.orderitem_set.all()
    
    # Send SMS order confirmation if payment is completed
    if order.payment_status == 'completed':
        try:
            payment = Payment.objects.get(order=order)
            sms_result = send_payment_sms(
                phone=payment.phone_number,
                order_id=order.id,
                amount=order.total_price,
                status='success'
            )
            print(f"Order confirmation SMS sent: {sms_result}")
        except Payment.DoesNotExist:
            pass
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'order_confirmation.html', context)


# MY ORDERS PAGE
@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(user=request.user)
    
    context = {
        'orders': orders,
    }
    return render(request, 'my_orders.html', context)


# M-PESA PAYMENT PROCESSING
@login_required(login_url='login')
def process_mpesa_payment(request, order_id):
    """Process M-Pesa STK Push payment"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        payment = get_object_or_404(Payment, order=order)
        
        # Initialize M-Pesa API
        mpesa = MpesaAPI()
        
        # Initiate STK Push
        phone_number = payment.phone_number
        # Ensure phone number is in correct format (254xxxxxxxxx)
        if not phone_number.startswith('254'):
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            else:
                phone_number = '254' + phone_number
        
        amount = int(payment.amount)  # M-Pesa requires integer amount
        
        result = mpesa.initiate_stk_push(
            phone_number=phone_number,
            amount=amount,
            order_id=order.id
        )
        
        if result.get('success'):
            # Store checkout request ID for tracking
            payment.mpesa_reference = result.get('checkout_request_id')
            payment.save()
            
            context = {
                'order': order,
                'payment': payment,
                'message': result.get('message'),
                'checkout_request_id': result.get('checkout_request_id'),
            }
            return render(request, 'mpesa_payment.html', context)
        else:
            messages.error(request, f"Payment initiation failed: {result.get('error')}")
            return redirect('order_confirmation', order_id=order.id)
            
    except Exception as e:
        messages.error(request, f'Error processing payment: {str(e)}')
        return redirect('view_cart')


# M-PESA PAYMENT CALLBACK (webhook)
@csrf_exempt
@require_http_methods(['POST'])
def mpesa_callback(request):
    """Handle M-Pesa payment callback"""
    try:
        # Parse the callback data
        callback_data = json.loads(request.body)
        
        # Process the callback
        result = process_payment_callback(callback_data)
        
        if result.get('success'):
            # Extract order ID from metadata
            metadata = result.get('metadata', {})
            account_reference = metadata.get('AccountReference', '')
            
            if account_reference.startswith('Order-'):
                order_id = int(account_reference.replace('Order-', ''))
                try:
                    payment = Payment.objects.get(order_id=order_id)
                    payment.status = 'completed'
                    payment.mpesa_reference = result.get('receipt_number')
                    payment.save()
                    
                    # Update order payment status
                    order = payment.order
                    order.payment_status = 'completed'
                    order.status = 'confirmed'
                    order.save()
                    
                    # Send SMS notification to customer
                    sms_result = send_payment_sms(
                        phone=payment.phone_number,
                        order_id=order.id,
                        amount=order.total_price,
                        status='success'
                    )
                    print(f"SMS notification sent: {sms_result}")
                except Payment.DoesNotExist:
                    pass
        else:
            # Payment failed
            metadata = result.get('metadata', {})
            account_reference = metadata.get('AccountReference', '')
            
            if account_reference.startswith('Order-'):
                order_id = int(account_reference.replace('Order-', ''))
                try:
                    payment = Payment.objects.get(order_id=order_id)
                    payment.status = 'failed'
                    payment.save()
                    
                    order = payment.order
                    order.payment_status = 'failed'
                    order.save()
                    
                    # Send SMS notification about failed payment
                    sms_result = send_payment_sms(
                        phone=payment.phone_number,
                        order_id=order.id,
                        amount=order.total_price,
                        status='failed'
                    )
                    print(f"SMS notification sent: {sms_result}")
                except Payment.DoesNotExist:
                    pass
        
        # Return success response to M-Pesa
        return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})
        
    except Exception as e:
        print(f"Error processing callback: {str(e)}")
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Error'}, status=400)


# CHECK PAYMENT STATUS
@login_required(login_url='login')
def check_payment_status(request, order_id):
    """Check payment status for an order"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        payment = get_object_or_404(Payment, order=order)
        
        if payment.mpesa_reference:
            mpesa = MpesaAPI()
            status_result = mpesa.check_transaction_status(payment.mpesa_reference)
            
            # Return as JSON for AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'payment_status': payment.status,
                    'order_status': order.status,
                    'mpesa_status': status_result
                })
        
        return redirect('order_confirmation', order_id=order.id)
        
    except Exception as e:
        messages.error(request, f'Error checking payment status: {str(e)}')
        return redirect('view_cart')