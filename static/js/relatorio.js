function validarCamposObrigatorios() {
    // IDs dos campos obrigatÃ³rios
    const camposObrigatorios = [
        "nome",
        "cpf",
        "endereco",
        "bairro", 
        "cidade",
        "estado",
        "tecnico",
        "data",
        "selectTecnico"
    ];

    // Lista de mensagens de erro para campos vazios
    const mensagensErro = [];

    // Verifica cada campo
    camposObrigatorios.forEach(id => {
        const campo = document.getElementById(id);
        if (!campo.value.trim()) {
            mensagensErro.push(`O campo "${campo.previousElementSibling.textContent}" está vazio.`);
        }
    });

    // Exibe mensagens de erro, se houver
    if (mensagensErro.length > 0) {
        alert(mensagensErro.join("\n")); // Exibe os erros em um Ãºnico alerta
        return false; // Interrompe o processo
    }

    return true; // Todos os campos estÃ£o preenchidos
}

// =============================
// FUNÃ‡ÃƒO PARA GERAR ASSINATURA MANUSCRITA
// =============================
function gerarAssinatura(nome) {
  const canvas = document.createElement("canvas");
  canvas.width = 400;
  canvas.height = 100;
  const ctx = canvas.getContext("2d");

  // Fundo branco
  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Fonte cursiva em azul Bic
  ctx.font = "italic 38px 'Great Vibes', cursive";
  ctx.fillStyle = "#0d47a1"; // azul de caneta Bic
  ctx.fillText(nome, 10, 60);

  return canvas.toDataURL("image/png");
}

// =============================================================
// MODELO ANTERIOR: assinatura cursiva desenhada direto no PDF
// =============================================================
function adicionarBlocoAssinaturaClassica(pdfDoc, paginas, tecnicoNome, tecnicoCNPJ) {
    const assinaturaImagem = gerarAssinatura(tecnicoNome);
    paginas.forEach((pagina) => {
        pdfDoc.setPage(pagina);
        pdfDoc.addImage(assinaturaImagem, "PNG", 24, 266, 45, 20);
        pdfDoc.setFont("helvetica", "normal");
        pdfDoc.setFontSize(10);
        pdfDoc.setTextColor(0, 0, 0);
        pdfDoc.text("-----------------------------------", 24, 280);
        pdfDoc.text(`${tecnicoNome}`, 24, 285);
        pdfDoc.text(`CNPJ ${tecnicoCNPJ}`, 24, 290);
    });
}

window.telefoneCidadeSelecionada = null;

function mascararCpfCnpj(valor) {
    const numeros = String(valor || "").replace(/\D/g, "");
    if (numeros.length === 11) {
        return `${numeros.slice(0, 3)}.***.***-${numeros.slice(9)}`;
    }
    if (numeros.length === 14) {
        return `${numeros.slice(0, 2)}.***.***/****-${numeros.slice(12)}`;
    }
    return valor || "Não informado";
}

function abreviarIdentificador(valor) {
    const texto = String(valor || "").trim();
    if (!texto) {
        return "Não informado";
    }
    if (texto.length <= 18) {
        return texto;
    }
    return `${texto.slice(0, 8)}...${texto.slice(-6)}`;
}

function truncarTextoPdf(pdfDoc, texto, larguraMaxima) {
    const conteudo = String(texto || "Não informado");
    if (pdfDoc.getTextWidth(conteudo) <= larguraMaxima) {
        return conteudo;
    }

    let resultado = conteudo;
    while (resultado.length > 1 && pdfDoc.getTextWidth(`${resultado}...`) > larguraMaxima) {
        resultado = resultado.slice(0, -1);
    }
    return `${resultado}...`;
}

function formatarTimestampAssinatura(valor) {
    if (!valor && valor !== 0) {
        return "Não informado";
    }
    const data = new Date(Number(valor) * 1000);
    if (Number.isNaN(data.getTime())) {
        return "Não informado";
    }
    return new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "medium",
        timeZone: "America/Sao_Paulo",
    }).format(data);
}

function normalizarDadosAssinaturaPdf(assinaturaDados, fallbackDocumento = "") {
    if (!assinaturaDados || assinaturaDados.valid !== true) {
        return null;
    }

    return {
        signerName: assinaturaDados.signer_name || "Não informado",
        signerDocument: mascararCpfCnpj(
            assinaturaDados.signer_document || fallbackDocumento,
        ),
        signedAt: formatarTimestampAssinatura(assinaturaDados.signed_at),
        documentHash: assinaturaDados.document_hash || "Não informado",
        documentHashShort: abreviarIdentificador(assinaturaDados.document_hash),
        fingerprint: assinaturaDados.fingerprint || "Não informado",
        fingerprintShort: abreviarIdentificador(assinaturaDados.fingerprint),
        credentialId: assinaturaDados.credential_id || "Não informado",
        credentialIdShort: abreviarIdentificador(assinaturaDados.credential_id),
        deviceLabel: assinaturaDados.device_label || "Não informado",
        verificationCode: assinaturaDados.verification_code || assinaturaDados.report_id || "Não informado",
        verificationUrl: assinaturaDados.verification_url || `/verificar-relatorio/${assinaturaDados.report_id || ""}`,
        verificationPath: `/verificar-relatorio/${assinaturaDados.verification_code || assinaturaDados.report_id || ""}`,
    };
}

