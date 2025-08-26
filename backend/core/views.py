from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, time
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
from django.db.models import Q,Count
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.core.paginator import Paginator, EmptyPage
from django.utils.dateparse import parse_datetime

def _parse_iso_dt(s, fallback):
    """ISO string → aware datetime; yoksa fallback döndürür."""
    if not s:
        return fallback
    try:
        dt = datetime.fromisoformat(s)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    except Exception:
        return fallback

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

@login_required
@require_GET
def report_gameplays(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        business = Business.objects.get(user=request.user)
    except Business.DoesNotExist:
        return JsonResponse({"error": "Business not found for user"}, status=404)

    start = request.GET.get('start')
    end = request.GET.get('end')
    result_filter = request.GET.get('result', 'all')  # all|won|lost
    game_id = request.GET.get('game_id', '').strip()
    username = request.GET.get('username', '').strip()

    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 25))

    qs = GamePlay.objects.filter(business=business)

    if start:
        dt = parse_datetime(start) or timezone.make_aware(timezone.datetime.fromisoformat(start))
        qs = qs.filter(timestamp__gte=dt)
    if end:
        dt = parse_datetime(end) or timezone.make_aware(timezone.datetime.fromisoformat(end))
        qs = qs.filter(timestamp__lte=dt)

    if result_filter == 'won':
        qs = qs.filter(result=True)
    elif result_filter == 'lost':
        qs = qs.filter(result=False)

    if game_id:
        qs = qs.filter(game_id=game_id)

    if username:
        if username.isdigit():
            qs = qs.filter(player_id=int(username))
        else:
            qs = qs.filter(player__username__icontains=username)

    qs = qs.select_related('game', 'player').order_by('-timestamp')

    paginator = Paginator(qs, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages if paginator.num_pages else 1)

    items = []
    for gp in page_obj.object_list:
        items.append({
            "id": gp.id,
            "timestamp": gp.timestamp.isoformat(),
            "game_name": gp.game.name if gp.game_id else None,
            "username": gp.player.username if gp.player_id else None,
            "ip_address": gp.ip_address,
            "result": bool(gp.result),
        })

    return JsonResponse({
        "items": items,
        "total": paginator.count,
        "page": page_obj.number,
        "page_size": page_size,
    })

@require_GET
def report_summary(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    # İşletme kısıtı
    try:
        business = Business.objects.get(user=request.user)
    except Business.DoesNotExist:
        return JsonResponse({"error": "Business not found for user"}, status=404)

    start = request.GET.get('start')  # ISO veya boş
    end = request.GET.get('end')
    result_filter = request.GET.get('result', 'all')  # all|won|lost
    game_id = request.GET.get('game_id', '').strip()
    username = request.GET.get('username', '').strip()

    qs = GamePlay.objects.filter(business=business)

    # Tarih aralığı
    if start:
        dt = parse_datetime(start) or timezone.make_aware(timezone.datetime.fromisoformat(start))
        qs = qs.filter(timestamp__gte=dt)
    if end:
        dt = parse_datetime(end) or timezone.make_aware(timezone.datetime.fromisoformat(end))
        qs = qs.filter(timestamp__lte=dt)

    # Sonuç filtresi
    if result_filter == 'won':
        qs = qs.filter(result=True)
    elif result_filter == 'lost':
        qs = qs.filter(result=False)

    # Oyun filtresi
    if game_id:
        qs = qs.filter(game_id=game_id)

    # Kullanıcı filtresi (player)
    if username:
        if username.isdigit():
            qs = qs.filter(player_id=int(username))
        else:
            qs = qs.filter(player__username__icontains=username)

    played = qs.count()
    won = qs.filter(result=True).count()
    lost = qs.filter(result=False).count()
    unique_ip = qs.values('ip_address').distinct().count()
    unique_player = qs.values('player_id').distinct().count()

    return JsonResponse({
        "summary": {
            "played": played,
            "won": won,
            "lost": lost,
            "unique_ip": unique_ip,
            "unique_player": unique_player,
        }
    })
def _parse_date_any(s: str):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None

# start/end string → TZ-aware datetime [00:00:00 .. 23:59:59]
def _get_range_from_request(request):
    start_str = request.GET.get("start")
    end_str   = request.GET.get("end")
    start_date = _parse_date_any(start_str) or timezone.localdate()
    end_date   = _parse_date_any(end_str) or start_date

    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
    end_dt   = timezone.make_aware(datetime.combine(end_date, time.max), tz)
    return start_dt, end_dt

