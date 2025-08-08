from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
import random
import json
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from .models import Business, Game, BusinessGame, GamePlay, Reward
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.views.decorators.http import require_GET
from django.db.models import Q

def _ip_in_range(ip: str, range_str: str) -> bool:
    if not range_str:
        return False
    if range_str.endswith("*"):
        return ip.startswith(range_str[:-1])
    return ip == range_str

@require_GET
def where_am_i(request):
    ip = request.GET.get("ip")
    if not ip:
        # Prod için (lokalde reverse proxy yoksa REMOTE_ADDR bazen 127.0.0.1 olur)
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or \
             request.META.get("REMOTE_ADDR", "")

    if not ip:
        return JsonResponse({"error": "IP belirlenemedi."}, status=400)

    # Basit tarama: tüm işletmelerin range’ine bak
    for b in Business.objects.all():
        if _ip_in_range(ip, b.network_ip_range or ""):
            return JsonResponse({
                "business_name": b.name,
                "unique_code": b.unique_code,
                "ip": ip
            })
    return JsonResponse({"error": "IP herhangi bir işletme aralığında değil."}, status=404)
@csrf_exempt
def login_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Sadece POST isteği kabul edilir."}, status=405)

    data = json.loads(request.body)
    username = data.get("username")
    password = data.get("password")

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        return JsonResponse({"message": "Giriş başarılı."})
    else:
        return JsonResponse({"error": "Geçersiz kullanıcı adı veya şifre."}, status=401)
@csrf_exempt
def logout_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Sadece POST kabul edilir.'}, status=405)
    logout(request)
    return JsonResponse({'message': 'Çıkış yapıldı.'})
def whoami(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Giriş yapılmamış."}, status=401)

    user = request.user

    # Rol belirleme
    if user.is_superuser:
        role = 'admin'
    elif Business.objects.filter(user=user).exists():
        role = 'business_user'
    else:
        role = 'player'

    return JsonResponse({
        "username": user.username,
        "role": role
    })
@csrf_exempt
def play_game(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Sadece POST isteği kabul edilir.'}, status=405)

    try:
        data = json.loads(request.body)
        unique_code = data.get('unique_code')
        game_id = data.get('game_id')
        ip_address = data.get('ip_address')

        if not all([unique_code, game_id, ip_address]):
            return JsonResponse({'error': 'unique_code, game_id ve ip_address zorunludur.'}, status=400)

        # İşletme kontrolü
        try:
            business = Business.objects.get(unique_code=unique_code)
        except Business.DoesNotExist:
            return JsonResponse({"error": "İşletme bulunamadı."}, status=404)

        # IP adresi kontrolü
        if not is_ip_allowed(ip_address, business.network_ip_range):
            return JsonResponse({"error": "Bu IP adresi işletmenin ağına ait değil."}, status=403)

        # Günlük oyun hakkı kontrolü
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        play_count_today = GamePlay.objects.filter(
            ip_address=ip_address,
            business=business,
            timestamp__range=(today_start, today_end)
        ).count()

        if play_count_today >= business.daily_game_limit_per_ip:
            return JsonResponse({'error': 'Bu IP adresi bugün maksimum oyun hakkını kullanmıştır.'}, status=403)

        # Game ve BusinessGame kontrolü
        try:
            game = Game.objects.get(id=game_id)
            business_game = BusinessGame.objects.get(business=business, game=game)
        except Game.DoesNotExist:
            return JsonResponse({"error": "Oyun bulunamadı."}, status=404)
        except BusinessGame.DoesNotExist:
            return JsonResponse({"error": "İşletme bu oyunu sunmuyor."}, status=403)

        # Kazanma durumu
        won = random.random() < business_game.win_probability

        # Oyun kaydını oluştur
        gameplay = GamePlay.objects.create(
            business=business,
            game=game,
            ip_address=ip_address,
            result=won,
            timestamp=timezone.now()
        )

        # Yanıt verisi
        response_data = {
            'business': business.name,
            'game': game.name,
            'ip_address': ip_address,
            'result': 'Kazandı' if won else 'Kaybetti'
        }

        # Ödül varsa ekle
        if won:
            rewards = business_game.rewards.all()
            if rewards.exists():
                reward = random.choice(rewards)
                response_data['reward'] = {
                    'title': reward.title,
                    'description': reward.description
                }

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Geçersiz JSON formatı.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'İşlem sırasında hata oluştu: {str(e)}'}, status=500)

# Yardımcı fonksiyon: IP kontrolü
def is_ip_allowed(ip, range_str):
    if range_str.endswith("*"):
        return ip.startswith(range_str[:-1])
    return ip == range_str
def business_games(request, business_code):
    try:
        business = Business.objects.get(unique_code=business_code)
        games = BusinessGame.objects.filter(business=business).select_related('game')
        data = {
            "business_name": business.name,
            "unique_code": business.unique_code,
            "games": [{
                'game_id': bg.game.id,
                'game_name': bg.game.name,
                'win_probability': bg.win_probability
            } for bg in games]
        }
        return JsonResponse(data)
    except Business.DoesNotExist:
        return JsonResponse({"error": "Business not found"}, status=404)

@method_decorator(csrf_exempt, name='dispatch')
class GamePlayListView(View):
    def get(self, request):
        gameplays = GamePlay.objects.all().order_by('-timestamp')[:10]
        data = [
            {
                'game': gameplay.game.name,
                'ip_address': gameplay.ip_address,
                'result': 'Kazandı' if gameplay.result else 'Kaybetti',
                'timestamp': gameplay.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for gameplay in gameplays
        ]
        return JsonResponse(data, safe=False)
    
@require_GET
def play_status(request):
    unique_code = request.GET.get("unique_code")
    ip = request.GET.get("ip")
    if not (unique_code and ip):
        return JsonResponse({"error": "unique_code ve ip zorunludur."}, status=400)

    try:
        business = Business.objects.get(unique_code=unique_code)
    except Business.DoesNotExist:
        return JsonResponse({"error": "İşletme bulunamadı."}, status=404)

    # IP range doğrulaması
    if not _ip_in_range(ip, business.network_ip_range or ""):
        return JsonResponse({"error": "IP işletme ağına ait değil."}, status=403)

    # Bugün sayacı
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    used = GamePlay.objects.filter(
        business=business,
        ip_address=ip,
        timestamp__range=(today_start, today_end)
    ).count()

    limit = business.daily_game_limit_per_ip
    remaining = max(0, limit - used)

    return JsonResponse({
        "business_name": business.name,
        "unique_code": business.unique_code,
        "ip": ip,
        "limit": limit,
        "used": used,
        "remaining": remaining
    })