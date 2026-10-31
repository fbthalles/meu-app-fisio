# Matriz científica e estado de verificação

## Limitação material desta etapa

**Nenhuma publicação externa foi verificada integralmente nesta execução.**
As consultas HTTPS ao PubMed (`https://pubmed.ncbi.nlm.nih.gov/10201543/`) e ao
portal oficial KOOS (`https://www.koos.nu/`) retornaram erro de CONNECT 403 do
proxy; a tentativa ao PubMed foi repetida após resposta do usuário, sem mudança.
Isso é bloqueio de acesso, não ausência de literatura nem refutação de estudos.

As adições de rede foram salvas no rascunho do ambiente após anuência do usuário,
preservando os domínios existentes. Salvamento não aplica política nem publica
ambiente. A observação runtime consultada continuava com lista customizada vazia.
Os domínios solicitados são PubMed/PMC, doi.org, koos.nu/www.koos.nu,
www.sportsmed.org, cosmin.nl/www.cosmin.nl. É necessário aplicar as configurações
para completar a verificação documental; não se trata de deploy do aplicativo.

A matriz abaixo distingue **citação encontrada no código**, **fonte bibliográfica
proposta** e **aplicabilidade ainda não demonstrada**. Os identificadores servem
para localizar os trabalhos originais; não se afirma leitura de seus métodos ou
resultados. Não foram produzidos novos valores de MCID, PASS ou critérios de alta.
Referências que não puderam ser identificadas com confiança usam busca por título,
sem atribuir DOI/PMID por suposição.

## Instrumentos: fontes para conferência

