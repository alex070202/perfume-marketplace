from django.shortcuts import render, redirect, get_object_or_404
from .models import Perfume, PerfumeImage, Cart, CartItem,TradeOffer
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Order, OrderItem, ORDER_STATUS_CHOICES
from .models import Review,TradeDeliveryInfo
from django.db.models import Avg
from django.http import JsonResponse
from .models import WishlistItem
from django.db.models import Q
from .forms import CustomUserCreationForm

def home(request):
    latest_perfumes = Perfume.objects.order_by('-id')[:6]
    return render(request, 'perfumes/home.html', {'latest_perfumes': latest_perfumes})

def perfume_list(request):
    query = request.GET.get('q', '')
    perfumes = Perfume.objects.all()

    if query:
        perfumes = perfumes.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query)
        )

    if request.user.is_authenticated:
        wishlist_ids = WishlistItem.objects.filter(user=request.user).values_list('perfume_id', flat=True)
        for perfume in perfumes:
            perfume.in_wishlist = perfume.id in wishlist_ids
    else:
        for perfume in perfumes:
            perfume.in_wishlist = False

    return render(request, 'perfumes/perfume_list.html', {
        'perfumes': perfumes,
        'query': query
    })

@login_required
def add_perfume(request):
    if request.method == 'POST':
        name = request.POST['name']
        brand = request.POST['brand']
        description = request.POST['description']
        price = request.POST['price']
        stock = request.POST['stock']
        category = request.POST.get('category')
        notes = request.POST.get('notes')
        is_for_trade = 'is_for_trade' in request.POST
        main_image = request.FILES.get('main_image')

        extra_image1 = request.FILES.get('extra_image1')
        extra_image2 = request.FILES.get('extra_image2')
        extra_image3 = request.FILES.get('extra_image3')

        perfume = Perfume(
            name=name,
            brand=brand,
            description=description,
            price=price,
            stock=stock,  
            is_for_trade=is_for_trade,
            owner=request.user,
            image=main_image,
            notes=notes,
            category=category
        )
        perfume.save()

        for img in [extra_image1, extra_image2, extra_image3]:
            if img:
                PerfumeImage.objects.create(perfume=perfume, image=img)

        messages.success(request, 'Perfume added successfully!')
        return redirect('perfume_list')

    return render(request, 'perfumes/add_perfume.html')

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'perfumes/register.html', {'form': form})

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You have been logged out.")
        return redirect('home')
    else:
        return redirect('home')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

@login_required
def wishlist(request):
    items = WishlistItem.objects.filter(user=request.user).select_related('perfume')
    return render(request, 'perfumes/wishlist.html', {'items': items})

@login_required
@require_POST
def toggle_wishlist(request, perfume_id):
    perfume = get_object_or_404(Perfume, id=perfume_id)
    item, created = WishlistItem.objects.get_or_create(user=request.user, perfume=perfume)
    if not created:
        item.delete()
        return JsonResponse({'status': 'removed'})
    return JsonResponse({'status': 'added'})

@login_required
def my_perfumes(request):
    perfumes = Perfume.objects.filter(owner=request.user)
    return render(request, 'perfumes/my_perfumes.html', {'perfumes': perfumes})

@login_required
def delete_perfume(request, perfume_id):
    perfume = get_object_or_404(Perfume, id=perfume_id, owner=request.user)
    if request.method == 'POST':
        perfume.delete()
        messages.success(request, 'Perfume deleted successfully!')
        return redirect('my_perfumes')
    return render(request, 'perfumes/confirm_delete.html', {'perfume': perfume})

@login_required
def edit_perfume(request, perfume_id):
    perfume = get_object_or_404(Perfume, id=perfume_id, owner=request.user)

    if request.method == 'POST':
        perfume.name = request.POST['name']
        perfume.brand = request.POST['brand']
        perfume.description = request.POST['description']
        perfume.price = request.POST['price']
        perfume.stock = request.POST['stock']
        perfume.category = request.POST['category']
        perfume.is_for_trade = 'is_for_trade' in request.POST

        if 'main_image' in request.FILES:
            perfume.image = request.FILES['main_image']

        extra_image1 = request.FILES.get('extra_image1')
        extra_image2 = request.FILES.get('extra_image2')
        extra_image3 = request.FILES.get('extra_image3')

        # Изтриваме старите допълнителни снимки
        perfume.additional_images.all().delete()

        # Добавяме новите, ако има
        for img in [extra_image1, extra_image2, extra_image3]:
            if img:
                PerfumeImage.objects.create(perfume=perfume, image=img)

        perfume.notes = request.POST.get('notes')

        perfume.save()
        messages.success(request, 'Perfume updated successfully!')
        return redirect('my_perfumes')

    return render(request, 'perfumes/edit_perfume.html', {'perfume': perfume})

