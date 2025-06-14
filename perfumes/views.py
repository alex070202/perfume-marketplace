from collections import defaultdict, OrderedDict

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Avg, Q
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.formats import sanitize_separators
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import CustomUserCreationForm
from .models import (
    Perfume, PerfumeImage, Cart, CartItem, WishlistItem,
    Order, OrderItem, ORDER_STATUS_CHOICES,
    TradeOffer, TradeDeliveryInfo,
    Review, UserReview, UserReport
)


def home(request):
    latest_perfumes = Perfume.objects.filter(is_active=True).order_by('-id')[:6]
    return render(request, 'perfumes/home.html', {'latest_perfumes': latest_perfumes})

def perfume_list(request):
    query = request.GET.get('q', '')
    perfumes = Perfume.objects.filter(is_active=True)

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
        raw_price = request.POST['price']
        price = sanitize_separators(raw_price) 
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

        messages.success(request, _('Perfume added successfully!'))
        return redirect('perfume_list')

    return render(request, 'perfumes/add_perfume.html')

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request,_('Registration successful!'))
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'perfumes/register.html', {'form': form})

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request,_("You have been logged out."))
        return redirect('home')
    else:
        return redirect('home')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None

        if user and user.check_password(password):
            if user.is_active:
                login(request, user)
                return redirect('home')
            else:
                return render(request, 'users/banned.html')
        else:
            messages.error(request,_("Invalid username or password."))
            form = AuthenticationForm(request)
            return render(request, 'registration/login.html', {'form': form})

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
        messages.success(request,_('Perfume deleted successfully!'))
        return redirect('my_perfumes')
    return render(request, 'perfumes/confirm_delete.html', {'perfume': perfume})

@login_required
def edit_perfume(request, perfume_id):
    perfume = get_object_or_404(Perfume, id=perfume_id, owner=request.user)

    if request.method == 'POST':
        perfume.name = request.POST['name']
        perfume.brand = request.POST['brand']
        perfume.description = request.POST['description']
        raw_price = request.POST['price']
        perfume.price = sanitize_separators(raw_price)
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
        messages.success(request,_('Perfume updated successfully!'))
        return redirect('my_perfumes')

    return render(request, 'perfumes/edit_perfume.html', {'perfume': perfume})


@login_required(login_url='/login/')
def add_to_cart(request, perfume_id):
    perfume = get_object_or_404(Perfume, id=perfume_id)
    quantity = int(request.POST.get('quantity', 1))

    cart, created = Cart.objects.get_or_create(user=request.user)

    cart_item = CartItem.objects.filter(cart=cart, perfume=perfume).first()
    current_quantity = cart_item.quantity if cart_item else 0
    requested_total = current_quantity + quantity

    if requested_total > perfume.stock:
        error_message = _("Only %(stock)s units of %(name)s are available in stock.") % {
            'stock': perfume.stock,
            'name': perfume.name,
        }

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

    success_message = _("%(name)s added to cart.") % {'name': perfume.name}

    # AJAX response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'message': success_message})

    messages.success(request, success_message)
    return redirect('perfume_detail', perfume_id=perfume.id)

@login_required
def cart_detail(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.cartitem_set.all()
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
            messages.error(request, _("Not enough stock for '%(name)s'. Only %(stock)s left.") % {
                'name': item.perfume.name,
                'stock': item.perfume.stock
            })
            has_error = True
        elif quantity < 1:
            messages.error(request, _("Invalid quantity for '%(name)s'.") % {
                'name': item.perfume.name
            })
            has_error = True
        else:
            item.quantity = quantity
            item.save()

    if has_error:
        return redirect('cart_detail')

    messages.success(request, _('Cart updated successfully!'))
    return redirect('cart_detail')

def perfumes_by_brand(request, brand_name):
    perfumes = Perfume.objects.filter(brand__iexact=brand_name, is_active=True)
    return render(request, 'perfumes/perfume_list.html', {
        'perfumes': perfumes,
        'filter_brand': brand_name
    })

@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request,_('Item removed from your cart!'))
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
                messages.error(request, _('Not enough stock for "%(name)s". Only %(available)s available.') % {
                    'name': name,
                    'available': available
                })
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
    # Връщаме поръчките за визуализация, подредени от най-нови към най-стари
    orders = request.user.orders.prefetch_related('items__perfume', 'items__seller').order_by('-created_at')

    # Взимаме всички поръчки по реда на създаване за номерация
    chronological_orders = request.user.orders.order_by('created_at').values_list('id', flat=True)
    local_number_map = {order_id: idx + 1 for idx, order_id in enumerate(chronological_orders)}

    # Присвояваме локален номер според реда на създаване
    for order in orders:
        order.local_number = local_number_map.get(order.id, '-')

    return render(request, 'perfumes/my_orders.html', {'orders': orders})