function desenharSeloValidacao(pdf, posX, posY) {
    pdf.setFillColor(13, 85, 144);
    pdf.circle(posX, posY, 2.8, "F");
    pdf.setDrawColor(255, 255, 255);
    pdf.setLineWidth(0.55);
    pdf.line(posX - 1.1, posY + 0.1, posX - 0.2, posY + 1.1);
    pdf.line(posX - 0.15, posY + 1.1, posX + 1.7, posY - 1.05);
}

function adicionarBlocoAssinaturaAvancadaProfissional(pdfDoc, assinaturaDados, posX, posY) {
    const dados = normalizarDadosAssinaturaPdf(assinaturaDados);
    if (!dados) {
        return;
    }

    const largura = 138;
    const altura = 51;
    const colunaEsquerdaX = posX + 7;
    const colunaDireitaX = posX + 73;
    const larguraColuna = 58;

    pdfDoc.setDrawColor(13, 85, 144);
    pdfDoc.setFillColor(255, 255, 255);
    pdfDoc.setLineWidth(0.8);
    pdfDoc.roundedRect(posX, posY, largura, altura, 3, 3, "FD");

    pdfDoc.setFillColor(244, 248, 252);
    pdfDoc.roundedRect(posX, posY, largura, 12, 3, 3, "F");
    desenharSeloValidacao(pdfDoc, posX + 8, posY + 7.2);

    pdfDoc.setTextColor(13, 85, 144);
    pdfDoc.setFont("helvetica", "bold");
    pdfDoc.setFontSize(8.8);
    pdfDoc.text("ASSINATURA ELETRÔNICA AVANÇADA", posX + 13.5, posY + 7.8);

    pdfDoc.setFont("helvetica", "normal");
    pdfDoc.setTextColor(70, 83, 96);
    pdfDoc.setFontSize(5.9);
    pdfDoc.text(
        "Documento assinado eletronicamente e validado no sistema.",
        posX + 7,
        posY + 13.1,
    );

    const escreverCampoEmpilhado = (titulo, valor, x, y, larguraTexto) => {
        pdfDoc.setFont("helvetica", "bold");
        pdfDoc.setTextColor(13, 85, 144);
        pdfDoc.setFontSize(5.1);
        pdfDoc.text(titulo, x, y);
        pdfDoc.setTextColor(40, 51, 64);
        pdfDoc.setFont("helvetica", "bold");
        pdfDoc.setFontSize(6.1);
        pdfDoc.text(
            truncarTextoPdf(pdfDoc, valor || "Não informado", larguraTexto),
            x,
            y + 4.2,
        );
    };

    escreverCampoEmpilhado("Signatário", dados.signerName, colunaEsquerdaX, posY + 19.2, larguraColuna);
    escreverCampoEmpilhado("Hash SHA-256", dados.documentHashShort, colunaDireitaX, posY + 19.2, larguraColuna);
    escreverCampoEmpilhado("CPF/CNPJ", dados.signerDocument, colunaEsquerdaX, posY + 29, larguraColuna);
    escreverCampoEmpilhado("Fingerprint", dados.fingerprintShort, colunaDireitaX, posY + 29, larguraColuna);
    escreverCampoEmpilhado("Data e Hora", dados.signedAt, colunaEsquerdaX, posY + 38.8, larguraColuna);
    escreverCampoEmpilhado("Dispositivo", dados.deviceLabel, colunaDireitaX, posY + 38.8, larguraColuna);

    pdfDoc.setDrawColor(209, 226, 240);
    pdfDoc.line(posX + 7, posY + 45.4, posX + largura - 7, posY + 45.4);
    pdfDoc.setFont("helvetica", "bold");
    pdfDoc.setTextColor(13, 85, 144);
    pdfDoc.setFontSize(4.9);
    pdfDoc.text("Código / Verificação:", posX + 7, posY + 49.2);
    pdfDoc.setTextColor(40, 51, 64);
    pdfDoc.setFontSize(5.2);
    pdfDoc.text(
        truncarTextoPdf(pdfDoc, `${dados.verificationCode}  •  ${dados.verificationPath}`, 96),
        posX + 43,
        posY + 49.2,
    );
}

