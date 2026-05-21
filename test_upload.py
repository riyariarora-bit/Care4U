import requests

session = requests.Session()

# Login
login_data = {
    'username': 'Riya-21',
    'password': 'Ycis2017'
}
login_url = 'http://127.0.0.1:5000/login'
res = session.post(login_url, data=login_data)

if 'Riya-21' not in res.text and 'Logout' not in res.text and res.url != 'http://127.0.0.1:5000/dashboard':
    print('Login failed.')
    # Actually, redirection happens.
    
predict_url = 'http://127.0.0.1:5000/predict'
with open('dummy_report.pdf', 'rb') as f:
    files = {'medical_report': ('dummy_report.pdf', f, 'application/pdf')}
    data = {
        'name': 'Riya Arora',
        'age': '22',
        'gender': 'Female',
        'high body temp': 'on',
        'fever_value': '102',
        'cough': 'on',
        'cough_level': '5'
    }
    res2 = session.post(predict_url, data=data, files=files)
    
if 'Blood Report Factored into Diagnosis' in res2.text:
    print('SUCCESS: Found "Blood Report Factored into Diagnosis" in response.')
else:
    print('FAILED: Could not find the expected string in response.')
