import os
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.core.files.base import ContentFile
from django.db.models import Q
import time
import cv2
import numpy as np

from .models import FaceShape, HairstyleFaceShapeRecommendation, UserFaceAnalysis, VirtualTryOn
from services.models import Service, Hairstyle
from .forms import UploadPhotoForm, HairstyleSelectionForm
from .face_analyzer import FaceShapeAnalyzer
from .tryon_processor import VirtualTryOnProcessor
from .ai_tryon_processor import AIVirtualTryOnProcessor
from .perfect_corp_processor import PerfectCorpProcessor

logger = logging.getLogger(__name__)

@login_required
def upload_photo(request):
    """View for uploading a photo for face analysis"""
    if request.method == 'POST':
        form = UploadPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the uploaded photo temporarily
            user_photo = request.FILES['photo']
            
            # Create a temporary file path
            temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', f"user_{request.user.id}_{user_photo.name}")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            # Save the uploaded photo
            with open(temp_path, 'wb+') as destination:
                for chunk in user_photo.chunks():
                    destination.write(chunk)
            
            # Analyze face shape
            analyzer = FaceShapeAnalyzer()
            analysis_result = analyzer.analyze_face_shape(temp_path)
            
            if not analysis_result['success']:
                messages.error(request, f"Face detection failed: {analysis_result.get('error', 'Unknown error')}")
                return render(request, 'virtual_tryon/upload_photo.html', {'form': form})
            
            # Get or create the face shape
            face_shape, _ = FaceShape.objects.get_or_create(
                name=analysis_result['face_shape'],
                defaults={'description': f"This is a {analysis_result['face_shape']} face shape."}
            )
            
            # Store face analysis data in session
            request.session['face_shape_id'] = face_shape.id
            request.session['face_analysis_data'] = {
                'face_width_ratio': analysis_result['measurements']['face_width_ratio'],
                'jaw_width_ratio': analysis_result['measurements']['jaw_width_ratio'],
                'forehead_width_ratio': analysis_result['measurements']['forehead_width_ratio'],
                'face_image_path': temp_path
            }
            
            # Redirect to hairstyle recommendations
            return redirect('virtual_tryon:recommend_hairstyles')
    else:
        form = UploadPhotoForm()
    
    return render(request, 'virtual_tryon/upload_photo.html', {'form': form})

@login_required
def recommend_hairstyles(request):
    """View for recommending hairstyles based on face shape"""
    # Get the face analysis from session
    face_shape_id = request.session.get('face_shape_id')
    if not face_shape_id:
        messages.error(request, "No face analysis found. Please upload a photo first.")
        return redirect('virtual_tryon:upload_photo')
    
    face_shape = get_object_or_404(FaceShape, id=face_shape_id)
    
    # Get all services that could be hairstyles
    all_services = Service.objects.all()
    
    # Filter out services without images
    services_with_images = []
    for service in all_services:
        if service.image and service.image.name:
            services_with_images.append(service)
    
    # Log the number of services found
    logger.info(f"Found {all_services.count()} total services")
    logger.info(f"Found {len(services_with_images)} services with images")
    
    # Use the VirtualTryOnProcessor to evaluate hairstyle suitability
    processor = VirtualTryOnProcessor()
    
    # Evaluate each hairstyle's suitability for the detected face shape
    suitable_hairstyles = []
    unsuitable_hairstyles = []
    
    face_shape_name = face_shape.name.lower() if hasattr(face_shape, 'name') else 'oval'
    
    for service in services_with_images:
        # Calculate suitability score for this hairstyle and face shape
        suitability_score = processor._get_hairstyle_suitability(face_shape_name, service.name)
        
        # Store the suitability score with the service for sorting
        service.suitability_score = suitability_score
        
        # Categorize as suitable or unsuitable based on threshold
        if suitability_score >= 0.7:  # 0.7 is our threshold for "suitable"
            suitable_hairstyles.append(service)
        else:
            unsuitable_hairstyles.append(service)
    
    # Sort hairstyles by suitability score (highest first)
    suitable_hairstyles.sort(key=lambda x: x.suitability_score, reverse=True)
    
    # Log the results
    logger.info(f"Found {len(suitable_hairstyles)} suitable hairstyles for {face_shape_name} face shape")
    logger.info(f"Found {len(unsuitable_hairstyles)} unsuitable hairstyles for {face_shape_name} face shape")
    
    context = {
        'face_shape': face_shape,
        'recommended_hairstyles': suitable_hairstyles,
        'other_hairstyles': unsuitable_hairstyles,
        'face_shape_name': face_shape.get_name_display()  
    }
    
    return render(request, 'virtual_tryon/recommend_hairstyles.html', context)

