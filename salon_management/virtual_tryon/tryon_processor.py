import cv2
import numpy as np
import mediapipe as mp
import os
import logging
from .face_analyzer import FaceShapeAnalyzer

logger = logging.getLogger(__name__)

class VirtualTryOnProcessor:
    """
    Class to process virtual try-on using MediaPipe face mesh.
    """
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_analyzer = FaceShapeAnalyzer()
        
    def process_tryon(self, user_image_path, hairstyle_path, output_path, hairstyle_name=None):
        """
        Process the virtual try-on by blending the hairstyle onto the user's photo
        using MediaPipe for advanced face detection and landmark tracking.
        
        Args:
            user_image_path: Path to the user's image
            hairstyle_path: Path to the hairstyle image
            output_path: Path to save the result
            hairstyle_name: Name of the hairstyle (optional)
            
        Returns:
            Path to the processed image if successful, None otherwise
        """
        try:
            # Load images
            user_img = cv2.imread(user_image_path)
            user_img_rgb = cv2.cvtColor(user_img, cv2.COLOR_BGR2RGB)
            hairstyle_img = cv2.imread(hairstyle_path, cv2.IMREAD_UNCHANGED)
            
            # Check if images were loaded successfully
            if user_img is None or hairstyle_img is None:
                logger.error("Failed to load images")
                return None
            
            # Resize images if needed
            if user_img.shape[0] > 800:
                scale = 800 / user_img.shape[0]
                user_img = cv2.resize(user_img, (int(user_img.shape[1] * scale), 800))
                user_img_rgb = cv2.cvtColor(user_img, cv2.COLOR_BGR2RGB)
            
            # Analyze face shape using the face analyzer
            face_analysis = self.face_analyzer.analyze_face_shape(user_image_path)
            if not face_analysis['success']:
                logger.warning(f"Face shape analysis failed: {face_analysis.get('error', 'Unknown error')}. Using default oval shape.")
                face_shape = 'oval'
                face_shape_confidence = 0.6
            else:
                face_shape = face_analysis['face_shape']
                face_shape_confidence = face_analysis['confidence']
                logger.info(f"Detected face shape: {face_shape} (confidence: {face_shape_confidence:.2f})")
            
            # Detect facial landmarks using MediaPipe
            with self.mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5) as face_mesh:
                
                results = face_mesh.process(user_img_rgb)
                
                if not results.multi_face_landmarks:
                    logger.error("No face detected in the image")
                    # Save the original image as fallback
                    cv2.imwrite(output_path, user_img)
                    return output_path
                
                # Get face landmarks
                face_landmarks = results.multi_face_landmarks[0]
                
                # Get image dimensions
                h, w, _ = user_img.shape
                
                # Calculate face bounding box
                x_min, y_min, x_max, y_max = self._get_face_bounding_box(face_landmarks, w, h)
                
                # Store hairstyle name
                self.hairstyle_name = hairstyle_name
                
                # Analyze hairstyle image to determine its characteristics
                hairstyle_characteristics = self._analyze_hairstyle_image(hairstyle_img)
                
                # Check if this hairstyle is suitable for the detected face shape
                suitability_score = self._get_hairstyle_suitability(face_shape, hairstyle_name)
                if suitability_score < 0.7:
                    logger.warning(f"Hairstyle '{hairstyle_name}' may not be ideal for {face_shape} face shape (score: {suitability_score:.2f})")
                
                # Calculate hair region based on face landmarks, hairstyle characteristics, and face shape
                hair_region = self._calculate_hair_region(face_landmarks, w, h, hairstyle_characteristics, face_shape)
                
                # Resize hairstyle to fit the calculated region
                hairstyle_resized = cv2.resize(hairstyle_img, (hair_region['width'], hair_region['height']))
                
                # Create a mask for the hairstyle (assuming alpha channel or background removal)
                hairstyle_mask = self._create_hairstyle_mask(hairstyle_resized)
                
                # Extract skin tone from user's face for color correction
                skin_tone = self._extract_skin_tone(user_img, face_landmarks)
                
                # Blend the images with skin tone correction
                result_img = self._blend_images(user_img, hairstyle_resized, hair_region, hairstyle_mask, skin_tone)
                
                # Save the result
                cv2.imwrite(output_path, result_img)
                
                # Return information about the try-on including face shape
                return {
                    'output_path': output_path,
                    'face_shape': face_shape,
                    'face_shape_confidence': face_shape_confidence,
                    'hairstyle_suitability': suitability_score
                }
                
        except Exception as e:
            logger.error(f"Error processing virtual try-on: {str(e)}")
            return None
    
    def _get_hairstyle_suitability(self, face_shape, hairstyle_name):
        """
        Determine how suitable a hairstyle is for a given face shape.
        
        Args:
            face_shape: The detected face shape (oval, round, square, heart, diamond, oblong)
            hairstyle_name: The name of the hairstyle
            
        Returns:
            A float between 0.0 and 1.0 indicating suitability (1.0 = perfect match)
        """
        # Convert hairstyle name to lowercase for easier matching
        hairstyle_lower = hairstyle_name.lower()
        
        # Define recommended hairstyles for each face shape
        face_shape_recommendations = {
            'oval': {
                'highly_recommended': ['layered', 'bob', 'pixie', 'bangs', 'side part', 'long', 'wavy', 'straight', 'textured'],
                'not_recommended': ['blow dry', 'round', 'full', 'wide', 'blunt']
            },
            'round': {
                'highly_recommended': ['layered', 'long', 'asymmetric', 'side part', 'pixie', 'angular', 'textured'],
                'not_recommended': ['blow dry', 'bob', 'round', 'full', 'blunt', 'chin length']
            },
            'square': {
                'highly_recommended': ['layered', 'wavy', 'soft', 'side part', 'wispy', 'textured', 'tousled'],
                'not_recommended': ['blow dry', 'blunt', 'straight', 'sleek', 'geometric']
            },
            'heart': {
                'highly_recommended': ['side part', 'chin length', 'bob', 'layered', 'bangs', 'medium', 'wavy'],
                'not_recommended': ['blow dry', 'volume', 'top heavy', 'pixie', 'spiky']
            },
            'diamond': {
                'highly_recommended': ['chin length', 'bob', 'textured', 'side part', 'layered', 'bangs', 'medium'],
                'not_recommended': ['blow dry', 'sleek', 'tight', 'slicked back', 'volume']
            },
            'oblong': {
                'highly_recommended': ['layered', 'bangs', 'wavy', 'side part', 'bob', 'textured', 'volume'],
                'not_recommended': ['blow dry', 'long straight', 'sleek', 'center part', 'vertical volume']
            }
        }
        
        # Default face shape if not recognized
        if face_shape not in face_shape_recommendations:
            face_shape = 'oval'
            
        # Get recommendations for the face shape
        recommendations = face_shape_recommendations[face_shape]
        
        # Calculate suitability score
        suitability = 0.7  # Default medium suitability
        
        # Check if hairstyle contains any highly recommended keywords
        for keyword in recommendations['highly_recommended']:
            if keyword in hairstyle_lower:
                suitability = max(suitability, 0.9)
                break
                
        # Check if hairstyle contains any not recommended keywords
        for keyword in recommendations['not_recommended']:
            if keyword in hairstyle_lower:
                suitability = min(suitability, 0.4)
                break
        
        # Special case for "Blow Dry" hairstyles - explicitly mark as not suitable for most face shapes
        if 'blow dry' in hairstyle_lower or 'blowdry' in hairstyle_lower:
            if face_shape in ['oval', 'round', 'square']:
                suitability = 0.3
        
        return suitability

    def _get_face_bounding_box(self, face_landmarks, img_width, img_height):
        """
        Get the bounding box of the face from landmarks.
        """
        x_min, y_min = img_width, img_height
        x_max, y_max = 0, 0
        
        for landmark in face_landmarks.landmark:
            x, y = int(landmark.x * img_width), int(landmark.y * img_height)
            x_min = min(x_min, x)
            y_min = min(y_min, y)
            x_max = max(x_max, x)
            y_max = max(y_max, y)
        
        return x_min, y_min, x_max, y_max
    
    def _analyze_hairstyle_image(self, hairstyle_img):
        """
        Analyze the hairstyle image to determine its characteristics.
        This helps in better positioning and sizing the hairstyle.
        """
        # Get image dimensions
        h, w = hairstyle_img.shape[:2]
        
        # Create a mask for the hairstyle (non-background parts)
        if hairstyle_img.shape[2] == 4:
            # If image has alpha channel, use it as mask
            mask = hairstyle_img[:,:,3] > 0
        else:
            # Otherwise, create a mask based on color (assuming black background)
            gray = cv2.cvtColor(hairstyle_img, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
            mask = mask > 0
        
        # Find the bounding box of the actual hairstyle in the image
        if np.any(mask):
            # Find rows and columns with non-zero pixels
            rows = np.any(mask, axis=1)
            cols = np.any(mask, axis=0)
            
            # Get the non-empty row and column indices
            row_indices = np.where(rows)[0]
            col_indices = np.where(cols)[0]
            
            if len(row_indices) > 0 and len(col_indices) > 0:
                # Get the bounding box
                y_min, y_max = row_indices[0], row_indices[-1]
                x_min, x_max = col_indices[0], col_indices[-1]
                
                # Calculate actual hairstyle dimensions
                actual_width = x_max - x_min + 1
                actual_height = y_max - y_min + 1
                
                # Calculate aspect ratio
                aspect_ratio = actual_width / actual_height if actual_height > 0 else 1.0
                
                # Calculate how much of the image is actually used by the hairstyle
                coverage = np.sum(mask) / (h * w)
                
                # Determine if the hairstyle is wide, tall, or balanced
                if aspect_ratio > 1.5:
                    style_type = "wide"
                elif aspect_ratio < 0.7:
                    style_type = "tall"
                else:
                    style_type = "balanced"
                
                # Determine if the hairstyle has bangs (hair at the top of the image)
                top_region = mask[:int(h*0.2), :]
                has_bangs = np.sum(top_region) > (top_region.size * 0.1)
                
                # Determine if the hairstyle has side coverage
                left_region = mask[:, :int(w*0.2)]
                right_region = mask[:, int(w*0.8):]
                has_sides = (np.sum(left_region) > (left_region.size * 0.1) or 
                            np.sum(right_region) > (right_region.size * 0.1))
                
                return {
                    "x_min": x_min,
                    "y_min": y_min,
                    "x_max": x_max,
                    "y_max": y_max,
                    "actual_width": actual_width,
                    "actual_height": actual_height,
                    "aspect_ratio": aspect_ratio,
                    "coverage": coverage,
                    "style_type": style_type,
                    "has_bangs": has_bangs,
                    "has_sides": has_sides
                }
        
        # Default values if analysis fails
        return {
            "x_min": 0,
            "y_min": 0,
            "x_max": w-1,
            "y_max": h-1,
            "actual_width": w,
            "actual_height": h,
            "aspect_ratio": w/h if h > 0 else 1.0,
            "coverage": 1.0,
            "style_type": "balanced",
            "has_bangs": False,
            "has_sides": False
        }

    def _calculate_hair_region(self, face_landmarks, img_width, img_height, hairstyle_characteristics=None, face_shape='oval'):
        """
        Calculate the region where the hairstyle should be placed.
        Uses face landmarks, hairstyle characteristics, and face shape for optimal positioning.
        """
        # Get face bounding box
        x_min, y_min, x_max, y_max = self._get_face_bounding_box(face_landmarks, img_width, img_height)
        
        face_width = x_max - x_min
        face_height = y_max - y_min
        face_center_x = (x_min + x_max) // 2
        
        # Get forehead position
        forehead_y = self._get_forehead_position(face_landmarks, img_height)
        
        # Determine hairstyle type based on name
        is_afro = False
        is_long = False
        is_blow_dry = False
        is_buzz_cut = False
        is_low_cut = False
        is_styled_cut = False
        is_braiding = False
        is_wig_extension = False
        is_short_styled = False  # New flag for short styled cuts like the one in the image
        
        if hasattr(self, 'hairstyle_name') and self.hairstyle_name:
            hairstyle_name_lower = self.hairstyle_name.lower()
            # Check for afro-type hairstyles
            afro_keywords = ['afro', 'natural', 'curly', 'coily', 'kinky', 'locks', 'dreadlocks']
            is_afro = any(keyword in hairstyle_name_lower for keyword in afro_keywords)
            
            # Check for braiding styles
            braiding_keywords = ['braid', 'braids', 'braided', 'box braids', 'french braid', 'goddess braids', 'cornrows', 'twist']
            is_braiding = any(keyword in hairstyle_name_lower for keyword in braiding_keywords)
            
            # Check for wigs and hair extensions
            wig_extension_keywords = ['wig', 'extension', 'weave', 'hairpiece', 'blonde', 'layered wig', 'hair attachment']
            is_wig_extension = any(keyword in hairstyle_name_lower for keyword in wig_extension_keywords)
            
            # Check for long hairstyles
            long_keywords = ['long', 'flowing', 'wavy', 'straight']
            is_long = any(keyword in hairstyle_name_lower for keyword in long_keywords)
            
            # Specific check for blow dry
            is_blow_dry = 'blow dry' in hairstyle_name_lower or 'styling' in hairstyle_name_lower
            
            # Specific check for buzz cuts
            buzz_cut_keywords = ['buzz', 'crew', 'military', 'bald']
            is_buzz_cut = any(keyword in hairstyle_name_lower for keyword in buzz_cut_keywords)
            
            # Specific check for low cuts (separate from buzz cuts)
            low_cut_keywords = ['fade', 'taper']  # Removed 'short' and 'low cut' as they're too generic
            is_low_cut = any(keyword in hairstyle_name_lower for keyword in low_cut_keywords)
            
            # Specific check for styled cuts
            styled_cut_keywords = ['styled', 'cut', 'layered', 'bob', 'pixie']
            is_styled_cut = any(keyword in hairstyle_name_lower for keyword in styled_cut_keywords)
            
            # Check for short styled cuts (like the brown styled haircut in the image)
            short_styled_keywords = ['short styled', 'short cut', 'classic cut', 'business cut', 'formal cut', 'gentleman', 'executive']
            is_short_styled = any(keyword in hairstyle_name_lower for keyword in short_styled_keywords)
            
            # Special handling for hairstyles named "low cut" but are actually styled cuts
            if 'low cut' in hairstyle_name_lower and not any(keyword in hairstyle_name_lower for keyword in low_cut_keywords):
                logger.info("Detected styled haircut incorrectly labeled as 'low cut' - applying short styled cut parameters")
                is_low_cut = False
                is_short_styled = True
        
        # Apply hairstyle-specific adjustments first, then face shape adjustments
        # This ensures that the hairstyle type is the primary factor in positioning
        
        # Default values
        top_extension = 0.4  # How much to extend above the face
        side_extension = 0.15  # How much to extend to the sides
        height_multiplier = 0.7  # Height relative to face
        width_multiplier = 1.3  # Width relative to face
        vertical_offset = 0  # Vertical adjustment (positive moves down)
        
        # Hairstyle-specific adjustments (these take priority)
        if is_buzz_cut:
            # Buzz cuts need to closely follow the head shape
            top_extension = 0.03  # Almost no space above for buzz cuts
            side_extension = 0.01  # Minimal space on sides
            height_multiplier = 0.45  # Much shorter to follow head shape
            width_multiplier = 1.05  # Just barely wider than the head
            vertical_offset = int(face_height * -0.12)  # Move up significantly to fit closer to the head
        elif is_low_cut:
            # Low cuts need to follow the head shape but with a bit more room
            top_extension = 0.0  # No space above for low cuts
            side_extension = 0.0  # No side padding
            height_multiplier = 0.7  # Extremely short to follow head shape closely
            width_multiplier = 1.2  # Exactly match head width
            vertical_offset = int(face_height * -0.1)  # Move up extremely high to position on top of head
        elif is_styled_cut:
            # Styled cuts like the one in your test image
            top_extension = 0.15  # Some space above for styled hair
            side_extension = 0.15  # Some side padding for styled hair
            height_multiplier = 0.75  # Height for styled cut
            width_multiplier = 1.27  # Width for styled cut
            vertical_offset = int(face_height * -0.25)  # Move up to position correctly on head

        elif is_wig_extension:
            # Wigs and hair extensions need specific positioning
            top_extension = 0.05  # Minimal space above for better positioning
            side_extension = 0.2  # Adequate space on sides for layered look
            height_multiplier = 0.9  # Slightly shorter than full height
            width_multiplier = 1.35  # Wider for layered look
            vertical_offset = int(face_height * -0.2)  # Move up to position correctly on head
            # Check for blonde layered wig specifically
            if 'blonde' in hairstyle_name_lower and ('layered' in hairstyle_name_lower or 'wig' in hairstyle_name_lower):
                logger.info("Detected blonde layered wig/extension - applying specialized positioning")
                top_extension = 0.3  # Very little space above
                side_extension = 0.5  # Specific side spacing for this style
                height_multiplier = 1.0  # Specific height for this style
                width_multiplier = 1.9  # Specific width for this style
                vertical_offset = int(face_height * -1.5)  # Move up significantly more to avoid covering eyes

        elif is_afro:
            # Afro styles need more space all around
            top_extension = 0.6  # More space above for volume
            side_extension = 0.4  # More space on sides for volume
            height_multiplier = 1.0  # Full height for afro volume
            width_multiplier = 1.8  # Wider for afro volume
            vertical_offset = int(face_height * -1.5)  # Move up to position correctly
        elif is_long:
            # Long styles need more height
            top_extension = 0.3  # Space above
            side_extension = 0.2  # Space on sides
            height_multiplier = 1.2  # Taller for long hair
            width_multiplier = 1.4  # Wider for framing
            vertical_offset = int(face_height * -0.05)  # Move up slightly
        elif is_blow_dry:
            # Blow dry styles need width
            top_extension = 0.2  # Space above
            side_extension = 0.3  # More space on sides
            height_multiplier = 0.85  # Not too tall
            width_multiplier = 1.7  # Wider for blow dry volume
            vertical_offset = int(face_height * 0.02)  # Move down slightly
        elif is_wig_extension:
            # Wigs and hair extensions need more space
            top_extension = 0.4  # More space above for volume
            side_extension = 0.3  # More space on sides for volume
            height_multiplier = 1.0  # Full height for volume
            width_multiplier = 1.5  # Wider for volume
            vertical_offset = int(face_height * -0.1)  # Move up slightly
        elif is_short_styled:
            # Short styled cuts need specific positioning
            top_extension = 0.1  # Minimal space above
            side_extension = 0.1  # Minimal space on sides
            height_multiplier = 0.6  # Shorter for styled cut
            width_multiplier = 1.2  # Wider for framing
            vertical_offset = int(face_height * -0.1)  # Move up slightly
        
        # Now apply face shape specific adjustments (these are secondary)
        if face_shape == 'oval':
            if is_blow_dry:
                # Fine-tune blow dry for oval faces
                side_extension = max(side_extension, 0.35)
                width_multiplier = max(width_multiplier, 1.9)
            elif is_buzz_cut:
                # Fine-tune buzz cut for oval faces
                vertical_offset = max(vertical_offset, int(face_height * -0.06))
            elif is_low_cut:
                # Fine-tune low cut for oval faces
                vertical_offset = max(vertical_offset, int(face_height * -0.04))
        elif face_shape == 'round':
            # Round faces need height and less width
            if not (is_buzz_cut or is_low_cut):  # Don't modify these for buzz/low cuts
                top_extension = max(top_extension, 0.5)  # More height
                side_extension = min(side_extension, 0.1)  # Less width
            if is_buzz_cut:
                # Fine-tune buzz cut for round faces
                width_multiplier = min(width_multiplier, 1.1)  # Narrower
                vertical_offset = max(vertical_offset, int(face_height * -0.07))
            elif is_low_cut:
                # Fine-tune low cut for round faces
                width_multiplier = min(width_multiplier, 1.2)  # Narrower
                vertical_offset = max(vertical_offset, int(face_height * -0.05))
        elif face_shape == 'square':
            # Square faces need softening at the sides
            if not (is_buzz_cut or is_low_cut):  # Don't modify these for buzz/low cuts
                side_extension = max(side_extension, 0.2)
            if is_buzz_cut:
                # Fine-tune buzz cut for square faces
                width_multiplier = min(width_multiplier, 1.15)  # Narrower
                vertical_offset = max(vertical_offset, int(face_height * -0.06))
            elif is_low_cut:
                # Fine-tune low cut for square faces
                width_multiplier = min(width_multiplier, 1.25)  # Narrower
                vertical_offset = max(vertical_offset, int(face_height * -0.04))
        elif face_shape == 'heart':
            # Heart faces need width at the jaw
            if is_buzz_cut:
                # Fine-tune buzz cut for heart faces
                width_multiplier = min(width_multiplier, 1.1)  # Narrower
                vertical_offset = max(vertical_offset, int(face_height * -0.08))
            elif is_low_cut:
                # Fine-tune low cut for heart faces
                width_multiplier = min(width_multiplier, 1.2)  # Narrower
                vertical_offset = max(vertical_offset, int(face_height * -0.06))
        elif face_shape == 'diamond':
            # Diamond faces need width at forehead and jaw
            if is_buzz_cut:
                # Fine-tune buzz cut for diamond faces
                width_multiplier = min(width_multiplier, 1.15)  # Narrower
                vertical_offset = max(vertical_offset, int(face_height * -0.07))
            elif is_low_cut:
                # Fine-tune low cut for diamond faces
                width_multiplier = min(width_multiplier, 1.25)  # Narrower
                vertical_offset = max(vertical_offset, int(face_height * -0.05))
        elif face_shape == 'oblong':
            # Oblong faces need width and less height
            if not (is_buzz_cut or is_low_cut):  # Don't modify these for buzz/low cuts
                top_extension = min(top_extension, 0.2)
                side_extension = max(side_extension, 0.3)
                height_multiplier = min(height_multiplier, 0.6)
            if is_buzz_cut:
                # Fine-tune buzz cut for oblong faces
                width_multiplier = max(width_multiplier, 1.3)  # Wider
                vertical_offset = max(vertical_offset, int(face_height * -0.04))
            elif is_low_cut:
                # Fine-tune low cut for oblong faces
                width_multiplier = max(width_multiplier, 1.4)  # Wider
                vertical_offset = max(vertical_offset, int(face_height * -0.02))
        
        # Calculate top of head
        top_of_head_y = max(0, y_min - int(face_height * top_extension))
        
        # Apply vertical offset (positive moves down)
        hair_y = top_of_head_y + vertical_offset
        
        # For blow dry styles, make special adjustments
        if is_blow_dry:
            # Calculate height to cover from top of head to bottom of face
            hair_height = int((y_max - top_of_head_y) * height_multiplier)
            
            # Center the hairstyle on the face
            hair_width = int(face_width * width_multiplier)
            hair_x = max(0, face_center_x - (hair_width // 2))
            
            # Ensure it doesn't go off the image
            if hair_x + hair_width > img_width:
                hair_x = max(0, img_width - hair_width)
                
            # For blow dry styles, ensure the hairstyle doesn't extend too far below the chin
            max_hair_bottom = min(img_height, y_max + int(face_height * 0.15))
            if hair_y + hair_height > max_hair_bottom:
                hair_height = max_hair_bottom - hair_y
        else:
            # For other styles, use the standard calculations
            hair_height = int((y_max - top_of_head_y) * height_multiplier)
            hair_x = max(0, x_min - int(face_width * side_extension))
            hair_width = min(img_width - hair_x, int(face_width * width_multiplier))
        
        return {
            'x': hair_x,
            'y': hair_y,
            'width': hair_width,
            'height': hair_height
        }

    def _get_forehead_position(self, face_landmarks, img_height):
        """
        Get the y-coordinate of the forehead from face landmarks.
        """
        # MediaPipe face mesh indices for the forehead region
        forehead_indices = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323]
        
        # Get the y-coordinates of the forehead landmarks
        forehead_y_coords = [int(face_landmarks.landmark[idx].y * img_height) for idx in forehead_indices]
        
        # Return the average y-coordinate
        return sum(forehead_y_coords) // len(forehead_y_coords)

    def _extract_skin_tone(self, user_img, face_landmarks):
        """
        Extract the average skin tone from the user's face.
        """
        # Convert to RGB for better color analysis
        user_img_rgb = cv2.cvtColor(user_img, cv2.COLOR_BGR2RGB)
        h, w, _ = user_img.shape
        
        # Create a mask for the face region
        face_mask = np.zeros((h, w), dtype=np.uint8)
        
        # Get specific landmarks for forehead and cheeks (avoiding eyes, nose, mouth)
        # Forehead landmarks (approximate)
        forehead_landmarks = [10, 67, 69, 104, 108, 151, 337, 338, 297, 299, 332, 333]
        # Cheek landmarks (approximate)
        cheek_landmarks = [34, 36, 115, 137, 138, 169, 170, 234, 264, 361, 367, 397, 401, 435]
        
        # Draw filled polygons for these regions
        forehead_points = []
        cheek_points = []
        
        for idx, landmark in enumerate(face_landmarks.landmark):
            x, y = int(landmark.x * w), int(landmark.y * h)
            if idx in forehead_landmarks:
                forehead_points.append((x, y))
            if idx in cheek_landmarks:
                cheek_points.append((x, y))
        
        if forehead_points:
            cv2.fillPoly(face_mask, [np.array(forehead_points)], 255)
        if cheek_points:
            cv2.fillPoly(face_mask, [np.array(cheek_points)], 255)
        
        # If we couldn't get specific landmarks, use a simpler approach
        if not forehead_points and not cheek_points:
            # Get face bounding box
            x_min, y_min, x_max, y_max = self._get_face_bounding_box(face_landmarks, w, h)
            face_width = x_max - x_min
            face_height = y_max - y_min
            
            # Create a mask for the upper cheeks (likely to be skin tone)
            cheek_y = y_min + int(face_height * 0.3)
            cheek_height = int(face_height * 0.2)
            left_cheek_x = x_min + int(face_width * 0.1)
            left_cheek_width = int(face_width * 0.25)
            right_cheek_x = x_max - int(face_width * 0.35)
            right_cheek_width = int(face_width * 0.25)
            
            # Draw filled rectangles for cheeks
            cv2.rectangle(face_mask, (left_cheek_x, cheek_y), 
                          (left_cheek_x + left_cheek_width, cheek_y + cheek_height), 255, -1)
            cv2.rectangle(face_mask, (right_cheek_x, cheek_y), 
                          (right_cheek_x + right_cheek_width, cheek_y + cheek_height), 255, -1)
        
        # Extract skin tone from the masked regions
        skin_pixels = user_img_rgb[face_mask > 0]
        
        if len(skin_pixels) > 0:
            # Calculate average skin tone
            avg_skin_tone = np.mean(skin_pixels, axis=0).astype(np.uint8)
            return avg_skin_tone
        else:
            # Default if no skin pixels found
            return np.array([150, 120, 100])  # Default skin tone
    
    def _create_hairstyle_mask(self, hairstyle_img):
        """
        Create a mask for the hairstyle.
        """
        # If the hairstyle has an alpha channel, use it as the mask
        if hairstyle_img.shape[2] == 4:
            return hairstyle_img[:,:,3] / 255.0
        
        # Otherwise, create a mask based on color (assuming black background)
        gray = cv2.cvtColor(hairstyle_img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        
        # Create feathered edges for smoother blending
        feather_size = int(min(hairstyle_img.shape[0], hairstyle_img.shape[1]) * 0.15)
        kernel = np.ones((feather_size, feather_size), np.uint8)
        mask_feathered = cv2.erode(mask, kernel)
        mask_feathered = cv2.GaussianBlur(mask_feathered, (feather_size*2+1, feather_size*2+1), 0)
        
        return mask_feathered / 255.0
    
    def _blend_images(self, user_img, hairstyle_img, hair_region, hairstyle_mask, skin_tone=None):
        """
        Blend the hairstyle onto the user's image.
        
        Args:
            user_img: User's image
            hairstyle_img: Hairstyle image
            hair_region: Region where to place the hairstyle
            hairstyle_mask: Mask for the hairstyle
            skin_tone: User's skin tone for color correction
            
        Returns:
            Blended image
        """
        # Create a copy of the user image to work with
        result = user_img.copy()
        
        # Get dimensions
        h, w, _ = user_img.shape
        hair_h, hair_w = hairstyle_img.shape[:2]
        
        # Get the region coordinates
        x, y = hair_region['x'], hair_region['y']
        
        # Check if this is a buzz cut (for special blending)
        is_buzz_cut = False
        if hasattr(self, 'hairstyle_name') and self.hairstyle_name:
            buzz_cut_keywords = ['buzz', 'crew', 'fade', 'short', 'military', 'bald']
            is_buzz_cut = any(keyword in self.hairstyle_name.lower() for keyword in buzz_cut_keywords)
        
        # Adjust kernel size based on hairstyle type
        kernel_size = 15
        if is_buzz_cut:
            kernel_size = 10  # Smaller kernel for buzz cuts for sharper edges
        else:
            kernel_size = 25  # Larger kernel for other styles for smoother blending
        
        # Check if hairstyle has alpha channel
        if hairstyle_img.shape[2] == 4:
            # Split the hairstyle image into color and alpha channels
            hairstyle_rgb = hairstyle_img[:, :, :3]
            alpha = hairstyle_img[:, :, 3] / 255.0
            
            # Apply color correction if skin tone is provided
            if skin_tone is not None:
                hairstyle_rgb = self._color_correct_hairstyle(hairstyle_rgb, skin_tone)
            
            # Create a region of interest (ROI) in the result image
            roi_y_end = min(y + hair_h, h)
            roi_x_end = min(x + hair_w, w)
            roi = result[y:roi_y_end, x:roi_x_end]
            
            # Calculate the portion of the hairstyle that fits in the ROI
            hairstyle_portion_h = roi_y_end - y
            hairstyle_portion_w = roi_x_end - x
            
            # Resize alpha to match the ROI dimensions
            alpha_resized = alpha[:hairstyle_portion_h, :hairstyle_portion_w]
            
            # Reshape alpha to allow broadcasting
            alpha_3d = np.stack([alpha_resized] * 3, axis=2)
            
            # Apply feathered blending at the edges for smoother transition
            feathered_alpha = self._create_feathered_alpha(alpha_resized, kernel_size=kernel_size)
            feathered_alpha_3d = np.stack([feathered_alpha] * 3, axis=2)
            
            # For buzz cuts, enhance the alpha to make it more defined
            if is_buzz_cut:
                # Enhance contrast of the alpha channel for buzz cuts
                feathered_alpha_3d = np.power(feathered_alpha_3d, 0.8)  # Increase contrast
            
            # Blend the hairstyle with the user image using the feathered alpha
            blended_roi = (hairstyle_rgb[:hairstyle_portion_h, :hairstyle_portion_w] * feathered_alpha_3d) + \
                         (roi * (1 - feathered_alpha_3d))
            
            # Update the ROI in the result image
            result[y:roi_y_end, x:roi_x_end] = blended_roi
        else:
            # For images without alpha channel, use the mask
            mask_resized = cv2.resize(hairstyle_mask, (hair_w, hair_h))
            
            # Apply color correction if skin tone is provided
            if skin_tone is not None:
                hairstyle_img = self._color_correct_hairstyle(hairstyle_img, skin_tone)
            
            # Create a region of interest (ROI) in the result image
            roi_y_end = min(y + hair_h, h)
            roi_x_end = min(x + hair_w, w)
            roi = result[y:roi_y_end, x:roi_x_end]
            
            # Calculate the portion of the hairstyle that fits in the ROI
            hairstyle_portion_h = roi_y_end - y
            hairstyle_portion_w = roi_x_end - x
            
            # Resize mask to match the ROI dimensions
            mask_portion = mask_resized[:hairstyle_portion_h, :hairstyle_portion_w]
            
            # Apply feathered blending at the edges for smoother transition
            feathered_mask = self._create_feathered_alpha(mask_portion, kernel_size=kernel_size)
            feathered_mask_3d = np.stack([feathered_mask] * 3, axis=2)
            
            # Blend the hairstyle with the user image using the feathered mask
            blended_roi = (hairstyle_img[:hairstyle_portion_h, :hairstyle_portion_w] * feathered_mask_3d) + \
                         (roi * (1 - feathered_mask_3d))
            
            # Update the ROI in the result image
            result[y:roi_y_end, x:roi_x_end] = blended_roi
        
        return result
    
    def _create_feathered_alpha(self, alpha, kernel_size=15):
        """
        Create a feathered alpha mask for smoother edge blending.
        
        Args:
            alpha: Original alpha channel or mask
            kernel_size: Size of the blur kernel for feathering
            
        Returns:
            Feathered alpha mask
        """
        # Apply Gaussian blur to create feathered edges
        feathered = cv2.GaussianBlur(alpha.astype(np.float32), (kernel_size, kernel_size), 0)
        
        # Apply additional edge softening for more natural transitions
        # Create a gradient falloff near the edges
        edge_mask = cv2.Canny(alpha.astype(np.uint8) * 255, 50, 150)
        edge_mask = cv2.dilate(edge_mask, np.ones((3, 3), np.uint8), iterations=2)
        edge_mask = cv2.GaussianBlur(edge_mask, (kernel_size, kernel_size), 0) / 255.0
        
        # Reduce alpha values near edges
        feathered = feathered * (1.0 - edge_mask * 0.3)
        
        # Normalize to ensure values are between 0 and 1
        feathered = np.clip(feathered, 0, 1)
        
        return feathered

    def _color_correct_hairstyle(self, hairstyle_img, skin_tone):
        """
        Adjust the hairstyle colors to better match the user's skin tone.
        """
        # Convert to HSV for better color manipulation
        hairstyle_hsv = cv2.cvtColor(hairstyle_img, cv2.COLOR_BGR2HSV).astype(np.float32)
        
        # Convert skin tone to HSV
        skin_tone_bgr = skin_tone[::-1]  # RGB to BGR
        skin_tone_bgr = np.array([[skin_tone_bgr]], dtype=np.uint8)
        skin_tone_hsv = cv2.cvtColor(skin_tone_bgr, cv2.COLOR_BGR2HSV)[0][0]
        
        # Calculate average color of the hairstyle
        mask = cv2.cvtColor(hairstyle_img, cv2.COLOR_BGR2GRAY) > 10
        if np.sum(mask) > 0:
            hairstyle_avg_color = np.mean(hairstyle_img[mask], axis=0)
            hairstyle_avg_color_bgr = np.array([[hairstyle_avg_color]], dtype=np.uint8)
            hairstyle_avg_hsv = cv2.cvtColor(hairstyle_avg_color_bgr, cv2.COLOR_BGR2HSV)[0][0]
        else:
            hairstyle_avg_hsv = np.array([0, 0, 128], dtype=np.uint8)
        
        # Calculate color correction factors
        # We'll adjust saturation and value based on skin tone
        # but keep the hue of the hairstyle
        s_factor = min(max(skin_tone_hsv[1] / max(hairstyle_avg_hsv[1], 1), 0.7), 1.3)
        v_factor = min(max(skin_tone_hsv[2] / max(hairstyle_avg_hsv[2], 1), 0.7), 1.3)
        
        # Apply correction factors
        # Adjust saturation and value while preserving hue
        hairstyle_hsv[:,:,1] = np.clip(hairstyle_hsv[:,:,1] * s_factor, 0, 255)
        hairstyle_hsv[:,:,2] = np.clip(hairstyle_hsv[:,:,2] * v_factor, 0, 255)
        
        # Convert back to BGR
        hairstyle_corrected = cv2.cvtColor(hairstyle_hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
        return hairstyle_corrected