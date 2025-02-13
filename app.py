from flask import Flask, render_template, request, flash, url_for, redirect
import os
from routes.crawl_routes import crawl_bp
from routes.analysis_routes import analysis_bp
from services.pdf_analysis_service import PDFAnalysisService
from config import Config

app = Flask(__name__)
app.register_blueprint(crawl_bp, url_prefix='/api/v1')
app.register_blueprint(analysis_bp, url_prefix='/api/v1')
app.secret_key = Config.SECRET_KEY

# static/pdf 폴더가 없으면 생성
pdf_dir = os.path.join('static', 'pdf')
os.makedirs(pdf_dir, exist_ok=True)

# PDF 서비스 초기화
pdf_service = PDFAnalysisService(pdf_dir)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # URL을 통한 다운로드
        if 'url' in request.form and request.form['url']:
            success, message = pdf_service.download_pdf_from_url(request.form['url'])
            flash(message, 'success' if success else 'error')
        
        # 파일 직접 업로드
        elif 'file' in request.files:
            success, message = pdf_service.upload_pdf(request.files['file'])
            flash(message, 'success' if success else 'error')
    
    return render_template('index.html')

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

