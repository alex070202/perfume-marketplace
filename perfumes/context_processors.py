from .models import OrderItem, TradeOffer, TradeDeliveryInfo
from django.db.models import Q

def global_notification_counts(request):
    context = {}

    if request.user.is_authenticated:
        # Нови поръчки
        context['new_orders_count'] = OrderItem.objects.filter(
            seller=request.user,
            order__status='pending'
        ).count()

        # Нови размени (получени)
        context['new_received_offers_count'] = TradeOffer.objects.filter(
            user_to=request.user,
            status='pending'
        ).count()

        # Приети размени, чакащи адрес от текущия потребител
        # Приети размени, чакащи адрес от текущия потребител
        context['awaiting_address_info_count'] = TradeOffer.objects.filter(
            status='accepted'
        ).exclude(
            delivery_infos__submitted_by=request.user
        ).filter(
            Q(user_from=request.user) | Q(user_to=request.user)
        ).count()


        context['updated_sent_offers_count'] = TradeOffer.objects.filter(
            user_from=request.user,
            is_seen_by_sender=False
        ).exclude(status='pending').count()


    return context
