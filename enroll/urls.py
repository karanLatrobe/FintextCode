from django.urls import path
from enroll import views


urlpatterns = [
    path('',views.home,name='home'),
    path('signup/',views.sign_up,name='signup'),
    path('login/',views.user_login,name='login'),
    path('profile/',views.user_profile,name='profile'),
    path('logout/',views.user_logout,name='logout'),
    path('changepass/',views.user_change_pass,name='user_change_pass'),
    path('userdetail/<int:id>',views.user_detail,name='user_detail'),
    path("download_excel/", views.download_excel, name="download_excel"),
    path("ajax-upload/", views.ajax_upload, name="ajax_upload"),
    path("FAQ/",views.faq,name='FAQ'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('forgot-password-otp/', views.forgot_password_otp, name='forgot_password_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),

]
