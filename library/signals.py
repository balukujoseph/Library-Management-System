from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Book
from sentence_transformers import SentenceTransformer
import json

# Initialize model once
model = SentenceTransformer('all-MiniLM-L6-v2')

@receiver(pre_save, sender=Book)
def generate_embedding(sender, instance, **kwargs):
    content = f"{instance.title} {instance.description}"
    vector = model.encode(content).tolist()
    instance.embedding = json.dumps(vector)