@login_required
def try_on_hairstyle(request, hairstyle_id):
    """View for trying on a specific hairstyle"""
    # Get the face analysis from session
    face_shape_id = request.session.get('face_shape_id')
    face_analysis_data = request.session.get('face_analysis_data')
    if not face_shape_id or not face_analysis_data:
        messages.error(request, "No face analysis found. Please upload a photo first.")
        return redirect('virtual_tryon:upload_photo')
    
    face_shape = get_object_or_404(FaceShape, id=face_shape_id)
    service = get_object_or_404(Service, id=hairstyle_id)  
    
    # Check if service has an image
    if not service.image or not service.image.name:
        messages.error(request, "This service doesn't have an image for virtual try-on.")
        return redirect('virtual_tryon:recommend_hairstyles')
    
    # Create output directory if it doesn't exist
    # Use a dedicated directory for try-on results within the media directory
    output_dir = os.path.join(settings.MEDIA_ROOT, 'virtual_tryon_results')
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate unique filename for the result
    output_filename = f"tryon_{request.user.id}_{service.id}_{int(time.time())}.jpg"
    output_path = os.path.join(output_dir, output_filename)
    
    try:
        # Try to use the Perfect Corp API first
        try:
            # Check if this hairstyle has a Perfect Corp ID
            if hasattr(service, 'perfect_corp_id') and service.perfect_corp_id:
                logger.info(f"Attempting Perfect Corp virtual try-on for hairstyle: {service.name}")
                perfect_corp_processor = PerfectCorpProcessor()
                
                # Get an access token if not already available
                if not settings.PERFECT_CORP_ACCESS_TOKEN:
                    access_token = perfect_corp_processor.get_access_token(
                        settings.PERFECT_CORP_API_KEY,
                        settings.PERFECT_CORP_API_SECRET
                    )
                    if not access_token:
                        raise Exception("Failed to get Perfect Corp access token")
                
                # Process using Perfect Corp API
                result_path = perfect_corp_processor.process_tryon(
                    face_analysis_data['face_image_path'], 
                    service.perfect_corp_id, 
                    output_path
                )
                
                if result_path:
                    logger.info("Perfect Corp virtual try-on completed successfully")
                else:
                    raise Exception("Perfect Corp processing returned None")
            else:
                # No Perfect Corp ID, so skip to AI processing
                raise Exception("No Perfect Corp ID available for this hairstyle")
                
        except Exception as perfect_corp_error:
            # If Perfect Corp processing fails, fall back to AI method
            logger.warning(f"Perfect Corp virtual try-on failed: {str(perfect_corp_error)}. Falling back to AI method.")
            
            # Try to use the AI processor, fall back to the traditional processor if it fails
            try:
                logger.info(f"Attempting AI virtual try-on for hairstyle: {service.name}")
                ai_processor = AIVirtualTryOnProcessor()
                result = ai_processor.process_tryon(
                    face_analysis_data['face_image_path'],
                    service.name,  # Pass the service name as the hairstyle description
                    output_path
                )
                
                if result:
                    logger.info("AI virtual try-on completed successfully")
                else:
                    raise Exception("AI processing returned None")
                    
            except Exception as ai_error:
                # If AI processing fails, fall back to traditional method
                logger.warning(f"AI virtual try-on failed: {str(ai_error)}. Falling back to traditional method.")
                processor = VirtualTryOnProcessor()
                result = processor.process_tryon(
                    face_analysis_data['face_image_path'],
                    service.image.path,  
                    output_path,
                    hairstyle_name=service.name  # Pass the service name to the processor
                )
                
                # Check if result is a dictionary (new format) or string (old format)
                if isinstance(result, dict):
                    result_path = result['output_path']
                    # Update face shape if provided in result
                    if 'face_shape' in result:
                        face_shape_str = result['face_shape']
                        # Convert string face shape to FaceShape object if needed
                        if isinstance(face_shape_str, str):
                            # Try to find matching face shape in database
                            try:
                                face_shape = FaceShape.objects.get(name=face_shape_str.upper())
                            except FaceShape.DoesNotExist:
                                # Keep using the original face shape
                                pass
                else:
                    result_path = result
        
        # For simplicity, we'll just render the result without saving to database
        context = {
            'hairstyle': service,  
            'face_shape': face_shape,
            'face_shape_name': face_shape.get_name_display() if hasattr(face_shape, 'get_name_display') else face_shape,
            'result_image_url': f"/media/virtual_tryon_results/{output_filename}?nocache={service.id}"
        }
        
        # Add additional information if available from the result
        if isinstance(result, dict):
            if 'face_shape_confidence' in result:
                context['face_shape_confidence'] = result['face_shape_confidence']
            if 'hairstyle_suitability' in result:
                context['hairstyle_suitability'] = result['hairstyle_suitability']
                # Calculate percentage for template display
                context['suitability_percent'] = int(result['hairstyle_suitability'] * 100)
        
        return render(request, 'virtual_tryon/tryon_result.html', context)
    except Exception as e:
        messages.error(request, f"Error processing virtual try-on: {str(e)}")
        return redirect('virtual_tryon:recommend_hairstyles')

