from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Book
import json

# Initialize model once

@receiver(pre_save, sender=Book)
def generate_embedding(sender, instance, **kwargs):
    content = f"{instance.title} {instance.description}"
    vector = model.encode(content).tolist()
    instance.embedding = json.dumps(vector)