# Rotina em ordem — o que explicar

Sistema de banho, tosa e hotel para uma loja pequena. A diferença não é um caixa genérico: a vaga de verdade é a **baia**. O horário só entra se existir uma baia do porte do pet, livre da chegada até a busca. No hotel, a baia fica ocupada noite a noite, e feriado muda o valor da diária.

Login da demonstração: **paulo** / **rotina** (administração).

---

## Por que essas linguagens

**Python.** A matéria exige FastAPI, e FastAPI é um framework Python. A regra da loja (porte, conflito de horário, feriado, atraso, crédito do pacote, dinheiro do caixa) está em funções puras, em `sistema/app/rules.py`, sem banco no meio. Dá para testar a regra sem subir a tela.

**FastAPI.** É o pedido da disciplina. Ele publica a API, valida o corpo das requisições, devolve erro de negócio com status HTTP (409 quando a baia não cabe, 403 quando a equipe tenta abrir a administração) e gera a documentação automática em `http://127.0.0.1:8765/docs`. A tela não acessa o banco. Ela só chama essa API.

**React.** A tela muda o tempo todo: status da baia, modal de agendamento, calendário, caixa aberto. Cada pedaço é um componente, em `sistema/frontend/src`. O Vite só serve essa tela no desenvolvimento, na porta 5173, e encaminha `/api` para o FastAPI. Em produção a interface continuaria sendo arquivos estáticos falando com a mesma API.

**SQLite.** Um arquivo, `sistema/rotina.db`. Não precisa instalar um servidor de banco para uma loja só. O SQLAlchemy monta as tabelas. Se a coluna nova não existir num arquivo antigo, `migrar()` faz o `ALTER TABLE`.

**Inter e Lucide.** A fonte e os ícones do desenho. O peso 400 é o texto, 500 é menu e rótulo, 600 é título e botão. Não é tudo em negrito.

---

## Como as peças se falam

```
navegador  →  React (5173)  →  /api  →  FastAPI (8765)  →  SQLite
```

O login devolve um cookie `sessao`, httponly, válido por 7 dias. A senha não fica em texto: é PBKDF2-SHA256 com sal, em `sistema/app/security.py`. Cada alteração que dá certo (criar horário, fechar caixa, cadastrar pet) gera uma linha de atividade. A administração lê essa lista.

O cargo limita o menu e a API. Recepção vê a rotina e o caixa. Veterinário vê agenda, pets, boletins, prontuário e lembretes. Banho e tosa vê o salão. Estoque vê catálogo, estoque e vendas. Gerência vê quase tudo, menos caixa, prontuário e administração. O dono vê tudo. Quem não tem o cargo recebe 403.

---

## A regra, na ordem em que ela decide

1. O pet tem porte P, M ou G. Um pet pequeno pode usar baia maior. O sistema escolhe a **menor** baia livre que caiba.
2. No salão, a baia ocupa da chegada até a hora combinada da busca. Tocar um intervalo no outro não é conflito.
3. Se o pet ficou pronto, ou o horário passou e ninguém deu baixa, a baia **continua ocupada**. Não libera sozinha. A equipe marca falta, cancela ou registra a busca.
4. O profissional só fica ocupado no tempo do serviço, e só continua ocupado se o serviço já começou e não foi encerrado.
5. No hotel, cada noite tem preço. Feriado usa o valor de feriado. Se o checkout previsto chegou e não foi lançado, a baia de hotel segue ocupada.
6. O pacote é crédito **do pet**. Na busca, um crédito zera o serviço. O atraso da busca, se a equipe confirmar, entra à parte.
7. O caixa do turno espera só dinheiro: saldo inicial, mais a parte em dinheiro das vendas, mais suprimento, menos sangria. Pix e cartão não entram na gaveta. Uma venda pode ser paga com mais de uma forma. No fechamento a pessoa conta sem ver o valor esperado; depois o sistema mostra a diferença e a sessão volta para o login. Não “acha” a diferença sozinho.

---

## O que cada tela faz

