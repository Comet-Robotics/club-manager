from typing import TypedDict, NamedTuple
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from payments.models import Product, PurchasedProduct
from payments.utilities import CostWithFee, calculate_cost_with_square_fee
from .serializers import (
    UserSerializer,
    ProductSerializer,
    EventSerializer,
)
from rest_framework import viewsets, status, serializers
from .permissions import IsOwnerOrStaff, DeleteNotAllowed, ReadOnlyView

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from common.robot_combat_events import RCETeam, get_robot_combat_event, RCERobot
from django.db.models import Q
import json
import hashlib

# TODO: that fn + some other logic i'm building here should probably move to payments app
from payments.utilities import can_purchase_product
from payments.models import Payment

from events.models import Event


# Create your views here.
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwnerOrStaff, DeleteNotAllowed]
    serializer_class = UserSerializer
    queryset = User.objects.all()


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = ProductSerializer
    queryset = Product.objects.all()


# TODO: endpoints for payments
# TODO: signing flow
#
# TODO: page for us to check robots/people in
# TODO: frontend polish


class EventViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = EventSerializer
    queryset = Event.objects.all()


def get_csrf(request):
    response = JsonResponse({"detail": "CSRF cookie set"})
    response["X-CSRFToken"] = get_token(request)
    return response


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class LoginResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class LoginView(APIView):
    @extend_schema(
        request=LoginRequestSerializer,
        responses={200: LoginResponseSerializer, 401: LoginResponseSerializer},
        description="Login with username and password",
    )
    def post(self, request):
        data = request.data
        username = data.get("username")
        password = data.get("password")

        user = authenticate(username=username, password=password)

        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        return Response({"detail": "Successfully logged in."})


class LogoutResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class LogoutView(APIView):
    @extend_schema(
        responses={200: LogoutResponseSerializer, 400: LogoutResponseSerializer}, description="Logout current user"
    )
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "You're not logged in."}, status=status.HTTP_400_BAD_REQUEST)

        logout(request)
        return Response({"detail": "Successfully logged out."})


class SessionResponseSerializer(serializers.Serializer):
    isAuthenticated = serializers.BooleanField()


class SessionView(APIView):
    @extend_schema(responses={200: SessionResponseSerializer}, description="Check if user is authenticated")
    @ensure_csrf_cookie
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"isAuthenticated": False})

        return Response({"isAuthenticated": True})


class WhoAmIView(APIView):
    @extend_schema(
        responses={
            403: {
                "type": "object",
                "properties": {"isAuthenticated": {"type": "boolean", "enum": [False]}},
                "required": ["isAuthenticated"],
            },
            200: {
                "type": "object",
                "properties": {
                    "isAuthenticated": {"type": "boolean", "enum": [True]},
                    "username": {"type": "string"},
                    "id": {"type": "integer"},
                },
                "required": ["isAuthenticated", "username", "id"],
            },
        },
        description="Get current user information",
    )
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"isAuthenticated": False}, status=status.HTTP_403_FORBIDDEN)

        return Response({"username": request.user.username, "id": request.user.id, "isAuthenticated": True})


class CartItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()


class CartItem(NamedTuple):
    product_id: int
    quantity: int


class CartSerializer(serializers.Serializer):
    cart = CartItemSerializer(many=True)
    hash = serializers.CharField()
    subtotal_cents = serializers.IntegerField()
    total_cents_with_fee = serializers.IntegerField()


class Cart(TypedDict):
    cart: list[CartItem]
    hash: str
    subtotal_cents: int
    process_fee_cents: int
    total_cents_with_fee: int


def build_cart(cart: list[CartItem], user: User, method: Payment.Method) -> tuple[Cart, dict[int, Product]]:
    """
    Creates a Cart from a list of CartItems.

    The goal of the cart key is to ensure that what the user sees in the cart preview is the same as what they end up paying for. It is worth checking this because:
    - Square fee is calculated server-side and then reported to the user, so we want to make sure that the user has seen their full total cost with Square fees before they pay.
    - Product price may be edited between the time the user views the cart and the time they pay for it, which would be a problem since we just calculate cost based on the quantity of each product in the cart.
    """

    products_list = Product.objects.filter(pk__in=[item.product_id for item in cart]).all()
    products_map = {product.id: product for product in products_list}

    subtotal = 0

    for item in cart:
        product = products_map[item.product_id]
        assert can_purchase_product(product, user) is None
        subtotal += item.quantity * product.amount_cents

    using_square = method == Payment.Method.square_api
    final_cost_calculation = (
        calculate_cost_with_square_fee(subtotal)
        if using_square
        else CostWithFee(product_amount_cents=subtotal, square_fee_cents=0, total_payment_amount_cents=subtotal)
    )

    cart_key_contents = f"{json.dumps(cart)}|{final_cost_calculation['total_payment_amount_cents']}"
    cart_key = hashlib.sha256(cart_key_contents.encode("utf-8")).hexdigest()

    return {
        "cart": cart,
        "hash": cart_key,
        "subtotal_cents": final_cost_calculation["product_amount_cents"],
        "process_fee_cents": final_cost_calculation["square_fee_cents"],
        "total_cents_with_fee": final_cost_calculation["total_payment_amount_cents"],
    }, products_map


