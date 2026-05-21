from app import app
import io

app.config['TESTING'] = True
with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user'] = 'Riya-21'
        sess['lang'] = 'en'
    
    # Submit the predict form
    data = {
        'name': 'Riya Arora',
        'age': '22',
        'gender': 'Female',
        'high body temp': 'on',
        'fever_value': '102',
        'cough': 'on',
        'cough_level': '5',
        'medical_report': (io.BytesIO(b"%PDF-1.4\n%EOF\n"), 'dummy.pdf')
    }
    
    response = client.post('/predict', data=data, content_type='multipart/form-data')
    html = response.data.decode('utf-8')
    if 'Blood Report Factored into Diagnosis' in html:
        print('SUCCESS: Found "Blood Report Factored into Diagnosis" in response.')
    else:
        print('FAILED: Could not find the expected string in response.')
