@echo off
echo Iniciando Streamlit...
cd /d C:\Python\Integra

REM Ativa o ambiente virtual se existir
if exist "venv\Scripts\activate" (
    call venv\Scripts\activate
)

REM Inicia o Streamlit
streamlit run app.py

REM Pausa para ver mensagens de erro
pause