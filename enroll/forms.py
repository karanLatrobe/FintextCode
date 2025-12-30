from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms

class SignUP(UserCreationForm):
    password2 = forms.CharField(label='Confirm Password (again)',widget=forms.PasswordInput)
    email = forms.EmailField(label="Email", required=True)
    class Meta:
        model = User
        fields = ['username','email']
        labels = {'email':'Email',
                  'username':'Username',
                  'first_name':"First Name",
                  'last_name':'Last Name'}
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already taken. Please use a different email.")
        return email

class EditUserProfileForm(UserChangeForm):
    password = None
    class Meta:
        model = User 
        fields = ['username','first_name','last_name','email']



class EditAdminProfileForm(UserChangeForm):
    password = None
    class Meta:
        model = User 
        fields = '__all__'