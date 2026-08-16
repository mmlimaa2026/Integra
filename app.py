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
import streamlit.components.v1 as components

# Configuração de Logging do sistema
logger = logging.getLogger(__name__)

# Importação das telas e módulos do projeto
from acolhimentos import acolhimento_screen
from home import home_screen
from administracao import administracao_screen

# Configuração inicial da página no Streamlit
st.set_page_config(
    page_title="Integra | Sistema de Novos Membros",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def get_db_config():
    """Recupera as credenciais do banco de dados PostgreSQL do st.secrets."""
    try:
        return st.secrets["postgres"]
    except KeyError:
        st.error("⚠️ Configuração do banco de dados não encontrada nos 'secrets'.")
        return None

def get_email_config():
    """Recupera as configurações do servidor SMTP de e-mail do st.secrets."""
    try:
        return st.secrets["email"]
    except KeyError:
        return None

# Inicialização de variáveis de controle no st.session_state
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
if 'is_mobile' not in st.session_state:
    st.session_state.is_mobile = False

# Controle de alertas temporários de formulário
if 'temp_alert_message' not in st.session_state:
    st.session_state.temp_alert_message = None
if 'temp_alert_type' not in st.session_state:
    st.session_state.temp_alert_type = None

# ==============================================================================
# DETECÇÃO AUTOMÁTICA DE DISPOSITIVOS MÓVEIS (ANDROID / IOS)
# ==============================================================================
if not st.session_state.is_mobile:
    detection_script = """
    <script>
    const ua = navigator.userAgent;
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua);
    if (isMobile) {
        const currentUrl = new URL(window.location.href);
        if (!currentUrl.searchParams.has('mobile_detected')) {
            currentUrl.searchParams.set('mobile_detected', 'true');
            window.location.replace(currentUrl.toString());
        }
    }
    </script>
    """
    components.html(detection_script, height=0, width=0)
    
    if "mobile_detected" in st.query_params:
        st.session_state.is_mobile = True

# ==============================================================================
# CSS CUSTOMIZADO: LIMITAÇÃO ESTRITA DE LARGURA PARA EVITAR TRANSBORDAMENTO (OVERFLOW)
# ==============================================================================
st.markdown("""
    <style>
    /* 1. RESET GLOBAL DE CORES E BLOQUEIO DE OVERFLOW HORIZONTAL */
    :root {
        color-scheme: light !important;
    }

    html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"], 
    [data-testid="stMain"], .main {
        background-color: #FFFFFF !important;
        color: #212529 !important;
        max-width: 100vw !important;
        width: 100% !important;
        overflow-x: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;
    }

    *, *:before, *:after {
        box-sizing: border-box !important;
    }

    /* Oculta barras padrão do Streamlit */
    header[data-testid="stHeader"], [data-testid="stHeader"], .stDeployButton, #MainMenu, footer {
        display: none !important;
        height: 0px !important;
        visibility: hidden !important;
    }

    /* Container de Conteúdo Principal limitado à tela do dispositivo */
    .main .block-container, div[data-testid="stMainBlockContainer"], .block-container {
        width: 100% !important;
        max-width: 100vw !important;
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        margin: 0 auto !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
    }

    /* Estilização para caixas de formulário (Login / Solicitação) */
    div[data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 12px !important;
        padding: 1.2rem !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
    }

    /* Estilização dos Botões nos Formulários */
    div[data-testid="stForm"] button {
        background-color: #FFFFFF !important;
        color: #212529 !important;
        font-weight: 700 !important;
        border: 1.5px solid #CED4DA !important;
        border-radius: 8px !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="stForm"] button:hover {
        background-color: #F8F9FA !important;
        border-color: #ADB5BD !important;
    }

    /* Inputs de Texto e Senha ajustados ao container */
    .stTextInput input, .stPasswordInput input {
        background-color: #F8F9FA !important;
        border: 1px solid #CED4DA !important;
        border-radius: 8px !important;
        color: #212529 !important;
        padding: 8px 12px !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }

    /* Quebra automática de linhas longas em textos */
    label, p, span, h1, h2, h3, h4, .stMarkdown, .element-container {
        color: #212529 !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }

    /* Imagens Responsivas que não estouram o container */
    div[data-testid="stImage"] img {
        max-width: 100% !important;
        height: auto !important;
        object-fit: contain !important;
    }

    /* 2. REGRAS EXCLUSIVAS PARA SMARTPHONES (ANDROID / IOS) */
    @media (max-width: 768px) {
        /* Cabeçalho do topo no Mobile (Logo + Menu Hambúrguer em 1 linha) */
        .block-container div[data-testid="stHorizontalBlock"]:first-of-type {
            display: flex !important;
            flex-direction: row !important;
            justify-content: space-between !important;
            align-items: center !important;
            width: 100% !important;
            max-width: 100% !important;
            margin-bottom: 0.5rem !important;
            gap: 0.5rem !important;
        }

        /* Coluna do Logo (~35% da largura, alinhada à esquerda) */
        .block-container div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:first-child {
            width: 35% !important;
            min-width: 35% !important;
            max-width: 35% !important;
            flex: 0 0 35% !important;
            display: flex !important;
            justify-content: flex-start !important;
            align-items: center !important;
        }

        /* Coluna do Menu Hambúrguer (~60% da largura, alinhada à direita) */
        .block-container div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"]:last-child {
            width: 60% !important;
            min-width: 60% !important;
            max-width: 60% !important;
            flex: 0 0 60% !important;
            display: flex !important;
            justify-content: flex-end !important;
            align-items: center !important;
        }

        /* Tamanho proporcional do Logo no smartphone */
        div[data-testid="stImage"] img {
            max-width: 110px !important;
        }

        /* Botões do formulário lado a lado no celular sem estourar */
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            gap: 0.5rem !important;
            width: 100% !important;
        }

        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            width: 50% !important;
            min-width: 50% !important;
            flex: 1 1 50% !important;
        }
    }

    /* 3. REGRAS PARA DESKTOP */
    @media (min-width: 769px) {
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {
            display: flex !important;
            justify-content: flex-end !important;
            align-items: center !important;
        }

        div[data-testid="stImage"] img {
            display: block !important;
            max-width: 180px !important;
            height: auto !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

def hash_password(password):
    """Gera o hash SHA-256 para senhas de usuários."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def connect_to_database():
    """Realiza a conexão com o banco de dados PostgreSQL."""
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
    """Mapeia os campos da tabela SolicitacaoAcesso."""
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
    """Busca os dados do usuário no schema 'integra' pelo Login."""
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM integra."Usuario" WHERE "Login" = %s', (login,))
        usuario = cursor.fetchone()
        if usuario:
            colunas = [desc[0] for desc in cursor.description]
            return dict(zip(colunas, usuario))
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar usuário: {e}")
        return None

def autenticar_usuario(conn, login, senha):
    """Valida o login e a senha do usuário informados na tela de acesso."""
    usuario = buscar_usuario_por_login(conn, login)
    if not usuario:
        return None, "Login inválido."
    senha_hash = hash_password(senha)
    if usuario.get('Senha') == senha_hash or usuario.get('Senha') == senha:
        return usuario, "Usuário autenticado com sucesso."
    else:
        return None, "Senha incorreta."

def enviar_email_notificacao(nome, email, celular):
    """Notifica a administração via e-mail sobre novas solicitações."""
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
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 10px;">
                <h2 style="color: #F7D44A; text-align: center;">🔗 Nova Solicitação de Acesso</h2>
                <p><strong>Nome:</strong> {nome}</p>
                <p><strong>E-mail:</strong> {email}</p>
                <p><strong>Celular:</strong> {celular}</p>
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
    """Grava o registro da solicitação de acesso no banco de dados."""
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
    """Encerra a sessão ativa do usuário e reseta variáveis de estado."""
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
    st.session_state.temp_alert_message = None
    st.session_state.temp_alert_type = None
    st.rerun()

MENU_ICONS = {
    "Home": "🏠 Home",
    "Acolhimento": "🤝 Acolhimento",
    "Classes": "📚 Classes",
    "Relatórios": "📊 Relatórios",
    "Administração": "⚙️ Administração"
}

def login_screen():
    """Exibe a tela inicial de autenticação e solicitação de acesso."""
    if os.path.exists("LogoIntegra.png"):
        st.image("LogoIntegra.png")
    else:
        st.markdown("""
            <h1 style="color: #212529 !important; font-size: 2rem; font-weight: 800; text-align: center; margin: 0;">🔗 Integra</h1>
            <p style="color: #495057 !important; text-align: center; font-size: 0.95rem; margin-bottom: 0.5rem;">Sistema de Novos Membros</p>
        """, unsafe_allow_html=True)
        
    st.markdown('<p style="color: #495057 !important; text-align: center; font-size: 0.9rem; margin-top: 0.2rem; margin-bottom: 1rem;">Entre com seu login e senha abaixo:</p>', unsafe_allow_html=True)
    
    with st.form("login_form", clear_on_submit=False):
        login = st.text_input("Login", max_chars=50, placeholder="Digite seu login", key="login_input")
        senha = st.text_input("Senha", type="password", max_chars=20, placeholder="Digite sua senha", key="password_input")
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            connect_button = st.form_submit_button("🔐 Conectar", use_container_width=True)
        with btn_col2:
            request_button = st.form_submit_button("📝 Solicitar Acesso", use_container_width=True)
        
        if st.session_state.temp_alert_message:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.session_state.temp_alert_type == "success":
                st.success(st.session_state.temp_alert_message)
            else:
                st.error(st.session_state.temp_alert_message)
            
            time.sleep(3)
            st.session_state.temp_alert_message = None
            st.session_state.temp_alert_type = None
            st.rerun()
        
        if connect_button:
            if not login or not senha:
                st.session_state.temp_alert_message = "❌ Por favor, preencha todos os campos!"
                st.session_state.temp_alert_type = "error"
                st.rerun()
            
            if not st.session_state.db_connected or not st.session_state.conn:
                conn, error = connect_to_database()
                if conn:
                    st.session_state.conn = conn
                    st.session_state.db_connected = True
                    columns, id_column = get_table_structure(conn)
                    st.session_state.table_columns = columns
                    st.session_state.id_column = id_column
                else:
                    st.session_state.temp_alert_message = f"❌ {error}"
                    st.session_state.temp_alert_type = "error"
                    st.rerun()
            
            if st.session_state.db_connected and st.session_state.conn:
                usuario, mensagem = autenticar_usuario(st.session_state.conn, login, senha)
                if usuario:
                    st.session_state.user = usuario
                    st.session_state.logged_in = True
                    st.session_state.menu_option = "Home"
                    st.session_state.temp_alert_message = f"✅ {mensagem}"
                    st.session_state.temp_alert_type = "success"
                    st.rerun()
                else:
                    st.session_state.temp_alert_message = f"❌ {mensagem}"
                    st.session_state.temp_alert_type = "error"
                    st.rerun()
        
        if request_button:
            st.session_state.show_request_form = True
            st.session_state.temp_alert_message = None
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
                st.session_state.temp_alert_message = None
                st.rerun()
            
            if enviar_solicitacao:
                if not nome_solicitante or not email_solicitante or not celular_solicitante:
                    st.session_state.temp_alert_message = "❌ Por favor, preencha todos os campos obrigatórios!"
                    st.session_state.temp_alert_type = "error"
                    st.rerun()
                
                celular_limpo = ''.join(filter(str.isdigit, celular_solicitante))
                if len(celular_limpo) != 11:
                    st.session_state.temp_alert_message = "❌ O celular deve ter exatamente 11 dígitos (DDD + 9 + número)!"
                    st.session_state.temp_alert_type = "error"
                    st.rerun()
                
                if not st.session_state.db_connected or not st.session_state.conn:
                    conn, error = connect_to_database()
                    if conn:
                        st.session_state.conn = conn
                        st.session_state.db_connected = True
                    else:
                        st.session_state.temp_alert_message = f"❌ {error}"
                        st.session_state.temp_alert_type = "error"
                        st.rerun()
                
                if st.session_state.db_connected and st.session_state.conn:
                    sucesso_banco, resultado = gravar_solicitacao(
                        st.session_state.conn, nome_solicitante, email_solicitante, celular_limpo
                    )
                    if sucesso_banco:
                        enviar_email_notificacao(nome_solicitante, email_solicitante, celular_limpo)
                        st.session_state.show_request_form = False
                        st.session_state.temp_alert_message = f"✅ Solicitação registrada com sucesso! ID: {resultado}"
                        st.session_state.temp_alert_type = "success"
                        st.rerun()
                    else:
                        st.session_state.temp_alert_message = f"❌ {resultado}"
                        st.session_state.temp_alert_type = "error"
                        st.rerun()

def classes_screen(): st.info("📌 Módulo de Classes em desenvolvimento.")
def relatorios_screen(): st.info("📌 Módulo de Relatórios em desenvolvimento.")

def dashboard_screen():
    """Monta a interface principal pós-login com suporte adaptativo para Mobile e Desktop."""
    user_info = st.session_state.user or {}
    eh_admin = user_info.get('Adm') == 'S'
    
    menu_keys = ["Home", "Acolhimento", "Classes", "Relatórios"]
    if eh_admin:
        menu_keys.append("Administração")

    db_config = get_db_config()
    server_name_full = db_config.get('host', 'Desconhecido') if db_config else 'Desconhecido'
    server_name_20 = server_name_full[:20]
    user_name = user_info.get('Nome') or user_info.get('Login') or 'Usuário'

    # LAYOUT ADAPTATIVO
    if st.session_state.is_mobile:
        # ==============================================================================
        # CABEÇALHO PARA DISPOSITIVOS MÓVEIS (SMARTPHONE ANDROID / IOS)
        # ==============================================================================
        col_logo, col_menu = st.columns([4, 8], vertical_alignment="center")
        
        with col_logo:
            if os.path.exists("LogoIntegra.png"):
                st.image("LogoIntegra.png")
            else:
                st.markdown("**🔗 Integra**")
                
        with col_menu:
            # Menu Hambúrguer unificado (Opções de Navegação + Dados do Usuário)
            with st.popover("🍔 Menu", use_container_width=False):
                st.markdown("### 📌 Navegação")
                for opcao in menu_keys:
                    is_active = (st.session_state.menu_option == opcao)
                    btn_type = "primary" if is_active else "secondary"
                    if st.button(MENU_ICONS.get(opcao, opcao), use_container_width=True, type=btn_type, key=f"mob_btn_{opcao}"):
                        st.session_state.menu_option = opcao
                        st.rerun()
                
                st.markdown("---")
                st.markdown("### 👤 Perfil do Usuário")
                st.markdown(f"**Usuário:** {user_name}")
                st.markdown(f"**Servidor:** {server_name_20}")
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                if st.button("🚪 Sair do Sistema", use_container_width=True, key="mob_logout_btn"):
                    logout()

    else:
        # ==============================================================================
        # CABEÇALHO PARA DESKTOP
        # ==============================================================================
        col_logo, col_menu, col_user = st.columns([1.8, 7.2, 1.0], vertical_alignment="center")
        
        with col_logo:
            if os.path.exists("LogoIntegra.png"):
                st.image("LogoIntegra.png")
            else:
                st.markdown("### 🔗 Integra")
                
        with col_menu:
            cols_nav = st.columns(len(menu_keys))
            for idx, opcao in enumerate(menu_keys):
                with cols_nav[idx]:
                    is_active = (st.session_state.menu_option == opcao)
                    btn_type = "primary" if is_active else "secondary"
                    if st.button(MENU_ICONS.get(opcao, opcao), use_container_width=True, type=btn_type, key=f"btn_nav_{opcao}"):
                        st.session_state.menu_option = opcao
                        st.rerun()
                        
        with col_user:
            with st.popover("👤", use_container_width=False):
                st.markdown(f"**Usuário:** {user_name}")
                st.markdown(f"**Servidor:** {server_name_20}")
                st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
                if st.button("🚪 Sair do Sistema", use_container_width=True, key="desktop_logout_btn"):
                    logout()

    st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)

    # Roteamento das telas dos módulos selecionados
    if st.session_state.menu_option == "Home":
        home_screen()
    elif st.session_state.menu_option == "Acolhimento":
        acolhimento_screen()
    elif st.session_state.menu_option == "Classes":
        classes_screen()
    elif st.session_state.menu_option == "Relatórios":
        relatorios_screen()
    elif st.session_state.menu_option == "Administração" and eh_admin:
        administracao_screen()

def main():
    if st.session_state.logged_in and st.session_state.user:
        dashboard_screen()
    else:
        login_screen()

if __name__ == "__main__":
    main()