@login_required
def view_tryon_history(request):
    """View for displaying the user's virtual try-on history"""
    tryon_results = VirtualTryOn.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    context = {
        'tryon_results': tryon_results
    }
    
    return render(request, 'virtual_tryon/tryon_history.html', context)

@login_required
def book_appointment(request, tryon_id):
    """View for booking an appointment with the tried-on hairstyle"""
    tryon_result = get_object_or_404(VirtualTryOn, id=tryon_id, user=request.user)
    
    # Store the selected hairstyle in session for the appointment booking process
    request.session['selected_service_id'] = tryon_result.hairstyle.id
    
    # Add a success message
    messages.success(
        request, 
        f"You've selected {tryon_result.hairstyle.name} for your appointment. Please complete the booking process."
    )
    
    # Redirect to the appointment booking page
    return redirect('appointments:book_appointment')

@login_required
def face_shape_guide(request):
    """View for displaying information about different face shapes and suitable hairstyles"""
    face_shapes = FaceShape.objects.all()
    
    # Get example hairstyles for each face shape
    face_shape_examples = {}
    for face_shape in face_shapes:
        examples = Hairstyle.objects.filter(
            face_shape_recommendations__face_shape=face_shape,
            face_shape_recommendations__recommendation_strength__gte=8,
            is_active=True
        )[:4]  # Get up to 4 examples
        
        face_shape_examples[face_shape.id] = examples
    
    context = {
        'face_shapes': face_shapes,
        'face_shape_examples': face_shape_examples
    }
    
    return render(request, 'virtual_tryon/face_shape_guide.html', context)

@login_required
def delete_tryon(request, tryon_id):
    """View for deleting a virtual try-on result"""
    tryon_result = get_object_or_404(VirtualTryOn, id=tryon_id, user=request.user)
    
    # Delete the try-on result
    tryon_result.delete()
    
    # Add a success message
    messages.success(request, "Virtual try-on result deleted successfully.")
    
    # Redirect to the try-on history page
    return redirect('virtual_tryon:view_tryon_history')