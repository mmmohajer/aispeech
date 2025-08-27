from celery import shared_task

from core.models import ProfileModel

@shared_task
def apply_cost_task(profile_id, cost):
    profile = ProfileModel.objects.filter(id=profile_id).first()
    profile.credit = profile.credit - cost
    profile.save()