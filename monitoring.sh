#!/bin/bash

# 종료 시그널 핸들러
trap 'echo "프로그램 종료중..."; exit' SIGINT SIGTERM

# 로그 함수
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

while true; do
    log_message "포트폴리오 업데이트 시작"
    
    # Python 스크립트 실행 및 에러 체크
    scripts=("./agg.py")
    
    for script in "${scripts[@]}"; do
        log_message "$script 실행중..."
        if ! python3 "$script"; then
            log_message "에러: $script 실행 실패"
            # 선택적: 실패시 이메일 알림 등 추가 가능
        fi
    done

    log_message "업데이트 완료. 3분 대기중..."
    symbols=("◐" "◓" "◑" "◒")

    # 대기시간 동안 애니메이션 표시
    for ((i = 0; i < 180; i++)); do
        symbol_index=$((i % 4))
        tput cr
        echo -n "${symbols[symbol_index]}"
        sleep 1
    done
done