@login_required(login_url='/login/')
def add_to_cart(request, perfume_id):
    perfume = get_object_or_404(Perfume, id=perfume_id)
    quantity = int(request.POST.get('quantity', 1))

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item = CartItem.objects.filter(cart=cart, perfume=perfume).first()

    current_quantity = cart_item.quantity if cart_item else 0
    requested_total = current_quantity + quantity

    if requested_total > perfume.stock:
        error_message = f"Only {perfume.stock} units of {perfume.name} are available in stock."
        
        # AJAX response
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': error_message}, status=400)
        
        messages.error(request, error_message)
        return redirect('perfume_detail', perfume_id=perfume.id)

    if cart_item:
        cart_item.quantity = requested_total
    else:
        cart_item = CartItem(cart=cart, perfume=perfume, quantity=quantity)

    cart_item.save()

    # AJAX response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'message': 'Item added to cart successfully'})

    messages.success(request, f"{perfume.name} added to cart.")
    return redirect('perfume_detail', perfume_id=perfume.id)

@login_required
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.cartitem_set.all()
    for item in cart_items:
        item.subtotal = item.perfume.price * item.quantity
    total = sum(item.subtotal for item in cart_items)
    return render(request, 'perfumes/cart_detail.html', {
        'cart_items': cart_items,
        'total': total
    })

@require_POST
@login_required
def update_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    has_error = False

    for item in cart.cartitem_set.all():
        try:
            quantity = int(request.POST.get(f'quantity_{item.id}'))
        except (TypeError, ValueError):
            continue

        if quantity > item.perfume.stock:
            messages.error(request, f"Not enough stock for '{item.perfume.name}'. Only {item.perfume.stock} left.")
            has_error = True
        elif quantity < 1:
            messages.error(request, f"Invalid quantity for '{item.perfume.name}'.")
            has_error = True
        else:
            item.quantity = quantity
            item.save()

    if has_error:
        return redirect('cart_detail')

    messages.success(request, 'Cart updated successfully!')
    return redirect('cart_detail')

def perfumes_by_brand(request, brand_name):
    perfumes = Perfume.objects.filter(brand__iexact=brand_name)
    return render(request, 'perfumes/perfume_list.html', {
        'perfumes': perfumes,
        'filter_brand': brand_name
    })

@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, 'Item removed from your cart!')
    return redirect('cart_detail')

@login_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # 🟢 ВЗИМАМЕ АКТУАЛНИТЕ НЕЩА ПРЕДИ ПОКУПКА
        items = cart.cartitem_set.select_related('perfume').all()
        total = sum(item.perfume.price * item.quantity for item in items)

        # Проверка за наличности
        overstocked_items = []
        for item in items:
            if item.quantity > item.perfume.stock:
                overstocked_items.append((item.perfume.name, item.perfume.stock))

        if overstocked_items:
            for name, available in overstocked_items:
                messages.error(request, f'Not enough stock for "{name}". Only {available} available.')
            return redirect('cart_detail')

        # Данни от формата
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        notes = request.POST.get('notes')

        order = Order.objects.create(
            buyer=request.user,
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            notes=notes,
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                perfume=item.perfume,
                seller=item.perfume.owner,
                quantity=item.quantity,
                price=item.perfume.price
            )
            item.perfume.stock -= item.quantity
            item.perfume.save()

        items.delete()

        return render(request, 'perfumes/checkout_success.html', {
            'order': order,
            'total': total
        })

    # 🟡 GET заявка – визуализиране на checkout формата
    items = cart.cartitem_set.select_related('perfume').all()
    total = sum(item.perfume.price * item.quantity for item in items)

    return render(request, 'perfumes/checkout.html', {
        'cart_items': items,
        'total': total
    })

