from django.shortcuts import render, redirect, get_object_or_404
from .models import Perfume, PerfumeImage, Cart, CartItem
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Order, OrderItem, ORDER_STATUS_CHOICES
from .models import Review
from django.db.models import Avg
from django.http import JsonResponse
from .models import WishlistItem
from django.db.models import Q

def home(request):
    latest_perfumes = Perfume.objects.order_by('-id')[:6]  # последните 6
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
        stock = request.POST['stock']  # <-- ново
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
            stock=stock,  # <-- добавено
            is_for_trade=is_for_trade,
            owner=request.user,
            image=main_image
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
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'perfumes/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Logged in successfully!')
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
    else:
        form = AuthenticationForm()
    return render(request, 'perfumes/login.html', {'form': form})

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'Logged out successfully!')
        return redirect('home')

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
    items = cart.cartitem_set.all()
    total = sum(item.perfume.price * item.quantity for item in items)
    return render(request,'perfumes/cart_detail.html', {
        'cart_items': items,
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
    items = cart.cartitem_set.select_related('perfume').all()
    total = sum(item.perfume.price * item.quantity for item in items)

    # Проверка за надвишена наличност
    overstocked_items = []
    for item in items:
        if item.quantity > item.perfume.stock:
            overstocked_items.append((item.perfume.name, item.perfume.stock))

    if overstocked_items:
        for name, available in overstocked_items:
            messages.error(request, f'Not enough stock for "{name}". Only {available} available.')
        return redirect('cart_detail')

    # Ако всичко е наред, продължаваме с поръчката
    if request.method == 'POST':
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

    return render(request, 'perfumes/checkout.html', {
        'cart_items': items,
        'total': total
    })


@login_required
def my_orders(request):
    orders = request.user.orders.prefetch_related('items__perfume', 'items__seller')
    return render(request, 'perfumes/my_orders.html', {'orders': orders})

@login_required
def sales_dashboard(request):
    items = OrderItem.objects.filter(seller=request.user).select_related('order', 'perfume')
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
        in_wishlist = WishlistItem.objects.filter(user=request.user, perfume=perfume).exists()

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


