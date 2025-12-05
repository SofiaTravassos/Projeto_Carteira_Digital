import os
import secrets
import hashlib
from typing import Dict, Any, Optional, List

from sqlalchemy import text

from api.persistence.db import get_connection


class CarteiraRepository:
    """
    Acesso a dados da carteira usando SQLAlchemy Core + SQL puro.
    """

    def criar(self) -> Dict[str, Any]:
        """
        Gera chave pública, chave privada, salva no banco (apenas hash da privada)
        e retorna os dados da carteira + chave privada em claro.
        """
        # 1) Geração das chaves
        private_key_size:int = int(os.getenv("PRIVATE_KEY_SIZE"))
        public_key_size:int = int(os.getenv("PUBLIC_KEY_SIZE"))
        chave_privada = secrets.token_hex(private_key_size)      # 32 bytes -> 64 hex chars (configurável depois)
        endereco = secrets.token_hex(public_key_size)           # "chave pública" simplificada
        hash_privada = hashlib.sha256(chave_privada.encode()).hexdigest()

        with get_connection() as conn:
            # 2) INSERT
            conn.execute(
                text("""
                    INSERT INTO carteira (endereco_carteira, hash_chave_privada)
                    VALUES (:endereco, :hash_privada)
                """),
                {"endereco": endereco, "hash_privada": hash_privada},
            )

            # 3) SELECT para retornar a carteira criada
            row = conn.execute(
                text("""
                    SELECT endereco_carteira,
                           data_criacao,
                           status,
                           hash_chave_privada
                      FROM carteira
                     WHERE endereco_carteira = :endereco
                """),
                {"endereco": endereco},
            ).mappings().first()

        carteira = dict(row)
        carteira["chave_privada"] = chave_privada
        return carteira

    def buscar_por_endereco(self, endereco_carteira: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute(
                text("""
                    SELECT endereco_carteira,
                           data_criacao,
                           status,
                           hash_chave_privada
                      FROM carteira
                     WHERE endereco_carteira = :endereco
                """),
                {"endereco": endereco_carteira},
            ).mappings().first()

        return dict(row) if row else None

    def listar(self) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                text("""
                    SELECT endereco_carteira,
                           data_criacao,
                           status,
                           hash_chave_privada
                      FROM carteira
                """)
            ).mappings().all()

        return [dict(r) for r in rows]

    def atualizar_status(self, endereco_carteira: str, status: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            conn.execute(
                text("""
                    UPDATE carteira
                       SET status = :status
                     WHERE endereco_carteira = :endereco
                """),
                {"status": status, "endereco": endereco_carteira},
            )

            row = conn.execute(
                text("""
                    SELECT endereco_carteira,
                           data_criacao,
                           status,
                           hash_chave_privada
                      FROM carteira
                     WHERE endereco_carteira = :endereco
                """),
                {"endereco": endereco_carteira},
            ).mappings().first()

        return dict(row) if row else None

    def listar_saldos(self, endereco_carteira: str) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                text("""
                    SELECT m.codigo AS moeda,
                           IFNULL(s.saldo, 0) AS saldo
                      FROM moeda m
                      LEFT JOIN saldo_carteira s 
                             ON m.id_moeda = s.id_moeda 
                            AND s.endereco_carteira = :endereco
                     ORDER BY m.id_moeda
                """),
                {"endereco": endereco_carteira},
            ).mappings().all()
            
        return [dict(r) for r in rows]

    def buscar_id_moeda(self, codigo: str) -> Optional[int]:
        with get_connection() as conn:
            row = conn.execute(
                text("SELECT id_moeda FROM moeda WHERE codigo = :codigo"),
                {"codigo": codigo}
            ).mappings().first()
        return row["id_moeda"] if row else None

    def buscar_saldo_especifico(self, endereco: str, id_moeda: int) -> float:
        with get_connection() as conn:
            row = conn.execute(
                text("""
                    SELECT saldo FROM saldo_carteira 
                     WHERE endereco_carteira = :endereco 
                       AND id_moeda = :id_moeda
                """),
                {"endereco": endereco, "id_moeda": id_moeda}
            ).mappings().first()
        return float(row["saldo"]) if row else 0.0

    def realizar_deposito(self, endereco: str, id_moeda: int, valor: float) -> int:
        with get_connection() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO deposito_saque (endereco_carteira, id_moeda, tipo, valor, taxa_valor)
                    VALUES (:endereco, :id_moeda, 'DEPOSITO', :valor, 0)
                """),
                {"endereco": endereco, "id_moeda": id_moeda, "valor": valor}
            )
            id_movimento = result.lastrowid

            conn.execute(
                text("""
                    INSERT INTO saldo_carteira (endereco_carteira, id_moeda, saldo)
                    VALUES (:endereco, :id_moeda, :valor)
                    ON DUPLICATE KEY UPDATE saldo = saldo + :valor
                """),
                {"endereco": endereco, "id_moeda": id_moeda, "valor": valor}
            )
            
        return id_movimento

    def realizar_saque(self, endereco: str, id_moeda: int, valor: float, taxa: float) -> int:
        total_debito = valor + taxa
        with get_connection() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO deposito_saque (endereco_carteira, id_moeda, tipo, valor, taxa_valor)
                    VALUES (:endereco, :id_moeda, 'SAQUE', :valor, :taxa)
                """),
                {"endereco": endereco, "id_moeda": id_moeda, "valor": valor, "taxa": taxa}
            )
            id_movimento = result.lastrowid

            conn.execute(
                text("""
                    UPDATE saldo_carteira
                       SET saldo = saldo - :total
                     WHERE endereco_carteira = :endereco
                       AND id_moeda = :id_moeda
                """),
                {"endereco": endereco, "id_moeda": id_moeda, "total": total_debito}
            )
        
        return id_movimento

    def realizar_conversao(self, endereco: str, id_origem: int, id_destino: int, 
                           valor_origem: float, valor_destino: float, 
                           taxa_valor: float, taxa_percentual: float, cotacao: float) -> int:
        total_debito = valor_origem + taxa_valor
        with get_connection() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO conversao (
                        endereco_carteira, id_moeda_origem, id_moeda_destino, 
                        valor_origem, valor_destino, taxa_percentual, taxa_valor, cotacao_utilizada
                    )
                    VALUES (
                        :endereco, :id_origem, :id_destino, 
                        :valor_origem, :valor_destino, :taxa_percentual, :taxa_valor, :cotacao
                    )
                """),
                {
                    "endereco": endereco, "id_origem": id_origem, "id_destino": id_destino,
                    "valor_origem": valor_origem, "valor_destino": valor_destino,
                    "taxa_percentual": taxa_percentual, "taxa_valor": taxa_valor, "cotacao": cotacao
                }
            )
            id_conversao = result.lastrowid

            conn.execute(
                text("""
                    UPDATE saldo_carteira
                       SET saldo = saldo - :total_debito
                     WHERE endereco_carteira = :endereco
                       AND id_moeda = :id_origem
                """),
                {"endereco": endereco, "id_origem": id_origem, "total_debito": total_debito}
            )

            conn.execute(
                text("""
                    INSERT INTO saldo_carteira (endereco_carteira, id_moeda, saldo)
                    VALUES (:endereco, :id_destino, :valor_destino)
                    ON DUPLICATE KEY UPDATE saldo = saldo + :valor_destino
                """),
                {"endereco": endereco, "id_destino": id_destino, "valor_destino": valor_destino}
            )

        return id_conversao

    def realizar_transferencia(self, end_origem: str, end_destino: str, 
                               id_moeda: int, valor: float, taxa: float) -> int:
        total_debito_origem = valor + taxa
        
        with get_connection() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO transferencia (
                        endereco_origem, endereco_destino, id_moeda, valor, taxa_valor
                    ) VALUES (
                        :origem, :destino, :id_moeda, :valor, :taxa
                    )
                """),
                {
                    "origem": end_origem, "destino": end_destino, 
                    "id_moeda": id_moeda, "valor": valor, "taxa": taxa
                }
            )
            id_transf = result.lastrowid

            conn.execute(
                text("""
                    UPDATE saldo_carteira
                       SET saldo = saldo - :total
                     WHERE endereco_carteira = :origem
                       AND id_moeda = :id_moeda
                """),
                {"origem": end_origem, "id_moeda": id_moeda, "total": total_debito_origem}
            )

            conn.execute(
                text("""
                    INSERT INTO saldo_carteira (endereco_carteira, id_moeda, saldo)
                    VALUES (:destino, :id_moeda, :valor)
                    ON DUPLICATE KEY UPDATE saldo = saldo + :valor
                """),
                {"destino": end_destino, "id_moeda": id_moeda, "valor": valor}
            )

        return id_transf