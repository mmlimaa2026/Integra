import streamlit as st
import pandas as pd
import time
from datetime import datetime
import psycopg2

# ==========================================
# GERENCIAMENTO SEGURO DA CONEXÃO
# ==========================================

def get_db_connection():
    """
    Obtém a conexão do banco de dados priorizando st.secrets.
    Previne hardcode de credenciais no código-fonte.
    """
    if 'conn' in st.session_state and st.session_state.conn:
        try:
            # Testa se a conexão ainda está viva
            with st.session_state.conn.cursor() as cur:
                cur.execute("SELECT 1;")
            return st.session_state.conn
        except Exception:
            st.session_state.conn = None

    # Inicializa a conexão usando st.secrets
    try:
        conn = psycopg2.connect(
            host=st.secrets["postgres"]["host"],
            port=st.secrets["postgres"]["port"],
            database=st.secrets["postgres"]["database"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"]
        )
        st.session_state.conn = conn
        return conn
    except Exception as e:
        st.error("Erro ao conectar ao banco de dados. Verifique os segredos configurados.")
        return None

# ==========================================
# MASCARAMENTO DE DADOS (PRIVACIDADE / LGPD)
# ==========================================

def mascarar_telefone(tel):
    """Mascara o telefone para privacidade na interface pública."""
    if not tel:
        return ""
    tel_str = str(tel).strip()
    if len(tel_str) == 11:
        return f"({tel_str[:2]}) *****-{tel_str[7:]}"
    return "*******"

# ==========================================
# FUNÇÕES DE BANCO DE DADOS (CONSULTAS PREPARADAS)
# ==========================================

def listar_acolhimentos(conn, id_usuario, is_admin, apenas_meus=False):
    if not conn:
        return []
    cursor = None
    try:
        try:
            conn.rollback()
        except Exception:
            pass
        
        cursor = conn.cursor()
        
        # Consultas parametrizadas evitando SQL Injection
        if is_admin == 'S' and not apenas_meus:
            query = """
                SELECT 
                    "idAcolhimento", "DataAcolhimento", "idPessoa", "idStatus",
                    "idFaixaEtaria", "AceitaContato", "idUsuario", "NomePessoa",
                    "NomeStatus", "NomeFaixaEtaria", "NomeUsuario", "Telefone"
                FROM integra.vw_lista_acolhimentos
                ORDER BY "DataAcolhimento" DESC
            """
            cursor.execute(query)
        else:
            query = """
                SELECT 
                    "idAcolhimento", "DataAcolhimento", "idPessoa", "idStatus",
                    "idFaixaEtaria", "AceitaContato", "idUsuario", "NomePessoa",
                    "NomeStatus", "NomeFaixaEtaria", "NomeUsuario", "Telefone"
                FROM integra.vw_lista_acolhimentos
                WHERE "idUsuario" = %s
                ORDER BY "DataAcolhimento" DESC
            """
            cursor.execute(query, (id_usuario,))
        
        resultados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        dados = [dict(zip(colunas, row)) for row in resultados]
        conn.commit()
        return dados
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []
    finally:
        if cursor:
            cursor.close()

def excluir_acolhimento(conn, id_acolhimento):
    if not conn:
        return False, "Sem conexão com o banco"
    cursor = None
    try:
        try:
            conn.rollback()
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute('DELETE FROM integra."Acolhimento" WHERE "idAcolhimento" = %s', (id_acolhimento,))
        conn.commit()
        return True, ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)
    finally:
        if cursor:
            cursor.close()

