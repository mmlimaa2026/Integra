import streamlit as st
import psycopg2
from psycopg2 import OperationalError
import hashlib
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import re
import pandas as pd
import logging

# Configuração de Logging
logger = logging.getLogger(__name__)

# Importação das telas dos módulos
from acolhimentos import acolhimento_screen
from home import home_screen
from administracao import administracao_screen

# Configuração da página Streamlit
st.set_page_config(
    page_title="Integra | Sistema de Novos Membros",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def get_db_config():
    """Recupera configurações de banco de dados do st.secrets."""
    try:
        return st.secrets["postgres"]
    except KeyError:
        st.error("⚠️ Configuração do banco de dados não encontrada nos 'secrets'.")
        return None

def get_email_config():
    """Recupera configurações de e-mail do st.secrets."""
    try:
        return st.secrets["email"]
    except KeyError:
        return None

# Inicialização de variáveis no session_state
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = False
if 'conn' not in st.session_state:
    st.session_state.conn = None
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'show_db_status' not in st.session_state:
    st.session_state.show_db_status = False
if 'db_status_message' not in st.session_state:
    st.session_state.db_status_message = ""
if 'db_status_type' not in st.session_state:
    st.session_state.db_status_type = ""
if 'status_timer' not in st.session_state:
    st.session_state.status_timer = 0
if 'show_request_form' not in st.session_state:
    st.session_state.show_request_form = False
if 'table_columns' not in st.session_state:
    st.session_state.table_columns = None
if 'id_column' not in st.session_state:
    st.session_state.id_column = None
if 'menu_option' not in st.session_state:
    st.session_state.menu_option = "Home"

is_logged = st.session_state.logged_in

# ==============================================================================
# CSS CUSTOMIZADO RESPONSIVO COM FIX PARA BOTÕES E TÍTULOS NO MOBILE
# ==============================================================================
st.markdown(f"""
    <style>
    /* Reset Geral */
    html, body, [data-testid="stApp"] {{
        margin: 0 !important;
        padding: 0 !important;
        height: 100% !important;
    }}

    header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
    }}
    
    .stDeployButton, #MainMenu {{
        display: none !important;
    }}

    .stApp {{
        background-color: #FFFFFF !important;
    }}

    /* Container Principal da View */
    div[data-testid="stAppViewContainer"] {{
        display: {"flex !important" if not is_logged else "block !important"};
        flex-direction: {"column !important" if not is_logged else "initial !important"};
        justify-content: {"center !important" if not is_logged else "flex-start !important"};
        align-items: {"center !important" if not is_logged else "stretch !important"};
        min-height: 100vh !important;
        width: 100% !important;
    }}

    /* Ajuste do Container de Conteúdo */
    div[data-testid="stMainBlockContainer"], .block-container {{
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: {"1rem !important" if not is_logged else "1.5rem !important"};
        padding-right: {"1rem !important" if not is_logged else "1.5rem !important"};
        width: {"60vw !important" if not is_logged else "100% !important"};
        max-width: {"550px !important" if not is_logged else "100% !important"};
        min-width: {"320px !important" if not is_logged else "100% !important"};
        margin: {"0 auto !important" if not is_logged else "0 !important"};
        display: {"flex !important" if not is_logged else "block !important"};
        flex-direction: column !important;
        align-items: {"center !important" if not is_logged else "stretch !important"};
    }}

    /* Logo em Login e Pós-Login */
    div[data-testid="stImage"] {{
        display: flex !important;
        justify-content: {"center !important" if not is_logged else "flex-start !important"};
        align-items: center !important;
        width: 100% !important;
        margin: 0 auto 10px auto !important;
    }}

    div[data-testid="stImage"] > img {{
        display: block !important;
        margin: {"0 auto !important" if not is_logged else "0 !important"};
        max-width: {"260px !important" if not is_logged else "180px !important"};
        height: auto !important;
    }}

    /* Container do Menu Superior */
    div[data-testid="column"]:nth-of-type(2) {{
        background-color: #1A1A1A !important;
        border-radius: 12px !important;
        padding: 8px 12px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        min-height: 52px !important;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.15) !important;
    }}

    div[data-testid="column"]:nth-of-type(2) div[data-testid="stHorizontalBlock"] {{
        width: 100% !important;
        align-items: center !important;
        gap: 0.5rem !important;
    }}

    /* --------------------------------------------------------------------------
       CORREÇÃO DOS BOTÕES DO MENU (PILLS) - FORÇA TEXTO BRANCO NO INATIVO
       -------------------------------------------------------------------------- */
    div[data-testid="stPills"] button,
    div[data-testid="stPills"] [role="option"],
    div[data-testid="column"]:nth-of-type(2) div[data-testid="stPills"] button,
    div[data-testid="column"]:nth-of-type(2) div[data-testid="stPills"] [role="option"] {{
        background-color: #2D2D2D !important;
        color: #FFFFFF !important; /* Força texto totalmente branco no botão inativo */
        border: 1px solid #444444 !important;
        border-radius: 20px !important;
        padding: 6px 14px !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        margin-right: 4px !important;
        white-space: nowrap !important;
    }}

    /* Garante cor branca nos spans dentro do botão inativo */
    div[data-testid="stPills"] button span,
    div[data-testid="stPills"] [role="option"] span,
    div[data-testid="stPills"] p {{
        color: #FFFFFF !important;
    }}

    /* Item Ativo (Selecionado) no Menu */
    div[data-testid="stPills"] button[aria-selected="true"],
    div[data-testid="stPills"] [role="option"][aria-selected="true"],
    div[data-testid="column"]:nth-of-type(2) div[data-testid="stPills"] button[aria-selected="true"],
    div[data-testid="column"]:nth-of-type(2) div[data-testid="stPills"] [role="option"][aria-selected="true"] {{
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-color: #FFFFFF !important;
    }}

    div[data-testid="stPills"] button[aria-selected="true"] span,
    div[data-testid="stPills"] [role="option"][aria-selected="true"] span,
    div[data-testid="stPills"] button[aria-selected="true"] p {{
        color: #000000 !important;
    }}

    /* Dropdown de Usuário */
    div[data-testid="column"]:nth-of-type(2) div[data-baseweb="select"] > div {{
        background-color: #2D2D2D !important;
        border: 1px solid #444444 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        min-height: 38px !important;
    }}

    div[data-testid="column"]:nth-of-type(2) div[data-baseweb="select"] span {{
        color: #FFFFFF !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
    }}

    div[data-testid="column"]:nth-of-type(2) div[data-baseweb="select"] svg {{
        fill: #FFFFFF !important;
    }}

    div[data-testid="stPills"] {{
        scrollbar-width: none !important;
        overflow-x: auto !important;
    }}
    div[data-testid="stPills"]::-webkit-scrollbar {{
        display: none !important;
    }}

    /* Inputs de texto */
    .stTextInput label {{
        color: #000000 !important;
        font-weight: 600 !important;
    }}
    
    .stTextInput input {{
        background-color: #FFFFFF !important;
        border: 1.5px solid #000000 !important;
        border-radius: 8px !important;
        color: #000000 !important;
        padding: 8px 12px !important;
    }}

    /* --------------------------------------------------------------------------
       REGRAS EXCLUSIVAS DE RESPONSIVIDADE MOBILE (ANDROID / IOS)
       -------------------------------------------------------------------------- */
    @media (max-width: 768px) {{
        div[data-testid="stMainBlockContainer"], .block-container {{
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 0.5rem !important;
            width: 100% !important;
            max-width: 100% !important;
        }}

        /* Redimensionamento e quebra de palavra para títulos no mobile */
        h1 {{
            font-size: 1.4rem !important;
            line-height: 1.3 !important;
            word-wrap: break-word !important;
            hyphens: auto !important;
        }}

        h2 {{
            font-size: 1.2rem !important;
            line-height: 1.3 !important;
        }}

        h3 {{
            font-size: 1.05rem !important;
        }}

        p, span, li {{
            font-size: 0.9rem !important;
            line-height: 1.4 !important;
        }}

        /* Ajuste do cabeçalho no mobile */
        div[data-testid="column"]:nth-of-type(2) {{
            padding: 6px 8px !important;
        }}

        div[data-testid="stPills"] button,
        div[data-testid="stPills"] [role="option"] {{
            padding: 4px 10px !important;
            font-size: 0.8rem !important;
        }}

        /* Correção para containers flex/cards não comprimirem no Android */
        div[data-testid="stVerticalBlock"] > div {{
            width: 100% !important;
        }}
    }}

    footer {{
        visibility: hidden;
    }}
    </style>
""", unsafe_allow_html=True)

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def connect_to_database():
    db_config = get_db_config()
    if not db_config:
        return None, "Configuração de Secrets do banco de dados não foi encontrada."

    try:
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password'],
            connect_timeout=10
        )
        return conn, None
    except Exception as e:
        logger.error(f"Erro de conexão com o banco: {e}")
        return None, "Falha ao conectar com o servidor do banco de dados."

