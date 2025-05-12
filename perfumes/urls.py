from django.urls import path
from . import views
from django.shortcuts import render
from django.views.generic import TemplateView
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('perfumes/', views.perfume_list, name='perfume_list'),
    path('perfumes/add/', views.add_perfume, name='add_perfume'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('myperfumes/', views.my_perfumes, name='my_perfumes'),
    path('perfumes/delete/<int:perfume_id>/', views.delete_perfume, name='delete_perfume'),
    path('perfumes/edit/<int:perfume_id>/', views.edit_perfume, name='edit_perfume'),
    path('perfumes/<int:perfume_id>/', views.perfume_detail, name='perfume_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:perfume_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('sales-dashboard/', views.sales_dashboard, name='sales_dashboard'),
    path('update-order-status/<int:item_id>/', views.update_order_status, name='update_order_status'),
    path('orders/<int:item_id>/', views.order_detail, name='order_detail'),
    path('perfumes/<int:perfume_id>/review/', views.add_review, name='add_review'),
    path('brand/<str:brand_name>/', views.perfumes_by_brand, name='perfumes_by_brand'),
    path('about/', views.about_us, name='about_us'),
    path('privacy-policy/', TemplateView.as_view(template_name='perfumes/privacy_policy.html'), name='privacy_policy'),
    path('terms-and-conditions/', TemplateView.as_view(template_name='perfumes/terms_and_conditions.html'), name='terms'),
    path('shipping-returns/', TemplateView.as_view(template_name='perfumes/shipping_returns.html'), name='shipping_returns'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/remove/<int:perfume_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/toggle/<int:perfume_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('perfumes/category/<str:category>/', views.perfume_category, name='perfume_category'),



]
