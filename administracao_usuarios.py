import streamlit as st
import pandas as pd
import time
import logging
import hashlib

logger = logging.getLogger(__name__)

def hash_senha(senha: str) -> str:
    """Gera hash seguro para armazenamento de senhas."""
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

def listar_usuarios(conn):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        query = 'SELECT * FROM integra.vw_lista_usuarios ORDER BY "NomeUsuario"'
        cursor.execute(query)
        resultados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        dados = [dict(zip(colunas, row)) for row in resultados]
        conn.commit()
        return dados
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return []
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass

def excluir_usuario(conn, id_usuario):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM integra."Acolhimento" WHERE "idUsuario" = %s', (id_usuario,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            return False, "Exclusão do usuário negada: existem acolhimentos vinculados a este perfil."
            
        cursor.execute('DELETE FROM integra."Usuario" WHERE "idUsuario" = %s', (id_usuario,))
        conn.commit()
        return True, ""
    except Exception as e:
        logger.error(f"Erro ao excluir usuário ID {id_usuario}: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, "Não foi possível excluir o usuário por erro interno."
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass

def salvar_usuario(conn, nome, email, celular, senha, login, adm):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        
        senha_hashed = hash_senha(senha)
        
        cursor.execute('''
            INSERT INTO integra."Usuario" 
            ("NomeUsuario", "Email", "Celular", "Senha", "Login", "Adm")
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING "idUsuario"
        ''', (nome, email if email else None, celular, senha_hashed, login, adm))
        
        id_usuario = cursor.fetchone()[0]
        conn.commit()
        return True, id_usuario
    except Exception as e:
        logger.error(f"Erro ao salvar usuário: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, "Erro ao cadastrar usuário."
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass

def atualizar_usuario(conn, id_usuario, nome, email, celular, senha, login, adm):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        
        senha_hashed = hash_senha(senha)
        
        cursor.execute('''
            UPDATE integra."Usuario" 
            SET "NomeUsuario" = %s, "Email" = %s, "Celular" = %s, "Senha" = %s, "Login" = %s, "Adm" = %s
            WHERE "idUsuario" = %s
        ''', (nome, email if email else None, celular, senha_hashed, login, adm, id_usuario))
        
        conn.commit()
        return True, ""
    except Exception as e:
        logger.error(f"Erro ao atualizar usuário ID {id_usuario}: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, "Erro ao atualizar dados do usuário."
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass

def administracao_usuarios_screen():
    st.markdown("""
        <style>
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
            padding: 15px !important;
            max-width: 650px !important;
            width: 90% !important;
            margin: auto !important;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if 'usuario_modo' not in st.session_state:
        st.session_state.usuario_modo = 'listar' 
    if 'usuario_selecionado_id' not in st.session_state:
        st.session_state.usuario_selecionado_id = None
    if 'mensagem_alerta_usuario' not in st.session_state:
        st.session_state.mensagem_alerta_usuario = ""

    st.markdown("### 🔑 Gerenciamento de Usuários")

    col_filtro1 = st.columns([1])[0]
    with col_filtro1:
        texto_filtro = st.text_input("Filtrar na grade", placeholder="Digite para buscar em qualquer coluna...", label_visibility="collapsed")

    dados = listar_usuarios(st.session_state.conn)
    
    if dados:
        df = pd.DataFrame(dados)
        if "Senha" in df.columns:
            df["Senha"] = "********"
    else:
        df = pd.DataFrame(columns=["idUsuario", "NomeUsuario", "Email", "Celular", "Senha", "Login", "Adm"])

    if texto_filtro and not df.empty:
        mask = df.astype(str).apply(lambda x: x.str.contains(texto_filtro, case=False, na=False)).any(axis=1)
        df = df[mask]

    colunas_para_ocultar = ['idUsuario']
    df_exibicao = df.drop(columns=[c for c in colunas_para_ocultar if c in df.columns], errors='ignore')

    rename_map = {
        'NomeUsuario': 'Nome',
        'Email': 'Email',
        'Celular': 'Celular',
        'Senha': 'Senha',
        'Login': 'Login',
        'Adm': 'Adm'
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
    
    if selected_row_indices and not df.empty:
        idx = selected_row_indices[0]
        if idx < len(df):
            selected_row = df.iloc[idx].to_dict()
            st.session_state.usuario_selecionado_id = selected_row.get('idUsuario')
    else:
        if not selected_row_indices:
            st.session_state.usuario_selecionado_id = None

    col_btn1, col_btn2, col_btn3, col_vazio = st.columns([0.8, 0.8, 0.8, 7.6])
    
    with col_btn1:
        if st.button("➕ Incluir", key="btn_incluir_usuario_acao"):
            st.session_state.usuario_modo = 'incluir'
            st.session_state.usuario_selecionado_id = None
            st.session_state.mensagem_alerta_usuario = ""
            st.rerun()
            
    with col_btn2:
        if st.button("✏️ Alterar", key="btn_alterar_usuario_acao"):
            if st.session_state.usuario_selecionado_id:
                st.session_state.usuario_modo = 'alterar'
                st.session_state.mensagem_alerta_usuario = ""
                st.rerun()
            else:
                st.session_state.mensagem_alerta_usuario = "Selecione uma linha da grade para alterar."
                st.rerun()
                
    with col_btn3:
        if st.button("🗑️ Excluir", key="btn_excluir_usuario_acao"):
            if st.session_state.usuario_selecionado_id:
                st.session_state.usuario_modo = 'excluir'
                st.session_state.mensagem_alerta_usuario = ""
                st.rerun()
            else:
                st.session_state.mensagem_alerta_usuario = "Selecione uma linha da grade para excluir."
                st.rerun()

    if st.session_state.mensagem_alerta_usuario:
        st.error(st.session_state.mensagem_alerta_usuario)
        time.sleep(3)
        st.session_state.mensagem_alerta_usuario = ""
        st.rerun()

    if st.session_state.usuario_modo in ['incluir', 'alterar']:
        @st.dialog("📝 Novo Usuário" if st.session_state.usuario_modo == 'incluir' else "✏️ Editar Usuário")
        def modal_usuario():
            reg_atual = None
            if st.session_state.usuario_modo == 'alterar' and st.session_state.usuario_selecionado_id and dados:
                for r in dados:
                    if str(r['idUsuario']) == str(st.session_state.usuario_selecionado_id):
                        reg_atual = r
                        break

            with st.form("form_cad_usuario_popup"):
                nome_val = reg_atual['NomeUsuario'] if reg_atual and reg_atual.get('NomeUsuario') else ""
                nome = st.text_input("Nome : *", value=str(nome_val) if nome_val and str(nome_val) != 'None' else "", max_chars=50, placeholder="Até 50 posições")
                
                email_val = reg_atual.get('Email', '') if reg_atual else ""
                email = st.text_input("Email :", value=str(email_val) if email_val and str(email_val) != 'None' else "", max_chars=100, placeholder="Opcional (Até 100 posições)")
                
                celular_val = reg_atual.get('Celular', '') if reg_atual else ""
                celular = st.text_input("Celular : *", value=str(celular_val) if celular_val and str(celular_val) != 'None' else "", max_chars=11, placeholder="Até 11 posições")
                
                senha = st.text_input("Senha : *", max_chars=20, type="password", placeholder="Digite a nova senha")
                
                login_val = reg_atual.get('Login', '') if reg_atual else ""
                login = st.text_input("Login : *", value=str(login_val) if login_val and str(login_val) != 'None' else "", max_chars=20, placeholder="Até 20 posições")
                
                adm_val = False
                if reg_atual and reg_atual.get('Adm') == 'S':
                    adm_val = True
                adm_checkbox = st.checkbox("Usuário Administrador", value=adm_val)
                
                col_salvar, col_cancel = st.columns(2)
                with col_salvar:
                    btn_salvar_form = st.form_submit_button("Salvar", use_container_width=True)
                with col_cancel:
                    btn_cancel_form = st.form_submit_button("Cancelar", use_container_width=True)
                
                msg_erro_placeholder = st.empty()
                    
                if btn_cancel_form:
                    st.session_state.usuario_modo = 'listar'
                    st.session_state.usuario_selecionado_id = None
                    st.rerun()
                    
                if btn_salvar_form:
                    adm_char = 'S' if adm_checkbox else 'N'
                    
                    if not nome or not nome.strip():
                        msg_erro_placeholder.error("O campo Nome é obrigatório!")
                        time.sleep(3)
                        msg_erro_placeholder.empty()
                    elif not celular or not celular.strip():
                        msg_erro_placeholder.error("O campo Celular é obrigatório!")
                        time.sleep(3)
                        msg_erro_placeholder.empty()
                    elif not senha or not senha.strip():
                        msg_erro_placeholder.error("O campo Senha é obrigatório!")
                        time.sleep(3)
                        msg_erro_placeholder.empty()
                    elif not login or not login.strip():
                        msg_erro_placeholder.error("O campo Login é obrigatório!")
                        time.sleep(3)
                        msg_erro_placeholder.empty()
                    else:
                        if st.session_state.usuario_modo == 'incluir':
                            suq, res = salvar_usuario(
                                st.session_state.conn, nome.strip(), email.strip() if email else None, 
                                celular.strip(), senha.strip(), login.strip(), adm_char
                            )
                            if suq:
                                msg_erro_placeholder.success("Usuário gravado.")
                                time.sleep(3)
                                st.session_state.usuario_modo = 'listar'
                                st.session_state.usuario_selecionado_id = res
                                st.rerun()
                            else:
                                msg_erro_placeholder.error(res)
                                time.sleep(3)
                                msg_erro_placeholder.empty()
                        elif st.session_state.usuario_modo == 'alterar':
                            suq, err_msg = atualizar_usuario(
                                st.session_state.conn, int(st.session_state.usuario_selecionado_id), 
                                nome.strip(), email.strip() if email else None, celular.strip(), 
                                senha.strip(), login.strip(), adm_char
                            )
                            if suq:
                                msg_erro_placeholder.success("Usuário gravado.")
                                time.sleep(3)
                                st.session_state.usuario_modo = 'listar'
                                st.rerun()
                            else:
                                msg_erro_placeholder.error(err_msg)
                                time.sleep(3)
                                msg_erro_placeholder.empty()

        modal_usuario()

    if st.session_state.usuario_modo == 'excluir':
        @st.dialog("⚠️ Confirmação de Exclusão")
        def modal_excluir():
            st.markdown("### Confirma exclusão?")
            
            with st.form("form_excluir_usuario_popup"):
                col_sim, col_nao = st.columns(2)
                with col_sim:
                    btn_sim = st.form_submit_button("Sim", use_container_width=True)
                with col_nao:
                    btn_nao = st.form_submit_button("Não", use_container_width=True)
                
                msg_erro_excluir_placeholder = st.empty()
                    
                if btn_nao:
                    st.session_state.usuario_modo = 'listar'
                    st.session_state.usuario_selecionado_id = None
                    st.rerun()
                    
                if btn_sim:
                    suq, err_msg = excluir_usuario(st.session_state.conn, int(st.session_state.usuario_selecionado_id))
                    if suq:
                        msg_erro_excluir_placeholder.success("Usuário excluído.")
                        time.sleep(3)
                        st.session_state.usuario_modo = 'listar'
                        st.session_state.usuario_selecionado_id = None
                        st.rerun()
                    else:
                        msg_erro_excluir_placeholder.error(err_msg)
                        time.sleep(3)
                        msg_erro_excluir_placeholder.empty()

        modal_excluir()