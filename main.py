import os
from flask import Flask, request, redirect, send_file
from google.cloud import storage

# Initialize Flask app
app = Flask(__name__)

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket_name = "pr1images-bucket"

@app.route('/')
def index():
    index_html = """
    <form method="post" enctype="multipart/form-data" action="/upload">
      <div>
        <label for="file">Choose file to upload</label>
        <input type="file" id="file" name="form_file" accept="image/jpeg"/>
      </div>
      <div>
        <button>Submit</button>
      </div>
    </form>
    <ul>
    """

    for file in get_list_of_files():
        index_html += f'<li><a href="/files/{file}">{file}</a></li>'
    
    index_html += "</ul>"
    return index_html

@app.route('/upload', methods=["POST"])
def upload():
    file = request.files['form_file']
    if file:
        upload_file(file)
        return redirect("/")
    return "No file uploaded.", 400

@app.route('/files')
def list_files():
    return {"files": get_list_of_files()}

@app.route('/files/<filename>')
def download(filename):
    local_file_path = download_file(filename)
    return send_file(local_file_path, as_attachment=True)

def get_list_of_files():
    """Lists all files in the Google Cloud Storage bucket."""
    blobs = storage_client.list_blobs(bucket_name)
    return [blob.name for blob in blobs]

def upload_file(file):
    """Uploads a file to the Google Cloud Storage bucket."""
    blob = storage_client.bucket(bucket_name).blob(file.filename)
    blob.upload_from_file(file)
    return

def download_file(filename):
    """Downloads a file from the Google Cloud Storage bucket."""
    local_path = os.path.join("./files", filename)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    blob = storage_client.bucket(bucket_name).blob(filename)
    blob.download_to_filename(local_path)
    return local_path

if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=8080)
