from typing import Literal, TypedDict
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta


"""
The goal of this app is to allow a project manager to easily view retention from meeting to meeting on their project, as well as being able to programmatically grant members access to project resources like GitHub repositories based on team membership. To do this, we need to be able to mark a user as being a 'member' to a project and/or team(s) within that project.

Projects are the top level organizational unit. A project can have multiple teams. Users are a member of a project through their membership of a team - projects have no direct associations with team members. Certain users can be marked as 'managers' of a team. Each team can have multiple team members. A user can be a member of multiple teams. This allows us to create a tree-like structure, like the one below.

Project: Solis Rover Project
  - Managers: Dylan Doe, Gabriel Doe
  - Team: Mechanical
    - Team Member: John Doe
    - Team Member: Jane Doe
    - Team: Arm
      - Team Member: John Doe
      - Team Member: Megan Doe
  - Team: Embedded
    - Team Member: Emily Doe
    - Team Member: Michael Doe
"""


class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    managers = models.ManyToManyField(User, related_name="projects_managing")

    def __str__(self):
        return self.name

    def all_team_members(self):
        return User.objects.filter(
            Q(projects_managing=self) | Q(teams_in__project=self) | Q(teams_leading__project=self)
        ).distinct("id")

    def all_teams(self):
        return Team.objects.filter(project=self)

    def direct_teams(self):
        return Team.objects.filter(project=self, parent_team=None)

    @staticmethod
    def user_can_manage_project(user: User, project: "Project"):
        # Users can manage projects they are a manager of, or if they are a superuser (only club officers should be superusers)
        return user.is_superuser or user in project.managers.all()

    @staticmethod
    def get_projects_user_can_manage(user: User):
        return Project.objects.all() if user.is_superuser else Project.objects.filter(managers=user)


class Team(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    parent_team = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)
    members = models.ManyToManyField(User, related_name="teams_in")
    leads = models.ManyToManyField(User, related_name="teams_leading")
    emoji = models.CharField(max_length=3, null=True, blank=True)

    def __str__(self):
        if self.parent_team:
            return str(self.parent_team) + " > " + self.name
        else:
            return self.project.name + " | " + self.name

    def direct_teams(self):
        return Team.objects.filter(parent_team=self)

    def get_unique_users(self):
        """
        Returns a QuerySet of all users who are either members or leads of this team
        and all of its subteams, without duplicates.
        """
        subteams = Team.objects.filter(parent_team=self)
        user_query = Q(teams_in=self) | Q(teams_leading=self)

        for subteam in subteams:
            user_query |= Q(teams_in=subteam) | Q(teams_leading=subteam)

        return User.objects.filter(user_query).distinct()

    def all_team_members(self):
        """
        Return a list of all the team's members and leads. This method includes members and leads of all subteams.

        NOTE: since this method includes subteam members and leads, it may return duplicate users
        """
        members = [TeamMember(user=i, team=self, role="member") for i in list(self.members.all())] + [
            TeamMember(user=i, team=self, role="lead") for i in list(self.leads.all())
        ]
        for team in self.direct_teams():
            members.extend(team.all_team_members())
        return members

    def get_member_count(self):
        return self.get_unique_users().count()

    def get_team_meetings(self):
        return self.events.all().count()

    def get_average_attendance(self):
        if self.get_team_meetings() == 0 or self.get_member_count() == 0:
            return 0
        return (
            sum([event.get_attendance() / self.get_member_count() for event in self.events.all()])
            / (self.get_team_meetings())
            * 100
        )

    @staticmethod
    def user_can_manage_team(user: User, team: "Team"):
        """
        Users can manage teams if any one of the following conditions is true:
        - they are able to manage the project that the team is in
        - if they are a lead on that specific team
        - if they are a lead on any of this team's parent teams
        """
        if Project.user_can_manage_project(user, team.project):
            return True

        team_to_check = team
        while team_to_check:
            if user in team_to_check.leads.all():
                return True
            team_to_check = team_to_check.parent_team

        return False

    @staticmethod
    def get_teams_associated_with_user(user: User):
        teams: list[TeamMember] = []

        for team in user.teams_leading.all():
            teams.append(TeamMember(user=user, team=team, role="lead"))

        for team in user.teams_in.all():
            teams.append(TeamMember(user=user, team=team, role="member"))

        return teams

    def get_suggested_members(self):
        """
        Returns a query set of users who are not members or leads of this team, but should be considered for membership based on their attendance (> 1 event attended in the last month).
        BTW CURSOR WROTE THIS. I NEED TO TEST THIS. PLEASE DON'T USE IT WITHOUT TESTING. reading it it does look quite reasonable but still. be careful.
        """
        # Calculate the date one month ago
        one_month_ago = timezone.now() - timedelta(days=30)
        
        # Get all users who are already members or leads of this team (to exclude them)
        current_team_users = self.get_unique_users()
        
        # Find users who have attended more than 1 event for this team in the last month
        suggested_users = User.objects.filter(
            # User has attended events for this team
            attendance__event__teams=self,
            # Events were in the last month
            attendance__event__event_date__gte=one_month_ago
        ).annotate(
            # Count the number of events attended
            event_count=Count('attendance__event', distinct=True)
        ).filter(
            # More than 1 event attended
            event_count__gt=1
        ).exclude(
            # Exclude users who are already members or leads of this team
            id__in=current_team_users.values_list('id', flat=True)
        ).distinct()
        
        return suggested_users


class TeamMember(TypedDict):
    user: User
    team: Team
    role: Literal["lead"] | Literal["member"]
