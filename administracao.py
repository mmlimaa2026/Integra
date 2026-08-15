import streamlit as st
from administracao_pessoas import administracao_pessoas_screen
from administracao_usuarios import administracao_usuarios_screen

def administracao_screen():
    # Inicializa a opção do submenu de administração se não existir
    if 'admin_sub_menu' not in st.session_state:
        st.session_state.admin_sub_menu = 'Pessoa'

    # Injeta CSS com seletores aprofundados para garantir o aumento da fonte no Streamlit
    st.markdown("""
        <style>
        /* Força o alinhamento à esquerda na primeira coluna */
        div[data-testid="column"]:nth-of-type(1) div[data-testid="stRadio"] {
            display: block !important;
            text-align: left !important;
        }
        
        /* Organiza os itens na vertical com espaçamento adequado */
        div[data-testid="column"]:nth-of-type(1) div[data-testid="stRadio"] > div[role="radiogroup"] {
            display: flex !important;
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 1.2rem !important;
            margin: 0 !important;
        }
        
        /* Aumenta a fonte do texto do radio em 40% (1.4rem) atingindo o contêiner interno */
        div[data-testid="column"]:nth-of-type(1) div[data-testid="stRadio"] label p,
        div[data-testid="column"]:nth-of-type(1) div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] > p {
            font-size: 1.4rem !important;
            font-weight: 500 !important;
            line-height: 1.5 !important;
        }
        
        /* Aumenta o tamanho do círculo do rádio para acompanhar a nova fonte de 40% */
        div[data-testid="column"]:nth-of-type(1) div[data-testid="stRadio"] label span[data-baseweb="radio"] {
            transform: scale(1.4) !important;
            margin-right: 0.8rem !important;
            margin-top: 0.2rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### ⚙️ Módulo de Administração")

    # Layout de colunas: 1/6 para o menu vertical e 5/6 para o conteúdo
    col_menu, col_conteudo = st.columns([1, 5])

    with col_menu:
        st.markdown("#### Opções")
        
        opcoes = ["Pessoa", "Usuarios"]
        icones = {
            "Pessoa": "Pessoa",
            "Usuarios": "Usuários"
        }

        st.markdown("""
            <style>
            /* Força o alinhamento de todo o grupo de rádio à esquerda sem margens automáticas */
            div[data-testid="stRadio"] > div[role="radiogroup"] {
                display: flex !important;
                flex-direction: column !important;
                align-items: flex-start !important;
                justify-content: flex-start !important;
                margin-left: 0px !important;
                padding-left: 0px !important;
                width: 100% !important;
            }

            /* Garante que os itens individuais fiquem alinhados à esquerda */
            div[data-testid="stRadio"] label {
                justify-content: flex-start !important;
                text-align: left !important;
                margin-left: 0px !important;
                padding-left: 0px !important;
            }
            
            /* Define o tamanho da fonte e peso normal para as opções inativas */
            div[data-testid="stRadio"] p {
                font-size: 22px !important;
                font-weight: 400 !important;
            }
            
            /* Aplica negrito APENAS na opção selecionada (marcada) */
            div[data-testid="stRadio"] label:has(input:checked) p {
                font-weight: 700 !important;
            }
            
            /* Ajusta a bolinha do Radio para acompanhar a proporção */
            div[data-testid="stRadio"] span[data-baseweb="radio"] {
                transform: scale(1.4) !important;
                margin-right: 10px !important;
                margin-left: 0px !important;
            }
            </style>
        """, unsafe_allow_html=True)

        # 3. O st.radio atuando como menu lateral
        escolha = st.radio(
            "Navegação",
            options=opcoes,
            format_func=lambda x: icones.get(x, x),
            index=opcoes.index(st.session_state.admin_sub_menu),
            label_visibility="collapsed",
            key="admin_radio_submenu"
        )

        # Se houver mudança de estado, atualiza a tela
        if escolha != st.session_state.admin_sub_menu:
            st.session_state.admin_sub_menu = escolha
            st.rerun()

    with col_conteudo:
        # Renderiza a tela de acordo com a opção selecionada no submenu
        if st.session_state.admin_sub_menu == 'Pessoa':
            administracao_pessoas_screen()
        elif st.session_state.admin_sub_menu == 'Usuarios':
            administracao_usuarios_screen()