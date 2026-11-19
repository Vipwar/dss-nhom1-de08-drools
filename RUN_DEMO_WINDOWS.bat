@echo off
chcp 65001 >nul
title Do an Cuoi ky DSS - Nhom 1 - De 08: DROOLS Rule Engine
echo ============================================================================
echo   HE THONG HO TRO RA QUYET DINH (DSS) - NHOM 1 - DE 08: DROOLS ENGINE
echo   Bai toan: Tham dinh Tin dung, Xep hang Rui ro va Dinh gia Khoan vay Ca nhan
echo ============================================================================
echo.
echo [1/3] Dang chay bo Kiem thu Tu dong (Unit va Integration Tests)...
python -m unittest discover -s tests -v
echo.
echo [2/3] Dang mo trinh duyet Web tai dia chi: http://localhost:8000 ...
start "" http://localhost:8000
echo.
echo [3/3] Dang khoi dong Drools DSS Web Server tren cong 8000...
python app.py --port 8000
pause
