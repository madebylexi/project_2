import os
import json
from flask import Flask, request, redirect, render_template
from google.cloud import storage
import google.generativeai as genai

# Initialize Flask app
app = Flask(__name__, template_folder='templates')

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket_name = "pr1images-bucket"

# Configure Gemini API key
genai.configure(api_key=os.environ['GEMINI_API'])

# Configure generation model for captions
generation_config = {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 50,
    "max_output_tokens": 512,
    "response_mime_type": "application/json",
}

model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

PROMPT = """Analyze the image and provide a short, concise title followed by a detailed description.
Respond in JSON format:  
{
  "title": "<A meaningful, short title>",
  "description": "<A clear and accurate description>"
}"""

@app.route('/')
def index():
    """Display file upload form and list of uploaded files."""
    index_html = """
    <form method="post" enctype="multipart/form-data" action="/upload">
        <div>
            <label for="file">Choose file to upload</label>
            <input type="file" id="file" name="form_file" accept="image/*"/>
        </div>
        <div>
            <button>Submit</button>
        </div>
    </form>
    <ul>
    """
    try:
        for file in get_list_of_files():
            if not file.endswith('.json'):
                index_html += f'<li><a href="/files/{file}" target="_blank">{file}</a></li>'
    except Exception as e:
        index_html += f"<li>Error fetching files: {str(e)}</li>"
    
    index_html += "</ul>"
    return index_html

@app.route('/upload', methods=["POST"])
def upload():
    """Handle image upload, generate caption/description, and save JSON."""
    file = request.files.get('form_file')
    if not file:
        return "No file uploaded.", 400

    filename = file.filename
    try:
        # Upload image to Google Cloud Storage
        local_file_path = upload_file(file)
        
        # Generate caption/description using Gemini AI
        generate_description_and_caption(filename)

        return redirect("/")
    except Exception as e:
        print(f"Error during upload or AI processing: {str(e)}")
        return f"Error during upload or AI processing: {str(e)}", 500

@app.route('/files/<filename>')
def view_file(filename):
    """Display image and its AI-generated title and description."""
    json_filename = f"{filename.rsplit('.', 1)[0]}.json"
    try:
        ai_response = get_ai_response(json_filename)
    except Exception as e:
        return f"Error fetching AI response: {str(e)}", 500
    
    return render_template('view_image.html', filename=filename, ai_response=ai_response, bucket_name=bucket_name)

def get_list_of_files():
    """Lists all files in the Google Cloud Storage bucket."""
    blobs = storage_client.list_blobs(bucket_name)
    return [blob.name for blob in blobs]

def upload_file(file):
    """Uploads a file to Google Cloud Storage and saves it locally in the container."""
    local_file_path = os.path.join("/app/files", file.filename)
    os.makedirs("/app/files", exist_ok=True)

    file.save(local_file_path)
    print(f"Saved file: {file.filename} to {local_file_path}")

    blob = storage_client.bucket(bucket_name).blob(file.filename)
    blob.upload_from_filename(local_file_path)
    print(f"Uploaded file: {file.filename} to GCS")

    return local_file_path

def generate_description_and_caption(filename):
    """Generates caption and description using Gemini AI."""
    local_file_path = os.path.join("/app/files", filename)
    mime_type = "image/jpeg"

    try:
        with open(local_file_path, "rb") as image_file:
            image_data = image_file.read()

        # Gemini API requires binary image data
        response = model.generate_content([{"mime_type": "image/jpeg", "data": image_data}, "\n\n", PROMPT])

        # Check if response has text
        if not response.text:
            raise ValueError("Gemini API did not return any text.")

        try:
            json_data = json.loads(response.text)  # Convert response to JSON
            title = json_data.get("title", "Untitled")
            description = json_data.get("description", "No description available.")
        except json.JSONDecodeError:
            print(" Failed to parse AI response. Using fallback title and description.")
            title = "Untitled"
            description = response.text.strip()

        # Store JSON result
        json_data = {"title": title, "description": description}
        json_filename = f"{filename.rsplit('.', 1)[0]}.json"
        json_blob = storage_client.bucket(bucket_name).blob(json_filename)
        json_blob.upload_from_string(json.dumps(json_data), content_type='application/json')

        print(f" Generated JSON and uploaded as: {json_filename}")

    except Exception as e:
        print(f" Error generating description for {filename}: {str(e)}")
        raise

def get_ai_response(json_filename):
    """Fetches AI-generated title/description JSON file from Cloud Storage."""
    try:
        blob = storage_client.bucket(bucket_name).blob(json_filename)
        ai_data = json.loads(blob.download_as_text())
        return ai_data
    except Exception as e:
        print(f"Error fetching AI response: {str(e)}")
        raise

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8083)
