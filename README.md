# Personalised Hairstyling System

A comprehensive salon management system with advanced AI-powered virtual hair try-on capabilities. This system helps salon owners manage appointments, services, inventory, and payments while providing customers with a unique virtual hairstyling experience.

## Features

- **User Management**
  - Role-based access control (admin, stylist, customer)
  - User profiles and authentication
  - Customer management

- **Appointment Scheduling**
  - Online booking system
  - Calendar integration
  - Appointment reminders and notifications

- **Virtual Hair Try-On**
  - AI-powered virtual hairstyle simulation
  - Face analysis for style recommendations
  - Preview different hair colors and styles

- **Service Management**
  - Service catalog with pricing
  - Service customization options
  - Service image gallery

- **Payment Processing**
  - Secure payment integration with Stripe
  - Invoice generation
  - Payment history tracking

- **Inventory Management**
  - Stock tracking
  - Low stock alerts
  - Product management

- **Reporting & Analytics**
  - Sales reports
  - Stylist performance metrics
  - Customer analytics

- **Communication Tools**
  - In-app messaging system
  - Notification center
  - Customer feedback

## Technology Stack

- **Backend**: Django 5.1.3
- **Database**: PostgreSQL
- **Frontend**: HTML, CSS, JavaScript
- **AI Components**: PyTorch, OpenCV, Diffusers
- **Payment Processing**: Stripe
- **PDF Generation**: xhtml2pdf, reportlab

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Git

### Setup Instructions

1. Clone the repository:
   ```
   git clone https://github.com/Keithpaul98/Personalised-Hairstyle-System.git
   cd Personalised-Hairstyling-System
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   cd salon_management
   pip install -r requirements.txt
   ```

4. Configure the database:
   - Create a PostgreSQL database named 'Impact_Looks'
   - Update database settings in `salon_management/settings.py` if needed

5. Apply migrations:
   ```
   python manage.py migrate
   ```

6. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

7. Run the development server:
   ```
   python manage.py runserver
   ```

8. Access the application at http://127.0.0.1:8000/

## Usage

### Admin Dashboard

Access the admin dashboard at http://127.0.0.1:8000/admin/ to manage users, services, and system settings.

### Virtual Hair Try-On

1. Upload a customer photo
2. Select hairstyles and colors to try
3. Generate AI-powered previews
4. Save and share results with customers

### Appointment Booking

1. Browse available services
2. Select preferred stylist and time slot
3. Confirm booking
4. Receive confirmation notifications

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions or support, please contact [your-email@example.com](mailto:your-email@example.com).

## Acknowledgments

- Perfect Corp API for face analysis capabilities
- Stripe for payment processing
- All contributors to the project
