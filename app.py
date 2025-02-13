from flask import Flask
from routes.crawl_routes import crawl_bp

app = Flask(__name__)
app.register_blueprint(crawl_bp)

if __name__ == '__main__':
    app.run('0.0.0.0', port=5001, debug=True)

