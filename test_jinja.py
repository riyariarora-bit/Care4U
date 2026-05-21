from jinja2 import Environment, FileSystemLoader
import os

def test_template():
    env = Environment(loader=FileSystemLoader('.'))
    try:
        template = env.get_template('templates/DoctorDashboard.html')
        print("Template parsed successfully!")
        
        # Mock data
        mock_context = {
            'user_data': {'name': 'Test Dr', 'specialization': 'Test Spec', 'license': '12345'},
            'username': 'test_dr',
            'current_lang': 'en',
            'pending_requests': [
                {
                    'name': 'Patient A',
                    'username': 'patient_a',
                    'summary': {
                        'disease': 'Test Cold',
                        'urgency': 'High',
                        'symptoms': 'cough',
                        'duration': '2 days'
                    }
                }
            ],
            'patients': [],
            'pending_count': 1,
            '_': lambda x: x
        }
        
        # render to check for runtime errors
        template.render(mock_context)
        print("Template rendered successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

test_template()
