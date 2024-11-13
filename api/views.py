from discord.components import ActionRow
from django.contrib.auth.models import User
from rest_framework.permissions import IsAdminUser, IsAuthenticated
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
from common.robot_combat_events import RCETeam, get_robot_combat_event, RCERobot
from django.db.models import Q


from events.models import CombatEventRegistration, Event, CombatTeam, CombatRobot, CombatEvent, Waiver

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

    def _upsert_teams_with_rce_data(self, rce_teams: list[RCETeam]) -> dict[str, CombatTeam]:
      """
      Upserts the given list of teams from Robot Combat Events into the database. Returns a dictionary mapping the Robot Combat Events team IDs to the upserted teams.
      
      Parameters:
      - rce_teams (list[RCETeam]): The list of teams to upsert.
      """
      combat_teams = [CombatTeam(name=team.name, robot_combat_events_team_id=team.rce_team_id) for team in rce_teams]
      CombatTeam.objects.bulk_create(combat_teams, update_conflicts=True, unique_fields=['robot_combat_events_team_id'], update_fields=['name'])

      upserted_teams = {team.robot_combat_events_team_id: team for team in CombatTeam.objects.filter(
          robot_combat_events_team_id__in=[team.rce_team_id for team in rce_teams]
      )}
      return upserted_teams

    def _upsert_robots_with_rce_data(self, rce_robots: list[RCERobot], combat_teams: dict[str, CombatTeam]) -> list[CombatRobot]:
      """
      Upserts the given list of robots from Robot Combat Events into the database. Returns a list of CombatRobot objects that were created or updated.
      
      Parameters:
      - rce_robots: A list of RCERobot objects to upsert.
      - combat_teams: A dictionary mapping RCE team IDs to CombatTeam objects.
      """
    
      RCE_WEIGHT_CLASS_LABEL_TO_COMBAT_ROBOT_WEIGHT_CLASS = {
          'Plastic Antweights': CombatRobot.WeightClass.PLANT,
          'Antweights': CombatRobot.WeightClass.ANT,
          'Beetleweights': CombatRobot.WeightClass.BEETLE
      }
    
      all_robots = [
        CombatRobot(
          name=rce_robot.name, 
          weight_class=RCE_WEIGHT_CLASS_LABEL_TO_COMBAT_ROBOT_WEIGHT_CLASS[rce_robot.weight_class], 
          robot_combat_events_robot_id=rce_robot.rce_resource_id, 
          combat_team=combat_teams[rce_robot.rce_team_id]
        ) for rce_robot in rce_robots
      ]
      CombatRobot.objects.bulk_create(
        all_robots, 
        update_conflicts=True, 
        unique_fields=['robot_combat_events_robot_id'], 
        update_fields=['name', 'weight_class', 'combat_team']
      )
      return all_robots

    def _associate_robots_with_event(self, combat_robots: list[CombatRobot], combat_event: CombatEvent, rce_robots: list[RCERobot]):
      RCE_STATUS_LABELS_TO_REG_STATUS = {
        'Competing': CombatEventRegistration.Status.COMPETING,
        'On Waitlist': CombatEventRegistration.Status.ON_WAITLIST
      }
      
      rce_robot_id_to_combat_robot_map: dict[str, CombatRobot] = {robot.robot_combat_events_robot_id: robot for robot in combat_robots}
      
      reg_objs = []
      for rce_robot in rce_robots:
          if rce_robot.rce_resource_id in rce_robot_id_to_combat_robot_map:
              reg_objs.append(
                  CombatEventRegistration(
                      combat_event=combat_event,
                      combat_robot=rce_robot_id_to_combat_robot_map[rce_robot.rce_resource_id],
                      status=RCE_STATUS_LABELS_TO_REG_STATUS[rce_robot.status]
                  )
              )
      CombatEventRegistration.objects.bulk_create(
          reg_objs, 
          update_conflicts=True,
          unique_fields=['combat_event', 'combat_robot'],
          update_fields=['status']
      )

    # TODO: fix openapi schema. also, this shouldn't be a GET
    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser], url_path='sync-with-rce')
    def sync_event_with_robot_combat_events(self, request, pk):
        combat_event = self.get_object()
        
        if not combat_event:
            return Response({'detail': 'CombatEvent not found.'}, status=status.HTTP_404_NOT_FOUND)

        rce_event = get_robot_combat_event(combat_event.robot_combat_events_event_id)

        upserted_teams = self._upsert_teams_with_rce_data(rce_event.teams)  
        upserted_robots = self._upsert_robots_with_rce_data(rce_event.robots, upserted_teams)
        self._associate_robots_with_event(upserted_robots, combat_event, rce_event.robots)
        
        # purging registrations for robots not returned by RCE
        CombatEventRegistration.objects.filter(
          combat_event=combat_event
        ).exclude(combat_robot__in=upserted_robots).delete()

        return Response(status=status.HTTP_200_OK)
        
    # TODO: fix openapi schema
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='teams')
    def get_teams_in_event(self, request, pk):
        combat_event = self.get_object()
        
        if not combat_event:
            return Response({'detail': 'CombatEvent not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        registrations = CombatEventRegistration.objects.filter(combat_event=combat_event)
        team_ids = registrations.values('combat_robot__combat_team').distinct()
        teams = CombatTeam.objects.filter(pk__in=team_ids)
        
        serializer = CombatTeamSerializer(teams, many=True, context={'request': request})
        
        
        return Response(serializer.data)
        
# TODO: action for user to become a team manager (allows them to pay for the team's robots)
# 
# TODO: action for user to become a robot owner. may need some refactoring, since
# I want to associate registration to an owner instead of owners to robots. 
# this way, Robot X can go to competion A with persons 1 and 2, but at comp B
# they can compete with persons 2 and 3, a different set of owners.
# 
# TODO: endpoints for payments


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
