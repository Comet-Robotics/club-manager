from django.db.models import Sum
from django.contrib.auth.models import User
from payments.models import Product, PurchasedProduct
from math import ceil
from typing import TypedDict


def can_purchase_product(product: Product, user: User) -> str | None:
    """
    Returns None if product can be purchased, otherwise returns a string messsage explaining why it can't be purchased
    """
    if product.max_purchases_per_user == -1:
        # Unlimited purchases
        return None
    elif product.max_purchases_per_user == 0:
        # No purchases allowed
        return "Payments are currently disabled for this object."
    else:
        # Purchases allowed, but need to check if user has reached max purchases

        # TODO: need to test this

        total_purchased = (
            PurchasedProduct.objects.filter(product=product, payment__user=user, payment__is_successful=True).aggregate(
                total_quantity=Sum("quantity")
            )["total_quantity"]
            or 0
        )

        allowed = total_purchased < product.max_purchases_per_user

        if allowed:
            return None
        else:
            return "You have reached the maximum number of purchases for this object."


class CostWithFee(TypedDict):
    product_amount_cents: int
    square_fee_cents: int
    total_payment_amount_cents: int


def calculate_cost_with_square_fee(amount_cents: int) -> CostWithFee:
    """
    Calculate the total amount in cents required to cover Square's transaction fees, ensuring the specified `amount_cents` is earned as net revenue without losses to Square fees.

    This function takes an input amount in cents and returns the total amount in cents needed to account for Square's fees. Square charges a fee of 30 cents plus 2.9% of the transaction amount. To ensure the full desired amount is received as revenue, the calculation involves adjusting the input amount using the formula: `(desired_amount + fixed_fee) / (1 - variable_fee)`. This approach accounts for the fixed 30-cent fee and the 2.9% variable fee.

    For more details, refer to [Square's pricing documentation](https://developer.squareup.com/docs/payments-pricing#online-and-in-app-payments).
    """

    total_payment_amount_cents = ceil((amount_cents + 30) / (1 - 0.029))
    square_fee_cents = total_payment_amount_cents - amount_cents

    return CostWithFee(
        product_amount_cents=amount_cents,
        square_fee_cents=square_fee_cents,
        total_payment_amount_cents=total_payment_amount_cents,
    )
