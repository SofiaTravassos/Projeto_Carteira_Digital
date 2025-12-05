from typing import Literal
from datetime import datetime
from pydantic import BaseModel


class Carteira(BaseModel):
    endereco_carteira: str
    data_criacao: datetime
    status: Literal["ATIVA", "BLOQUEADA"]

class CarteiraCriada(Carteira):
    chave_privada: str

class Saldo(BaseModel):
    moeda: str
    saldo: float

class OperacaoDeposito(BaseModel):
    codigo_moeda: str
    valor: float

class OperacaoSaque(BaseModel):
    codigo_moeda: str
    valor: float
    chave_privada: str

class OperacaoConversao(BaseModel):
    moeda_origem: str
    moeda_destino: str
    valor: float
    chave_privada: str

class OperacaoTransferencia(BaseModel):
    endereco_destino: str
    codigo_moeda: str
    valor: float
    chave_privada: str

class ReciboMovimentacao(BaseModel):
    id_movimento: int
    tipo: str
    valor: float
    taxa: float
    saldo_atual: float

class ReciboConversao(BaseModel):
    id_conversao: int
    moeda_origem: str
    moeda_destino: str
    valor_convertido: float
    valor_recebido: float
    taxa_paga: float
    cotacao: float

class ReciboTransferencia(BaseModel):
    id_transferencia: int
    endereco_origem: str
    endereco_destino: str
    moeda: str
    valor_transferido: float
    taxa_paga: float