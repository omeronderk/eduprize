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
    path('api/logout/', logout_view, name='logout'),
    path('api/whoami/', whoami, name='whoami'),
]