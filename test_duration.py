from app import app
import io
import csv
import json

app.config['TESTING'] = True
with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user'] = 'Riya-21'
        sess['lang'] = 'en'
    
    # Submit the predict form with symptom duration
    data = {
        'name': 'Riya Arora',
        'age': '22',
        'gender': 'Female',
        'high body temp': 'on',
        'fever_value': '102',
        'cough': 'on',
        'cough_level': '5',
        'symptom_duration': '4-7 days',
    }
    
    print("Testing /predict route with symptom_duration...")
    response = client.post('/predict', data=data, content_type='multipart/form-data')
    
    # Verify the CSV row was written with the expected symptom duration
    print("\nVerifying dataset insertion...")
    with open('symptoms_dataset.csv', 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        last_row = reader[-1]
        
        if last_row.get('symptom_duration') == '4-7 days':
            print('SUCCESS: "symptom_duration" correctly saved as "4-7 days" in dataset.')
        else:
            print(f"FAILED: Expected '4-7 days', found '{last_row.get('symptom_duration')}'.")
            
    # Test if History renders it
    print("\nTesting /history route...")
    history_response = client.get('/history')
    html = history_response.data.decode('utf-8')
    
    if '⏳ 4-7 days' in html:
        print('SUCCESS: Found "⏳ 4-7 days" rendered in History HTML.')
    else:
        print('FAILED: Could not find the expected duration string in History HTML.')