@login_required
def sales_dashboard(request):
    # всички артикули на продавача
    items = OrderItem.objects.filter(seller=request.user)\
        .select_related('order', 'perfume')\
        .order_by('-order__created_at')  # най-новите първи в таблицата

   
    unique_orders = OrderItem.objects.filter(seller=request.user)\
        .select_related('order')\
        .order_by('order__created_at')\
        .values_list('order_id', flat=True)\
        .distinct()

    order_number_map = {order_id: idx + 1 for idx, order_id in enumerate(unique_orders)}

    for item in items:
        item.local_order_number = order_number_map.get(item.order.id, '-')

    return render(request, 'perfumes/sales_dashboard.html', {'items': items})



@login_required
def update_order_status(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, seller=request.user)

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(ORDER_STATUS_CHOICES):
            item.order.status = status
            item.order.save()
            messages.success(request,_('Order status updated.'))

    return redirect('sales_dashboard')

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # проверка дали потребителят има достъп
    if request.user != order.buyer and not order.items.filter(seller=request.user).exists():
        return HttpResponseForbidden(_("You don't have permission to view this order."))

    items = order.items.all()

    if request.method == 'POST':
        status = request.POST.get('status', '').strip()
        if status in dict(ORDER_STATUS_CHOICES):
            if status != order.status:
                order.status = status
                order.save()
                messages.success(request, _('Order status updated.'))
            else:
                messages.info(request, _('Status was not changed.'))
        return redirect('order_detail', order_id=order_id)

    order_total = sum(i.price * i.quantity for i in items)

    return render(request, 'perfumes/order_detail.html', {
    'order': order,
    'items': items,
    'status_choices': ORDER_STATUS_CHOICES,
    'order_total': order_total
    })


def perfume_detail(request, perfume_id):
    perfume = get_object_or_404(Perfume, id=perfume_id)
    reviews = perfume.reviews.all()
    additional_images = perfume.additional_images.all()

    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    review_count = reviews.count()
    filled_stars = range(int(round(average_rating)))
    empty_stars = range(5 - int(round(average_rating)))


    seller_reviews = perfume.owner.received_user_reviews.all()
    seller_avg_rating = seller_reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    seller_review_count = seller_reviews.count()

    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = perfume.wishlistitem_set.filter(user=request.user).exists()

    return render(request, 'perfumes/perfume_detail.html', {
        'perfume': perfume,
        'additional_images': additional_images,
        'reviews': reviews,
        'average_rating': round(average_rating, 1),  
        'avg_rating': round(average_rating, 1),
        'review_count': review_count,
        'filled_stars': filled_stars,
        'empty_stars': empty_stars,
        'in_wishlist': in_wishlist,
        'seller_reviews': seller_reviews,
        'seller_avg_rating': round(seller_avg_rating, 1),  
        'seller_review_count': seller_review_count,
    })

@login_required
def remove_from_wishlist(request, perfume_id):
    perfume = get_object_or_404(Perfume, id=perfume_id)
    WishlistItem.objects.filter(user=request.user, perfume=perfume).delete()
    messages.success(request, _('%(name)s was removed from your wishlist.') % {
        'name': perfume.name
    })
    return redirect('wishlist')