| Tela | Para que serve |
| --- | --- |
| Visão geral | O dia: quantos horários, pets, clientes, vendas do mês, quem ainda segura baia e se o caixa do turno está aberto. |
| Mapa de baias | O salão e o hotel agora. Daqui a equipe marca chegou, inicia, pronto, busca, falta ou checkout. |
| Agenda & hotel | Mês, semana ou lista. Banho, tosa e hospedagem no mesmo calendário. Dá para filtrar o profissional. |
| Vendas | O que foi recebido: busca, checkout, pacote ou venda de balcão. |
| Pets & clientes | O serviço nasce do pet: porte, cuidado e crédito do pacote. O CEP completa o endereço. |
| Caixas | Abre o turno, mostra o dinheiro esperado e fecha com o valor que a equipe contou. |
| Boletins | A passagem de turno de um dia: salão, hotel, lembretes e produto no limite. |
| Prontuário | Observação do banho, da tosa e do hotel. Não substitui o veterinário. |
| Lembretes | O que a próxima pessoa da loja precisa ver. |
| Catálogo | Preço do serviço por porte e os produtos do balcão. |
| Estoque | Entrada e saída. Não deixa a quantidade ficar negativa. Avisa quando passa do mínimo. |
| Financeiro | Vendas do mês por forma de pagamento, menos as despesas lançadas. |
| WhatsApp | O número da loja e as mensagens. Se a frase tiver pet, serviço e horário **e a baia couber**, o horário nasce. Se não couber, a mensagem fica para a equipe ler. |
| Administração | Cadastro de funcionário e o que cada pessoa fez. |

O primeiro acesso (loja sem pet, sem cliente, sem venda e sem caixa) troca a visão geral por um convite a cadastrar. Quando os dados entram, volta o painel preenchido. Uma lista vazia dentro de uma loja que já funciona explica o que falta naquela lista, sem zerar o resto da tela.

---

## APIs de fora

**BrasilAPI**, feriados nacionais (`/api/feriados/v1/{ano}`). Na subida, o sistema pede o ano atual e o seguinte e grava na tabela. Por baixo existe uma lista local (Páscoa, Sexta-feira Santa e as datas fixas, inclusive Consciência Negra em 20/11). Se a rede falhar, a lista local continua valendo. Finados, 2/11, é o exemplo da diária de feriado na demonstração.

**ViaCEP** (`/ws/{cep}/json/`). No cadastro do cliente, o CEP preenche rua, bairro e cidade. O sistema não inventa endereço.

**WhatsApp.** Não é o WhatsApp Web e não raspa conversa. A loja guarda o número dela e recebe um token. O endereço `POST /api/whatsapp/webhook` aceita o formato do webhook oficial da Meta, ou uma mensagem simples `{ texto, telefone, token }`. O botão “Receber” da tela usa a mesma função, para a aula funcionar sem conta na Meta. Não diga que a Meta está conectada.

---

## O que não prometer

Está fora de propósito, e a tela não faz:

- o tutor marcar sozinho
- mensagem automática de WhatsApp
- nota fiscal
- várias lojas
- aplicativo do dono do pet
- estoque baixando sozinho no banho
- o sistema descobrir sozinho a diferença do caixa

---

## Como rodar e como provar

Duas janelas, a partir de `sistema`:

```powershell
python -m uvicorn app.main:app --port 8765
```

```powershell
cd frontend
npm run dev
```

A tela abre em `http://127.0.0.1:5173/`. A porta 8000 nesta máquina não sobe; por isso a API ficou na 8765.

Os testes estão em `sistema/tests` e rodam com `python -m pytest` dentro de `sistema`. Eles usam um banco na memória, não o `rotina.db` da demonstração. O que eles travam: porte grande sem baia, diária de Finados, pacote que zera o serviço e atraso cobrado à parte, horário de outro dia sem baixa que continua no mapa, estoque que recusa saída maior que o saldo, e equipe sem acesso à administração.

---

## Se o professor perguntar

**Por que FastAPI e não outro framework?** Porque a disciplina pede FastAPI. Ele entrega a API, a validação e o `/docs`. A regra da baia não ficou presa na rota: está em funções testáveis.

**Por que React se o backend já poderia servir HTML?** A tela tem estado demais para um HTML único: baia, agenda, modal e o que cada papel pode ver. Separar a interface deixa a API testável sem abrir o navegador.

**Por que a baia não libera quando o horário acaba?** Porque o pet pronto, ou o horário que ninguém encerrou, ainda está na vaga. Liberar sozinho faria a loja vender a mesma baia duas vezes. A equipe marca falta, cancela ou registra a busca.

**Por que o mapa de hoje mostra pet de outro dia?** Pelo mesmo motivo. A demonstração foi montada em 31/10. O que não teve baixa (Mel em atendimento, Amora, Pipoca, Luna) segue na baia. O aviso no topo diz isso. Não é dado fantasma: é a regra.

**Por que Pix não entra no dinheiro esperado?** Porque Pix e cartão não ficam na gaveta. O caixa confere cédula. O esperado é saldo inicial, mais a parte em dinheiro, mais suprimento, menos sangria.

**Por que o feriado não vem só da internet?** Porque a aula e a loja precisam funcionar sem rede. A BrasilAPI atualiza os nomes oficiais. A lista local segura o ano se a chamada falhar.

**O WhatsApp cria horário sozinho?** Só quando a frase traz um pet já cadastrado, o serviço (banho, tosa ou hotel) e um horário, e a regra da baia aceita. Caso contrário a mensagem fica pendente para uma pessoa ler. Não há envio automático de volta para o tutor.

