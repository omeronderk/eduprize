from django.contrib import admin
from .models import Business, Game, BusinessGame, Reward, GamePlay


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'unique_code', 'user', 'network_ip_range', 'daily_game_limit_per_ip')
    search_fields = ('name', 'unique_code', 'user__username')
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)
@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(BusinessGame)
class BusinessGameAdmin(admin.ModelAdmin):
    list_display = ['business', 'game', 'win_probability']
    list_filter = ['business', 'game']
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(business__user=request.user)

@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ['title', 'business_game']
    list_filter = ['business_game']
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(business_game__business__user=request.user)

@admin.register(GamePlay)
class GamePlayAdmin(admin.ModelAdmin):
    list_display = ['get_business', 'get_game', 'ip_address', 'result', 'timestamp']
    list_filter = ['business', 'game', 'result']
    search_fields = ['ip_address']
    ordering = ['-timestamp']

    def get_business(self, obj):
        return obj.business.name
    get_business.short_description = 'İşletme'

    def get_game(self, obj):
        return obj.game.name
    get_game.short_description = 'Oyun'
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            business = Business.objects.get(user=request.user)
            return qs.filter(business=business)
        except Business.DoesNotExist:
            return qs.none()