class PaymentChoiceSerializer(serializers.Serializer):
    payment_choice = serializers.ChoiceField(choices=Payment.Method.choices)


# TODO: in both of these views, build_cart could throw so we need to handle those errors. also just finish the impl


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CartSerializer}, description="Generates subtotal and total cost for a user's cart")
    def post(self, request):
        user = request.user

        if not user.is_authenticated:
            return Response({"detail": "You're not logged in."}, status=status.HTTP_401_UNAUTHORIZED)

        # TODO: im 99% sure there is a way to make DRF do this request body validation for us in a cleaner way
        payment_method_serializer = PaymentChoiceSerializer(data=request.data.get("payment_choice"))
        if not payment_method_serializer.is_valid():
            return Response(payment_method_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        cart_serializer = CartItemSerializer(data=request.data.get("cart", []), many=True)
        if not cart_serializer.is_valid():
            return Response(cart_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        cart_items_as_tuples = [
            CartItem(product_id=item["product_id"], quantity=item["quantity"])
            for item in cart_serializer.validated_data
        ]
        cart, products = build_cart(
            cart_items_as_tuples, user, Payment.Method(payment_method_serializer.validated_data["payment_choice"])
        )

        response_serializer = CartSerializer(data=cart)

        if not response_serializer.is_valid():
            return Response(response_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(response_serializer.data)


class PayView(APIView):
    # TODO: finish impl lol
    permission_classes = [IsAuthenticated]

    # @extend_schema(
    #   responses={
    #     200: PaymentSerializer
    #   },
    #   description='Allows a user to pay for their cart'
    # )
    def post(self, request):
        user = request.user

        if not user.is_authenticated:
            return Response({"detail": "You're not logged in."}, status=status.HTTP_401_UNAUTHORIZED)

        # TODO: im 99% sure there is a way to make DRF do request body validation for us
        payment_method_serializer = PaymentChoiceSerializer(data=request.data.get("payment_choice"))
        if not payment_method_serializer.is_valid():
            return Response(payment_method_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        cart_serializer = CartSerializer(data=request.data.get("cart"))
        if not cart_serializer.is_valid():
            return Response(cart_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        provided_cart = cart_serializer.validated_data["cart"]
        cart_items_as_tuples = [
            CartItem(product_id=item["product_id"], quantity=item["quantity"]) for item in provided_cart
        ]

        method = Payment.Method(payment_method_serializer.validated_data["payment_choice"])
        control_cart, product_map = build_cart(cart_items_as_tuples, user, method)
        assert control_cart["hash"] == cart_serializer.validated_data["hash"]

        with transaction.atomic():
            payment = Payment(method=method, user=user, amount_cents=control_cart["total_cents_with_fee"])
            payment.save()
            PurchasedProduct.objects.bulk_create(
                [
                    PurchasedProduct(product=product_map[product_id], quantity=quantity, payment=payment)
                    for product_id, quantity in cart_items_as_tuples
                ]
            )

        create_payment_response = client.payments.create_payment(
            body={
                "source_id": token,
                "idempotency_key": idempotency_key,
                "amount_money": {
                    "amount": payment.amount_cents,
                    "currency": ACCOUNT_CURRENCY,
                },
                "reference_id": str(payment.pk),
                "note": str(payment),
            }
        )

        payment.metadata = {"square_response_body": create_payment_response.body}
        payment.save()

        if create_payment_response.is_success():
            payment.completed_at = timezone.now()
            payment.save()
            # TODO: some success response
            return
        elif create_payment_response.is_error():
            # TODO: some error response
            return

        return Response(cart_serializer.validated_data, status=status.HTTP_200_OK)
