from .models import NovaPoshtaSettings

def get_nova_poshta_api_key():
    settings = NovaPoshtaSettings.objects.order_by("-updated_at").first()
    if settings:
        return settings.api_key
    return None