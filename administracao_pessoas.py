import streamlit as st
import pandas as pd
import time
from datetime import datetime
import logging

# Configuração de log para auditoria de erros internos
logger = logging.getLogger(__name__)

def listar_pessoas(conn):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        query = 'SELECT * FROM integra.vw_lista_pessoas ORDER BY "NomePessoa"'
        cursor.execute(query)
        resultados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        dados = [dict(zip(colunas, row)) for row in resultados]
        conn.commit()
        return dados
    except Exception as e:
        logger.error(f"Erro ao listar pessoas: {e}")
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

def listar_telefones_pessoa_view(conn, id_pessoa):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        query = 'SELECT "idPessoa", "idPessoaTelefone", "Telefone", "Observacao" FROM integra.vw_lista_pessoas_telefones WHERE "idPessoa" = %s'
        cursor.execute(query, (id_pessoa,))
        resultados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        dados = [dict(zip(colunas, row)) for row in resultados]
        conn.commit()
        return dados
    except Exception as e:
        logger.error(f"Erro ao listar telefones da pessoa ID {id_pessoa}: {e}")
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

def excluir_pessoa(conn, id_pessoa):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM integra."Pessoa" WHERE "idPessoa" = %s', (id_pessoa,))
        conn.commit()
        return True, "Pessoa excluída com sucesso."
    except Exception as e:
        logger.error(f"Erro ao excluir pessoa ID {id_pessoa}: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, "Não foi possível excluir a pessoa devido a um erro no sistema."
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass

def salvar_pessoa(conn, nome, cpf, email, data_nasc, id_grupo):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO integra."Pessoa" 
            ("NomePessoa", "CPF", "Email", "DataNascimento", "idGrupo")
            VALUES (%s, %s, %s, %s, %s)
            RETURNING "idPessoa"
        ''', (nome, cpf if cpf else None, email if email else None, data_nasc, id_grupo))
        
        id_pessoa = cursor.fetchone()[0]
        conn.commit()
        return True, id_pessoa
    except Exception as e:
        logger.error(f"Erro ao salvar pessoa: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, "Erro interno ao cadastrar pessoa."
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass

def atualizar_pessoa(conn, id_pessoa, nome, cpf, email, data_nasc, id_grupo):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE integra."Pessoa" 
            SET "NomePessoa" = %s, "CPF" = %s, "Email" = %s, "DataNascimento" = %s, "idGrupo" = %s
            WHERE "idPessoa" = %s
        ''', (nome, cpf if cpf else None, email if email else None, data_nasc, id_grupo, id_pessoa))
        
        conn.commit()
        return True, ""
    except Exception as e:
        logger.error(f"Erro ao atualizar pessoa ID {id_pessoa}: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, "Erro interno ao atualizar dados da pessoa."
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass

def buscar_grupos(conn):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        cursor.execute('SELECT "idGrupo", "NomeGrupo" FROM integra."GrupoPessoa" ORDER BY "NomeGrupo"')
        res = cursor.fetchall()
        conn.commit()
        return res
    except Exception as e:
        logger.error(f"Erro ao buscar grupos: {e}")
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

def administracao_pessoas_screen():
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

    if 'pessoa_modo' not in st.session_state:
        st.session_state.pessoa_modo = 'listar' 
    if 'pessoa_selecionada_id' not in st.session_state:
        st.session_state.pessoa_selecionada_id = None
    if 'mensagem_alerta_pessoa' not in st.session_state:
        st.session_state.mensagem_alerta_pessoa = ""

    st.markdown("### 👤 Gerenciamento de Pessoas")

    col_filtro1 = st.columns([1])[0]
    with col_filtro1:
        texto_filtro = st.text_input("Filtrar na grade", placeholder="Digite para buscar em qualquer coluna...", label_visibility="collapsed")

    dados = listar_pessoas(st.session_state.conn)
    
    if dados:
        df = pd.DataFrame(dados)
        if "DataNascimento" in df.columns:
            df["DataNascimento"] = pd.to_datetime(df["DataNascimento"], errors='coerce').dt.strftime('%d/%m/%Y')
    else:
        df = pd.DataFrame(columns=["idPessoa", "NomePessoa", "CPF", "Email", "DataNascimento", "idGrupo", "DataCadastro", "NomeGrupo"])

    if texto_filtro and not df.empty:
        mask = df.astype(str).apply(lambda x: x.str.contains(texto_filtro, case=False, na=False)).any(axis=1)
        df = df[mask]

    colunas_para_ocultar = ['idPessoa', 'idGrupo', 'DataCadastro']
    df_exibicao = df.drop(columns=[c for c in colunas_para_ocultar if c in df.columns], errors='ignore')

    rename_map = {
        'NomePessoa': 'Nome',
        'CPF': 'CPF',
        'Email': 'Email',
        'DataNascimento': 'Data Nasc.',
        'NomeGrupo': 'Grupo'
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
        if idx < len(df):
            selected_row = df.iloc[idx].to_dict()
            st.session_state.pessoa_selecionada_id = selected_row.get('idPessoa')
    else:
        if not selected_row_indices:
            st.session_state.pessoa_selecionada_id = None

    col_btn1, col_btn2, col_btn3, col_btn4, col_vazio = st.columns([0.8, 0.8, 0.8, 1.0, 6.6])
    
    with col_btn1:
        if st.button("➕ Incluir", key="btn_incluir_pessoa_acao"):
            st.session_state.pessoa_modo = 'incluir'
            st.session_state.pessoa_selecionada_id = None
            st.session_state.mensagem_alerta_pessoa = ""
            st.rerun()
            
    with col_btn2:
        if st.button("✏️ Alterar", key="btn_alterar_pessoa_acao"):
            if st.session_state.pessoa_selecionada_id:
                st.session_state.pessoa_modo = 'alterar'
                st.session_state.mensagem_alerta_pessoa = ""
                st.rerun()
            else:
                st.session_state.mensagem_alerta_pessoa = "Selecione uma linha da grade para alterar."
                st.rerun()
                
    with col_btn3:
        if st.button("🗑️ Excluir", key="btn_excluir_pessoa_acao"):
            if st.session_state.pessoa_selecionada_id:
                st.session_state.pessoa_modo = 'excluir'
                st.session_state.mensagem_alerta_pessoa = ""
                st.rerun()
            else:
                st.session_state.mensagem_alerta_pessoa = "Selecione uma linha da grade para excluir."
                st.rerun()

    with col_btn4:
        if st.button("📞 Telefones", key="btn_telefones_pessoa_acao"):
            if st.session_state.pessoa_selecionada_id:
                st.session_state.pessoa_modo = 'gerenciar_telefones'
                st.session_state.mensagem_alerta_pessoa = ""
                st.rerun()
            else:
                st.session_state.mensagem_alerta_pessoa = "Selecione uma pessoa para visualizar os telefones."
                st.rerun()

    if st.session_state.mensagem_alerta_pessoa:
        st.error(st.session_state.mensagem_alerta_pessoa)
        time.sleep(3)
        st.session_state.mensagem_alerta_pessoa = ""
        st.rerun()

    if st.session_state.pessoa_modo in ['incluir', 'alterar']:
        @st.dialog("📝 Nova Pessoa" if st.session_state.pessoa_modo == 'incluir' else "✏️ Editar Pessoa")
        def modal_pessoa():
            reg_atual = None
            if st.session_state.pessoa_modo == 'alterar' and st.session_state.pessoa_selecionada_id and dados:
                for r in dados:
                    if str(r['idPessoa']) == str(st.session_state.pessoa_selecionada_id):
                        reg_atual = r
                        break

            grupos_list = buscar_grupos(st.session_state.conn)

            with st.form("form_cad_pessoa_popup"):
                nome_val = reg_atual['NomePessoa'] if reg_atual and reg_atual.get('NomePessoa') else ""
                nome = st.text_input("Nome : *", value=str(nome_val) if nome_val and str(nome_val) != 'None' else "", max_chars=100, placeholder="Até 100 caracteres").upper()
                
                cpf_val = reg_atual.get('CPF', '') if reg_atual else ""
                cpf = st.text_input("CPF :", value=str(cpf_val) if cpf_val and str(cpf_val) != 'None' else "", max_chars=11, placeholder="Opcional (11 números)")
                
                email_val = reg_atual.get('Email', '') if reg_atual else ""
                email = st.text_input("Email :", value=str(email_val) if email_val and str(email_val) != 'None' else "", max_chars=50, placeholder="Opcional")
                
                id_grupo = None
                if grupos_list:
                    grupo_options = {g[1]: g[0] for g in grupos_list}
                    grupo_keys = ["Nenhum grupo"] + list(grupo_options.keys())
                    def_grupo_idx = 0
                    if reg_atual and reg_atual.get('NomeGrupo') in grupo_options:
                        def_grupo_idx = grupo_keys.index(reg_atual.get('NomeGrupo'))
                    grupo_sel = st.selectbox("Grupo :", options=grupo_keys, index=def_grupo_idx)
                    if grupo_sel != "Nenhum grupo":
                        id_grupo = grupo_options.get(grupo_sel)
                
                data_val = None
                if reg_atual and reg_atual.get('DataNascimento') and str(reg_atual.get('DataNascimento')) != 'None':
                    try:
                        data_val = pd.to_datetime(reg_atual.get('DataNascimento'), format='%d/%m/%Y').date()
                    except Exception:
                        try:
                            data_val = pd.to_datetime(reg_atual.get('DataNascimento')).date()
                        except Exception:
                            pass
                data_nasc = st.date_input("Data de Nascimento :", value=data_val, format="DD/MM/YYYY")
                
                col_salvar, col_cancel = st.columns(2)
                with col_salvar:
                    btn_salvar_form = st.form_submit_button("Salvar", use_container_width=True)
                with col_cancel:
                    btn_cancel_form = st.form_submit_button("Cancelar", use_container_width=True)
                
                msg_erro_placeholder = st.empty()
                    
                if btn_cancel_form:
                    st.session_state.pessoa_modo = 'listar'
                    st.session_state.pessoa_selecionada_id = None
                    st.rerun()
                    
                if btn_salvar_form:
                    if not nome or not nome.strip():
                        msg_erro_placeholder.error("O campo Nome é obrigatório!")
                        time.sleep(3)
                        msg_erro_placeholder.empty()
                    elif cpf and cpf.strip() != "" and (not cpf.strip().isdigit() or len(cpf.strip()) != 11):
                        msg_erro_placeholder.error("CPF deve ter 11 posições numéricas.")
                        time.sleep(3)
                        msg_erro_placeholder.empty()
                    else:
                        if st.session_state.pessoa_modo == 'incluir':
                            suq, res = salvar_pessoa(
                                st.session_state.conn, nome.strip(), cpf.strip() if cpf else None, 
                                email.strip() if email else None, data_nasc, id_grupo
                            )
                            if suq:
                                st.success("Pessoa gravada.")
                                time.sleep(3)
                                st.session_state.pessoa_modo = 'listar'
                                st.session_state.pessoa_selecionada_id = res
                                st.rerun()
                            else:
                                msg_erro_placeholder.error(res)
                                time.sleep(3)
                                msg_erro_placeholder.empty()
                        elif st.session_state.pessoa_modo == 'alterar':
                            suq, err_msg = atualizar_pessoa(
                                st.session_state.conn, int(st.session_state.pessoa_selecionada_id), 
                                nome.strip(), cpf.strip() if cpf else None, email.strip() if email else None, 
                                data_nasc, id_grupo
                            )
                            if suq:
                                st.success("Pessoa gravada.")
                                time.sleep(3)
                                st.session_state.pessoa_modo = 'listar'
                                st.rerun()
                            else:
                                msg_erro_placeholder.error(err_msg)
                                time.sleep(3)
                                msg_erro_placeholder.empty()

        modal_pessoa()

    if st.session_state.pessoa_modo == 'excluir':
        @st.dialog("⚠️ Confirmação de Exclusão")
        def modal_excluir():
            st.markdown("### Confirma exclusão?")
            
            with st.form("form_excluir_pessoa_popup"):
                col_sim, col_nao = st.columns(2)
                with col_sim:
                    btn_sim = st.form_submit_button("Sim", use_container_width=True)
                with col_nao:
                    btn_nao = st.form_submit_button("Não", use_container_width=True)
                    
                if btn_nao:
                    st.session_state.pessoa_modo = 'listar'
                    st.session_state.pessoa_selecionada_id = None
                    st.rerun()
                    
                if btn_sim:
                    suq, err_msg = excluir_pessoa(st.session_state.conn, int(st.session_state.pessoa_selecionada_id))
                    if suq:
                        st.success(err_msg)
                        time.sleep(3)
                        st.session_state.pessoa_modo = 'listar'
                        st.session_state.pessoa_selecionada_id = None
                        st.rerun()
                    else:
                        st.error(err_msg)
                        time.sleep(3)

        modal_excluir()

    if st.session_state.pessoa_modo == 'gerenciar_telefones':
        @st.dialog("📞 Gerenciamento de Telefones")
        def modal_gerenciar_telefones():
            id_pes = st.session_state.pessoa_selecionada_id
            telefones_dados = listar_telefones_pessoa_view(st.session_state.conn, id_pes)
            
            if telefones_dados:
                df_tel = pd.DataFrame(telefones_dados)
            else:
                df_tel = pd.DataFrame(columns=["idPessoa", "idPessoaTelefone", "Telefone", "Observacao"])

            colunas_ocultar_tel = ['idPessoa', 'idPessoaTelefone']
            df_tel_exibicao = df_tel.drop(columns=[c for c in colunas_ocultar_tel if c in df_tel.columns], errors='ignore')
            df_tel_exibicao = df_tel_exibicao.rename(columns={'Observacao': 'Obs'})

            st.dataframe(
                df_tel_exibicao,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )

            c_b1, c_b2, c_b3, c_b4 = st.columns(4)
            with c_b1:
                st.button("Incluir", key="btn_tel_inc")
            with c_b2:
                st.button("Alterar", key="btn_tel_alt")
            with c_b3:
                st.button("Excluir", key="btn_tel_exc")
            with c_b4:
                if st.button("Fechar", key="btn_tel_fechar"):
                    st.session_state.pessoa_modo = 'listar'
                    st.rerun()

        modal_gerenciar_telefones()