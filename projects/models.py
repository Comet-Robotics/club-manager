from django.db import models

class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    default_sub_team = models.ForeignKey('SubTeam', on_delete=models.CASCADE)

    def __str__(self):
        return self.name
        

class SubTeam(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    parent_sub_team = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
      if self.parent_sub_team:
        return self.parent_sub_team.name + " > " + self.name
      else:
        return self.project.name + " | " + self.name


class TeamMember(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    sub_team = models.ForeignKey(SubTeam, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
      constraints = [
          models.UniqueConstraint(fields=['user', 'sub_team'], name='unique_user_sub_team')
      ]

    def __str__(self):
        return str(self.user) + " | " + self.sub_team.name