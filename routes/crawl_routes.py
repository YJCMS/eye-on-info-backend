from flask import Blueprint
from services.crawl_service import CrawlService
from config import Config
import os

crawl_bp = Blueprint('crawl', __name__)

@crawl_bp.route('/crawl')
def crawl_image():
    service = CrawlService()
    img_url = service.get_bcontent_image(Config.TARGET_INFO_URL)
    print(f"최종 이미지 URL: {img_url}")
    
    if img_url:
        success, save_path = service.download_image(img_url, 'protest-img.jpg')
        if success:
            return f'이미지 다운로드 완료: {save_path}'
    
    return '이미지를 찾을 수 없거나 다운로드하는 데 실패했습니다.'