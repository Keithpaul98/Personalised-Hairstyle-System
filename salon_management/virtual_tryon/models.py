from django.db import models
from django.conf import settings
from services.models import Hairstyle

class FaceShape(models.Model):
    """Model to store different face shapes and their characteristics"""
    SHAPE_CHOICES = [
        ('oval', 'Oval'),
        ('round', 'Round'),
        ('square', 'Square'),
        ('heart', 'Heart'),
        ('diamond', 'Diamond'),
        ('oblong', 'Oblong'),
    ]
    
    # Using 'name' field to match the database schema
    name = models.CharField(max_length=20, choices=SHAPE_CHOICES, unique=True)
    description = models.TextField()
    
    def __str__(self):
        return self.get_name_display()
    
    # Property to maintain compatibility with existing code
    @property
    def shape_type(self):
        return self.name

class HairstyleFaceShapeRecommendation(models.Model):
    """Model to store which hairstyles work well with which face shapes"""
    hairstyle = models.ForeignKey(Hairstyle, on_delete=models.CASCADE, related_name='face_shape_recommendations')
    face_shape = models.ForeignKey(FaceShape, on_delete=models.CASCADE, related_name='recommended_hairstyles')
    recommendation_strength = models.IntegerField(
        default=5,
        help_text="Rating from 1-10 how well this hairstyle suits this face shape"
    )
    
    class Meta:
        unique_together = ('hairstyle', 'face_shape')
    
    def __str__(self):
        return f"{self.hairstyle.name} for {self.face_shape}"

class UserFaceAnalysis(models.Model):
    """Model to store user's face analysis results"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    face_shape = models.ForeignKey(FaceShape, on_delete=models.CASCADE)
    face_width_ratio = models.FloatField(help_text="Width to height ratio of the face")
    jaw_width_ratio = models.FloatField(help_text="Jaw width to face width ratio")
    forehead_width_ratio = models.FloatField(help_text="Forehead width to face width ratio")
    cheekbone_width_ratio = models.FloatField(help_text="Cheekbone width to face width ratio")
    face_image = models.ImageField(upload_to='face_analysis/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s face analysis - {self.face_shape}"

class VirtualTryOn(models.Model):
    """Model to store virtual try-on results"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    hairstyle = models.ForeignKey(Hairstyle, on_delete=models.CASCADE)
    user_image = models.ImageField(upload_to='user_photos/')
    result_image = models.ImageField(upload_to='virtual_tryon_results/')
    face_analysis = models.ForeignKey(UserFaceAnalysis, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s try-on of {self.hairstyle.name}"