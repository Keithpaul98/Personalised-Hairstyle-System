import cv2
import numpy as np
import mediapipe as mp
import logging

logger = logging.getLogger(__name__)

def normalize_vector(v):
    """
    Simple normalization function to replace sklearn's normalize
    """
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm

class FaceShapeAnalyzer:
    """
    Class to analyze face shape using MediaPipe face mesh.
    """
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Define key landmark indices for face shape analysis
        # Based on MediaPipe Face Mesh 468 points
        self.FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
        
        # Forehead points
        self.FOREHEAD = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323]
        
        # Cheekbone points
        self.CHEEKBONES = [123, 50, 205, 425, 36, 142, 361, 288, 397, 365]
        
        # Jawline points
        self.JAWLINE = [172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288, 361]
        
        # Chin point
        self.CHIN = [152]
    
    def analyze_face_shape(self, image_path):
        """
        Analyze the face shape from an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            A dictionary with face shape analysis results
        """
        try:
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image from {image_path}")
            
            # Convert to RGB for MediaPipe
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Process the image with MediaPipe Face Mesh
            with self.mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5) as face_mesh:
                
                results = face_mesh.process(image_rgb)
                
                if not results.multi_face_landmarks:
                    return {
                        'success': False,
                        'error': 'No face detected in the image'
                    }
                
                # Get the first face
                face_landmarks = results.multi_face_landmarks[0]
                
                # Get image dimensions
                h, w, _ = image.shape
                
                # Extract key measurements
                measurements = self._extract_measurements(face_landmarks, w, h)
                
                # Determine face shape
                face_shape, confidence = self._determine_face_shape(measurements)
                
                # Create a visualization of the face mesh
                annotated_image = self._create_visualization(image.copy(), face_landmarks, w, h)
                
                return {
                    'success': True,
                    'face_shape': face_shape,
                    'confidence': confidence,
                    'measurements': measurements,
                    'annotated_image': annotated_image
                }
                
        except Exception as e:
            logger.error(f"Error analyzing face shape: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_measurements(self, face_landmarks, img_width, img_height):
        """
        Extract key measurements from face landmarks.
        """
        # Convert landmarks to numpy array of (x, y) coordinates
        landmarks = np.array([(lm.x * img_width, lm.y * img_height) for lm in face_landmarks.landmark])
        
        # Extract forehead width (top 1/3 of face)
        forehead_points = landmarks[[10, 338, 297, 332, 284, 251, 389, 356, 454, 323]]
        forehead_width = np.max(forehead_points[:, 0]) - np.min(forehead_points[:, 0])
        
        # Extract cheekbone width (middle 1/3 of face)
        cheekbone_points = landmarks[[123, 50, 205, 425, 36, 142, 361, 288, 397, 365]]
        cheekbone_width = np.max(cheekbone_points[:, 0]) - np.min(cheekbone_points[:, 0])
        
        # Extract jawline width (bottom 1/3 of face)
        jawline_points = landmarks[[172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288, 361]]
        jawline_width = np.max(jawline_points[:, 0]) - np.min(jawline_points[:, 0])
        
        # Extract face height
        top_point = np.min(landmarks[self.FOREHEAD, 1])
        bottom_point = np.max(landmarks[self.CHIN, 1])
        face_height = bottom_point - top_point
        
        # Calculate key ratios
        face_width_ratio = cheekbone_width / face_height  # Width to height ratio
        jaw_width_ratio = jawline_width / cheekbone_width  # Jaw width to cheekbone width
        forehead_width_ratio = forehead_width / cheekbone_width  # Forehead width to cheekbone width
        
        return {
            'face_width_ratio': face_width_ratio,
            'jaw_width_ratio': jaw_width_ratio,
            'forehead_width_ratio': forehead_width_ratio,
            'cheekbone_width': cheekbone_width,
            'face_height': face_height
        }
    
    def _determine_face_shape(self, measurements):
        """
        Determine face shape based on measurements.
        
        Returns:
            Tuple of (face_shape, confidence)
        """
        # Extract key ratios
        face_width_ratio = measurements['face_width_ratio']
        jaw_width_ratio = measurements['jaw_width_ratio']
        forehead_width_ratio = measurements['forehead_width_ratio']
        
        # Define face shape classification rules based on ratios
        # These thresholds are based on general guidelines and may need adjustment
        
        # Oval face: balanced proportions
        if (0.65 <= face_width_ratio <= 0.75 and
            0.85 <= jaw_width_ratio <= 0.95 and
            0.9 <= forehead_width_ratio <= 1.1):
            return 'oval', 0.9
        
        # Round face: wider at cheekbones, similar width and height
        elif (face_width_ratio >= 0.8 and
              jaw_width_ratio >= 0.9 and
              forehead_width_ratio >= 0.9):
            return 'round', 0.85
        
        # Square face: strong jawline, similar width at forehead, cheekbones, and jawline
        elif (0.75 <= face_width_ratio <= 0.85 and
              jaw_width_ratio >= 0.9 and
              forehead_width_ratio >= 0.9):
            return 'square', 0.85
        
        # Heart face: wider forehead, narrower jawline
        elif (0.65 <= face_width_ratio <= 0.75 and
              jaw_width_ratio <= 0.8 and
              forehead_width_ratio >= 1.0):
            return 'heart', 0.8
        
        # Diamond face: narrow forehead and jawline, wider cheekbones
        elif (0.65 <= face_width_ratio <= 0.75 and
              jaw_width_ratio <= 0.8 and
              forehead_width_ratio <= 0.9):
            return 'diamond', 0.8
        
        # Oblong face: longer face with similar widths
        elif (face_width_ratio < 0.65 and
              0.85 <= jaw_width_ratio <= 1.1 and
              0.9 <= forehead_width_ratio <= 1.1):
            return 'oblong', 0.8
        
        # Default to oval if no clear match
        else:
            return 'oval', 0.6
    
    def _create_visualization(self, image, face_landmarks, img_width, img_height):
        """
        Create a visualization of the face mesh and key measurements.
        """
        # Draw the face mesh
        self.mp_drawing.draw_landmarks(
            image=image,
            landmark_list=face_landmarks,
            connections=self.mp_face_mesh.FACEMESH_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_tesselation_style()
        )
        
        # Draw the face contours
        self.mp_drawing.draw_landmarks(
            image=image,
            landmark_list=face_landmarks,
            connections=self.mp_face_mesh.FACEMESH_CONTOURS,
            landmark_drawing_spec=None,
            connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_contours_style()
        )
        
        return image