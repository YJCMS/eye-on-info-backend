from flask import Flask, render_template, request, flash, url_for, redirect, jsonify
import os
from routes.crawl_routes import crawl_bp
from routes.analysis_routes import analysis_bp
from services.pdf_analysis_service import PDFAnalysisService
from services.protest_info_search_service import ProtestInfoSearchService
from services.protest_url_crawler_service import ProtestUrlCrawlerService
from config import Config

app = Flask(__name__)
app.register_blueprint(crawl_bp, url_prefix='/api/v1')
app.register_blueprint(analysis_bp, url_prefix='/api/v1')
app.secret_key = Config.SECRET_KEY

# 기본 디렉토리 설정
pdf_dir = os.path.join('static', 'pdf')
text_dir = os.path.join('static', 'text')
os.makedirs(pdf_dir, exist_ok=True)
os.makedirs(text_dir, exist_ok=True)

# 서비스 초기화
pdf_service = PDFAnalysisService(pdf_dir)
search_service = ProtestInfoSearchService()
protest_url_crawler_service = ProtestUrlCrawlerService()

def handle_response(success, message, status_code=200):
    """API 응답 처리를 위한 유틸리티 함수"""
    response = {"status": "success" if success else "error", "message": message}
    return jsonify(response), status_code if not success else 200

@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        # 뉴스 텍스트 읽기
        news_text = None
        news_file_path = os.path.join(text_dir, 'news_info.txt')
        if os.path.exists(news_file_path):
            with open(news_file_path, 'r', encoding='utf-8') as f:
                news_text = f.read()

        # POST 요청 처리
        if request.method == 'POST':
            if 'url' in request.form and request.form['url']:
                success, message = pdf_service.download_pdf_from_url(request.form['url'])
            elif 'file' in request.files:
                success, message = pdf_service.upload_pdf(request.files['file'])
            flash(message, 'success' if success else 'error')

        return render_template('index.html', news_text=news_text)

    except Exception as e:
        flash('처리 중 오류가 발생했습니다.', 'error')
        return render_template('index.html')

@app.route('/get_news_text', methods=['GET'])
def get_news_text():
    try:
        if not search_service.save_protest_info_to_txt():
            return handle_response(False, "뉴스 정보 가져오기 실패", 500)

        with open(os.path.join(text_dir, 'news_info.txt'), 'r', encoding='utf-8') as f:
            return handle_response(True, f.read())

    except Exception as e:
        return handle_response(False, "뉴스 처리 중 오류 발생", 500)

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

@app.route('/auto', methods=['GET'])
def auto_scheduler():
    try:
        # 1단계: 크롤링 및 PDF 다운로드
        todays_info = protest_url_crawler_service.execute_and_get_final_url()
        pdf_service.download_pdf_from_url(todays_info)
        pdf_path = os.path.join(pdf_dir, 'protest-info-pdf.pdf')
        
        # 2단계: PDF 파일 존재 확인
        if not os.path.exists(pdf_path):
            return handle_response(False, "분석할 PDF 파일이 없습니다.", 404)
        
        # 3단계: 시위 정보를 텍스트로 저장
        if not search_service.save_protest_info_to_txt():
            return handle_response(False, "뉴스 정보 가져오기 실패", 500)
            
        # 4단계: PDF 분석 및 결과 전송
        result = pdf_service.analyze_pdf(pdf_path)
        if not result:
            return handle_response(False, "PDF 분석 중 오류가 발생했습니다.", 500)
            
        success = pdf_service.send_to_server(result)
        if not success:
            return handle_response(False, "분석 결과 전송 중 오류가 발생했습니다.", 500)
        
        # 5단계: 뉴스 정보와 함께 성공 응답 반환
        with open(os.path.join(text_dir, 'news_info.txt'), 'r', encoding='utf-8') as f:
            return handle_response(True, f.read())
            
    except Exception as e:
        return handle_response(False, f"처리 중 오류 발생: {str(e)}", 500)
    

# 전역 에러 핸들러
@app.errorhandler(404)
def not_found_error(error):
    return handle_response(False, "페이지를 찾을 수 없습니다", 404)

@app.errorhandler(500)
def internal_error(error):
    return handle_response(False, "서버 오류가 발생했습니다", 500)

if __name__ == '__main__':
    app.run('0.0.0.0', port=5001, debug=True)