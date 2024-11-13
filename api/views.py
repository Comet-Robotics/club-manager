from discord.components import ActionRow
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
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
from rest_framework.decorators import action
from common.robot_combat_events import get_robot_combat_event


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
    
    # TODO: figure out permissions for this action, fix serializers
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='sync-with-rce')
    def sync_event_with_robot_combat_events(self, request, pk):
        combat_event = self.get_object()
        
        rce_details = get_robot_combat_event(combat_event.robot_combat_events_event_id)
        
        team_objs = [CombatTeam(name=team.name, robot_combat_events_team_id=team.rce_team_id) for team in rce_details.teams]
        CombatTeam.objects.bulk_create(team_objs, update_conflicts=True, unique_fields=['robot_combat_events_team_id'], update_fields=['name'])
        
        teams = {team.robot_combat_events_team_id: team for team in CombatTeam.objects.filter(
                robot_combat_events_team_id__in=[team.rce_team_id for team in rce_details.teams]
            )}
        
        rce_plant_label = 'Plastic Antweights'
        rce_ant_label = 'Antweights'
        rce_beetle_label = 'Beetleweights'
        
        plants = [CombatRobot(name=robot.name, weight_class=CombatRobot.WeightClass.PLANT, robot_combat_events_robot_id=robot.rce_resource_id, combat_team=teams[robot.rce_team_id]) for robot in rce_details.robots_by_weight_class[rce_plant_label]]
        ants = [CombatRobot(name=robot.name, weight_class=CombatRobot.WeightClass.ANT, robot_combat_events_robot_id=robot.rce_resource_id, combat_team=teams[robot.rce_team_id]) for robot in rce_details.robots_by_weight_class[rce_ant_label]]
        beetles = [CombatRobot(name=robot.name, weight_class=CombatRobot.WeightClass.BEETLE, robot_combat_events_robot_id=robot.rce_resource_id, combat_team=teams[robot.rce_team_id]) for robot in rce_details.robots_by_weight_class[rce_beetle_label]]
        
        all_robots = plants + ants + beetles
        CombatRobot.objects.bulk_create(all_robots, update_conflicts=True, unique_fields=['robot_combat_events_robot_id'], update_fields=['name', 'weight_class', 'combat_team'])
        
        # Get all robot IDs from the RCE data
        current_robot_ids = [robot.robot_combat_events_robot_id for robot in all_robots]
        
        # Get the robot objects that were just created/updated
        robots_to_add = CombatRobot.objects.filter(robot_combat_events_robot_id__in=current_robot_ids)
        
        # Add the combat event to each robot that should be in the event
        for robot in robots_to_add:
            robot.combat_events.add(combat_event)
            
        # Remove event association from robots no longer in the event
        robots_to_remove = CombatRobot.objects.filter(
            combat_events=combat_event
        ).exclude(
            robot_combat_events_robot_id__in=current_robot_ids
        )
        
        for robot in robots_to_remove:
            robot.combat_events.remove(combat_event)
        
        return Response(status=status.HTTP_200_OK)
          

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
          # TODO: fix this so the return type is a list
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
class RobotsInEventView(APIView):
    @extend_schema(
        responses={
          # TODO: fix this so the return type is a list
            200: CombatRobotSerializer,
            403: CombatRobotSerializer
        },
        description='Get teams in a combat event'
    )
    def get(self, request, combatevent_id):
        combat_event = CombatEvent.objects.get(pk=combatevent_id)
        
        if not combat_event:
            return Response({'detail': 'CombatEvent not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        robots = CombatRobot.objects.filter(combat_events__id=combatevent_id)
        serializer = CombatRobotSerializer(robots, many=True, context={'request': request}) 
        
        return Response(serializer.data)