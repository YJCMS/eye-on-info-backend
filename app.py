from flask import Flask, render_template, request, flash, url_for, redirect, jsonify
import os
from routes.crawl_routes import crawl_bp
from routes.analysis_routes import analysis_bp
from services.pdf_analysis_service import PDFAnalysisService
from services.Protest_info_search_service import ProtestInfoSearchService
from config import Config

app = Flask(__name__)
app.register_blueprint(crawl_bp, url_prefix='/api/v1')
app.register_blueprint(analysis_bp, url_prefix='/api/v1')
app.secret_key = Config.SECRET_KEY

# static/pdf 폴더가 없으면 생성
pdf_dir = os.path.join('static', 'pdf')
os.makedirs(pdf_dir, exist_ok=True)

# static/text 폴더가 없으면 생성
text_dir = os.path.join('static', 'text')
os.makedirs(text_dir, exist_ok=True)

# PDF 서비스 초기화
pdf_service = PDFAnalysisService(pdf_dir)
# 검색 서비스 초기화
search_service = ProtestInfoSearchService()

@app.route('/', methods=['GET', 'POST'])
def index():
    news_text = None
    try:
        news_file_path = os.path.join('static', 'text', 'news_info.txt')
        if os.path.exists(news_file_path):
            with open(news_file_path, 'r', encoding='utf-8') as f:
                news_text = f.read()
    except Exception as e:
        print(f"Error reading news file: {e}")

    if request.method == 'POST':
        # URL을 통한 다운로드
        if 'url' in request.form and request.form['url']:
            success, message = pdf_service.download_pdf_from_url(request.form['url'])
            flash(message, 'success' if success else 'error')
        
        # 파일 직접 업로드
        elif 'file' in request.files:
            success, message = pdf_service.upload_pdf(request.files['file'])
            flash(message, 'success' if success else 'error')
    
    return render_template('index.html', news_text=news_text)

@app.route('/get_news_text', methods=['GET'])
def get_news_text():
    try:
        success = search_service.save_protest_info_to_txt()
        if success:
            # 파일을 읽어서 내용 반환
            try:
                with open('static/text/news_info.txt', 'r', encoding='utf-8') as f:
                    content = f.read()
                return jsonify({
                    "status": "success",
                    "message": content
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"File read error: {str(e)}"
                }), 500
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to fetch and save news information"
            }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/analyze_pdf', methods=['POST'])
def analyze_pdf():
    pdf_path = os.path.join(pdf_dir, 'protest-info-pdf.pdf')
    
    if not os.path.exists(pdf_path):
        flash('분석할 PDF 파일이 없습니다. 먼저 파일을 업로드해주세요.', 'error')
        return redirect(url_for('index'))
    
    try:
        result = pdf_service.analyze_pdf(pdf_path)
        if result:
            success = pdf_service.send_to_server(result)
            if success:
                flash('PDF 분석이 완료되었습니다.', 'success')
            else:
                flash('분석 결과 전송 중 오류가 발생했습니다.', 'error')
        else:
            flash('PDF 분석 중 오류가 발생했습니다.', 'error')
    except Exception as e:
        flash(f'PDF 분석 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run('0.0.0.0', port=5001, debug=True)