from django.contrib.auth.models import User
from payments.models import Product
from .serializers import UserSerializer, ProductSerializer, CombatTeamSerializer, CombatRobotSerializer, CombatEventSerializer, EventSerializer, WaiverSerializer
from rest_framework import viewsets, status, serializers
from .permissions import IsOwnerOrStaff, DeleteNotAllowed, ReadOnlyView

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from events.models import Event, CombatTeam, CombatRobot, CombatEvent, Waiver

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

class CombatRobotViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = CombatRobotSerializer
    queryset = CombatRobot.objects.all()

class CombatEventViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = CombatEventSerializer
    queryset = CombatEvent.objects.all()

class EventViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = EventSerializer
    queryset = Event.objects.all()

class WaiverViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = WaiverSerializer
    queryset = Waiver.objects.all()

def get_csrf(request):
    response = JsonResponse({'detail': 'CSRF cookie set'})
    response['X-CSRFToken'] = get_token(request)
    return response


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class LoginResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    

class LoginView(APIView):
    @extend_schema(
        request=LoginRequestSerializer,
        responses={
            200: LoginResponseSerializer,
            401: LoginResponseSerializer
        },
        description='Login with username and password'
    )
    def post(self, request):
        data = request.data
        username = data.get('username')
        password = data.get('password')

        user = authenticate(username=username, password=password)

        if user is None:
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        return Response({'detail': 'Successfully logged in.'})



class LogoutResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class LogoutView(APIView):
    @extend_schema(
        responses={
            200: LogoutResponseSerializer,
            400: LogoutResponseSerializer
        },
        description='Logout current user'
    )
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'detail': 'You\'re not logged in.'}, status=status.HTTP_400_BAD_REQUEST)

        logout(request)
        return Response({'detail': 'Successfully logged out.'})


class SessionResponseSerializer(serializers.Serializer):
    isAuthenticated = serializers.BooleanField()
    
    
class SessionView(APIView):
    @extend_schema(
        responses={200: SessionResponseSerializer},
        description='Check if user is authenticated'
    )
    @ensure_csrf_cookie 
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'isAuthenticated': False})

        return Response({'isAuthenticated': True})


class WhoAmIView(APIView):
    @extend_schema(
        responses={
          403: {
            "type": "object",
            "properties": {
                "isAuthenticated": {
                    "type": "boolean",
                    "enum": [False]
                }
            },
            "required": ["isAuthenticated"]
          }, 
          200: {
              "type": "object",
              "properties": {
                  "isAuthenticated": {
                      "type": "boolean",
                      "enum": [True]
                  },
                  "username": {
                      "type": "string"
                  },
                  "id": {
                      "type": "integer"
                  }
              },
              "required": ["isAuthenticated", "username", "id"]
          }
        },
        description='Get current user information'
    )
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'isAuthenticated': False}, status=status.HTTP_403_FORBIDDEN)

        return Response({'username': request.user.username, 'id': request.user.id, 'isAuthenticated': True})
        
        
        
class RobotsInTeamView(APIView):
    @extend_schema(
        responses={
            200: CombatRobotSerializer,
            403: CombatRobotSerializer,
        },
        description='Get robots belonging to a team'
    )
    def get(self, request, combatteam_id):
        team = CombatTeam.objects.get(pk=combatteam_id)
        
        if not team:
            return Response({'detail': 'Team not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        robots = CombatRobot.objects.filter(combat_team=team)
        serializer = CombatRobotSerializer(robots, many=True, context={'request': request})
        return Response(serializer.data)
        

# view to get teams in event
class TeamsInEventView(APIView):
    @extend_schema(
        responses={
            200: CombatTeamSerializer,
            403: CombatTeamSerializer
        },
        description='Get teams in an event'
    )
    def get(self, request, combatevent_id):
        event = CombatEvent.objects.get(pk=combatevent_id)
        
        if not event:
            return Response({'detail': 'Event not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        robots = CombatRobot.objects.filter(events__id=combatevent_id)
        # get distinct teams from the robots
        teams = CombatTeam.objects.filter(pk__in=robots.values('combat_team_id'))
        serializer = CombatTeamSerializer(teams, many=True, context={'request': request})
        return Response(serializer.data)