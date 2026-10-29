# Relatório da montagem V502 RAM1 experimental

Data: 29/10/2026. Nenhuma gravação no teclado foi realizada.

## Base e alteração

Base oficial ID2782_V502, SHA-256 `2e188151b6025aac685855c6088959fa3d9c9058d9055bfb07a92c380b68f306`.

Experimental SHA-256 `b17a120cdd266c67dbc529e6972a6c452ad29923487d1c96a2700d05d9b0d753`, 139.712 bytes, aplicação transmitida após offset `0x5000`: 119.232 bytes, 1.863 blocos de 64 bytes.

No trecho existente foram alterados 13 bytes, dentro de três literais de heap/pilha, um desvio de seis bytes na entrada do codificador de LEDs e uma entrada de dois bytes da tabela de comandos. O código adicional foi colocado em `0x08022000`, abaixo da região de configuração. O prefixo `0x0000..0x4FFF` do arquivo, incluindo o bootloader, permanece byte a byte idêntico. Os detalhes exatos estão no manifesto.

## RAM

- Contexto novo: `0x20009D98..0x20009FB8`, 544 bytes, coberto pela zeragem original no início.
- Globais/controle da biblioteca abaixo desse intervalo permanecem no mesmo endereço.
- Heap novo: `0x20009FB8..0x2000A1B8`, capacidade original de 512 bytes preservada.
- Pilha: `0x2000A1B8..0x2000DF98`, 15.840 bytes; topo inicial inalterado.

A rotina original de expansão dos dados comprimidos foi executada no teste. Não foram encontradas referências nesses dados iniciais para dentro do contexto reservado. A busca dos antigos limites de heap/pilha no binário localizou somente os literais esperados. Foram conferidos o helper alterado, alinhamento e ausência de sobreposição estática.

O maior aprofundamento de pilha observado **somente nos caminhos exercitados** foi de 60 bytes. Isso não é o pior caso do teclado: não inclui todo o programa, interrupções reais ou todas as combinações de funções. A reserva menor de pilha é uma limitação explícita da montagem.

## Teste do firmware integrado

O código Thumb montado foi executado em Unicorn, com flash apenas para leitura/execução e sem periféricos mapeados:

- 134 pacotes pelo processador original de comandos.
- 1.598 comparações da saída de LEDs entre original e modificado: controle inativo, controle ativo, retorno aos efeitos e índices fora da faixa principal.
- 16 comandos existentes representativos comparados, incluindo leituras de estado e alguns setters. Isso não é cobertura de todos os comandos.
- 16 quadros completos com cores variadas pelo novo caminho integrado.
- 6.723 leituras do contexto na rotina de saída conferidas com interrupções mascaradas.
- Registradores preservados, argumento azul do chamador intacto e pilha restaurada nos testes de saída.
- Indicadores de persistência em `0x200000EC` inalterados pelos pacotes RGB.

Os testes anteriores do receptor independente também exercitaram quadros incompletos, cabeçalhos/comprimentos/sequências incorretos e pacotes aleatórios. O teste integrado acrescenta os desvios reais, o endereço reservado, o processador original e a saída original de LEDs.

### Particularidade da instrumentação

Nesta versão do emulador, callbacks de escrita de memória alteraram a execução de caminhos Thumb com stores condicionais, inclusive na imagem original. Foi preservada a falha nos arquivos de trabalho e comparado o comportamento com e sem essa instrumentação. A suíte integrada usa flash protegida, periféricos não mapeados, rastreamento de instruções e comparação da RAM antes/depois, em vez desses callbacks nos caminhos do codificador.

Isso evita tratar um efeito da instrumentação como defeito do patch, mas **não fornece uma segunda implementação independente de CPU**. O teste físico continua pendente.

## Formato da atualização e reversão

O aplicativo usa o formato do driver original: início `BA C0`, blocos de 64 bytes, verificação `BA C2`, soma dos bytes e quantidade de blocos. Não transmite os primeiros `0x5000` bytes do arquivo.

Esse código de transferência foi conectado ao parser do bootloader original, executado em uma MCU virtual. As operações elétricas de desbloquear/programar/bloquear flash foram substituídas por memória virtual. Foram transferidas:

- V502 original: 1.769 blocos / 113.216 bytes de aplicação.
- Experimental: 1.863 blocos / 119.232 bytes de aplicação.

Nos dois casos o parser original retornou status `0x55`, e o conteúdo virtual recebido coincidiu integralmente com a aplicação. O bootloader virtual não foi alterado. Isso valida o enquadramento e o cálculo usados pelo aplicativo; não valida a enumeração USB, o reset ou a eletrônica de gravação no equipamento.

## Aplicativo e proteção contra acionamento involuntário

18 testes de backend passaram com hardware simulado: instalação, restauração, transferência interrompida, resposta de início errada, checksum inválido, porta divergente, assinatura de retorno errada e recuperação sem identificação prévia. A transferência não é repetida automaticamente após falha.

Três testes de interface conferiram que as opções de presença/recuperação começam desmarcadas, os botões de gravação começam desabilitados e a simulação não acessa hardware. A ação de flash desarmada não chega ao serviço de gravação.

A consulta no teclado físico confirmou ID2782/V502 e a porta via propriedades de localização do Windows. O app registra essa porta e recusa selecionar um bootloader de outra localização. Somente consultas `0x8F` e `0x0F` de capacidade foram enviadas nesta etapa. Não houve entrada em bootloader nem teste de cor real.

## Limites de recuperação

O bootloader analisado decide entre iniciar a aplicação e atualizar usando uma flag e o identificador inicial. Ele pode iniciar código defeituoso com identificador válido. Entrar no caminho de atualização chama apagamento da aplicação antes do laço de transferência. Por isso, o app não oferece reversão automática como garantia.

O aplicativo prepara retorno à **V502 oficial**, não à antiga V501 nem às configurações anteriores da unidade. Sem aplicação e sem bootloader acessível, a recuperação exige outro meio; Wireshark não substitui um programador físico.

## Pendências físicas

1. Pico real de pilha e efeito da seção crítica na latência dos sensores Hall/interrupções.
2. Temporização do mecanismo de saída/DMA e estabilidade em diferentes taxas de quadros.
3. Correspondência visual dos 83 LEDs.
4. Instalação e restauração no aparelho, inclusive acesso à recuperação após falhas.

**Conclusão:** montagem e ferramentas preparadas para ensaio acompanhado. Não é uma certificação de segurança operacional nem uma versão de produção.
