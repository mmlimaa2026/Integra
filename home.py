import streamlit as st

def home_screen():
    """
    Renderiza a tela inicial (Home) do sistema Integra com caixa de boas-vindas
    de fundo branco, textos pretos e largura alinhada a 3/5 (60%) da tela.
    """
    
    # Obtém o nome do usuário logado na sessão (com fallback seguro)
    user_info = st.session_state.get('user', {}) or {}
    nome_usuario = user_info.get('NomeUsuario', user_info.get('Login', 'Membro'))
    
    # Renderização da caixa de boas-vindas estilizada (3/5 da largura da tela = 60%)
    st.markdown(f"""
        <div style="
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            padding: 40px 30px;
            text-align: center;
            width: 60%;
            margin: 30px auto;
        ">
            <h1 style="
                color: #000000 !important;
                font-size: 1.8rem !important;
                font-weight: 800 !important;
                margin: 0 0 12px 0 !important;
                text-align: center !important;
                letter-spacing: -0.5px;
            ">
                Bem-vindo(a) ao Sistema Integra, {nome_usuario}!
            </h1>
            <p style="
                color: #333333 !important;
                font-size: 1rem !important;
                font-weight: 400 !important;
                line-height: 1.6;
                margin: 0 auto !important;
                text-align: center !important;
            ">
                Plataforma oficial para gestão, acolhimento e acompanhamento da jornada de novos membros.<br>
                Utilize o menu superior para navegar entre os módulos do sistema.
            </p>
        </div>
    """, unsafe_allow_html=True)