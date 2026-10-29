# Akko TAC75 HE — SignalRGB

> **PRÉ-VERSÃO EXPERIMENTAL — AINDA EM TESTES. USO POR SUA CONTA E RISCO.** Sem garantia, promessa de suporte, reparo, ressarcimento ou recuperação. L30k e colaboradores não assumem responsabilidade na extensão permitida pela legislação. Leia o [aviso completo](DISCLAIMER.md).

Plugin de iluminação individual mantido por [L30k](https://github.com/L30k), com comunicação USB direta e taxa fixa de **5 FPS**. Dispensa o aplicativo ponte durante o uso.

## Requisito e limites

Exige o firmware modificado **ID2782/V502 RAM1**. O plugin não instala firmware e recusa transmitir cores sem a assinatura RAM1. A modificação foi experimentada em uma unidade; isso não comprova compatibilidade com outros lotes nem recuperação em qualquer falha.

A gravação experimental pode impedir a inicialização. O retorno pelo aplicativo depende de bootloader USB acessível. O pacote de firmware oficial é uma imagem de atualização, não um backup completo da unidade.

## Instalação, para quem já tem RAM1

1. Pare e feche a ponte antiga. Feche o aplicativo Akko e suas abas de configuração.
2. Encerre o SignalRGB normalmente.
3. Copie `plugin/Akko_TAC75_HE.js` para `Documentos/WhirlwindFX/Plugins`.
4. Guarde os plugins antigos fora dessa pasta, deixando apenas uma versão para o TAC75.
5. Abra o SignalRGB. O dispositivo aparece como **Akko TAC75 HE**, autor **L30k**.
6. Ative **Enable per-key lighting (5 FPS)**.

Desativar esse controle ou encerrar normalmente o SignalRGB devolve os LEDs aos efeitos internos. Encerramento forçado pode deixar a última cor até nova liberação ou desligamento do teclado.

## Teclas e layout

A página Layout do SignalRGB representa o dispositivo como retângulo. O plugin registra 83 posições e nomes de teclas, mas não altera o desenho dessa página. Para ver os LEDs individuais, use **Dispositivos → Akko TAC75 HE → Iluminação → Pintar LEDs**. O [mapa visual](../assets/keyboard-map.svg) mostra os nomes e índices; não é uma medição da largura das keycaps.

O README principal em inglês inclui requisitos, construção reproduzível e testes. Os binários proprietários da Akko não estão neste pacote de código: o desenvolvedor obtém a base oficial exata e confere o hash antes de construir. Nada é publicado no GitHub automaticamente.
