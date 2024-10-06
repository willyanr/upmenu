from django.db import models
from django.contrib.auth.models import User



class Ingredient(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ingredients')
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Menu(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='menus')
    restaurant = models.ForeignKey('restaurant.Restaurant', on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.BooleanField(default=True)
    img = models.ImageField(upload_to='menu_images/')
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    ingredients = models.ManyToManyField(Ingredient, related_name='menus', blank=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True, related_name='menus')

    def __str__(self):
        return self.name

    def get_description(self):
        ingredients_list = [ingredient.name for ingredient in self.ingredients.all()]
        description = ", ".join(ingredients_list)
        return description
    
   
class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
