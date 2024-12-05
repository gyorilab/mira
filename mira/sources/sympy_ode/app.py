from flask import Flask, request, render_template
import base64

app = Flask(__name__)


def convert(base64_image):
    # This is where we should call the OpenAI API
    return "Processed text from image: " + base64_image[:100]


@app.route("/", methods=["GET", "POST"])
def upload_image():
    result_text = None
    if request.method == "POST":
        if 'file' not in request.files:
            return render_template("index.html", error="No file part")

        file = request.files['file']
        if file.filename == '':
            return render_template("index.html", error="No selected file")

        if file:
            # Convert file to base64
            image_data = file.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
            # Call the 'convert' function
            result_text = convert(base64_image)

    return render_template("index.html", result_text=result_text)


if __name__ == "__main__":
    app.run(debug=True)