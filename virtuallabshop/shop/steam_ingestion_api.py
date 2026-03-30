from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.core.files.base import ContentFile
import requests
import json
import traceback

from .models import Product, Genre, Company, SystemRequirements, ProductImage

@method_decorator(staff_member_required, name='dispatch')
class SteamDashboardView(TemplateView):
    template_name = "admin/custom/steam_ingestion.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pre-load existing relationships to render in dropdowns on the frontend
        context['genres'] = Genre.objects.all().order_by('name')
        
        # Developers & Publishers
        context['companies'] = Company.objects.all().order_by('name')
        return context

@method_decorator(staff_member_required, name='dispatch')
class FetchSteamProxyView(View):
    def get(self, request, app_id, *args, **kwargs):
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            if str(app_id) not in data or not data[str(app_id)]['success']:
                return JsonResponse({'error': 'Invalid App ID or failed to fetch from Steam. Steam may restrict this game in some regions.'}, status=400)
            
            game_data = data[str(app_id)]['data']
            
            # Extract basic mapped fields easily consumable by frontend
            result = {
                'name': game_data.get('name', ''),
                'description': game_data.get('about_the_game', '') or game_data.get('detailed_description', ''),
                'short_description': game_data.get('short_description', ''),
                'developers': game_data.get('developers', []),
                'publishers': game_data.get('publishers', []),
                'genres': [g['description'] for g in game_data.get('genres', [])],
                'pc_requirements': game_data.get('pc_requirements', {}),
                'header_image': game_data.get('header_image', ''),
                'capsule_image': game_data.get('capsule_image', ''),
                'screenshots': [s['path_full'] for s in game_data.get('screenshots', [])]
            }
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(staff_member_required, name='dispatch')
class SaveSteamGameView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            # Create Product
            product = Product.objects.create(
                title=data.get('title'),
                edition=data.get('edition') or 'Standard Edition',
                slug=data.get('slug'),
                description=data.get('description', ''),
                price=data.get('price', 0),
                currency=data.get('currency', 'LKR'),
                game_size_gb=data.get('game_size_gb', 0),
                is_active=data.get('is_active', True),
                is_cracked=data.get('is_cracked', True)
            )

            # Associate Developer/Publisher
            dev_id = data.get('developer_id')
            if dev_id:
                product.developer = Company.objects.get(id=dev_id)
            
            pub_id = data.get('publisher_id')
            if pub_id:
                product.publisher = Company.objects.get(id=pub_id)
            product.save()

            # Genres
            genre_ids = data.get('genre_ids', [])
            if genre_ids:
                genres = Genre.objects.filter(id__in=genre_ids)
                product.genres.set(genres)

            # System Requirements
            sys_req = data.get('system_requirements', {})
            SystemRequirements.objects.create(
                product=product,
                min_cpu=sys_req.get('min_cpu', ''),
                min_ram_gb=sys_req.get('min_ram_gb', 8),
                min_gpu=sys_req.get('min_gpu', ''),
                min_storage_gb=sys_req.get('min_storage_gb', 0),
                min_os=sys_req.get('min_os', ''),
                rec_cpu=sys_req.get('rec_cpu', ''),
                rec_ram_gb=sys_req.get('rec_ram_gb') or None,
                rec_gpu=sys_req.get('rec_gpu', ''),
                rec_storage_gb=sys_req.get('rec_storage_gb') or None,
                rec_os=sys_req.get('rec_os', '')
            )

            # Images
            primary_url = data.get('primary_image_url')
            selected_urls = data.get('selected_image_urls', [])
            
            for url in selected_urls:
                if not url: continue
                try:
                    # Provide User-Agent to avoid 403 Forbidden from Akamai/Steam edges
                    img_response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
                    if img_response.status_code == 200:
                        is_prim = (url == primary_url)
                        file_name = url.split('/')[-1]
                        if '?' in file_name:
                            file_name = file_name.split('?')[0]
                        if not file_name:
                            file_name = 'image.jpg'
                            
                        prod_img = ProductImage(product=product, is_primary=is_prim)
                        prod_img.image.save(file_name, ContentFile(img_response.content), save=True)
                except Exception as e:
                    print(f"Failed to download image {url}: {e}")

            return JsonResponse({'success': True, 'product_id': product.id, 'sku': product.sku})
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=400)
