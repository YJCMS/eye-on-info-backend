from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time
import logging

TARGET_URL = "https://www.smpa.go.kr/user/nd54882.do" 

class ProtestUrlCrawlerService:
    
    @staticmethod
    def setup_driver():
        """Chrome 웹드라이버 설정"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # 화면 표시 없이 실행
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Mac용 ChromeDriver 설정
        driver = webdriver.Chrome(options=options)
        return driver

    @staticmethod
    def get_todays_date_format():
        """오늘 날짜를 YYMMDD 형식으로 반환"""
        now = datetime.now()
        return now.strftime("%y%m%d")

    @staticmethod
    def execute_and_get_final_url():
        """자바스크립트 링크를 실행하고 최종 URL 반환"""
        today_date = ProtestUrlCrawlerService.get_todays_date_format()
        logging.info(f"오늘 날짜 형식: {today_date}")
        
        driver = None
        try:
            driver = ProtestUrlCrawlerService.setup_driver()
            driver.set_page_load_timeout(30)
            
            # 페이지 로드
            logging.info(f"URL 접속 중: {TARGET_URL}")
            driver.get(TARGET_URL)
            logging.info("페이지 로드 완료")
            
            # 테이블 로딩 대기
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "data-list"))
            )
            
            # 테이블의 모든 행 찾기
            rows = driver.find_elements(By.CSS_SELECTOR, "table.data-list tbody tr")
            logging.info(f"테이블에서 {len(rows)}개 행 발견")
            
            # 각 행에서 오늘 날짜 포함된 게시물 찾기
            for row in rows:
                try:
                    # 제목 셀 찾기
                    subject_cell = row.find_element(By.CLASS_NAME, "subject")
                    link = subject_cell.find_element(By.TAG_NAME, "a")
                    title_text = link.text
                    
                    # 오늘 날짜 문자열이 제목에 있는지 확인
                    if today_date in title_text:
                        logging.info(f"오늘 날짜 매칭 게시물 발견: {title_text}")
                        
                        # 링크 클릭
                        logging.info("링크 클릭 시도...")
                        link.click()
                        
                        # 페이지 전환 대기
                        time.sleep(3)
                        
                        # 현재 URL 가져오기
                        final_url = driver.current_url
                        logging.info(f"최종 URL: {final_url}")
                        
                        return final_url
                    
                except Exception as e:
                    logging.error(f"행 처리 오류: {e}")
                    continue
                    
            # 오늘 날짜 포함된 게시물이 없는 경우 None 반환
            logging.warning(f"오늘({today_date}) 날짜가 포함된 게시물이 없습니다.")
            return None
                
        except Exception as e:
            logging.error(f"처리 오류: {e}")
            return None
        finally:
            if driver:
                driver.quit()
                logging.info("웹드라이버 종료")