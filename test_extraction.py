from app import extract_keywords_from_file, app
import os

# Test with a PDF
test_file_pdf = "rx_56c1cd92379348c2abdae6368069496a.pdf"
orig_name_pdf = "Prescription_Eye.pdf"

# Test with an Image
test_file_img = "rx_38be050355144cccbfc36954fc996498.png"
orig_name_img = "test_image.png"

def run_test(test_file, orig_name):
    print(f"\n--- Testing extraction for: {test_file} ({orig_name}) ---")
    with app.app_context():
        result = extract_keywords_from_file(test_file, orig_name)
        print("\nEXTRACTED TEXT:")
        print("-" * 20)
        print(result if result else "[No text extracted]")
        print("-" * 20)
        
        # Simulated disease prediction check
        keywords = ['urc', 'cold', 'flu', 'congestion', 'cough', 'throat', 'rhinitis', 'fever', 'eye']
        found = [k for k in keywords if k in result.lower()]
        print(f"\nKeywords Found: {found}")

run_test(test_file_pdf, orig_name_pdf)
run_test(test_file_img, orig_name_img)