def salvar_acolhimento(conn, data_acolhimento, nome_pessoa, celular, id_status, id_faixa_etaria, aceita_contato, id_usuario):
    if not conn:
        return False, "Sem conexão com o banco"
    cursor = None
    try:
        try:
            conn.rollback()
        except Exception:
            pass
        cursor = conn.cursor()
        
        cursor.execute('SELECT "idPessoa" FROM integra."Pessoa" WHERE "NomePessoa" = %s', (nome_pessoa,))
        pessoa = cursor.fetchone()
        
        if pessoa:
            id_pessoa = pessoa[0]
            if celular:
                cursor.execute('UPDATE integra."Pessoa" SET "Telefone" = %s WHERE "idPessoa" = %s', (celular, id_pessoa))
        else:
            cursor.execute('INSERT INTO integra."Pessoa" ("NomePessoa", "Telefone") VALUES (%s, %s) RETURNING "idPessoa"', (nome_pessoa, celular))
            id_pessoa = cursor.fetchone()[0]
        
        cursor.execute('''
            INSERT INTO integra."Acolhimento" 
            ("DataAcolhimento", "idPessoa", "idStatus", "idFaixaEtaria", "AceitaContato", "idUsuario", "Telefone")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING "idAcolhimento"
        ''', (data_acolhimento, id_pessoa, id_status, id_faixa_etaria, aceita_contato, id_usuario, celular))
        
        id_acolhimento = cursor.fetchone()[0]
        conn.commit()
        return True, id_acolhimento
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)
    finally:
        if cursor:
            cursor.close()

def atualizar_acolhimento(conn, id_acolhimento, id_pessoa, nome_pessoa, celular, id_status, id_faixa_etaria, aceita_contato):
    if not conn:
        return False, "Sem conexão com o banco"
    cursor = None
    try:
        try:
            conn.rollback()
        except Exception:
            pass
        cursor = conn.cursor()
        
        if id_pessoa:
            cursor.execute('UPDATE integra."Pessoa" SET "NomePessoa" = %s, "Telefone" = %s WHERE "idPessoa" = %s', (nome_pessoa, celular, id_pessoa))
            
        cursor.execute('''
            UPDATE integra."Acolhimento" 
            SET "idStatus" = %s, "idFaixaEtaria" = %s, "AceitaContato" = %s, "Telefone" = %s
            WHERE "idAcolhimento" = %s
        ''', (id_status, id_faixa_etaria, aceita_contato, celular, id_acolhimento))
        
        conn.commit()
        return True, ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)
    finally:
        if cursor:
            cursor.close()

def buscar_status(conn):
    if not conn:
        return []
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT "idStatus", "NomeStatus" FROM integra."AcolhimentoStatus" ORDER BY "NomeStatus"')
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        if cursor:
            cursor.close()

def buscar_faixas_etarias(conn):
    if not conn:
        return []
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT "idFaixaEtaria", "NomeFaixaEtaria" FROM integra."FaixaEtaria" ORDER BY "NomeFaixaEtaria"')
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        if cursor:
            cursor.close()

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================

