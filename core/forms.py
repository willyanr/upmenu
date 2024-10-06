from django import forms
from restaurant.models import Table, Restaurant
from menu.models import Menu, Ingredient
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class MenuForm(forms.ModelForm):
    name = forms.CharField(
        label="Nome do Item",  # Nome em português
        widget=forms.TextInput(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500'
        })
    )
    
    img = forms.ImageField(
        label="Imagem do Item",  # Nome em português
        widget=forms.ClearableFileInput(attrs={
            'class': 'block w-full mb-5 text-xs text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400'
        })
    )
    
    value = forms.DecimalField(
        label="Valor",  # Nome em português
        widget=forms.NumberInput(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500'
        })
    )
    
    status = forms.BooleanField(
        label="Status Ativo",  # Nome em português
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-5 w-5 text-red-600'
        })
    )
    
    ingredients = forms.ModelMultipleChoiceField(
        label="Ingredientes",  # Nome em português
        queryset=Ingredient.objects.none(),  # Inicialmente vazio
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Menu
        fields = ['name', 'img', 'value', 'status', 'ingredients']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Recebe o usuário da view
        super(MenuForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['ingredients'].queryset = Ingredient.objects.filter(user=user)

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name']  # Certifique-se de que 'name' é o nome correto do campo
        labels = {
            'name': 'Nome do Ingrediente',  # Nome do campo como será exibido no formulário
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-gray-100 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 p-2.5 mb-3 mt-4',
                'placeholder': 'Digite o nome do ingrediente'
            }),
        }
        
        
        
class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['table_number', 'is_active']
        labels = {
            'table_number': 'Número da Mesa',
            'is_active': 'Disponível'
        }
        widgets = {
            'table_number': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-gray-100 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 p-2.5 mb-10',
                'placeholder': 'Digite o número da mesa'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-blue-600'
            }),
        }
        
class RestaurantImageForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ['img']
        widgets = {
            'img': forms.ClearableFileInput(attrs={'multiple': False}),
        }
        
class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    verification_code = forms.CharField(max_length=6, required=False, widget=forms.TextInput(attrs={'placeholder': 'Código de verificação'}))


    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Já existe um usuário com este email.')
        return email

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ['name', 'address', 'cep', 'cnpj', 'cpf', 'phone_number', 
                  'delivery_rate_per_km', 'delivery_opening_time', 'delivery_closing_time', 'description', 'img']

    def clean(self):
        cleaned_data = super().clean()
        cep = cleaned_data.get('cep')
        cpf = cleaned_data.get('cpf')
        cnpj = cleaned_data.get('cnpj')
        phone_number = cleaned_data.get('phone_number')

        # Check for duplicate entries
        if cep and Restaurant.objects.filter(cep=cep).exists():
            raise ValidationError({'cep': 'Já existe um restaurante com este CEP.'})

        if Restaurant.objects.filter(cpf=cpf).exists():
            raise ValidationError({'cpf': 'Já existe um restaurante com este CPF.'})

        if Restaurant.objects.filter(phone_number=phone_number).exists():
            raise ValidationError({'phone_number': 'Já existe um restaurante com este número de telefone.'})

        if Restaurant.objects.filter(cnpj=cnpj).exists():
            raise ValidationError({'cnpj': 'Já existe um restaurante com este CNPJ.'})

        return cleaned_data