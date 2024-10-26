from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/endpoint", methods=["POST"])
def handle_post():
    data = request.json
    print("Received JSON data:", data)  # Print the received JSON data
    return jsonify({"status": "success", "received_data": data}), 200


if __name__ == "__main__":
    app.run(port=5000)