def acolhimento_screen():
    # Estilização CSS e Espaçamentos ajustados
    st.markdown("""
        <style>
        /* AJUSTE NOVO: Reduz o padding do topo do container principal para aproximar do menu */
        div[data-testid="block-container"] {
            padding-top: 1rem !important;
        }

        /* AJUSTE NOVO: Aplica margem negativa no título para puxar o cabeçalho para cima */
        .titulo-tela {
            margin-top: -15px !important;
            margin-bottom: 10px !important;
        }

        div.stButton > button {
            background-color: #FFD700 !important;
            color: #000000 !important;
            border: 1.5px solid #000000 !important;
            font-weight: 500 !important;
            font-size: 0.85rem !important;
            border-radius: 6px !important;
            padding: 0.25rem 0.6rem !important;
            width: auto !important;
            min-width: 80px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.15) !important;
            transition: none !important;
        }
        div.stButton > button:hover {
            background-color: #FFE05A !important;
            color: #000000 !important;
            border: 1.5px solid #000000 !important;
        }
        div.stButton > button:active {
            background-color: #000000 !important;
            color: #FFD700 !important;
            border: 1.5px solid #FFD700 !important;
        }
        
        div[data-testid="stModal"] {
            background-color: rgba(0, 0, 0, 0.6) !important;
        }
        div[data-testid="stModal"] > div {
            background-color: #ffffff !important;
            border: 2px solid #FFD700 !important;
            border-radius: 12px !important;
            padding: 10px !important;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3) !important;
        }

        /* Redução das margens do bloco do filtro para aproximá-lo do DataFrame */
        div[data-testid="stHorizontalBlock"]:has(div[data-testid="stTextInput"]) {
            margin-top: 4px !important;
            margin-bottom: 4px !important;
            align-items: center !important;
        }

        /* Remoção do espaço vertical nativo do Streamlit logo abaixo da tabela e aproximação dos botões */
        div[data-testid="stDataFrame"] {
            margin-bottom: 0px !important;
        }
        
        /* Puxa o container de botões de ação mais para cima */
        div[data-testid="stHorizontalBlock"]:has(button[key="btn_incluir_acao"]) {
            margin-top: -10px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Obtenção Segura da Conexão
    conn = get_db_connection()

    user_info = st.session_state.get('user', {})
    id_usuario = user_info.get('idUsuario', user_info.get('Id', user_info.get('id')))
    is_admin = user_info.get('ADM', 'N')
    is_admin_user = is_admin == 'S' if is_admin else False
    
    if 'acolhimento_modo' not in st.session_state:
        st.session_state.acolhimento_modo = 'listar' 
    if 'acolhimento_selecionado_id' not in st.session_state:
        st.session_state.acolhimento_selecionado_id = None
    if 'mensagem_alerta' not in st.session_state:
        st.session_state.mensagem_alerta = ""

    # AJUSTE NOVO: Renderiza o título com uma classe customizada para aproximação do menu superior
    st.markdown("<h3 class='titulo-tela'>📋 Gerenciamento de Acolhimentos</h3>", unsafe_allow_html=True)

    # Área de Filtros
    col_filtro1, col_filtro2 = st.columns([3, 1])
    with col_filtro1:
        texto_filtro = st.text_input(
            "Filtrar na grade", 
            placeholder="Digite para buscar em qualquer coluna...", 
            label_visibility="collapsed"
        )
    with col_filtro2:
        apenas_meus = st.checkbox("Mostrar apenas meus acolhimentos", value=False)

    dados = listar_acolhimentos(conn, id_usuario, is_admin_user, apenas_meus)
    
    if dados:
        df = pd.DataFrame(dados)
    else:
        df = pd.DataFrame(columns=[
            "idAcolhimento", "DataAcolhimento", "idPessoa", "idStatus", 
            "idFaixaEtaria", "AceitaContato", "idUsuario", "NomePessoa", 
            "NomeStatus", "NomeFaixaEtaria", "NomeUsuario", "Telefone"
        ])
        
    if "DataAcolhimento" in df.columns and not df.empty:
        df["DataAcolhimento"] = pd.to_datetime(df["DataAcolhimento"], errors='coerce').dt.strftime('%d/%m/%Y')

    if texto_filtro and not df.empty:
        mask = df.astype(str).apply(lambda x: x.str.contains(texto_filtro, case=False, na=False)).any(axis=1)
        df = df[mask]

    colunas_para_ocultar = ['idAcolhimento', 'idPessoa', 'idStatus', 'idFaixaEtaria', 'idUsuario', 'Telefone']
    df_exibicao = df.drop(columns=[c for c in colunas_para_ocultar if c in df.columns], errors='ignore')

    rename_map = {
        'DataAcolhimento': 'Data Acolhimento',
        'AceitaContato': 'Aceita Contato',
        'NomePessoa': 'Nome',
        'NomeStatus': 'Status',
        'NomeFaixaEtaria': 'Faixa Etária',
        'NomeUsuario': 'Usuário'
    }
    df_exibicao = df_exibicao.rename(columns=rename_map)
    df_exibicao = df_exibicao.head(15)

    evento_selecao = st.dataframe(
        df_exibicao,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

    selected_row_indices = evento_selecao.selection.rows if evento_selecao and hasattr(evento_selecao, 'selection') else []
    
    selected_row = None
    if selected_row_indices and not df.empty:
        idx = selected_row_indices[0]
        if idx < len(idx if isinstance(idx, list) else [idx]) and idx < len(df):
            selected_row = df.iloc[idx].to_dict()
            st.session_state.acolhimento_selecionado_id = selected_row.get('idAcolhimento')
    else:
        st.session_state.acolhimento_selecionado_id = None

    col_btn1, col_btn2, col_btn3, col_vazio = st.columns([0.8, 0.8, 0.8, 7.6])
    
    with col_btn1:
        if st.button("➕ Incluir", key="btn_incluir_acao"):
            st.session_state.acolhimento_modo = 'incluir'
            st.session_state.acolhimento_selecionado_id = None
            st.session_state.mensagem_alerta = ""
            st.rerun()
            
    with col_btn2:
        if st.button("✏️ Alterar", key="btn_alterar_acao"):
            if st.session_state.acolhimento_selecionado_id:
                st.session_state.acolhimento_modo = 'alterar'
                st.session_state.mensagem_alerta = ""
                st.rerun()
            else:
                st.session_state.mensagem_alerta = "Selecione uma linha da grade para alterar."
                st.rerun()
                
    with col_btn3:
        if st.button("🗑️ Excluir", key="btn_excluir_acao"):
            if st.session_state.acolhimento_selecionado_id:
                st.session_state.acolhimento_modo = 'excluir'
                st.session_state.mensagem_alerta = ""
                st.rerun()
            else:
                st.session_state.mensagem_alerta = "Selecione uma linha da grade para excluir."
                st.rerun()

    if st.session_state.mensagem_alerta:
        st.error(st.session_state.mensagem_alerta)
        time.sleep(3)
        st.session_state.mensagem_alerta = ""
        st.rerun()

    # Modal Incluir / Alterar
    if st.session_state.acolhimento_modo in ['incluir', 'alterar']:
        @st.dialog("📝 Novo Acolhimento" if st.session_state.acolhimento_modo == 'incluir' else "✏️ Editar Acolhimento", width="large")
        def modal_acolhimento():
            reg_atual = None
            if st.session_state.acolhimento_modo == 'alterar' and st.session_state.acolhimento_selecionado_id and dados:
                for r in dados:
                    if str(r['idAcolhimento']) == str(st.session_state.acolhimento_selecionado_id):
                        reg_atual = r
                        break

            status_list = buscar_status(conn)
            faixas = buscar_faixas_etarias(conn)

            with st.form("form_cad_acolhimento_popup"):
                c1, c2 = st.columns(2)
                
                with c1:
                    data_val = datetime.now().date()
                    if reg_atual and reg_atual.get('DataAcolhimento'):
                        try:
                            data_val = pd.to_datetime(reg_atual.get('DataAcolhimento')).date()
                        except Exception:
                            pass
                    data_acolhimento = st.date_input("Data : *", value=data_val, format="DD/MM/YYYY", disabled=(st.session_state.acolhimento_modo == 'alterar'))
                    
                    nome_val = reg_atual['NomePessoa'] if reg_atual else ""
                    nome_pessoa = st.text_input("Nome : *", value=nome_val, max_chars=100, placeholder="10 a 100 caracteres").upper()
                    
                    cel_val = reg_atual.get('Telefone', '') if reg_atual else ""
                    celular = st.text_input("Celular : *", value=str(cel_val) if cel_val else "", max_chars=11, placeholder="11 caracteres")
                
                with c2:
                    id_status = None
                    if status_list:
                        status_options = {s[1]: s[0] for s in status_list}
                        status_keys = list(status_options.keys())
                        def_status_idx = 0
                        if reg_atual and reg_atual.get('NomeStatus') in status_options:
                            def_status_idx = status_keys.index(reg_atual.get('NomeStatus'))
                        status_sel = st.selectbox("Status : *", options=status_keys, index=def_status_idx)
                        id_status = status_options.get(status_sel)
                    
                    id_faixa_etaria = None
                    if faixas:
                        faixa_options = {f[1]: f[0] for f in faixas}
                        faixa_keys = list(faixa_options.keys())
                        def_faixa_idx = 0
                        if reg_atual and reg_atual.get('NomeFaixaEtaria') in faixa_options:
                            def_faixa_idx = faixa_keys.index(reg_atual.get('NomeFaixaEtaria'))
                        faixa_sel = st.selectbox("Faixa Etária : *", options=faixa_keys, index=def_faixa_idx)
                        id_faixa_etaria = faixa_options.get(faixa_sel)
                
                aceita_def = True if st.session_state.acolhimento_modo == 'incluir' else False
                if reg_atual:
                    val = reg_atual.get('AceitaContato')
                    aceita_def = (val in [True, 'Sim', 'true', '✅ Sim', 'S'])
                aceita_contato = st.checkbox("Aceita contato", value=aceita_def)
                
                col_salvar, col_cancel = st.columns(2)
                with col_salvar:
                    btn_salvar_form = st.form_submit_button("Salvar", use_container_width=True)
                with col_cancel:
                    btn_cancel_form = st.form_submit_button("Cancelar", use_container_width=True)
                    
                if btn_cancel_form:
                    st.session_state.acolhimento_modo = 'listar'
                    st.session_state.acolhimento_selecionado_id = None
                    st.rerun()
                    
                if btn_salvar_form:
                    if not nome_pessoa or len(nome_pessoa.strip()) < 10 or len(nome_pessoa.strip()) > 100:
                        st.error("❌ O campo Nome é obrigatório e deve ter entre 10 e 100 caracteres!")
                    elif not celular or len(celular.strip()) != 11:
                        st.error("❌ O campo Celular é obrigatório e deve possuir exatamente 11 caracteres!")
                    elif not id_status or not id_faixa_etaria:
                        st.error("❌ Status e Faixa Etária são obrigatórios!")
                    else:
                        if st.session_state.acolhimento_modo == 'incluir':
                            suq, res = salvar_acolhimento(
                                conn, data_acolhimento, nome_pessoa, celular, 
                                id_status, id_faixa_etaria, aceita_contato, id_usuario
                            )
                            if suq:
                                st.success("Acolhimento concluído.")
                                time.sleep(2)
                                st.session_state.acolhimento_modo = 'listar'
                                st.session_state.acolhimento_selecionado_id = res
                                st.rerun()
                            else:
                                st.error(f"❌ Erro ao incluir: {res}")
                        elif st.session_state.acolhimento_modo == 'alterar':
                            id_p = reg_atual.get('idPessoa') if reg_atual else None
                            suq, err_msg = atualizar_acolhimento(
                                conn, int(st.session_state.acolhimento_selecionado_id), 
                                id_p, nome_pessoa, celular, id_status, id_faixa_etaria, aceita_contato
                            )
                            if suq:
                                st.success("Acolhimento alterado.")
                                time.sleep(2)
                                st.session_state.acolhimento_modo = 'listar'
                                st.rerun()
                            else:
                                st.error(f"Falha ao gravar o acolhimento: {err_msg}")

        modal_acolhimento()

    # Modal Excluir
    if st.session_state.acolhimento_modo == 'excluir':
        @st.dialog("⚠️ Confirmação de Exclusão", width="small")
        def modal_excluir():
            st.markdown("### Confirma exclusão?")
            
            with st.form("form_excluir_acolhimento_popup"):
                col_sim, col_nao = st.columns(2)
                with col_sim:
                    btn_sim = st.form_submit_button("Sim", use_container_width=True)
                with col_nao:
                    btn_nao = st.form_submit_button("Não", use_container_width=True)
                    
                if btn_nao:
                    st.session_state.acolhimento_modo = 'listar'
                    st.session_state.acolhimento_selecionado_id = None
                    st.rerun()
                    
                if btn_sim:
                    suq, err_msg = excluir_acolhimento(conn, int(st.session_state.acolhimento_selecionado_id))
                    if suq:
                        st.success("Acolhimento excluído.")
                        time.sleep(2)
                        st.session_state.acolhimento_modo = 'listar'
                        st.session_state.acolhimento_selecionado_id = None
                        st.rerun()
                    else:
                        st.error(f"Falha ao excluir o acolhimento: {err_msg}")

        modal_excluir()