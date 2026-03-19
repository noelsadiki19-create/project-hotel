from django.contrib import admin
from .models import Food, Cart, CartItem, Order, OrderItem, Payment, TableBooking

# FOOD ADMIN
@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_available', 'created_at')
    list_filter = ('category', 'is_available', 'created_at')
    search_fields = ('name', 'description')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category')
        }),
        ('Pricing & Image', {
            'fields': ('price', 'image')
        }),
        ('Status', {
            'fields': ('is_available',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
    class Media:
        css = {
            'all': ('admin/css/food_admin.css',)
        }


# ORDER ITEM INLINE
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('food', 'quantity', 'price_at_order', 'get_total_price')
    can_delete = False
    
    def get_total_price(self, obj):
        return f"KS{obj.get_total_price()}"
    get_total_price.short_description = "Total Price"


# PAYMENT ADMIN
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_order_id', 'amount', 'phone_number', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('phone_number', 'mpesa_reference', 'order__customer_name')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_order_id(self, obj):
        return f"Order #{obj.order.id}"
    get_order_id.short_description = "Order"


# TABLE BOOKING ADMIN
@admin.register(TableBooking)
class TableBookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'booking_date', 'booking_time', 'number_of_persons', 'status', 'created_at')
    list_filter = ('status', 'booking_date', 'created_at')
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('id', 'name', 'email', 'phone', 'user', 'created_at', 'updated_at')
        }),
        ('Table Details', {
            'fields': ('booking_date', 'booking_time', 'number_of_persons')
        }),
        ('Special Requests', {
            'fields': ('special_requests',)
        }),
        ('Status', {
            'fields': ('status',)
        }),
    )
    
    actions = ['confirm_booking', 'cancel_booking']
    
    def confirm_booking(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} booking(s) confirmed.')
    confirm_booking.short_description = "Mark selected bookings as confirmed"
    
    def cancel_booking(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} booking(s) cancelled.')
    cancel_booking.short_description = "Mark selected bookings as cancelled"


# ORDER ADMIN
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('customer_name', 'customer_email', 'customer_phone')
    readonly_fields = ('user', 'created_at', 'updated_at', 'total_price')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('id', 'user', 'status', 'total_price', 'created_at', 'updated_at')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Delivery', {
            'fields': ('delivery_address', 'special_instructions')
        }),
    )
    
    ordering = ('-created_at',)


# CART ADMIN (for viewing only)
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_item_count', 'get_total_price', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user', 'created_at', 'updated_at')
    
    def get_item_count(self, obj):
        return obj.get_item_count()
    get_item_count.short_description = "Item Count"
    
    def get_total_price(self, obj):
        return f"KS{obj.get_total_price()}"
    get_total_price.short_description = "Total Price"