async function gerarPDF() {
    // Impede mÃºltiplos cliques
    const btn = document.getElementById("btnGerarPDF");
    btn.disabled = true;
    btn.innerText = "Gerando PDF...";

    document.getElementById("loadingPopup").style.display = "flex";

     // Primeiro, valida os campos obrigatÃ³rios
    if (!validarCamposObrigatorios()) {
        // Reativa o botÃ£o se houver erro
        btn.disabled = false;
        btn.innerText = "Baixar como PDF";
        document.getElementById("loadingPopup").style.display = "none";
        return;
    }

    const tecnicoSelect = document.getElementById("tecnico");
    if (!tecnicoSelect.value || tecnicoSelect.value.trim() === "") {
        alert("Por favor, selecione um técnico responsável antes de gerar o relatório.");
        // Reativa o botÃ£o
        btn.disabled = false;
        btn.innerText = "Baixar como PDF";
        document.getElementById("loadingPopup").style.display = "none";
        return;
    }

    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({ compress: true });
    const paginasAssinaturaAvancada = [];
    let nome;
    let cpf;
    let tecnicoNome = "";
    let tecnicoCNPJ = "";
    let tecnicoUserId = "";

    /*try {
        // Definir logo
        const logoURL = "../static/img/logo.png";
        let imgLogo = new Image();
        imgLogo.src = logoURL;

        // Esperar o carregamento da logo
        await new Promise((resolve, reject) => {
            imgLogo.onload = resolve;
            imgLogo.onerror = reject;
        });

        // Adicionar logo no PDF
        pdf.addImage(imgLogo, "PNG", 1, 1, 45, 45);
    } catch (error) {
        console.warn("Logo nÃ£o carregada. Continuando sem logo.");
    }*/
    
    
    await adicionarShapeSuperiorPagina();
    
    
  // FunÃ§Ã£o para carregar imagens selecionadas no input e retornar um array de DataURLs
    async function adicionarShapeSuperiorPagina() {
        try {
            const shapeTop = new Image();
            shapeTop.src = "../static/img/shape_123_superior.png";
                await new Promise((resolve, reject) => {
                shapeTop.onload = resolve;
                shapeTop.onerror = reject;
      });
      pdf.addImage(shapeTop, "PNG", 0, 0, 210, 33);
        } catch (e) {
            console.warn("Shape superior nÃ£o carregado:", e);
        }
    }

    async function adicionarShapeInferiorPagina() {
        try {
            const shapeBottom = new Image();
            shapeBottom.src = "../static/img/shape_123_inferior.png";
            await new Promise((resolve, reject) => {
                shapeBottom.onload = resolve;
                shapeBottom.onerror = reject;
            });
            pdf.addImage(shapeBottom, "PNG", 0, 282, 210, 17);
        } catch (e) {
            console.warn("Shape inferior nÃ£o carregado:", e);
        }
    }

    async function adicionarCabecalhoPagina(telefone) {
        await adicionarShapeSuperiorPagina();
        //pdf.setFontSize(14);
        //pdf.setTextColor(255, 255, 255);
        //pdf.setFont("helvetica", "bold");
        //pdf.text("123 Caça Vazamentos", 130, 20);
        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(10);
        pdf.setTextColor(6, 32, 58);
        pdf.text("CNPJ: 41.713.002/0001-05", 130, 8);
        pdf.text(`Telefone: ${telefone}`, 130, 13);
        pdf.text("E-mail: 123cacavazamentos@gmail.com", 130, 18);
        pdf.setTextColor(0, 0, 0);
    }

    async function adicionarRodapePagina(cidade, data) {
        await adicionarShapeInferiorPagina();
        pdf.setTextColor(255, 255, 255);
        if (data) {
            const [ano, mes, dia] = data.split("-");
            const dataFormatada = `${dia}/${mes}/${ano}`;
            pdf.text(`${dataFormatada}, ${cidade}`, 140, 292);
        }
        pdf.setTextColor(0, 0, 0);
    }

    function registrarPaginaAssinaturaAvancada() {
        const paginaAtual = pdf.getCurrentPageInfo().pageNumber;
        if (!paginasAssinaturaAvancada.includes(paginaAtual)) {
            paginasAssinaturaAvancada.push(paginaAtual);
        }
    }

    async function escreverTextoPaginado(
        linhas,
        posX,
        posYInicial,
        telefone,
        tituloContinuacao = "",
        limiteInferior = 272,
        posYNovaPagina = 60,
        alturaLinha = 6,
    ) {
        let posYAtual = posYInicial;

        for (const linha of linhas) {
            if (posYAtual > limiteInferior) {
                pdf.addPage();
                await adicionarCabecalhoPagina(telefone);
                posYAtual = posYNovaPagina;

                if (tituloContinuacao) {
                    pdf.setFont("helvetica", "bold");
                    pdf.text(tituloContinuacao, posX, posYAtual);
                    pdf.setFont("helvetica", "normal");
                    posYAtual += alturaLinha + 2;
                }
            }

            pdf.text(linha, posX, posYAtual);
            posYAtual += alturaLinha;
        }

        return posYAtual;
    }

    const carregarImagensDoInput = async (inputId) => {
        const input = document.getElementById(inputId);
        const files = input.files;
        const dataUrls = [];

        for (const file of files) {
            const dataUrl = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (event) => resolve(event.target.result);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
            dataUrls.push(dataUrl);
        }
        return dataUrls;
    };

    try {
        // Carregar as imagens do input
        const imagensDataUrls = await carregarImagensDoInput("imagens");

        // Primeira pÃ¡gina: conteÃºdo textual do relatÃ³rio
        /*pdf.setFontSize(16);
        pdf.text("CLIENTE", 90, 45);*/

        // Exemplo de conteÃºdo da primeira pÃ¡gina
        nome = document.getElementById("nome").value;
        cpf = document.getElementById("cpf").value;
        const endereco = document.getElementById("endereco").value;
        const bairro = document.getElementById("bairro").value;
        const cidade = document.getElementById("cidade").value;
        const data = document.getElementById("data").value;
        const observacao = document.getElementById("observacao").value;
        //const total = document.getElementById("total").value;
        //const formaPagamento = document.getElementById("forma-pagamento").value;
        //const empresaSolicitacao = document.getElementById("empresaSolicitacao").value;

        const detalhesFrente = document.getElementById("detalhes_frente").value.trim();
        const detalhesFundo = document.getElementById("detalhes_fundos").value.trim();
        const detalhesAreaServico = document.getElementById("detalhes_area_servico").value.trim();
        const detalhesDispensa = document.getElementById("detalhes_dispensa").value.trim();
        const detalhesCozinha = document.getElementById("detalhes_cozinha").value.trim();
        const detalhesBanheiro = document.getElementById("detalhes_banheiro").value.trim();
        const detalhesJardim = document.getElementById("detalhes_jardim").value.trim();
        const detalhesSala = document.getElementById("detalhes_sala").value.trim();

        const detalhesAreaComum = document.getElementById("detalhes_areacomum").value.trim();
        const detalhesGaragem = document.getElementById("detalhes_garagem").value.trim();
        const detalhesPiscina = document.getElementById("detalhes_piscina").value.trim();
        const detalhesRedeDeIncendio = document.getElementById("detalhes_rededeincendio").value.trim();


        const geofonamentoCheckbox = document.getElementById("geofonamentoCheckbox");
        const pressurizacaoCheckbox = document.getElementById("pressurizacaoCheckbox");
        const cameraTermograficaCheckbox = document.getElementById("cameraTermograficaCheckbox");
        const sensorDeUmidadeCheckbox = document.getElementById("sensorDeUmidadeCheckbox");
        
        

        const larguraMaximaLinha = 180; // Ajuste conforme necessÃ¡rio

          // =============================
        // CABEÃ‡ALHO DO CLIENTE
        // =============================
        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(14);
        pdf.text(`${nome}`, 10, 55);
        pdf.setFontSize(10);
        pdf.text(`CPF/CNPJ: ${cpf}`, 10, 62);
        pdf.text(`Endereço: ${endereco}`, 10, 69);
        pdf.text(`Bairro: ${bairro}`, 10, 76);
        pdf.text(`Cidade: ${cidade}`, 10, 83);
        pdf.text(`-------------------------------------------------------------------------------------------------------------------------------------------------------------------`, 10, 87);
        pdf.setFont("helvetica", "bold");
        pdf.text("RELATÓRIO TÉCNICO", 85, 95);
        pdf.setFont("helvetica", "normal");


        const telefone = window.telefoneCidadeSelecionada || "Telefone não disponível";
        
          // =============================
  // INFORMAÃ‡Ã•ES DA EMPRESA
  // =============================
  //pdf.setFontSize(14);
  //pdf.setTextColor(255, 255, 255);
  //pdf.setFont("helvetica", "bold");
  //pdf.text("123 Caça Vazamentos", 130, 20);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(10);
  pdf.setTextColor(6, 32, 58);
  pdf.text("CNPJ: 41.713.002/0001-05", 130, 8);
  pdf.text(`Telefone: ${telefone}`, 130, 13);
  pdf.text("E-mail: 123cacavazamentos@gmail.com", 130, 18);
  pdf.setTextColor(0, 0, 0);



        const selectedTechniques = [];

        // Verifica os checkboxes e adiciona os textos ao array
        if (geofonamentoCheckbox.checked) {
            selectedTechniques.push("Geofonamento com o geofone eletrônico");
        }
        if (pressurizacaoCheckbox.checked) {
            selectedTechniques.push("Pressurização da Rede");
        }
        if (cameraTermograficaCheckbox.checked) {
            selectedTechniques.push("Inspeção com câmera termográfica");
        }
        if (sensorDeUmidadeCheckbox.checked) {
            selectedTechniques.push("Verificação de umidade com o sensor de umidade");
        }

        let solicitacaoUM = true;
        let solicitacaoDois = true;

        // Formata o texto final de forma dinÃ¢mica
        let techniquesText = "";
        if (selectedTechniques.length > 0) {
            const lastTechnique = selectedTechniques.pop(); // Remove o Ãºltimo elemento
            techniquesText = `Técnicas utilizadas: ${selectedTechniques.join(", ")}${selectedTechniques.length > 0 ? " e " : ""}${lastTechnique}.`;

            const techniquesTextLinhas = pdf.splitTextToSize(techniquesText, larguraMaximaLinha);
            pdf.text(techniquesTextLinhas, 10, 105);
        } else {
            techniquesText = "Nenhuma técnica foi selecionada.";
        }
     
        
        // FunÃ§Ã£o para formatar os itens
        function formatarLocalizacao(nome, valor) {
            if (valor) {
                return `(X) ${nome}: ${valor}`;
            } else {
                return `() ${nome}:`;
            }
        }


        const larguraLinhaLocalVazamento = 80;

        let verifica_detalhes_existe = false;

        // ConstruÃ§Ã£o do texto
        const locaisDireita = [
            formatarLocalizacao("Frente do imóvel", detalhesFrente),
            formatarLocalizacao("Fundos do imóvel", detalhesFundo),
            formatarLocalizacao("Área de Serviço", detalhesAreaServico),
            formatarLocalizacao("Dispensa", detalhesDispensa),
            formatarLocalizacao("Cozinha", detalhesCozinha),
            formatarLocalizacao("Banheiro", detalhesBanheiro),
        ];
        const locaisEsquerda = [
            formatarLocalizacao("Sala", detalhesSala),
            formatarLocalizacao("Jardim", detalhesJardim),
            formatarLocalizacao("Garagem", detalhesGaragem),
            formatarLocalizacao("Piscina", detalhesPiscina),
            formatarLocalizacao("Área Comum", detalhesAreaComum),
            formatarLocalizacao("Rede de Incêndio", detalhesRedeDeIncendio),
        ];

        // Adicionar tÃ­tulo e itens ao PDF apenas se houver pelo menos um preenchido
        if (locaisDireita.some(texto => texto.includes("(X)")) || locaisEsquerda.some(texto => texto.includes("(X)"))) {
            pdf.setFont("helvetica", "bold");
            pdf.text("LOCAL DO VAZAMENTO", 85, 140);
            pdf.setFont("helvetica", "normal");

            let posicaoY = 150; // PosiÃ§Ã£o inicial Y
            locaisDireita.forEach((local) => {
                const linhasLocal = pdf.splitTextToSize(local, larguraLinhaLocalVazamento);
                pdf.text(linhasLocal, 20, posicaoY); // Escreve cada item no PDF
                posicaoY += linhasLocal.length * 6 + 2; // Incrementa conforme a altura real
            });

            let posicaoYD = 150; // PosiÃ§Ã£o inicial Y
            locaisEsquerda.forEach((local) => {
                const linhasLocal = pdf.splitTextToSize(local, larguraLinhaLocalVazamento);
                pdf.text(linhasLocal, 110, posicaoYD); // Escreve cada item no PDF
                posicaoYD += linhasLocal.length * 6 + 2; // Incrementa conforme a altura real
            });
            verifica_detalhes_existe = true;
        }
        
        
        // OBSERVAÃ‡ÃƒO
        const linhasTextoObservacao = pdf.splitTextToSize(observacao, larguraMaximaLinha);
        

        let fimObservacao = 0;

        if (verifica_detalhes_existe == true) {
            pdf.setFont("helvetica", "bold"); 
            pdf.text("Observação:", 10, 220);
            pdf.setFont("helvetica", "normal");

            if (observacao.length === 0) {
                pdf.text(`Nenhuma observação`, 10, 227);
                fimObservacao = 233;
            }
            else {
                fimObservacao = await escreverTextoPaginado(
                    linhasTextoObservacao,
                    10,
                    227,
                    telefone,
                    "Observação (continuação):",
                );
            }
        }
        else {
            pdf.setFont("helvetica", "bold"); 
            pdf.text("Observação:", 10, 140);
            pdf.setFont("helvetica", "normal");

            if (observacao.length === 0) {
                pdf.text(`Nenhuma observação`, 10, 147);
                fimObservacao = 153;
            }
            else {
                fimObservacao = await escreverTextoPaginado(
                    linhasTextoObservacao,
                    10,
                    147,
                    telefone,
                    "Observação (continuação):",
                );
            }
        }
        
        
        /*pdf.text(`-------------------------------------------------------------------------------------------------------------------------------------------------------------------`, 10, 240);


        // SOLICITAÃ‡ÃƒO
        let solicitacao = '';
        
        if (empresaSolicitacao !== 'selecionar') {
            
            if (solicitacaoUM == true || solicitacaoDois == true) {
                solicitacao = `Por meio desse relatÃ³rio, solicitamos Ã  ${empresaSolicitacao}, a refazer as contas altas.`;
            }
            else {
                solicitacao = `Por meio desse relatÃ³rio, solicitamos Ã  ${empresaSolicitacao} a refazer as contas altas jÃ¡ que essa Ã¡gua nÃ£o foi consumida e sim perdida no solo, sem o conhecimento e a intenÃ§Ã£o do cliente.`;
            }

            const linhasTextoSolicitacaoEmpresa = pdf.splitTextToSize(solicitacao, larguraMaximaLinha);
            pdf.setFont("helvetica", "bold"); 
            pdf.text("SOLICITAÃ‡ÃƒO", 90, 245);
            pdf.setFont("helvetica", "normal");
            pdf.text(linhasTextoSolicitacaoEmpresa, 10, 253);
     
        };*/
        //const garantiaUm = `Garantia total no local localizado pelo tÃ©cnico. ( Prazo mÃ¡ximo de 30 dias para acionar a garantia) caso solicite a mesma sem a necessidade devida, serÃ¡ cobrado novamente o valor do serviÃ§o de localizaÃ§Ã£o.`;
        //const linhasTextoGaramtiaUm = pdf.splitTextToSize( garantiaUm, larguraMaximaLinha);
        //pdf.text(linhasTextoGaramtiaUm, 10, 245);

        //const garantiaDois = `Garantia de 180 dias em todos os serviÃ§os  hidrÃ¡ulicos reparados pela empresa. PorÃ©m se o reparo for executado por terceiros, prevalece a garantia de 30 dias da localizaÃ§Ã£o.`;
        //const linhasTextoGaramtiaDois = pdf.splitTextToSize( garantiaDois, larguraMaximaLinha);
        //pdf.text(linhasTextoGaramtiaDois, 10, 255);

        // Obter o técnico selecionado (nome/CNPJ e, no modo atribuir, o UID)
        const tecnicoInfo = window.obterTecnicoSelecionado('tecnico');
        tecnicoNome = tecnicoInfo.nome; // Nome do técnico
        tecnicoCNPJ = tecnicoInfo.cnpj; // CNPJ do técnico
        tecnicoUserId = tecnicoInfo.userId; // UID do técnico (modo atribuir)
        const imagemAssinatura = null;
        /*
        if (imagemAssinatura) {
            const imagemAssinaturaURL = `../static/img/${imagemAssinatura}`;
            const imgAssinatura = new Image();
            imgAssinatura.src = imagemAssinaturaURL;

            // Esperar o carregamento da imagem
            await new Promise((resolve, reject) => {
                imgAssinatura.onload = resolve;
                imgAssinatura.onerror = reject;
            });

            // Adicionar a assinatura no PDF
            pdf.addImage(imgAssinatura, "PNG", 15, 262, 45, 20); // Ajuste as dimensÃµes conforme necessÃ¡rio
        }*/

        if (fimObservacao > 244) {
            pdf.addPage();
            await adicionarCabecalhoPagina(telefone);
        }

        /* const assinaturaImagem = gerarAssinatura(tecnicoNome);
        pdf.addImage(assinaturaImagem, "PNG", 24, 266, 45, 20);
        pdf.text(`-----------------------------------`, 24, 280);
        pdf.text(`${tecnicoNome}`, 24, 285);
        pdf.text(`CNPJ ${tecnicoCNPJ}`, 24, 290); */
        registrarPaginaAssinaturaAvancada();



        
        await adicionarRodapePagina(cidade, data);

        // -----------------------------------------------------------------------------------------------------------

        

        const tipoDeVistoria = document.getElementById("tipodeservicoVistoria").value;

        let textUM = '';
        let textDois = '';
        

        const possuiVazamento = document.querySelector('input[name="possui-vazamento"]:checked')?.value;
        const revisarConta = document.querySelector('input[name="revisar-conta"]:checked')?.value;

        if (tipoDeVistoria === 'Conta Alta') {
            // ||    
            if (possuiVazamento === "sim" && revisarConta === "sim") {
                pdf.addPage();
                await adicionarCabecalhoPagina(telefone);

                //await logo(pdf);
                textUM = 'No local identificado não havia evidências superficiais de vazamento, de modo que não havia possibilidade de o cliente identificar a existência do vazamento no local sem os serviços técnicos contratados.'
                textDois = 'As características acima indicadas podem ensejar a revisão das contas de água e de esgoto junto à Concessionária do Serviço Público de Saneamento Básico, a qual deverá ser instruída com este Relatório Técnico.';
                const P1 = pdf.splitTextToSize(textUM, larguraMaximaLinha);
                const P2 = pdf.splitTextToSize(textDois, larguraMaximaLinha);
                pdf.setFont("helvetica", "bold"); 
                pdf.text("SOLICITAÇÃO", 90, 70);
                pdf.setFont("helvetica", "normal");
                pdf.text(P1, 10, 80);
                pdf.text(P2, 10, 90);

                /*if (imagemAssinatura) {
                    const imagemAssinaturaURL = `../static/img/${imagemAssinatura}`;
                    const imgAssinatura = new Image();
                    imgAssinatura.src = imagemAssinaturaURL;

                    // Esperar o carregamento da imagem
                    await new Promise((resolve, reject) => {
                        imgAssinatura.onload = resolve;
                        imgAssinatura.onerror = reject;
                    });

                    // Adicionar a assinatura no PDF
                    pdf.addImage(imgAssinatura, "PNG", 15, 262, 45, 20); // Ajuste as dimensÃµes conforme necessÃ¡rio
                }
                // Adicionar informaÃ§Ãµes do tÃ©cnico
                pdf.text(`-----------------------------------`, 15, 280);    
                pdf.text(`${tecnicoNome}`, 15, 285);
                pdf.text(`CNPJ ${tecnicoCNPJ}`, 15, 290);*/

                /* const assinaturaImagem = gerarAssinatura(tecnicoNome);
                pdf.addImage(assinaturaImagem, "PNG", 24, 266, 45, 20);
                pdf.text(`-----------------------------------`, 24, 280);
                pdf.text(`${tecnicoNome}`, 24, 285);
                pdf.text(`CNPJ ${tecnicoCNPJ}`, 24, 290); */
                registrarPaginaAssinaturaAvancada();

            }
            else if (possuiVazamento === "nao" && revisarConta === "sim") {
                pdf.addPage();
                await adicionarCabecalhoPagina(telefone);

                //await logo(pdf);
                textUM = 'Após a inspeção técnica no local, não foram identificadas evidências superficiais ou ocultas de vazamento, de modo que a área analisada não apresentou quaisquer sinais de perda de água ou problemas relacionados.'
                textDois = 'As características acima indicadas podem ensejar a revisão das contas de água e de esgoto junto à Concessionária do Serviço Público de Saneamento Básico, a qual deverá ser instruída com este Relatório Técnico.';
                const P1 = pdf.splitTextToSize(textUM, larguraMaximaLinha);
                const P2 = pdf.splitTextToSize(textDois, larguraMaximaLinha);
                pdf.setFont("helvetica", "bold"); 
                pdf.text("SOLICITAÇÃO", 90, 70);
                pdf.setFont("helvetica", "normal");
                pdf.text(P1, 10, 80);
                pdf.text(P2, 10, 90);

                /*if (imagemAssinatura) {
                    const imagemAssinaturaURL = `../static/img/${imagemAssinatura}`;
                    const imgAssinatura = new Image();
                    imgAssinatura.src = imagemAssinaturaURL;

                    // Esperar o carregamento da imagem
                    await new Promise((resolve, reject) => {
                        imgAssinatura.onload = resolve;
                        imgAssinatura.onerror = reject;
                    });

                    // Adicionar a assinatura no PDF
                    pdf.addImage(imgAssinatura, "PNG", 15, 262, 45, 20); // Ajuste as dimensÃµes conforme necessÃ¡rio
                }
                // Adicionar informaÃ§Ãµes do tÃ©cnico
                pdf.text(`-----------------------------------`, 15, 280);    
                pdf.text(`${tecnicoNome}`, 15, 285);
                pdf.text(`CNPJ ${tecnicoCNPJ}`, 15, 290);*/

                /* const assinaturaImagem = gerarAssinatura(tecnicoNome);
                pdf.addImage(assinaturaImagem, "PNG", 24, 266, 45, 20);
                pdf.text(`-----------------------------------`, 24, 280);
                pdf.text(`${tecnicoNome}`, 24, 285);
                pdf.text(`CNPJ ${tecnicoCNPJ}`, 24, 290); */
                registrarPaginaAssinaturaAvancada();


            }
            await adicionarRodapePagina(cidade, data);
        };

        // ------------------------------------------------------------------------------------------------------------


        // Adicionar uma nova pÃ¡gina para comeÃ§ar a inserir as imagens
        if (imagensDataUrls.length != 0){
        pdf.addPage();

        pdf.setFont("helvetica", "bold");
        pdf.text("ANEXO", 95, 10);
        pdf.setFont("helvetica", "normal");
        // Configura a posiÃ§Ã£o inicial na segunda pÃ¡gina
        // Configura a posiÃ§Ã£o inicial na segunda pÃ¡gina
        // Configura a posiÃ§Ã£o inicial na segunda pÃ¡gina
        let yPosition = 22;
        let positionAnexo = 20;
        let countAnexo = 1;

        // Adicionar cada imagem a partir da segunda pÃ¡gina
        for (const dataUrl of imagensDataUrls) {
            const imgComprimida = await comprimirImagem(dataUrl, 0.7); // 70% de qualidade (Ã³timo equilÃ­brio)

            const img = new Image();
            img.src = imgComprimida;
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
            });

            const imgWidth = img.naturalWidth;
            const imgHeight = img.naturalHeight;

            const maxWidth = 150;
            const maxHeight = 100;
            let width = imgWidth;
            let height = imgHeight;

            if (imgWidth > maxWidth || imgHeight > maxHeight) {
                const widthRatio = maxWidth / imgWidth;
                const heightRatio = maxHeight / imgHeight;
                const scale = Math.min(widthRatio, heightRatio);
                width = imgWidth * scale;
                height = imgHeight * scale;
            }

            if (yPosition + height > 280) {
                pdf.addPage();
                yPosition = 22;
                positionAnexo = 20;
            }

            pdf.text(`Imagem: ${countAnexo}`, 10, positionAnexo);
            pdf.addImage(imgComprimida, "JPEG", 10, yPosition, width, height);

            yPosition += height + 10;
            positionAnexo = yPosition - 5;
            countAnexo += 1;
            }
        }

    } catch (error) {
        console.warn("Erro ao carregar uma ou mais imagens:", error);
    }

    // Salvar PDF e encaminhar para o componente de assinatura
    document.getElementById("loadingPopup").style.display = "flex";

    try {
        const pdfBlob = pdf.output("blob");
        const downloadFilename = `Relatorio_Tecnico_${nome}.pdf`;

        if (window.relatorioSignatureMode === "atribuir") {
            // Atendente: envia para o técnico assinar depois (status pendente)
            await window.enviarRelatorioParaAssinatura({
                pdfBlob,
                nome,
                cpf,
                documentType: "Relatório Técnico - Vistoria",
                tecnicoUserId,
            });
            alert("Relatório enviado para assinatura do técnico responsável.");
        } else if (window.relatorioSignatureComponent) {
            window.relatorioSignatureComponent.config.buildSignedPresentationBlob = async ({ signatureData, originalBlob }) => {
                if (!signatureData || signatureData.valid !== true) {
                    return originalBlob;
                }

                const assinaturaPdfDados = {
                    ...signatureData,
                    signer_document: signatureData.signer_document || tecnicoCNPJ,
                };

                paginasAssinaturaAvancada.forEach((pagina) => {
                    pdf.setPage(pagina);
                    adicionarBlocoAssinaturaAvancadaProfissional(
                        pdf,
                        assinaturaPdfDados,
                        8,
                        233,
                    );
                });

                return pdf.output("blob");
            };

            await window.relatorioSignatureComponent.processGeneratedPdf({
                pdfBlob,
                nome,
                cpf,
                downloadFilename,
            });
        } else {
            // Modelo anterior: desenha a assinatura cursiva nas paginas marcadas
            if (window.relatorioSignatureMode === "classica") {
                adicionarBlocoAssinaturaClassica(
                    pdf,
                    paginasAssinaturaAvancada,
                    tecnicoNome,
                    tecnicoCNPJ,
                );
            }
            pdf.save(downloadFilename);
        }
    } catch (err) {
        console.error("Falha no fluxo do relatório:", err);
        alert(err.message || "Erro ao gerar ou assinar o relatório.");
    } finally {
        document.getElementById("loadingPopup").style.display = "none";
        btn.disabled = false;
        btn.innerText = "Baixar como PDF";
    }
}



async function logo(pdf) {
    try {
        // Definir logo
        const logoURL = "../static/img/logo.png";
        const imgLogo = new Image();
        imgLogo.src = logoURL;

        // Esperar o carregamento da logo
        await new Promise((resolve, reject) => {
            imgLogo.onload = resolve;
            imgLogo.onerror = reject;
        });

        // Adicionar logo no PDF
        pdf.addImage(imgLogo, "PNG", 1, 1, 45, 45);
    } catch (error) {
        console.warn("Logo nÃ£o carregada. Continuando sem logo.");
    }
}

async function comprimirImagem(dataUrl, qualidade = 0.7) {
  return new Promise((resolve) => {
    const img = new Image();
    img.src = dataUrl;
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      resolve(canvas.toDataURL("image/jpeg", qualidade)); // converte e comprime
    };
  });
}


