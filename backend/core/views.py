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
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
def _ip_in_range(ip: str, range_str: str) -> bool:
    if not range_str:
        return False
    if range_str.endswith("*"):
        return ip.startswith(range_str[:-1])
    return ip == range_str
def _today_range():
    start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end
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
            player=request.user if request.user.is_authenticated and not request.user.is_superuser else None,
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
def _get_business_for_request_user(request):
    """Business user için bağlı işletmeyi döndürür; admin ise ?unique_code= ile hedef seçebilir."""
    user = request.user
    if user.is_superuser:
        code = request.GET.get("unique_code")
        if not code:
            return None, JsonResponse({"error": "Admin için unique_code zorunlu."}, status=400)
        b = Business.objects.filter(unique_code=code).first()
        if not b:
            return None, JsonResponse({"error": "İşletme bulunamadı."}, status=404)
        return b, None
    else:
        b = Business.objects.filter(user=user).first()
        if not b:
            return None, JsonResponse({"error": "Bu kullanıcıya bağlı işletme yok."}, status=403)
        return b, None

@login_required
@require_http_methods(["GET"])
def business_summary(request):
    """İşletme kullanıcısı için anlık özet + oyun başına istatistikler."""
    business, err = _get_business_for_request_user(request)
    if err:
        return err

    start, end = _today_range()
    today_qs = GamePlay.objects.filter(business=business, timestamp__range=(start, end))

    total = today_qs.count()
    wins = today_qs.filter(result=True).count()
    losses = total - wins
    unique_ips = today_qs.values("ip_address").distinct().count()

    bg_list = BusinessGame.objects.filter(business=business).select_related("game")
    games = []
    for bg in bg_list:
        g_qs = today_qs.filter(game=bg.game)
        g_total = g_qs.count()
        g_wins = g_qs.filter(result=True).count()
        games.append({
            "business_game_id": bg.id,
            "game_id": bg.game.id,
            "game_name": bg.game.name,
            "win_probability": bg.win_probability,
            "plays_today": g_total,
            "wins_today": g_wins,
            "losses_today": g_total - g_wins,
        })

    return JsonResponse({
        "business": {
            "name": business.name,
            "unique_code": business.unique_code,
            "daily_game_limit_per_ip": business.daily_game_limit_per_ip,
        },
        "today": {
            "total": total,
            "wins": wins,
            "losses": losses,
            "unique_ips": unique_ips,
        },
        "games": games,
    })

@login_required
@csrf_exempt
@require_http_methods(["GET", "POST"])
def business_games_manage(request):
    """
    GET: İşletmenin BusinessGame listesi
    POST: {game_id, win_probability} ile yeni ilişki ekle (0..1 doğrulaması + unique constraint)
    """
    business, err = _get_business_for_request_user(request)
    if err:
        return err

    if request.method == "GET":
        items = BusinessGame.objects.filter(business=business).select_related("game")
        data = [{
            "business_game_id": i.id,
            "game_id": i.game.id,
            "game_name": i.game.name,
            "win_probability": i.win_probability,
        } for i in items]
        return JsonResponse({"business": {"name": business.name, "unique_code": business.unique_code}, "items": data})

    # POST
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Geçersiz JSON."}, status=400)

    game_id = payload.get("game_id")
    win_probability = payload.get("win_probability")

    if game_id is None or win_probability is None:
        return JsonResponse({"error": "game_id ve win_probability zorunludur."}, status=400)

    try:
        wp = float(win_probability)
        if not (0.0 <= wp <= 1.0):
            return JsonResponse({"error": "win_probability 0.0 ile 1.0 arasında olmalı."}, status=400)
    except (TypeError, ValueError):
        return JsonResponse({"error": "win_probability sayısal olmalı."}, status=400)

    try:
        game = Game.objects.get(id=game_id)
    except Game.DoesNotExist:
        return JsonResponse({"error": "Oyun bulunamadı."}, status=404)

    try:
        obj, created = BusinessGame.objects.get_or_create(
            business=business, game=game, defaults={"win_probability": wp}
        )
        if not created:
            return JsonResponse({"error": "Bu oyun zaten işletmeye ekli."}, status=409)
    except IntegrityError:
        return JsonResponse({"error": "Bu oyun zaten işletmeye ekli."}, status=409)

    return JsonResponse({
        "message": "Oyun işletmeye eklendi.",
        "business_game_id": obj.id
    }, status=201)

@login_required
@csrf_exempt
@require_http_methods(["PATCH", "DELETE"])
def business_game_detail(request, pk: int):
    """
    PATCH: {win_probability} güncelle
    DELETE: ilişkiyi kaldır
    """
    try:
        bg = BusinessGame.objects.select_related("business").get(id=pk)
    except BusinessGame.DoesNotExist:
        return JsonResponse({"error": "Kayıt bulunamadı."}, status=404)

    # Yetki kontrolü
    if not (request.user.is_superuser or (bg.business.user_id == request.user.id)):
        return JsonResponse({"error": "Yetkisiz."}, status=403)

    if request.method == "DELETE":
        bg.delete()
        return JsonResponse({"message": "Silindi."})

    # PATCH
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Geçersiz JSON."}, status=400)

    if "win_probability" in payload:
        try:
            wp = float(payload["win_probability"])
            if not (0.0 <= wp <= 1.0):
                return JsonResponse({"error": "win_probability 0.0 ile 1.0 arasında olmalı."}, status=400)
        except (TypeError, ValueError):
            return JsonResponse({"error": "win_probability sayısal olmalı."}, status=400)
        bg.win_probability = wp
        bg.save(update_fields=["win_probability"])

    return JsonResponse({"message": "Güncellendi.", "win_probability": bg.win_probability})

