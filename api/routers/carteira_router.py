from fastapi import APIRouter, HTTPException, Depends
from typing import List

from api.services.carteira_service import CarteiraService
from api.persistence.repositories.carteira_repository import CarteiraRepository
from api.models.carteira_models import Carteira, CarteiraCriada, Saldo, OperacaoDeposito, ReciboMovimentacao, OperacaoSaque, OperacaoConversao, ReciboConversao, OperacaoTransferencia, ReciboTransferencia

router = APIRouter(prefix="/carteiras", tags=["carteiras"])


def get_carteira_service() -> CarteiraService:
    repo = CarteiraRepository()
    return CarteiraService(repo)


@router.post("", response_model=CarteiraCriada, status_code=201)
def criar_carteira(
    service: CarteiraService = Depends(get_carteira_service),
)->CarteiraCriada:
    """
    Cria uma nova carteira. O body é opcional .
    Retorna endereço e chave privada (apenas nesta resposta).
    """
    try:
        return service.criar_carteira()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[Carteira])
def listar_carteiras(service: CarteiraService = Depends(get_carteira_service)):
    return service.listar()


@router.get("/{endereco_carteira}", response_model=Carteira)
def buscar_carteira(
    endereco_carteira: str,
    service: CarteiraService = Depends(get_carteira_service),
):
    try:
        return service.buscar_por_endereco(endereco_carteira)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{endereco_carteira}", response_model=Carteira)
def bloquear_carteira(
    endereco_carteira: str,
    service: CarteiraService = Depends(get_carteira_service),
):
    try:
        return service.bloquear(endereco_carteira)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{endereco_carteira}/saldos", response_model=List[Saldo])
def listar_saldos_carteira(
    endereco_carteira: str,
    service: CarteiraService = Depends(get_carteira_service),
):
    try:
        return service.buscar_saldos(endereco_carteira)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{endereco_carteira}/depositos", response_model=ReciboMovimentacao)
def realizar_deposito(
    endereco_carteira: str,
    operacao: OperacaoDeposito,
    service: CarteiraService = Depends(get_carteira_service),
):
    try:
        return service.depositar(endereco_carteira, operacao)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{endereco_carteira}/saques", response_model=ReciboMovimentacao)
def realizar_saque(
    endereco_carteira: str,
    operacao: OperacaoSaque,
    service: CarteiraService = Depends(get_carteira_service),
):
    try:
        return service.sacar(endereco_carteira, operacao)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{endereco_carteira}/conversoes", response_model=ReciboConversao)
def realizar_conversao(
    endereco_carteira: str,
    operacao: OperacaoConversao,
    service: CarteiraService = Depends(get_carteira_service),
):
    try:
        return service.converter(endereco_carteira, operacao)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{endereco_carteira}/transferencias", response_model=ReciboTransferencia)
def realizar_transferencia(
    endereco_carteira: str,
    operacao: OperacaoTransferencia,
    service: CarteiraService = Depends(get_carteira_service),
):
    try:
        return service.transferir(endereco_carteira, operacao)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))