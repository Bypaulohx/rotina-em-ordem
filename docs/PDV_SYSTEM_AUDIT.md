# Auditoria do PDV

Data: 24/11/2026. O sistema é o Rotina em ordem: FastAPI, SQLAlchemy e SQLite em `sistema/rotina.db`, com a tela em React e Vite. A vaga operacional do pet shop continua sendo a baia. O PDV registra produto e pagamento; não substitui agenda, hotel nem pacote.

## O que já existe e foi reutilizado

- Produto, com preço, custo, estoque, mínimo, código de barras, categoria, marca, validade, fornecedor e unidade (`un` ou `kg`).
- Cliente, com telefone, CPF e pets. A venda exige um cliente cadastrado.
- Estoque baixa numa única venda (`Venda` + `ItemVenda` + `MovimentoEstoque`). O pedido da loja pública só reserva; o recebimento cria uma venda.
- Caixa por operador. Dinheiro esperado = saldo inicial + parte em dinheiro + suprimento − sangria. Pix e cartão não entram na gaveta.
- Pagamento dividido em `Pagamento` (forma, valor, recebido, troco, parcelas). Formas reais: dinheiro, Pix, débito e crédito.
- Venda suspensa não mexe no estoque. Cancelar uma venda paga, no caixa ainda aberto do mesmo operador, devolve o estoque.
- Conferência cega no fechamento. A diferença aparece depois da contagem.
- Transferência do caixa aberto para outro operador que não tenha caixa aberto. As vendas antigas continuam no mesmo caixa.
- Código de balança de 13 dígitos começando com 2: PLU no produto e peso em gramas. Não há SDK de balança.
- Papéis: recepção, banho e tosa, veterinário, estoque, gerência e dono. A API recusa a rota quando o cargo não tem o recurso.
- Atividade do funcionário, indicadores e financeiro. Despesa aberta não entra no gasto. Venda que não está paga não entra na receita.
- Leitor USB no modo teclado. WhatsApp oficial por webhook, sem sessão da Meta configurada. Ponto só por arquivo AFD.

## O que esta entrega acrescentou

A frente de caixa deixou de ser só um modal. A página `Frente de caixa` usa o catálogo real: busca por nome, código, marca e categoria, grade de produtos, pedido à direita, tutor, animal, desconto e acréscimo da venda, pagamento dividido, troco, suspensão e comprovante para impressão do navegador.

Atalhos que não brigam com o navegador: F2 busca, F3 cliente, F4 quantidade, F6 suspender, F8 consulta de preço, F10 receber, Esc limpa a busca. F1, F5, F11 e F12 ficam com o navegador.

O histórico da venda passa a devolver o `produto_id`, para a venda suspensa voltar ao pedido. A lista de pessoas passa a incluir o CPF que já estava no cadastro. Sangria, suprimento, transferência, cancelamento e venda no PDV ganham texto na auditoria de atividade.

## O que não foi feito, e por quê

Não há segunda tabela de venda, de caixa ou de pagamento.

Não há filial, terminal numerado nem status de impressora, balança ou pinpad. A loja é um estabelecimento. Mostrar “impressora online” seria falso.

Não há foto de produto. O cartão mostra as iniciais. Não foram colocadas imagens de banco.

Não há imposto no total. A linha de “sales tax” da referência visual é de outro país. NFC-e, SAT, CF-e e NF-e não são emitidos. O comprovante da tela é comercial, não é documento fiscal.

Pix não gera QR Code nem consulta pagamento. O operador registra que recebeu. Cartão não tem adquirente, bandeira, NSU nem TID, porque não existe integração. O número de parcelas é só o que foi combinado no balcão.

Não há vale-presente, crédito interno, frete, cupom, fidelidade, promoção automática nem desconto por quantidade. O desconto é o valor que o operador lança na venda, limitado ao total dos itens. Não há senha de gerente separada: quem está logado e pode vender aplica o desconto, e a atividade fica no nome dele.

Não há venda sem cliente. Serviço de banho e tosa, pacote e hotel continuam na agenda, porque a baia e o crédito do pacote não podem ser contornados por um item genérico no pedido.

Não há devolução nem troca como fluxo próprio. O cancelamento da venda paga, com o caixa do operador ainda aberto, estorna o estoque. Uma troca parcial precisaria de um documento novo e não foi inventada.

Não há histórico de preço. O preço vigente é o do cadastro.

Unidade de pacote e de caixa não existe. Só unidade e quilograma.

## Riscos

- O desconto e o acréscimo ficam na venda. O valor de cada item continua o bruto. O total financeiro é o líquido. Quem ler só a soma dos itens, sem o desconto, erra o caixa.
- Produto por peso guarda o estoque em gramas. Um produto antigo em unidade não pode ser marcado como `kg` sem converter o número do estoque.
- A grade carrega até 200 produtos ativos. Acima disso a busca por nome continua, mas a grade não mostra a loja inteira de uma vez.
- Gerência e estoque enxergam a frente, mas só recebem se tiverem o próprio caixa aberto. A gerência não abre caixa.
- A conferência cega esconde o dinheiro esperado no fechamento. O resumo por forma continua visível durante o turno, senão o operador não confere Pix e cartão.

## Plano que permanece

1. Feito: auditoria e frente de caixa em cima da venda, do estoque e do caixa atuais.
2. Feito nesta tela: catálogo, carrinho, cliente, pagamento e atalhos.
3. Caixa: abertura, sangria, suprimento, transferência e fechamento cego já operam na página Caixas.
4. Histórico: a página Vendas lista o que foi pago. Falta filtrar por período, operador, produto e status sem criar outro relatório.
5. Pet shop: tutor e animal entram no pedido. Banho, tosa, pacote e agenda permanecem no fluxo da baia.
6. Supermercado: peso e código variável já funcionam. Falta pacote, caixa, promoção e impressora térmica de verdade.
7. Fiscal e dispositivos: só quando houver certificado, provedor de Pix e protocolo do equipamento. Até lá a camada não finge autorização.
8. Relatórios: os indicadores atuais usam venda paga. Ticket médio, ranking e horário de movimento podem sair dessa mesma consulta, sem outra base.