def _parse_date_range(request):
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    # varsayılan: bugün
    today = datetime.now().date()
    if not start_str and not end_str:
        return today, today + timedelta(days=1)

    start = parse_date(start_str) if start_str else today
    end = parse_date(end_str) if end_str else start

    # end dahil görünsün diye +1 gün
    end_plus = end + timedelta(days=1)
    return start, end_plus


def _business_scope_queryset(request, qs):
    """
    Admin tüm işletmeleri görebilir, ?business_code= ile seçebilir.
    İşletme kullanıcıları sadece kendi işletmesini görür.
    """
    user = request.user
    if user.is_superuser:
        code = request.GET.get('business_code') or request.GET.get('unique_code')
        if code:
            return qs.filter(business__unique_code=code)
        return qs  # tümü
    else:
        # business user ise kendi işletmesi
        return qs.filter(business__user=user)


@require_GET
@login_required
def report_gameplays(request):
    """
    Listeleme + filtre + sayfalama
    GET /api/reports/gameplays?start=2025-07-15&end=2025-07-18
        &game=2&user=hasankose&result=win&page=1&page_size=50
    """
    start, end = _parse_date_range(request)

    qs = GamePlay.objects.select_related('business', 'game', 'player') \
        .filter(timestamp__gte=start, timestamp__lt=end)

    qs = _business_scope_queryset(request, qs)

    # Filtreler
    game_id = request.GET.get('game')
    if game_id:
        qs = qs.filter(game_id=game_id)

    user_param = request.GET.get('user')
    if user_param:
        if user_param.isdigit():
            qs = qs.filter(player_id=int(user_param))
        else:
            qs = qs.filter(player__username__icontains=user_param)

    result_param = request.GET.get('result')
    if result_param in ('win', 'loss'):
        qs = qs.filter(result=(result_param == 'win'))

    qs = qs.order_by('-timestamp')

    # sayfalama
    page = int(request.GET.get('page', 1))
    page_size = min(max(int(request.GET.get('page_size', 50)), 1), 200)
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    items = []
    for gp in page_obj.object_list:
        items.append({
            'business': gp.business.name,
            'business_code': gp.business.unique_code,
            'game': gp.game.name,
            'game_id': gp.game_id,
            'ip': gp.ip_address,
            'player': gp.player.username if gp.player else None,
            'result': 'win' if gp.result else 'loss',
            'timestamp': gp.timestamp.isoformat(),
        })

    return JsonResponse({
        'items': items,
        'page': page_obj.number,
        'total': paginator.count,
        'num_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_prev': page_obj.has_previous(),
    })


@require_GET
@login_required
def report_summary(request):
    """
    Özet/gruplama
    GET /api/reports/summary?period=day|week|month&start=2025-07-01&end=2025-07-31
    Opsiyonel: &game=2
    """
    start, end = _parse_date_range(request)

    period = request.GET.get('period', 'day')
    if period == 'week':
        trunc = TruncWeek('timestamp')
    elif period == 'month':
        trunc = TruncMonth('timestamp')
    else:
        trunc = TruncDay('timestamp')

    qs = GamePlay.objects.filter(timestamp__gte=start, timestamp__lt=end)
    qs = _business_scope_queryset(request, qs)

    game_id = request.GET.get('game')
    if game_id:
        qs = qs.filter(game_id=game_id)

    grouped = qs.annotate(bucket=trunc).values('bucket').annotate(
        plays=Count('id'),
        wins=Count('id', filter=Q(result=True)),
        losses=Count('id', filter=Q(result=False)),
        unique_ips=Count('ip_address', distinct=True),
        unique_players=Count('player', distinct=True),
    ).order_by('bucket')

    data = []
    for row in grouped:
        data.append({
            'bucket': row['bucket'].isoformat() if row['bucket'] else None,
            'plays': row['plays'],
            'wins': row['wins'],
            'losses': row['losses'],
            'unique_ips': row['unique_ips'],
            'unique_players': row['unique_players'],
        })

    return JsonResponse({'period': period, 'data': data})

def parse_date_any(value: str):
    """'YYYY-MM-DD' ya da 'DD.MM.YYYY' formatlarını kabul eder."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
def day_bounds(d):
    """Yerel günün [start, end) aware datetime sınırları."""
    start_naive = datetime.combine(d, datetime.min.time())
    start = timezone.make_aware(start_naive)
    end = start + timedelta(days=1)
    return start, end