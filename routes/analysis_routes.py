from flask import Blueprint, jsonify
from services.claude_service import ClaudeService
from config import Config
import os

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/analyze')
def analyze_image():
    try:
        # 이미지 경로 설정
        image_path = os.path.join(Config.SAVE_DIR, 'protest-img.jpg')
        if not os.path.exists(image_path):
            return jsonify({'error': '이미지 파일이 없습니다'}), 404

        # Claude 서비스 초기화 및 분석 요청
        claude_service = ClaudeService()
        analysis_result = claude_service.analyze_image(image_path)
        
        if not analysis_result:
            return jsonify({'error': '이미지 분석 실패'}), 500

        # 분석 결과 전송
        if claude_service.send_to_server(analysis_result):
            return jsonify({
                'status': 'success',
                'message': '이미지 분석 및 전송 완료',
                'result': analysis_result
            })
        else:
            return jsonify({'error': '서버 전송 실패'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500