@login_required
def my_orders(request):
    orders = request.user.orders.prefetch_related('items__perfume', 'items__seller').order_by('-created_at')
    return render(request, 'perfumes/my_orders.html', {'orders': orders})

@login_required
def sales_dashboard(request):
    items = OrderItem.objects.filter(seller=request.user).select_related('order', 'perfume').order_by('-order__created_at')
    return render(request, 'perfumes/sales_dashboard.html', {'items': items})

@login_required
def update_order_status(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, seller=request.user)

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(ORDER_STATUS_CHOICES):
            item.order.status = status
            item.order.save()
            messages.success(request, 'Order status updated.')

    return redirect('sales_dashboard')

@login_required
def order_detail(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, seller=request.user)
    order = item.order

    if request.method == 'POST':
        status = request.POST.get('status', '').strip()
        if status in dict(ORDER_STATUS_CHOICES):
            if status != order.status:
                order.status = status
                order.save()
                messages.success(request, 'Order status updated.')
            else:
                messages.info(request, 'Status was not changed.')
            return redirect('order_detail', item_id=item_id)

    return render(request, 'perfumes/order_detail.html', {
        'item': item,
        'order': order,
        'status_choices': ORDER_STATUS_CHOICES
    })

def perfume_detail(request, perfume_id):
    perfume = get_object_or_404(Perfume, id=perfume_id)
    reviews = perfume.reviews.all()
    additional_images = perfume.additional_images.all()
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    review_count = reviews.count()
    filled_stars = range(int(round(average_rating)))
    empty_stars = range(5 - int(round(average_rating)))

    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = perfume.wishlistitem_set.filter(user=request.user).exists()
    return render(request, 'perfumes/perfume_detail.html', {
        'perfume': perfume,
        'additional_images': additional_images,
        'reviews': reviews,
        'average_rating': round(average_rating, 1),
        'review_count': review_count,
        'filled_stars': filled_stars,
        'empty_stars': empty_stars,
        'in_wishlist': in_wishlist,
    })

@login_required
def remove_from_wishlist(request, perfume_id):
    perfume = get_object_or_404(Perfume, id=perfume_id)
    WishlistItem.objects.filter(user=request.user, perfume=perfume).delete()
    messages.success(request, f"{perfume.name} was removed from your wishlist.")
    return redirect('wishlist')

@login_required
def add_review(request, perfume_id):
    perfume = get_object_or_404(Perfume, id=perfume_id)
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 5))
        comment = request.POST.get('comment')
        Review.objects.create(perfume=perfume, user=request.user, rating=rating, comment=comment)
        messages.success(request, 'Review submitted successfully!')
    return redirect('perfume_detail', perfume_id=perfume.id)

def about_us(request):
    return render(request, 'perfumes/about_us.html')

def perfume_category(request, category):
    perfumes = Perfume.objects.filter(category=category)
    return render(request, 'perfumes/perfume_list.html', {'perfumes': perfumes})

@login_required
def exchange_request(request, perfume_id):
    requested_perfume = get_object_or_404(Perfume, id=perfume_id)

    if requested_perfume.owner == request.user:
        return redirect('perfume_detail', perfume_id=perfume_id)

    if request.method == 'POST':
        offered_id = request.POST.get('offered_perfume')
        extra_payment = request.POST.get('extra_payment') or None
        offered_perfume = get_object_or_404(Perfume, id=offered_id, owner=request.user)

        offer = TradeOffer.objects.create(
            user_from=request.user,
            user_to=requested_perfume.owner,
            offered_perfume=offered_perfume,
            requested_perfume=requested_perfume,
            additional_payment=extra_payment if extra_payment else None
        )
        return redirect('provide_delivery_info', trade_id=offer.id)

    user_perfumes = Perfume.objects.filter(owner=request.user, is_for_trade=True)
    return render(request, 'perfumes/exchange_request.html', {
        'requested_perfume': requested_perfume,
        'user_perfumes': user_perfumes
    })

@require_POST
@login_required
def respond_exchange(request, request_id):
    exchange = get_object_or_404(TradeOffer, id=request_id, user_to=request.user)
    action = request.POST.get('action')
    if action == 'accept':
        exchange.status = 'accepted'
        exchange.save()
        return redirect('provide_delivery_info', trade_id=exchange.id)

    elif action == 'reject':
        exchange.status = 'rejected'
        exchange.save()

    messages.success(request, f'Trade offer {action}ed.')
    return redirect('my_received_offers')

