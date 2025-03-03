from typing import TypedDict, NamedTuple
from discord.components import ActionRow
from django.contrib.auth.models import User
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from payments.models import Product, PurchasedProduct
from payments.views import CostWithFee, calculate_cost_with_square_fee
from .serializers import (
    UserSerializer,
    ProductSerializer,
    CombatTeamSerializer,
    CombatRobotSerializer,
    CombatEventSerializer,
    EventSerializer,
    WaiverSerializer,
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
from common.robot_combat_events import (
    RCETeam,
    get_robot_combat_event,
    RCERobot,
)
from django.db.models import Q
import json
import hashlib

# TODO: that fn + some other logic i'm building here should probably move to payments app
from payments.views import can_purchase_product
from payments.models import Payment

from events.models import (
    CombatEventRegistration,
    Event,
    CombatTeam,
    CombatRobot,
    CombatEvent,
    Waiver,
)


# Create your views here.
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwnerOrStaff, DeleteNotAllowed]
    serializer_class = UserSerializer
    queryset = User.objects.all()


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = ProductSerializer
    queryset = Product.objects.all()


class CombatTeamViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = CombatTeamSerializer
    queryset = CombatTeam.objects.all()

    # TODO: only one user should be able to add themselves as a manager. after that, that manager or an admin has to add any subsequent managers
    @extend_schema(
        responses={
            200: {"type": "enum", "enum": [""]},
            400: {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "enum": ["You are already a manager for this team."],
                    }
                },
                "required": ["detail"],
            },
        },
        description="Add a manager to a team",
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        url_path="add-manager",
    )
    def add_manager(self, request, pk):
        team = self.get_object()
        manager = request.user

        if team.managers.filter(pk=manager.pk).exists():
            return Response(
                {"detail": "You are already a manager for this team."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        team.managers.add(manager)
        team.save()

        return Response(status=status.HTTP_200_OK)


class CombatRobotViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = CombatRobotSerializer
    queryset = CombatRobot.objects.all()


class CombatEventViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = CombatEventSerializer
    queryset = CombatEvent.objects.all()

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="my-waivers",
    )
    def get_my_waivers(self, request, pk):
        user = request.user

        if not user.is_authenticated:
            return Response(
                {"detail": "You're not logged in."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user.userprofile.date_of_birth is None:
            return Response(
                {"detail": "You have no DOB on file. DOB required to determine applicable waivers"},
                status=status.HTTP_428_PRECONDITION_REQUIRED,
            )

        user_is_minor = user.userprofile.is_minor()

        combat_event = self.get_object()

        if not combat_event:
            return Response(
                {"detail": "CombatEvent not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        waivers = Waiver.objects.filter(user=user, combat_event=combat_event)
        # TODO: revisit the mofel

        serializer = WaiverSerializer(waivers, many=True, context={"request": request})
        return Response(serializer.data)

    def _upsert_teams_with_rce_data(self, rce_teams: list[RCETeam]) -> dict[str, CombatTeam]:
        """
        Upserts the given list of teams from Robot Combat Events into the database. Returns a dictionary mapping the Robot Combat Events team IDs to the upserted teams.

        Parameters:
        - rce_teams (list[RCETeam]): The list of teams to upsert.
        """
        combat_teams = [CombatTeam(name=team.name, robot_combat_events_team_id=team.rce_team_id) for team in rce_teams]
        CombatTeam.objects.bulk_create(
            combat_teams,
            update_conflicts=True,
            unique_fields=["robot_combat_events_team_id"],
            update_fields=["name"],
        )

        upserted_teams = {
            team.robot_combat_events_team_id: team
            for team in CombatTeam.objects.filter(
                robot_combat_events_team_id__in=[team.rce_team_id for team in rce_teams]
            )
        }
        return upserted_teams

    def _upsert_robots_with_rce_data(
        self, rce_robots: list[RCERobot], combat_teams: dict[str, CombatTeam]
    ) -> list[CombatRobot]:
        """
        Upserts the given list of robots from Robot Combat Events into the database. Returns a list of CombatRobot objects that were created or updated.

        Parameters:
        - rce_robots: A list of RCERobot objects to upsert.
        - combat_teams: A dictionary mapping RCE team IDs to CombatTeam objects.
        """

        RCE_WEIGHT_CLASS_LABEL_TO_COMBAT_ROBOT_WEIGHT_CLASS = {
            "Plastic Antweights": CombatRobot.WeightClass.PLANT,
            "Antweights": CombatRobot.WeightClass.ANT,
            "Beetleweights": CombatRobot.WeightClass.BEETLE,
        }

        all_robots = [
            CombatRobot(
                name=rce_robot.name,
                weight_class=RCE_WEIGHT_CLASS_LABEL_TO_COMBAT_ROBOT_WEIGHT_CLASS[rce_robot.weight_class],
                robot_combat_events_robot_id=rce_robot.rce_resource_id,
                combat_team=combat_teams[rce_robot.rce_team_id],
                image_url=rce_robot.img_url,
            )
            for rce_robot in rce_robots
        ]
        CombatRobot.objects.bulk_create(
            all_robots,
            update_conflicts=True,
            unique_fields=["robot_combat_events_robot_id"],
            update_fields=["name", "weight_class", "combat_team", "image_url"],
        )
        return all_robots

    def _associate_robots_with_event(
        self,
        combat_robots: list[CombatRobot],
        combat_event: CombatEvent,
        rce_robots: list[RCERobot],
    ):
        RCE_STATUS_LABELS_TO_REG_STATUS = {
            "Competing": CombatEventRegistration.Status.COMPETING,
            "On Waitlist": CombatEventRegistration.Status.ON_WAITLIST,
        }

        rce_robot_id_to_combat_robot_map: dict[str, CombatRobot] = {
            robot.robot_combat_events_robot_id: robot for robot in combat_robots
        }

        reg_objs = []
        for rce_robot in rce_robots:
            if rce_robot.rce_resource_id in rce_robot_id_to_combat_robot_map:
                reg_objs.append(
                    CombatEventRegistration(
                        combat_event=combat_event,
                        combat_robot=rce_robot_id_to_combat_robot_map[rce_robot.rce_resource_id],
                        status=RCE_STATUS_LABELS_TO_REG_STATUS[rce_robot.status],
                    )
                )
        CombatEventRegistration.objects.bulk_create(
            reg_objs,
            update_conflicts=True,
            unique_fields=["combat_event", "combat_robot"],
            update_fields=["status"],
        )

    @extend_schema(
        responses={
            200: {
                "type": "enum",
                "enum": [""],
            },
            404: {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "enum": ["CombatEvent not found."],
                    }
                },
                "required": ["detail"],
            },
        },
        description="Synchronize a combat event with RCE",
    )
    # TODO: this shouldn't be a GET btu i need to figure out how to make it not require a request body
    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsAdminUser],
        url_path="sync-with-rce",
    )
    def sync_event_with_robot_combat_events(self, request, pk):
        combat_event = self.get_object()

        if not combat_event:
            return Response(
                {"detail": "CombatEvent not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        rce_event = get_robot_combat_event(combat_event.robot_combat_events_event_id)

        upserted_teams = self._upsert_teams_with_rce_data(rce_event.teams)
        upserted_robots = self._upsert_robots_with_rce_data(rce_event.robots, upserted_teams)
        self._associate_robots_with_event(upserted_robots, combat_event, rce_event.robots)

        # purging registrations for robots not returned by RCE
        CombatEventRegistration.objects.filter(combat_event=combat_event).exclude(
            combat_robot__in=upserted_robots
        ).delete()

        return Response("", status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            200: CombatTeamSerializer(many=True),
        },
        description="Get teams in a combat event",
    )
    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="teams",
    )
    def get_teams_in_event(self, request, pk):
        combat_event = self.get_object()

        if not combat_event:
            return Response(
                {"detail": "CombatEvent not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        registrations = CombatEventRegistration.objects.filter(combat_event=combat_event)
        team_ids = registrations.values("combat_robot__combat_team").distinct()
        teams = CombatTeam.objects.filter(pk__in=team_ids)

        serializer = CombatTeamSerializer(teams, many=True, context={"request": request})

        return Response(serializer.data)


# TODO: action for user to become a robot owner. may need some refactoring, since
# I want to associate registration to an owner instead of owners to robots.
# this way, Robot X can go to competion A with persons 1 and 2, but at comp B
# they can compete with persons 2 and 3, a different set of owners.
#
# TODO: endpoints for payments
# TODO: signing flow
#
# TODO: page for us to check robots/people in
# TODO: frontend polish
# QUESTION: what is the contingency plan for when a person hasn't filled a waiver online and/or paid robot fees online?
#


class EventViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = EventSerializer
    queryset = Event.objects.all()


class WaiverViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = WaiverSerializer
    queryset = Waiver.objects.all()


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
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response({"detail": "Successfully logged in."})


class LogoutResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class LogoutView(APIView):
    @extend_schema(
        responses={
            200: LogoutResponseSerializer,
            400: LogoutResponseSerializer,
        },
        description="Logout current user",
    )
    def post(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "You're not logged in."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logout(request)
        return Response({"detail": "Successfully logged out."})


class SessionResponseSerializer(serializers.Serializer):
    isAuthenticated = serializers.BooleanField()


class SessionView(APIView):
    @extend_schema(
        responses={200: SessionResponseSerializer},
        description="Check if user is authenticated",
    )
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

        return Response(
            {
                "username": request.user.username,
                "id": request.user.id,
                "isAuthenticated": True,
            }
        )


class RobotsInTeamView(APIView):
    @extend_schema(
        responses={
            200: CombatRobotSerializer(many=True),
        },
        description="Get robots belonging to a team",
    )
    def get(self, request, combatteam_id):
        team = CombatTeam.objects.get(pk=combatteam_id)

        if not team:
            return Response({"detail": "Team not found."}, status=status.HTTP_404_NOT_FOUND)

        robots = CombatRobot.objects.filter(combat_team=team)
        serializer = CombatRobotSerializer(robots, many=True, context={"request": request})
        return Response(serializer.data)


# view to get teams in event
class RobotsInEventView(APIView):
    @extend_schema(
        responses={
            200: CombatRobotSerializer(many=True),
            403: CombatRobotSerializer(many=True),
        },
        description="Get teams in a combat event",
    )
    def get(self, request, combatevent_id):
        combat_event = CombatEvent.objects.get(pk=combatevent_id)

        if not combat_event:
            return Response(
                {"detail": "CombatEvent not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        robots = CombatRobot.objects.filter(combat_events__id=combatevent_id)
        serializer = CombatRobotSerializer(robots, many=True, context={"request": request})

        return Response(serializer.data)


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
    """Create a Cart from a list of CartItems.

    The goal of the cart key is to ensure that what the user sees in the cart preview is the same
    as what they end up paying for. It is worth checking this because:
    - Square fee is calculated server-side and then reported to the user, so we want to make sure
    that the user has seen their full total cost with Square fees before they pay.
    - Product price may be edited between the time the user views the cart and the time they pay
    for it, which would be a problem since we just calculate cost based on the quantity of each
    product in the cart.
    """
    products_list = Product.objects.get(pk__in=[item.product_id for item in cart])
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
        else CostWithFee(
            product_amount_cents=subtotal,
            square_fee_cents=0,
            total_payment_amount_cents=subtotal,
        )
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

    @extend_schema(
        responses={200: CartSerializer},
        description="Generates subtotal and total cost for a user's cart",
    )
    def post(self, request):
        user = request.user

        if not user.is_authenticated:
            return Response(
                {"detail": "You're not logged in."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # TODO: im 99% sure there is a way to make DRF do this request body validation for us in a cleaner way
        payment_method_serializer = PaymentChoiceSerializer(data=request.data.get("payment_choice"))
        if not payment_method_serializer.is_valid():
            return Response(
                payment_method_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_serializer = CartItemSerializer(data=request.data.get("cart", []), many=True)
        if not cart_serializer.is_valid():
            return Response(cart_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        cart_items_as_tuples = [
            CartItem(product_id=item["product_id"], quantity=item["quantity"])
            for item in cart_serializer.validated_data
        ]
        cart, products = build_cart(
            cart_items_as_tuples,
            user,
            Payment.Method(payment_method_serializer.validated_data["payment_choice"]),
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
            return Response(
                {"detail": "You're not logged in."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # TODO: im 99% sure there is a way to make DRF do request body validation for us
        payment_method_serializer = PaymentChoiceSerializer(data=request.data.get("payment_choice"))
        if not payment_method_serializer.is_valid():
            return Response(
                payment_method_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

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
            payment = Payment(
                method=method,
                user=user,
                amount_cents=control_cart["total_cents_with_fee"],
            )
            payment.save()
            PurchasedProduct.objects.bulk_create(
                [
                    PurchasedProduct(
                        product=product_map[product_id],
                        quantity=quantity,
                        payment=payment,
                    )
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