---

## O que entrou na evolução, e o que depende de contrato

O cadastro exige telefone com DDD, CEP e endereço. CPF e e-mail, quando preenchidos, são validados no servidor. Telefone repetido não cria outro cliente. O mesmo tutor não cadastra dois animais com o mesmo nome. A ficha do cliente e a ficha do animal reúnem pacote, atendimento, hospedagem, compra e prontuário que já existiam.

O pacote tem nome comercial (`Banho — 4 sessões`). O nome do animal não entra nesse título. Na busca, uma sessão é baixada do pacote e do crédito.

O PDV recebe o leitor USB ou Bluetooth que se apresenta como teclado (HID): o equipamento digita o código e manda Enter. O produto entra no carrinho, a quantidade soma se o mesmo código passar de novo, e a venda confirmada baixa o estoque na mesma transação da venda. Não há uma segunda receita no financeiro: a venda paga é a entrada. Conta em aberto (`status` aberta) não entra no resultado até ser paga.

A loja pública fica em `http://127.0.0.1:5173/loja`. Ela usa o mesmo estoque. O checkout reserva a unidade. O pagamento na retirada, lançado uma vez pela equipe, gera a única venda. Dois pedidos não levam a última unidade. Cartão e Pix online não estão ligados: isso exige contrato com um provedor (PagSeguro, Mercado Pago ou o banco). A retirada evita uma cobrança fictícia.

O ponto não tem botão de bater entrada. A equipe importa o arquivo AFD do relógio, no registro tipo 3 da Portaria 1510. O NSR repetido não duplica a marcação. O PIS associa o funcionário quando o cadastro tem esse número. Relógio de rede de um fabricante específico (Control iD, Henry, Topdata, Dimep) fala um protocolo próprio; ligar um modelo exige o SDK ou a API daquele fabricante, e isso fica de fora até haver o equipamento e o contrato.

Papéis: recepção opera a rotina e o caixa; veterinário fica no prontuário e na agenda; gerência vê o financeiro e o ponto, sem caixa e sem prontuário; o dono vê tudo e cadastra funcionário. Abrir e fechar o caixa fica no nome de quem está logado. O fechamento é cego: a diferença aparece depois da contagem, e aí a sessão volta para o login. A senha continua em PBKDF2. O backup da loja é o arquivo `sistema/rotina.db`.

---

## O que entrou na evolução, e o que depende de contrato

O cadastro exige telefone com DDD, CEP e endereço. CPF e e-mail, quando preenchidos, são validados no servidor. Telefone repetido não cria outro cliente. O mesmo tutor não cadastra dois animais com o mesmo nome. A ficha do cliente e a ficha do animal reúnem pacote, atendimento, hospedagem, compra e prontuário que já existiam.

O pacote tem nome comercial (`Banho — 4 sessões`). O nome do animal não entra nesse título. Na busca, uma sessão é baixada do pacote e do crédito.

O PDV recebe o leitor USB ou Bluetooth que se apresenta como teclado (HID): o equipamento digita o código e manda Enter. O produto entra no carrinho, a quantidade soma se o mesmo código passar de novo, e a venda confirmada baixa o estoque na mesma transação da venda. Não há uma segunda receita no financeiro: a venda paga é a entrada. Conta em aberto (`status` aberta) não entra no resultado até ser paga.

A loja pública fica em `http://127.0.0.1:5173/loja`. Ela usa o mesmo estoque. O checkout reserva a unidade. O pagamento na retirada, lançado uma vez pela equipe, gera a única venda. Dois pedidos não levam a última unidade. Cartão e Pix online não estão ligados: isso exige contrato com um provedor (PagSeguro, Mercado Pago ou o banco). A retirada evita uma cobrança fictícia.

O ponto não tem botão de bater entrada. A equipe importa o arquivo AFD do relógio, no registro tipo 3 da Portaria 1510. O NSR repetido não duplica a marcação. O PIS associa o funcionário quando o cadastro tem esse número. Relógio de rede de um fabricante específico (Control iD, Henry, Topdata, Dimep) fala um protocolo próprio; ligar um modelo exige o SDK ou a API daquele fabricante, e isso fica de fora até haver o equipamento e o contrato.

Papéis: recepção opera a rotina e o caixa; veterinário fica no prontuário e na agenda; gerência vê o financeiro e o ponto, sem caixa e sem prontuário; o dono vê tudo e cadastra funcionário. Abrir e fechar o caixa fica no nome de quem está logado. O fechamento é cego: a diferença aparece depois da contagem, e aí a sessão volta para o login. A senha continua em PBKDF2. O backup da loja é o arquivo `sistema/rotina.db`.
