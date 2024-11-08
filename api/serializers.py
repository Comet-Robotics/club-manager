from django.contrib.auth.models import Group, User
from payments.models import Product, PurchasedProduct
from rest_framework import serializers
from events.models import Event, CombatTeam, CombatRobot, CombatEvent

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url','id', 'username', 'email', 'groups']
        
class ProductSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'amount_cents', 'max_purchases_per_user', 'image']


class CombatTeamSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CombatTeam
        fields = ['id', 'name', 'managers']


class ProductSerializer(serializers.HyperlinkedModelSerializer):
  class Meta:
      model = Product
      fields = ['id', 'name', 'description', 'amount_cents', 'max_purchases_per_user', 'image']

class PurchasedProductSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PurchasedProduct
        fields = ['id', 'product', 'quantity']
        
    product = ProductSerializer(read_only=True)

class CombatRobotSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CombatRobot
        fields = ['id', 'name', 'owners', 'combat_team']

class EventSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'event_name', 'event_date', 'url', 'combat_event']
        

class CombatEventSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CombatEvent
        fields = ['id', 'event', 'robot_combat_events_event_id', 'product_id']