@login_required
def add_review(request, perfume_id):
    perfume = get_object_or_404(Perfume, id=perfume_id)
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 5))
        comment = request.POST.get('comment')
        Review.objects.create(perfume=perfume, user=request.user, rating=rating, comment=comment)
        messages.success(request,_('Review submitted successfully!'))
    return redirect('perfume_detail', perfume_id=perfume.id)

def about_us(request):
    return render(request, 'perfumes/about_us.html')

def perfume_category(request, category):
    perfumes = Perfume.objects.filter(category=category, is_active=True)
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

    user_perfumes = Perfume.objects.filter(owner=request.user, is_for_trade=True, is_active=True)
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
        messages.info(request,_("You have already submitted your delivery information for this trade."))
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
        messages.success(request,_("Your delivery info has been saved."))
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

    if not hasattr(offer, 'delivery_info_from') or not hasattr(offer, 'delivery_info_to'):
        messages.error(request,_("Delivery information is not yet complete."))
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
    messages.success(request,_("Trade offer canceled."))
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
    perfumes = Perfume.objects.filter(is_for_trade=True, is_active=True)
    return render(request, 'perfumes/perfume_list.html', {
        'perfumes': perfumes,
        'filter_for_trade': True
    })

@staff_member_required
def reports_dashboard(request):
    reports = UserReport.objects.select_related('reported_user', 'reporter').order_by('-created_at')
    return render(request, 'admin/reports_dashboard.html', {'reports': reports})


@login_required
def ban_user(request, user_id):
    if not request.user.is_staff:
        return HttpResponseForbidden("You are not allowed to perform this action.")

    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()

    Perfume.objects.filter(owner=user).update(is_active=False)

    messages.success(request, _('User %(username)s has been banned and their perfumes have been hidden.') % {
        'username': user.username
    })
    return redirect('admin_dashboard')

@login_required
def user_profile(request, user_id):
    seller = get_object_or_404(User, id=user_id)
    perfumes = Perfume.objects.filter(owner=seller, is_active=True)
    reviews = seller.received_user_reviews.select_related('reviewer')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    return render(request, 'users/profile.html', {
        'seller': seller,
        'perfumes': perfumes,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1)
    })

@login_required
def leave_user_review(request, user_id):
    reviewed_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment')
        UserReview.objects.update_or_create(
            reviewer=request.user,
            reviewed_user=reviewed_user,
            defaults={'rating': rating, 'comment': comment}
        )
        messages.success(request,_('Your review has been submitted.'))
        return redirect('user_profile', user_id=user_id)
    return render(request, 'users/leave_review.html', {'reviewed_user': reviewed_user})

@login_required
def report_user(request, user_id):
    reported_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        reason = request.POST.get('reason')
        UserReport.objects.create(
            reported_user=reported_user,
            reporter=request.user,
            reason=reason
        )
        messages.success(request,_('User has been reported.'))
        return redirect('user_profile', user_id=user_id)
    return render(request, 'users/report_user.html', {'reported_user': reported_user})
@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    
    UserReport.objects.filter(is_reviewed=False).update(is_reviewed=True)
    
    all_reports = UserReport.objects.select_related('reported_user', 'reporter').order_by('-created_at')
    grouped_reports = defaultdict(list)

    for report in all_reports:
        grouped_reports[report.reported_user].append(report)

    grouped_reports = dict(sorted(grouped_reports.items(), key=lambda x: len(x[1]), reverse=True))

    banned_users = User.objects.filter(is_active=False)

    return render(request, 'admin/dashboard.html', {
        'grouped_reports': grouped_reports,
        'banned_users': banned_users
    })

@login_required
def unban_user(request, user_id):
    if not request.user.is_staff:
        return HttpResponseForbidden("You are not allowed to perform this action.")

    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()

    Perfume.objects.filter(owner=user).update(is_active=True)
    
    messages.success(request, _('User %(username)s has been unbanned and their perfumes are now visible again.') % {
        'username': user.username
    })
    return redirect('admin_dashboard')