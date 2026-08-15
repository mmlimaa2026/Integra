import streamlit as st
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def listar_telefones_pessoa(conn, id_pessoa):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        query = 'SELECT * FROM integra.vw_lista_pessoas_telefones WHERE "idPessoa" = %s'
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

def verificar_telefone_existente(conn, telefone):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM integra."PessoaTelefone" WHERE "Telefone" = %s', (telefone,))
        count = cursor.fetchone()[0]
        conn.commit()
        return count > 0
    except Exception as e:
        logger.error(f"Erro ao verificar telefone existente: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass

def incluir_telefone(conn, id_pessoa, telefone, observacao):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO integra."PessoaTelefone" 
            ("idPessoa", "Telefone", "Observacao")
            VALUES (%s, %s, %s)
            RETURNING "idPessoaTelefone"
        ''', (id_pessoa, telefone, observacao if observacao else None))
        
        id_tel = cursor.fetchone()[0]
        conn.commit()
        return True, id_tel
    except Exception as e:
        logger.error(f"Erro ao incluir telefone: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, "Erro ao registrar telefone."
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass

def alterar_telefone(conn, id_pessoa_telefone, telefone, observacao):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE integra."PessoaTelefone" 
            SET "Telefone" = %s, "Observacao" = %s
            WHERE "idPessoaTelefone" = %s
        ''', (telefone, observacao if observacao else None, id_pessoa_telefone))
        
        conn.commit()
        return True, ""
    except Exception as e:
        logger.error(f"Erro ao alterar telefone ID {id_pessoa_telefone}: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, "Erro ao atualizar telefone."
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass

def excluir_telefone(conn, id_pessoa_telefone):
    cursor = None
    try:
        conn.rollback()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM integra."PessoaTelefone" WHERE "idPessoaTelefone" = %s', (id_pessoa_telefone,))
        conn.commit()
        return True, ""
    except Exception as e:
        logger.error(f"Erro ao excluir telefone ID {id_pessoa_telefone}: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, "Erro ao excluir telefone."
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass