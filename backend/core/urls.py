from django.urls import path
from .views import play_game
from . import views
from .views import GamePlayListView
from .views import login_view, logout_view, whoami
urlpatterns = [
    path('api/play_game/', views.play_game, name='play_game'),
    path('api/business_games/<str:business_code>/', views.business_games, name='business_games'),
    path('api/gameplays/', GamePlayListView.as_view(), name='gameplay-list'),
    path('api/login/', login_view, name='login'),
    path('api/logout/', views.logout_view, name='logout'),
    path('api/whoami/', whoami, name='whoami'),
    path('api/where_am_i/', views.where_am_i, name='where_am_i'),           # NEW
    path('api/play_status/', views.play_status, name='play_status'),   
    path('api/business/summary/', views.business_summary, name='business_summary'),
    path('api/business/games/', views.business_games_manage, name='business_games_manage'),
    path('api/business/games/<int:pk>/', views.business_game_detail, name='business_game_detail'),     
]