def get_table_structure(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, udt_name, character_maximum_length,
                   is_identity
            FROM information_schema.columns 
            WHERE table_schema = 'integra' 
            AND table_name = 'SolicitacaoAcesso'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        result = []
        id_column = None
        for col in columns:
            result.append({
                'name': col[0],
                'data_type': col[1],
                'udt_name': col[2],
                'max_length': col[3],
                'is_identity': col[4] == 'YES'
            })
            if col[4] == 'YES':
                id_column = col[0]
        
        return result, id_column
    except Exception as e:
        logger.error(f"Erro ao obter estrutura da tabela: {e}")
        return None, None

def buscar_usuario_por_login(conn, login):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM integra."Usuario" 
            WHERE "Login" = %s
        ''', (login,))
        
        usuario = cursor.fetchone()
        
        if usuario:
            colunas = [desc[0] for desc in cursor.description]
            return dict(zip(colunas, usuario))
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar usuário: {e}")
        return None

def autenticar_usuario(conn, login, senha):
    usuario = buscar_usuario_por_login(conn, login)
    
    if not usuario:
        return None, "Login inválido."
    
    senha_hash = hash_password(senha)
    if usuario.get('Senha') == senha_hash or usuario.get('Senha') == senha:
        return usuario, "Usuário autenticado com sucesso."
    else:
        return None, "Senha incorreta."

def enviar_email_notificacao(nome, email, celular):
    email_config = get_email_config()
    
    if not email_config:
        return False, "Configurações de e-mail ausentes."
        
    try:
        msg = MIMEMultipart()
        msg['From'] = email_config['remetente']
        msg['To'] = email_config['destinatario']
        msg['Subject'] = f"Nova Solicitação de Acesso - {nome}"
        
        corpo = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #F7D44A; text-align: center; border-bottom: 2px solid #F7D44A; padding-bottom: 10px;">
                    🔗 Nova Solicitação de Acesso
                </h2>
                <div style="padding: 20px 0;">
                    <p style="font-size: 16px; color: #333;"><strong>Uma nova solicitação de acesso foi recebida:</strong></p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr>
                            <td style="padding: 10px; background-color: #f9f9f9; font-weight: bold; border: 1px solid #ddd;">Nome:</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{nome}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; background-color: #f9f9f9; font-weight: bold; border: 1px solid #ddd;">E-mail:</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{email}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; background-color: #f9f9f9; font-weight: bold; border: 1px solid #ddd;">Celular:</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{celular}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; background-color: #f9f9f9; font-weight: bold; border: 1px solid #ddd;">Data da Solicitação:</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</td>
                        </tr>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(corpo, 'html'))
        
        server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
        server.starttls()
        server.login(email_config['email'], email_config['password'])
        server.send_message(msg)
        server.quit()
        
        return True, "E-mail enviado com sucesso!"
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail: {e}")
        return False, "Erro ao processar o envio de e-mail."

def gravar_solicitacao(conn, nome, email, celular):
    try:
        cursor = conn.cursor()
        data_atual = datetime.now()
        
        celular_limpo = ''.join(filter(str.isdigit, celular))
        if len(celular_limpo) == 10:
            celular_limpo = '9' + celular_limpo
        elif len(celular_limpo) != 11:
            celular_limpo = celular_limpo.zfill(11)
        
        if st.session_state.table_columns is None:
            columns, id_column = get_table_structure(conn)
            st.session_state.table_columns = columns
            st.session_state.id_column = id_column
        
        columns = st.session_state.table_columns
        id_column = st.session_state.id_column
        
        if not columns or not id_column:
            return False, "Estrutura da tabela inválida"
        
        col_names = [col['name'] for col in columns]
        insert_fields = []
        insert_values = []
        insert_params = []
        
        if 'Nome' in col_names:
            insert_fields.append('"Nome"')
            insert_values.append(nome)
            insert_params.append('%s')
        if 'Email' in col_names:
            insert_fields.append('"Email"')
            insert_values.append(email)
            insert_params.append('%s')
        if 'Celular' in col_names:
            insert_fields.append('"Celular"')
            insert_values.append(celular_limpo)
            insert_params.append('%s')
        if 'Data' in col_names:
            insert_fields.append('"Data"')
            insert_values.append(data_atual)
            insert_params.append('%s')
        
        query = f'''
            INSERT INTO integra."SolicitacaoAcesso" 
            ({', '.join(insert_fields)})
            VALUES ({', '.join(insert_params)})
            RETURNING "{id_column}"
        '''
        
        cursor.execute(query, tuple(insert_values))
        id_solicitacao = cursor.fetchone()[0]
        conn.commit()
        
        return True, id_solicitacao
    except Exception as e:
        logger.error(f"Erro ao gravar solicitação: {e}")
        return False, "Erro interno ao gravar solicitação."

def logout():
    if st.session_state.conn:
        try:
            st.session_state.conn.close()
        except Exception:
            pass
    st.session_state.db_connected = False
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.conn = None
    st.session_state.show_request_form = False
    st.session_state.menu_option = "Home"
    st.rerun()

MENU_ICONS = {
    "Home": "🏠 Home",
    "Acolhimento": "🤝 Acolhimento",
    "Classes": "📚 Classes",
    "Relatórios": "📊 Relatórios",
    "Administração": "⚙️ Administração"
}

def render_menu():
    user_info = st.session_state.get('user', {}) or {}
    eh_admin = user_info.get('Adm') == 'S'

    menu_keys = ["Home", "Acolhimento", "Classes", "Relatórios"]
    if eh_admin:
        menu_keys.append("Administração")
    
    if st.session_state.menu_option not in menu_keys:
        st.session_state.menu_option = "Home"

    try:
        escolha = st.pills(
            "Navegação",
            options=menu_keys,
            format_func=lambda x: MENU_ICONS.get(x, x),
            default=st.session_state.menu_option,
            label_visibility="collapsed",
            key="menu_pills_nav"
        )
    except AttributeError:
        escolha = st.radio(
            "Navegação",
            options=menu_keys,
            format_func=lambda x: MENU_ICONS.get(x, x),
            index=menu_keys.index(st.session_state.menu_option) if st.session_state.menu_option in menu_keys else 0,
            horizontal=True,
            label_visibility="collapsed",
            key="menu_radio_nav"
        )

    if escolha and escolha != st.session_state.menu_option:
        st.session_state.menu_option = escolha
        st.rerun()

def login_screen():
    if os.path.exists("LogoIntegra.png"):
        st.image("LogoIntegra.png")
    else:
        st.markdown("""
            <h1 style="color: #000000; font-size: 2.2rem; font-weight: 800; text-align: center; margin: 0;">🔗 Integra</h1>
            <p style="color: #333333; text-align: center; font-size: 1rem; margin-bottom: 0.5rem;">Sistema de Novos Membros</p>
        """, unsafe_allow_html=True)
        
    st.markdown('<p style="color: #555555; text-align: center; font-size: 0.95rem; margin-top: 0.2rem; margin-bottom: 1.5rem;">Entre com seu login e senha abaixo:</p>', unsafe_allow_html=True)
    
    with st.form("login_form", clear_on_submit=False):
        login = st.text_input("Login", max_chars=50, placeholder="Digite seu login", key="login_input")
        senha = st.text_input("Senha", type="password", max_chars=20, placeholder="Digite sua senha", key="password_input")
        
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        
        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            connect_button = st.form_submit_button("🔐 Conectar", use_container_width=True)
        with btn_col2:
            request_button = st.form_submit_button("📝 Solicitar Acesso", use_container_width=True)
        
        if connect_button:
            if not login or not senha:
                st.error("❌ Por favor, preencha todos os campos!")
                return
            
            if not st.session_state.db_connected or not st.session_state.conn:
                conn, error = connect_to_database()
                if conn:
                    st.session_state.conn = conn
                    st.session_state.db_connected = True
                    columns, id_column = get_table_structure(conn)
                    st.session_state.table_columns = columns
                    st.session_state.id_column = id_column
                else:
                    st.error(f"❌ {error}")
                    return
            
            if st.session_state.db_connected and st.session_state.conn:
                usuario, mensagem = autenticar_usuario(st.session_state.conn, login, senha)
                if usuario:
                    st.session_state.user = usuario
                    st.session_state.logged_in = True
                    st.session_state.menu_option = "Home"
                    st.success(f"✅ {mensagem}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ {mensagem}")
        
        if request_button:
            st.session_state.show_request_form = True
            st.rerun()
    
    if st.session_state.show_request_form:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        st.markdown("### 📝 Solicitar Acesso ao Sistema")
        with st.form("request_form", clear_on_submit=False):
            nome_solicitante = st.text_input("Nome completo *", max_chars=50, placeholder="Digite seu nome completo", key="nome_solicitante")
            email_solicitante = st.text_input("E-mail *", max_chars=50, placeholder="Digite seu e-mail", key="email_solicitante")
            celular_solicitante = st.text_input("Celular *", max_chars=11, placeholder="Ex: 11999999999", key="celular_solicitante")
            
            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
            
            req_col1, req_col2 = st.columns([1, 1])
            with req_col1:
                enviar_solicitacao = st.form_submit_button("📤 Enviar Solicitação", use_container_width=True)
            with req_col2:
                cancelar = st.form_submit_button("❌ Cancelar", use_container_width=True)
            
            if cancelar:
                st.session_state.show_request_form = False
                st.rerun()
            
            if enviar_solicitacao:
                if not nome_solicitante or not email_solicitante or not celular_solicitante:
                    st.error("❌ Por favor, preencha todos os campos obrigatórios!")
                    return
                
                celular_limpo = ''.join(filter(str.isdigit, celular_solicitante))
                if len(celular_limpo) != 11:
                    st.error("❌ O celular deve ter exatamente 11 dígitos (DDD + 9 + número)!")
                    return
                
                if not st.session_state.db_connected or not st.session_state.conn:
                    conn, error = connect_to_database()
                    if conn:
                        st.session_state.conn = conn
                        st.session_state.db_connected = True
                    else:
                        st.error(f"❌ {error}")
                        return
                
                if st.session_state.db_connected and st.session_state.conn:
                    sucesso_banco, resultado = gravar_solicitacao(
                        st.session_state.conn, nome_solicitante, email_solicitante, celular_limpo
                    )
                    if sucesso_banco:
                        st.success(f"✅ Solicitação registrada com sucesso! ID: {resultado}")
                        enviar_email_notificacao(nome_solicitante, email_solicitante, celular_limpo)
                        st.session_state.show_request_form = False
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ {resultado}")

def classes_screen(): st.info("📌 Módulo de Classes em desenvolvimento.")
def relatorios_screen(): st.info("📌 Módulo de Relatórios em desenvolvimento.")

def dashboard_screen():
    user_info = st.session_state.user
    
    col_logo, col_navbar = st.columns([1.5, 8.5], vertical_alignment="center")
    
    with col_logo:
        if os.path.exists("LogoIntegra.png"):
            st.image("LogoIntegra.png")
        else:
            st.markdown("""
                <h2 style="color: #000000 !important; font-size: 1.5rem !important; margin: 0 !important; font-weight: 800 !important;">🔗 Integra</h2>
            """, unsafe_allow_html=True)
            
    with col_navbar:
        nav_col1, nav_col2 = st.columns([7.5, 2.5], vertical_alignment="center")
        
        with nav_col1:
            render_menu()
            
        with nav_col2:
            login_val = user_info.get('Login', 'N/A')
            nome_val = user_info.get('NomeUsuario', 'N/A')
            email_val = user_info.get('Email', user_info.get('E-mail', 'N/A'))
            
            db_cfg = get_db_config()
            if db_cfg and 'host' in db_cfg:
                host_str = str(db_cfg['host'])
                server_name = host_str[:10]
            else:
                server_name = "N/A"
            
            user_options = [
                f"👤 {login_val}",
                f"Nome: {nome_val}",
                f"E-mail: {email_val}",
                f"🖥️ Servidor: {server_name}",
                "🚪 Sair"
            ]
            
            selected_user_action = st.selectbox(
                "Usuário",
                options=user_options,
                index=0,
                label_visibility="collapsed",
                key="user_dropdown_menu"
            )
            
            if selected_user_action == "🚪 Sair":
                logout()

    st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)

    if st.session_state.menu_option == "Home":
        home_screen()
    elif st.session_state.menu_option == "Acolhimento":
        acolhimento_screen()
    elif st.session_state.menu_option == "Classes":
        classes_screen()
    elif st.session_state.menu_option == "Relatórios":
        relatorios_screen()
    elif st.session_state.menu_option == "Administração" and (user_info.get('Adm') == 'S'):
        administracao_screen()

def main():
    if st.session_state.logged_in and st.session_state.user:
        dashboard_screen()
    else:
        login_screen()

if __name__ == "__main__":
    main()