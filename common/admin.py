class SearchFields:
    USER = ["user__username", "user__first_name", "user__last_name"]
    EVENT = ["event__event_name", "event__id"]
    PRODUCT = ["product__name"]
    PURCHASED_PRODUCT = ["purchased_products__product__name"]