@login_required
def incoming_requests(request):
    offers = TradeOffer.objects.filter(user_to=request.user).select_related('offered_perfume', 'requested_perfume', 'user_from')
    return render(request, 'perfumes/my_received_offers.html', {'received_offers': offers})
@login_required
def my_sent_offers(request):
    # Всички изпратени
    sent_offers = request.user.sent_trades.select_related(
        'offered_perfume', 'requested_perfume', 'user_to'
    ).order_by('-created_at')

    TradeOffer.objects.filter(
        Q(user_from=request.user) & ~Q(status='pending'),
        is_seen_by_sender=False
    ).update(is_seen_by_sender=True)
    return render(request, 'perfumes/my_sent_offers.html', {
        'sent_offers': sent_offers
    })

@login_required
def my_received_offers(request):
    received_offers = request.user.received_trades.select_related('offered_perfume', 'requested_perfume', 'user_from').order_by('-created_at')
    return render(request, 'perfumes/my_received_offers.html', {'received_offers': received_offers})

@login_required
def provide_delivery_info(request, trade_id):
    offer = get_object_or_404(TradeOffer, id=trade_id)

    if TradeDeliveryInfo.objects.filter(trade_offer=offer, submitted_by=request.user).exists():
        messages.info(request, "You have already submitted your delivery information for this trade.")
        return redirect('my_sent_offers' if offer.user_from == request.user else 'my_received_offers')

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        note = request.POST.get('note')

        TradeDeliveryInfo.objects.create(
            trade_offer=offer,
            submitted_by=request.user,
            full_name=full_name,
            address=address,
            phone=phone,
            note=note
        )
        messages.success(request, "Your delivery info has been saved.")
        return redirect('my_sent_offers' if offer.user_from == request.user else 'my_received_offers')

    return render(request, 'perfumes/provide_delivery_info.html', {
        'offer': offer
    })

@login_required
def trade_summary(request, trade_id):
    offer = get_object_or_404(TradeOffer, id=trade_id)

    # Проверка дали потребителят е замесен
    if request.user != offer.user_from and request.user != offer.user_to:
        return redirect('home')

    # Убедени сме, че и двете страни са попълнили информация
    if not hasattr(offer, 'delivery_info_from') or not hasattr(offer, 'delivery_info_to'):
        messages.error(request, "Delivery information is not yet complete.")
        return redirect('my_sent_offers')

    return render(request, 'perfumes/trade_summary.html', {
        'offer': offer,
        'from_info': offer.delivery_info_from,
        'to_info': offer.delivery_info_to,
    })

@login_required
@require_POST
def cancel_trade_offer(request, offer_id):
    offer = get_object_or_404(TradeOffer, id=offer_id, user_from=request.user, status='pending')
    offer.delete()
    messages.success(request, "Trade offer canceled.")
    return redirect('my_sent_offers')

@login_required
def trade_history(request):
    show_completed = request.GET.get('completed') == 'on'
    show_rejected = request.GET.get('rejected') == 'on'
    offers = TradeOffer.objects.filter(
        Q(user_from=request.user) | Q(user_to=request.user),
        status__in=['completed', 'rejected']
    )
    if show_completed and not show_rejected:
        offers = offers.filter(status='completed')
    elif show_rejected and not show_completed:
        offers = offers.filter(status='rejected')
    return render(request, 'perfumes/trade_history.html', {
        'offers': offers,
        'show_completed': show_completed,
        'show_rejected': show_rejected
    })

@login_required
@require_POST
def update_trade_status(request, offer_id):
    offer = get_object_or_404(TradeOffer, id=offer_id)

    if request.user != offer.user_from and request.user != offer.user_to:
        return redirect('home')

    new_status = request.POST.get('new_status')
    if new_status in ['in_transit', 'completed']:
        offer.status = new_status
        offer.save()
        messages.success(request, f"Trade marked as {new_status.replace('_', ' ').title()}.")

    return redirect('trade_summary', trade_id=offer.id)

def perfumes_for_trade(request):
    perfumes = Perfume.objects.filter(is_for_trade=True)
    return render(request, 'perfumes/perfume_list.html', {
        'perfumes': perfumes,
        'filter_for_trade': True
    })
