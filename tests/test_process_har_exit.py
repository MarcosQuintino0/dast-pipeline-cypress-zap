"""
Testes do codigo de saida do processamento do HAR.

O processamento e a etapa do meio do pipeline: os testes Cypress gravam o
trafego, ele filtra, e o scan consome o resultado. Quando essa etapa do meio
falha em silencio — registrando o erro no log e devolvendo status zero — o
passo seguinte recebe sinal de sucesso sobre um arquivo que nunca foi escrito.

Foi assim que a primeira execucao no GitHub Actions terminou: o log dizia
"No HAR files found", o passo ficou verde, e a falha so apareceu duas etapas
adiante, com uma mensagem que nao apontava para a causa.

Cada teste aqui fixa uma das tres formas de nao ter o que processar.
"""

import pytest

from security_tests.cli import process_har


def test_sem_arquivos_har_encerra_com_erro(monkeypatch):
    """Os testes Cypress nao rodaram, ou nao conseguiram gravar o HAR."""
    monkeypatch.setattr(process_har, "load_hars", lambda: [])

    with pytest.raises(SystemExit) as saida:
        process_har.main()

    assert saida.value.code == 1


def test_har_sem_entradas_encerra_com_erro(monkeypatch):
    """O arquivo existe, mas nao registrou requisicao alguma."""
    monkeypatch.setattr(process_har, "load_hars", lambda: [{"log": {"entries": []}}])
    monkeypatch.setattr(process_har, "extract_entries", lambda _hars: [])

    with pytest.raises(SystemExit) as saida:
        process_har.main()

    assert saida.value.code == 1


def test_nenhuma_entrada_aprovada_encerra_com_erro(monkeypatch):
    """Ha trafego, mas nenhuma requisicao passou pelas regras de endpoint.

    E o caso mais traicoeiro dos tres: o HAR esta la e parece saudavel. Sem
    esta verificacao, o scan rodaria contra uma lista vazia de alvos e
    reportaria zero alertas.
    """
    monkeypatch.setattr(process_har, "load_hars", lambda: [{"log": {"entries": [{}]}}])
    monkeypatch.setattr(process_har, "extract_entries", lambda _hars: [{}])
    monkeypatch.setattr(process_har, "filter_and_deduplicate_entries", lambda _entries: [])

    with pytest.raises(SystemExit) as saida:
        process_har.main()

    assert saida.value.code == 1
