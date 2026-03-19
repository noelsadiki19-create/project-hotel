from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('menu/', views.menu, name='menu'),
    path('about/', views.about, name='about'),
    path('book/', views.book, name='book'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Admin
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-food/', views.add_food, name='add_food'),
    path('edit-food/<int:food_id>/', views.edit_food, name='edit_food'),
    path('delete-food/<int:food_id>/', views.delete_food, name='delete_food'),
    
    # Cart & Order
    path('add-to-cart/<int:food_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('my-orders/', views.my_orders, name='my_orders'),
]
