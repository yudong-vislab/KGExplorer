from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


HIERARCHY = {
    "name": "wiki",
    "children": [
        {
            "name": "concepts",
            "children": [
                {"name": "field", "children": [{"name": "visual analytics"}, {"name": "knowledge graph"}]},
                {"name": "method", "children": [{"name": "embedding"}, {"name": "retrieval"}]},
                {"name": "phenomenon"},
                {"name": "theory"},
            ],
        },
        {
            "name": "entities",
            "children": [
                {"name": "event"},
                {"name": "organization"},
                {"name": "person"},
                {"name": "product", "children": [{"name": "GPT-4o"}, {"name": "MindTrellis"}]},
                {"name": "project"},
            ],
        },
        {"name": "raw"},
        {"name": "schema"},
        {"name": "sources"},
        {"name": "index"},
        {"name": "log"},
    ],
}


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "KGExplorer Flask API"})


@app.get("/api/hierarchy")
def hierarchy():
    return jsonify(HIERARCHY)


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = payload.get("message", "")
    return jsonify(
        {
            "reply": f"LLM placeholder received: {message}",
            "source": "placeholder",
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
