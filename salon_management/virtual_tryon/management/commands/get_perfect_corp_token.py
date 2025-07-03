import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from virtual_tryon.perfect_corp_processor import PerfectCorpProcessor

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Get an access token from the Perfect Corp API and display it'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--mock',
            action='store_true',
            help='Use mock mode for testing without internet connection',
        )

    def handle(self, *args, **options):
        # Initialize the Perfect Corp processor with mock mode if specified
        processor = PerfectCorpProcessor(mock_mode=options['mock'])
        
        # Get an access token
        self.stdout.write("Getting access token from Perfect Corp API...")
        access_token = processor.get_access_token(
            settings.PERFECT_CORP_API_KEY,
            settings.PERFECT_CORP_API_SECRET
        )
        
        if access_token:
            self.stdout.write(self.style.SUCCESS(f"Access token obtained: {access_token}"))
            self.stdout.write("\nTo use this token, add it to your settings.py file:")
            self.stdout.write(f'PERFECT_CORP_ACCESS_TOKEN = "{access_token}"')
            
            if options['mock']:
                self.stdout.write(self.style.WARNING("\nNOTE: This is a mock token for testing purposes only."))
        else:
            self.stderr.write(self.style.ERROR("Failed to get access token."))