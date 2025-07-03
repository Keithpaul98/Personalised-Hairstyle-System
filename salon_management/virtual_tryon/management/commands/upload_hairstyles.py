import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from virtual_tryon.perfect_corp_processor import PerfectCorpProcessor
from services.models import Service

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Upload service images to the Perfect Corp API and store their IDs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--directory',
            default=None,
            help='Directory containing service images to upload',
        )
        parser.add_argument(
            '--hairstyle-id',
            type=int,
            default=None,
            help='Upload only a specific service by ID',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-upload even if the service already has a Perfect Corp ID',
        )
        parser.add_argument(
            '--mock',
            action='store_true',
            help='Use mock mode for testing without internet connection',
        )

    def handle(self, *args, **options):
        # Initialize the Perfect Corp processor with mock mode if specified
        processor = PerfectCorpProcessor(mock_mode=options['mock'])
        
        # Get an access token if not already available
        if not settings.PERFECT_CORP_ACCESS_TOKEN:
            self.stdout.write("Getting access token from Perfect Corp API...")
            access_token = processor.get_access_token(
                settings.PERFECT_CORP_API_KEY,
                settings.PERFECT_CORP_API_SECRET
            )
            if not access_token:
                self.stderr.write(self.style.ERROR("Failed to get access token. Aborting."))
                return
            self.stdout.write(self.style.SUCCESS(f"Access token obtained: {access_token[:10]}..."))
            if options['mock']:
                self.stdout.write(self.style.WARNING("NOTE: This is a mock token for testing purposes only."))
            # Note: In a production environment, you would want to store this token securely
        
        # Determine which services to upload
        if options['hairstyle_id']:
            try:
                services = [Service.objects.get(id=options['hairstyle_id'])]
                self.stdout.write(f"Found service: {services[0].name}")
            except Service.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Service with ID {options['hairstyle_id']} not found."))
                return
        else:
            if options['force']:
                services = Service.objects.all()
                self.stdout.write(f"Found {services.count()} services to process (force mode).")
            else:
                services = Service.objects.filter(perfect_corp_id__isnull=True)
                self.stdout.write(f"Found {services.count()} services without Perfect Corp IDs.")
        
        # Upload each service
        success_count = 0
        for service in services:
            self.stdout.write(f"Processing service: {service.name}")
            
            # Skip if already has an ID and not forcing
            if service.perfect_corp_id and not options['force']:
                self.stdout.write(f"  Already has Perfect Corp ID: {service.perfect_corp_id}")
                continue
            
            # Skip if no image file is associated
            if not service.image:
                self.stderr.write(self.style.ERROR(f"  No image associated with service {service.name} (ID {service.id}). Skipping."))
                continue
            # Get the image path
            image_path = service.image.path
            if not os.path.exists(image_path):
                self.stderr.write(self.style.ERROR(f"  Image file not found: {image_path}"))
                continue
            
            # Upload the service
            self.stdout.write(f"  Uploading {image_path}...")
            service_id = processor.upload_hairstyle(image_path)
            
            if service_id:
                # Update the service with the Perfect Corp ID
                service.perfect_corp_id = service_id
                service.save()
                self.stdout.write(self.style.SUCCESS(f"  Successfully uploaded. Perfect Corp ID: {service_id}"))
                success_count += 1
            else:
                self.stderr.write(self.style.ERROR(f"  Failed to upload service."))
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f"Uploaded {success_count} out of {services.count()} services."))