| Instrumento | Fonte original/proposta e localizador | Citação/uso no app | Estado e verificação pendente |
|---|---|---|---|
| KOOS | Roos et al., *Knee Injury and Osteoarthritis Outcome Score (KOOS)—development of a self-administered outcome measure*, 1998; [DOI](https://doi.org/10.2519/jospt.1998.28.2.88); [portal dos autores](https://www.koos.nu/) | Roos 2003 e MCID 8–10; 12 itens chamados KOOS-12 | Acesso bloqueado; conferir manual KOOS e, separadamente, KOOS-12, versão brasileira e regras de itens ausentes |
| KOOS-12 | [Busca bibliográfica específica](https://pubmed.ncbi.nlm.nih.gov/?term=KOOS-12+Gandek+Roos+Franklin) e portal KOOS acima | Mesma referência do KOOS completo aplicada ao resumo de 12 itens | DOI específico não atribuído sem consulta; conferir itens, domínios e summary score. Não herdar automaticamente MCID do KOOS completo |
| IKDC | Irrgang et al., *Development and validation of the International Knee Documentation Committee subjective knee form*, 2001; [DOI](https://doi.org/10.1177/03635465010290051301); [AOSSM](https://www.sportsmed.org/) | Irrgang 2006, MCID 9; 5 perguntas/4 termos pontuados | Referência original proposta, não consultada; conferir formulário, itens válidos, denominador e versão linguística. Citação de 2006 do código ainda sem identificação exata |
| LEFS | Binkley et al., *The Lower Extremity Functional Scale (LEFS): scale development, measurement properties, and clinical application*, 1999; [DOI](https://doi.org/10.1093/ptj/79.4.371); [PubMed](https://pubmed.ncbi.nlm.nih.gov/10201543/) | Binkley 1999, MCID 9; 10 itens extrapolados para 80 | Consulta ao registro bloqueada. Conferir formulário de 20 itens e validade da versão de 10 itens; 9 pontos não se transportam automaticamente para a adaptação |
| Lysholm | Lysholm e Gillquist, *Evaluation of knee ligament surgery results with special emphasis on use of a scoring scale*, 1982; [DOI](https://doi.org/10.1177/036354658201000306) | Briggs 2009, MCID 10, categorias 65/84/95 | Identificador da fonte original proposto, sem texto consultado. Conferir versão revisada, tradução, pesos, adequação a diagnóstico e limiares. [Busca Briggs](https://pubmed.ncbi.nlm.nih.gov/?term=Briggs+2009+Lysholm) |
| WOMAC | Bellamy et al., *Validation study of WOMAC: a health status instrument for measuring clinically important patient relevant outcomes to antirheumatic drug therapy in patients with osteoarthritis of the hip or knee*, 1988; [PubMed](https://pubmed.ncbi.nlm.nih.gov/3068365/) | Sem referência específica no bloco, 15 itens e escore invertido 0–100 | Acesso não disponível. Conferir WOMAC LK e eventual short form validada; licença, tradução, 5 dor/2 rigidez/17 função e direção da transformação |
| VISA-P | Visentini et al., *The VISA score: an index of severity of symptoms in patients with jumper's knee (patellar tendinosis)*, 1998; [DOI](https://doi.org/10.1016/S1440-2440(98)80005-4) | Hernández-Sánchez 2014, MCID 13; 8 itens ditos oficiais | Texto original não consultado. Conferir âncoras, pesos e ramificações de duração/dor esportiva; [busca MCID](https://pubmed.ncbi.nlm.nih.gov/?term=Hernandez-Sanchez+2014+VISA-P+clinically+important) |

## Interpretações: localizar antes de aprovar

| Tema | Fonte/localizador proposto | O que NÃO está demonstrado no app |
|---|---|---|
| LSI/retorno ao esporte | Grindem 2016: [DOI](https://doi.org/10.1136/bjsports-2016-096031); [busca Kyritsis 2016](https://pubmed.ncbi.nlm.nih.gov/?term=Kyritsis+2016+discharge+criteria+ACL) | Transferibilidade de protocolo, população e limiar 90 ao handheld kgf; regra isolada não comprova retorno seguro; 85 precisa de justificativa própria |
| GROC | Kamper, Maher e Mackay, *Global Rating of Change Scales: A Review of Strengths and Weaknesses and Considerations for Design*, 2009; [DOI](https://doi.org/10.1179/jmt.2009.17.3.163) | Código cita “JOSPT 2009”; conferir metadados e escala específica. Não sustenta por si GROC≥3 universal |
| SANE | [Busca original por Single Assessment Numeric Evaluation](https://pubmed.ncbi.nlm.nih.gov/?term=Williams+1999+Single+Assessment+Numeric+Evaluation); [busca Shelbourne/Winterstein](https://pubmed.ncbi.nlm.nih.gov/?term=Shelbourne+Winterstein+SANE+knee) | Códigos citam Shelbourne 2009 e Winterstein 2013 sem identificação completa; pergunta “quão perto do objetivo” pode medir construto diferente de percentual do normal. SANE85/ganho15 não validados neste protocolo |
| PASS | [Busca Tubach 2005 PASS](https://pubmed.ncbi.nlm.nih.gov/?term=Tubach+2005+patient+acceptable+symptom+state) | Estado aceitável não equivale automaticamente a alta esportiva; nenhum ponto de corte do protocolo GENUA foi confirmado |
| Dor/MCID | [Salaffi 2004](https://doi.org/10.1016/j.ejpain.2003.09.004), identificador também presente no código | Confirmar tipo de escala e contexto, magnitude absoluta versus relativa e baseline. No app “EVA” é slider numérico discreto: conferir nomenclatura NRS/EVA |
| Curva SANE | Nenhum artigo identificado para `tau**0.75`, meta85, faixas±5 e semanas por fenótipo | Modelo determinístico ilustrativo; sem validação de calibração individual demonstrada. Não atribuir a estudos de SANE validação dessa curva |
| MCID por cinco sessões | Nenhum estudo identificado para a combinação exata implementada | Aplicar MCID a qualquer janela de cinco registros sem duração e sem versão correta do instrumento não foi sustentado |

## COSMIN e GRADE: como aplicar na segunda etapa

[COSMIN](https://www.cosmin.nl/) orienta a avaliação de propriedades de medida.
Para cada versão/idioma/população, registrar validade de conteúdo (relevância,
abrangência, compreensão), estrutural, consistência interna quando pertinente,
confiabilidade, erro de medida, validade transcultural, construto, responsividade
e interpretabilidade. **Ausência de avaliação não significa propriedade ruim**;
classificar “não avaliada” até consultar estudos e métodos. Não atribuir um selo
COSMIN a um questionário só por conter uma citação.

[GRADE: Guyatt et al., 2008](https://doi.org/10.1136/bmj.39489.470347.AD) é um ponto
de partida metodológico, não uma certificação do algoritmo. Uma classificação da
certeza exige pergunta/população/desfecho definidos, seleção de estudos e avaliação
de viés, inconsistência, indireção, imprecisão e viés de publicação. Para PROMs,
usar a abordagem de síntese de propriedades de medida descrita pelo COSMIN; para
recomendações de tratamento/alta, definir a pergunta clínica apropriada antes de
usar GRADE. **Não foi atribuído grau alto/moderado/baixo a nenhuma regra nesta
auditoria**, porque não houve leitura crítica de um corpo de evidência.

Critério de conclusão científica: obter documentos oficiais e validações em
português, verificar cada identificador, registrar páginas/trechos, preencher
versão/população/protocolo/unidade de MCID/PASS e submeter ao responsável clínico.
