import os
import hashlib
import httpx
from typing import List

from api.persistence.repositories.carteira_repository import CarteiraRepository
from api.models.carteira_models import Carteira, CarteiraCriada, Saldo, OperacaoDeposito, OperacaoSaque, ReciboMovimentacao, OperacaoConversao, ReciboConversao, OperacaoTransferencia, ReciboTransferencia

class CarteiraService:
    def __init__(self, carteira_repo: CarteiraRepository):
        self.carteira_repo = carteira_repo

    def criar_carteira(self) -> CarteiraCriada:
        row = self.carteira_repo.criar()
        # row tem: endereco_carteira, data_criacao, status, hash_chave_privada, chave_privada
        # não expomos o hash
        return CarteiraCriada(
            endereco_carteira=row["endereco_carteira"],
            data_criacao=row["data_criacao"],
            status=row["status"],
            chave_privada=row["chave_privada"],
        )

    def buscar_por_endereco(self, endereco_carteira: str) -> Carteira:
        row = self.carteira_repo.buscar_por_endereco(endereco_carteira)
        if not row:
            raise ValueError("Carteira não encontrada")

        return Carteira(
            endereco_carteira=row["endereco_carteira"],
            data_criacao=row["data_criacao"],
            status=row["status"],
        )

    def listar(self) -> List[Carteira]:
        rows = self.carteira_repo.listar()
        return [
            Carteira(
                endereco_carteira=r["endereco_carteira"],
                data_criacao=r["data_criacao"],
                status=r["status"],
            )
            for r in rows
        ]

    def bloquear(self, endereco_carteira: str) -> Carteira:
        row = self.carteira_repo.atualizar_status(endereco_carteira, "BLOQUEADA")
        if not row:
            raise ValueError("Carteira não encontrada")

        return Carteira(
            endereco_carteira=row["endereco_carteira"],
            data_criacao=row["data_criacao"],
            status=row["status"],
        )

    def buscar_saldos(self, endereco_carteira: str) -> List[Saldo]:
        if not self.carteira_repo.buscar_por_endereco(endereco_carteira):
            raise ValueError("Carteira não encontrada")

        rows = self.carteira_repo.listar_saldos(endereco_carteira)
        return [
            Saldo(moeda=r["moeda"], saldo=float(r["saldo"]))
            for r in rows
        ]

    def depositar(self, endereco: str, dados: OperacaoDeposito) -> ReciboMovimentacao:
        id_moeda = self.carteira_repo.buscar_id_moeda(dados.codigo_moeda)
        if not id_moeda:
            raise ValueError(f"Moeda {dados.codigo_moeda} inválida")

        id_mov = self.carteira_repo.realizar_deposito(endereco, id_moeda, dados.valor)
        novo_saldo = self.carteira_repo.buscar_saldo_especifico(endereco, id_moeda)

        return ReciboMovimentacao(
            id_movimento=id_mov,
            tipo="DEPOSITO",
            valor=dados.valor,
            taxa=0.0,
            saldo_atual=novo_saldo
        )

    def sacar(self, endereco: str, dados: OperacaoSaque) -> ReciboMovimentacao:
        carteira_row = self.carteira_repo.buscar_por_endereco(endereco)
        if not carteira_row:
            raise ValueError("Carteira não encontrada")

        hash_enviado = hashlib.sha256(dados.chave_privada.encode()).hexdigest()
        if carteira_row["hash_chave_privada"] != hash_enviado:
             raise ValueError("Chave privada inválida!")

        id_moeda = self.carteira_repo.buscar_id_moeda(dados.codigo_moeda)
        if not id_moeda:
            raise ValueError(f"Moeda {dados.codigo_moeda} inválida")

        taxa_percentual = float(os.getenv("TAXA_SAQUE_PERCENTUAL", 0.01))
        taxa_valor = dados.valor * taxa_percentual
        total_necessario = dados.valor + taxa_valor

        saldo_atual = self.carteira_repo.buscar_saldo_especifico(endereco, id_moeda)
        if saldo_atual < total_necessario:
            raise ValueError("Saldo insuficiente para saque + taxa")

        id_mov = self.carteira_repo.realizar_saque(endereco, id_moeda, dados.valor, taxa_valor)
        novo_saldo = self.carteira_repo.buscar_saldo_especifico(endereco, id_moeda)

        return ReciboMovimentacao(
            id_movimento=id_mov,
            tipo="SAQUE",
            valor=dados.valor,
            taxa=taxa_valor,
            saldo_atual=novo_saldo
        )

    def converter(self, endereco: str, dados: OperacaoConversao) -> ReciboConversao:
        carteira_row = self.carteira_repo.buscar_por_endereco(endereco)
        if not carteira_row:
            raise ValueError("Carteira não encontrada")

        hash_enviado = hashlib.sha256(dados.chave_privada.encode()).hexdigest()
        if carteira_row["hash_chave_privada"] != hash_enviado:
             raise ValueError("Chave privada inválida!")

        id_origem = self.carteira_repo.buscar_id_moeda(dados.moeda_origem)
        id_destino = self.carteira_repo.buscar_id_moeda(dados.moeda_destino)
        if not id_origem or not id_destino:
            raise ValueError("Moeda de origem ou destino inválida")

        par = f"{dados.moeda_origem.upper()}-{dados.moeda_destino.upper()}"
        url = f"https://api.coinbase.com/v2/prices/{par}/spot"
        
        try:
            resp = httpx.get(url, timeout=10)
            if resp.status_code != 200:
                raise ValueError(f"Par {par} não disponível na Coinbase.")
            cotacao = float(resp.json()["data"]["amount"])
        except Exception:
            raise ValueError("Erro ao obter cotação.")

        taxa_percentual = float(os.getenv("TAXA_CONVERSAO_PERCENTUAL", 0.02))
        taxa_valor = dados.valor * taxa_percentual
        total_debito = dados.valor + taxa_valor
        valor_destino = dados.valor * cotacao

        saldo_origem = self.carteira_repo.buscar_saldo_especifico(endereco, id_origem)
        if saldo_origem < total_debito:
            raise ValueError(f"Saldo insuficiente em {dados.moeda_origem}.")

        id_conv = self.carteira_repo.realizar_conversao(
            endereco, id_origem, id_destino, dados.valor, valor_destino, 
            taxa_valor, taxa_percentual, cotacao
        )

        return ReciboConversao(
            id_conversao=id_conv,
            moeda_origem=dados.moeda_origem,
            moeda_destino=dados.moeda_destino,
            valor_convertido=dados.valor,
            valor_recebido=valor_destino,
            taxa_paga=taxa_valor,
            cotacao=cotacao
        )

    def transferir(self, endereco_origem: str, dados: OperacaoTransferencia) -> ReciboTransferencia:
        origem_row = self.carteira_repo.buscar_por_endereco(endereco_origem)
        if not origem_row:
            raise ValueError("Carteira de origem não encontrada")

        hash_enviado = hashlib.sha256(dados.chave_privada.encode()).hexdigest()
        if origem_row["hash_chave_privada"] != hash_enviado:
             raise ValueError("Chave privada inválida!")

        if endereco_origem == dados.endereco_destino:
            raise ValueError("Não é possível transferir para a própria carteira.")
            
        destino_row = self.carteira_repo.buscar_por_endereco(dados.endereco_destino)
        if not destino_row:
            raise ValueError("Carteira de destino não encontrada")

        if destino_row["status"] != "ATIVA":
             raise ValueError("Carteira de destino está bloqueada/inativa")

        id_moeda = self.carteira_repo.buscar_id_moeda(dados.codigo_moeda)
        if not id_moeda:
            raise ValueError(f"Moeda {dados.codigo_moeda} inválida")

        taxa_percentual = float(os.getenv("TAXA_TRANSFERENCIA_PERCENTUAL", 0.01))
        taxa_valor = dados.valor * taxa_percentual
        total_debito = dados.valor + taxa_valor

        saldo_origem = self.carteira_repo.buscar_saldo_especifico(endereco_origem, id_moeda)
        if saldo_origem < total_debito:
            raise ValueError("Saldo insuficiente para transferência + taxa")

        id_transf = self.carteira_repo.realizar_transferencia(
            endereco_origem, dados.endereco_destino, id_moeda, dados.valor, taxa_valor
        )

        return ReciboTransferencia(
            id_transferencia=id_transf,
            endereco_origem=endereco_origem,
            endereco_destino=dados.endereco_destino,
            moeda=dados.codigo_moeda,
            valor_transferido=dados.valor,
            taxa_paga=taxa_valor
        )